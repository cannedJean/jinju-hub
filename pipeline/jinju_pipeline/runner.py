"""End-to-end run: collect -> clean -> merge -> curate -> report/gate -> load (only when the gate passes).

``from_raw`` replays the raw records stored in the previous places.db (``place_sources.raw_json``, the same
records a failed source falls back to) instead of collecting: an offline rebuild after a clean/merge/curation
change. TourAPI detail responses live only there (the raw store keeps list pages), so it is the complete copy.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Literal

import httpx
from pydantic import BaseModel

from jinju_pipeline.clean import clean_all
from jinju_pipeline.collect import collect_all, default_sources, replay_sources
from jinju_pipeline.curation import apply_curation, collection_source_keys, load_curation
from jinju_pipeline.http import ConfigError, QuotaLedger, make_client
from jinju_pipeline.load import compute_content_hash, read_previous, write_places_db
from jinju_pipeline.merge import load_overrides, merge_records
from jinju_pipeline.models import PreviousSnapshot, SourceResult
from jinju_pipeline.raw_store import KST, RawStore, new_run_id
from jinju_pipeline.region import load_region
from jinju_pipeline.report import GateResult, build_report, evaluate_gate, write_report
from jinju_pipeline.settings import Settings
from jinju_pipeline.sources.base import Source, make_context
from jinju_pipeline.state import RefreshState, advance_synced_at, read_state, state_path_for, write_state

log = logging.getLogger(__name__)

__all__ = ["run_pipeline", "next_id_order", "reused_streak_for", "previous_source_counts"]


def _write_jsonl(path: Path, rows: Iterable) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            line = row.model_dump_json() if isinstance(row, BaseModel) else json.dumps(row, ensure_ascii=False)
            f.write(line + "\n")


def reused_streak_for(results: list[SourceResult], prior_streak: int) -> int:
    """Consecutive runs (including this one) that reused previous data for some source."""
    if not any(r.status == "reused_previous" for r in results):
        return 0
    return prior_streak + 1


def previous_source_counts(report_path: Path, previous: PreviousSnapshot | None) -> dict[str, int]:
    """Records per source in the previous published report.json (fallback: the snapshot's raw records)."""
    if previous is None:
        return {}
    try:
        data = json.loads(Path(report_path).read_text(encoding="utf-8"))
        return {str(s["source"]): int(s.get("records") or 0) for s in data["sources"]}
    except (OSError, ValueError, TypeError, KeyError) as e:
        log.warning("previous report %s unavailable (%s); using the snapshot's source records", report_path, e)
        return {source: len(records) for source, records in previous.raw_by_source.items()}


def _refuse_network(request: httpx.Request) -> httpx.Response:
    raise RuntimeError(f"run --from-raw must not touch the network: {request.url.host}")


def next_id_order(previous: PreviousSnapshot | None, place_ids: list[str]) -> dict[str, int]:
    """Previous issue order kept as-is; ids new to this run get the next sequence numbers."""
    order = dict(previous.id_order) if previous else {}
    seq = max(order.values(), default=-1) + 1
    for pid in place_ids:
        if pid not in order:
            order[pid] = seq
            seq += 1
    return order


async def run_pipeline(
    settings: Settings,
    *,
    incremental: bool,
    today: date,
    now: datetime,
    sources: list[Source] | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    until: Literal["clean", "merge"] | None = None,
    from_raw: bool = False,
) -> tuple[dict, GateResult]:
    started = time.perf_counter()
    run_id = new_run_id(now)
    work = Path(settings.work_dir) / run_id
    region = load_region(settings.region_path)
    previous_db = settings.previous_db or settings.output_db
    previous = read_previous(previous_db)
    if from_raw:
        if previous is None:
            raise ConfigError(f"--from-raw replays the previous places.db, which does not exist: {previous_db}")
        sources = replay_sources(previous)
        transport = httpx.MockTransport(_refuse_network)
    state = read_state(state_path_for(previous_db))
    prior_streak = state.reused_streak if state else (previous.reused_streak if previous else 0)
    prior_synced = state.synced_at if state else {}
    previous_report = settings.previous_db.with_name("report.json") if settings.previous_db else settings.output_report
    cur = load_curation(settings.curation_dir)

    ledger = QuotaLedger(Path(settings.state_dir) / "quota.json", settings.daily_quota, settings.run_quota,
                         today=today)
    store = RawStore(settings.raw_dir, run_id)
    async with make_client(transport=transport) as client:
        ctx = make_context(
            client=client, store=store, ledger=ledger, settings=settings, region=region, previous=previous,
            incremental=incremental, today=today, collection_keys=collection_source_keys(cur),
            synced_at=prior_synced,
        )
        try:
            results = await collect_all(sources if sources is not None else default_sources(settings), ctx)
        finally:
            ledger.save()
            store.finalize()
    for r in results:
        log.info("source %s: %s, %d records, %d calls", r.source, r.status, len(r.records), r.calls)

    cleaned = clean_all([rec for r in results for rec in r.records], region)
    _write_jsonl(work / "clean.jsonl", cleaned.records)
    if until == "clean":
        report = {"run_id": run_id, "stage": "clean", "cleaned_count": len(cleaned.records),
                  "dropped": dict(cleaned.dropped)}
        return report, GateResult(passed=True, warnings=["stopped after clean; nothing published"])

    overrides = load_overrides(Path(settings.curation_dir) / "merge_overrides.yaml")
    now_iso = now.astimezone(KST).isoformat(timespec="seconds")
    merged = merge_records(cleaned.records, overrides, previous, now_iso)
    _write_jsonl(work / "merge.jsonl", merged.places)
    _write_jsonl(work / "merge_log.jsonl", merged.log)
    if until == "merge":
        report = {"run_id": run_id, "stage": "merge", "cleaned_count": len(cleaned.records),
                  "merged_count": len(merged.places), "merge_pairs": len(merged.log)}
        return report, GateResult(passed=True, warnings=["stopped after merge; nothing published"])

    curated = apply_curation(merged.places, cur)
    out_of_bbox_final = sum(
        1 for p in curated.places if p.lat is not None and not region.contains(p.lat, p.lng)
    )
    # A replay is not a collection: it neither counts as reuse nor advances any source's watermark.
    streak = prior_streak if from_raw else reused_streak_for(results, prior_streak)
    synced = dict(prior_synced) if from_raw else advance_synced_at(prior_synced, results, now)
    content_hash = compute_content_hash(curated.places, merged.aliases, curated.badges)
    report = build_report(
        run_id, results, cleaned, merged, curated, previous, ledger, time.perf_counter() - started,
        out_of_bbox_final, streak, content_hash, replayed_from=previous.data_version if from_raw else None,
    )
    gate = evaluate_gate(report, previous, min_first_run=settings.gate_min_first_run,
                         previous_source_counts=previous_source_counts(previous_report, previous))

    # The work copy is always written first; the published report only accompanies a published db.
    write_report(report, gate, work / "report.json", work / "report.md")
    if gate.passed:
        meta = {
            "data_version": run_id,
            "generated_at": now_iso,
            "region": region.model_dump_json(),
            "source_counts": json.dumps({r.source: len(r.records) for r in results}, ensure_ascii=False),
            "category_counts": json.dumps(report["category_counts"], ensure_ascii=False),
            "festival_programs": json.dumps(curated.festival_programs, ensure_ascii=False),
            "reused_streak": str(streak),
            "content_hash": content_hash,
        }
        id_order = next_id_order(previous, [p.id for p in curated.places])
        write_places_db(settings.output_db, curated.places, merged.aliases, curated.badges, meta, id_order)
        write_report(report, gate, settings.output_report, work / "report.md")
        write_state(state_path_for(settings.output_db), RefreshState(reused_streak=streak, synced_at=synced))
    return report, gate
