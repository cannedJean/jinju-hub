"""End-to-end run: collect -> clean -> merge -> curate -> report/gate -> load (only when the gate passes)."""
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
from jinju_pipeline.collect import collect_all, default_sources
from jinju_pipeline.curation import apply_curation, collection_source_keys, load_curation
from jinju_pipeline.http import QuotaLedger, make_client
from jinju_pipeline.load import compute_content_hash, read_previous, write_places_db
from jinju_pipeline.merge import load_overrides, merge_records
from jinju_pipeline.models import PreviousSnapshot, SourceResult
from jinju_pipeline.raw_store import KST, RawStore, new_run_id
from jinju_pipeline.region import load_region
from jinju_pipeline.report import GateResult, build_report, evaluate_gate, write_report
from jinju_pipeline.settings import Settings
from jinju_pipeline.sources.base import Source, make_context

log = logging.getLogger(__name__)

__all__ = ["run_pipeline", "next_id_order", "reused_streak_for"]


def _write_jsonl(path: Path, rows: Iterable) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            line = row.model_dump_json() if isinstance(row, BaseModel) else json.dumps(row, ensure_ascii=False)
            f.write(line + "\n")


def reused_streak_for(results: list[SourceResult], previous: PreviousSnapshot | None) -> int:
    """Consecutive runs (including this one) that reused previous data for some source."""
    if not any(r.status == "reused_previous" for r in results):
        return 0
    return (previous.reused_streak if previous else 0) + 1


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
) -> tuple[dict, GateResult]:
    started = time.perf_counter()
    run_id = new_run_id(now)
    work = Path(settings.work_dir) / run_id
    region = load_region(settings.region_path)
    previous = read_previous(settings.previous_db or settings.output_db)
    cur = load_curation(settings.curation_dir)

    ledger = QuotaLedger(Path(settings.state_dir) / "quota.json", settings.daily_quota, settings.run_quota,
                         today=today)
    store = RawStore(settings.raw_dir, run_id)
    async with make_client(transport=transport) as client:
        ctx = make_context(
            client=client, store=store, ledger=ledger, settings=settings, region=region, previous=previous,
            incremental=incremental, today=today, collection_keys=collection_source_keys(cur),
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
    streak = reused_streak_for(results, previous)
    content_hash = compute_content_hash(curated.places, merged.aliases, curated.badges)
    report = build_report(
        run_id, results, cleaned, merged, curated, previous, ledger, time.perf_counter() - started,
        out_of_bbox_final, streak, content_hash,
    )
    gate = evaluate_gate(report, previous, min_first_run=settings.gate_min_first_run)

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
    return report, gate
