"""Quality report and publish gate."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jinju_pipeline.clean import CleanResult
from jinju_pipeline.curation import CurationResult
from jinju_pipeline.http import QuotaLedger
from jinju_pipeline.merge import MergeResult
from jinju_pipeline.models import Place, PreviousSnapshot, SourceResult
from jinju_pipeline.raw_store import KST

__all__ = ["GateResult", "build_report", "evaluate_gate", "write_report"]

COMPLETENESS_FIELDS = ("hero_image", "overview", "phone", "hours")
REQUIRED_CATEGORIES = ("sight", "food", "festival")
# Spec §5.7 starts at 0.85 for sight/culture/stay and lets the builder adjust after the first real run.
# 2026-11-04 first run (Jinju city API only, no TourAPI key): sight 0.98, culture 0.65, stay 0.48 —
# heritage lists many tombs/steles and lodging many motels without coordinates. culture/stay are set as
# regression guards about 10 points below that run (see DATA.md); revisit once TourAPI is collected.
COORDS_MIN_BY_CATEGORY = {"sight": 0.85, "culture": 0.55, "stay": 0.40}
DROP_FLOOR = 0.8


def _ratio(n: int, total: int) -> float:
    return round(n / total, 4) if total else 0.0


def _has_coords(p: Place) -> bool:
    return p.lat is not None and p.lng is not None


def build_report(
    run_id: str,
    results: list[SourceResult],
    cleaned: CleanResult,
    merged: MergeResult,
    curated: CurationResult,
    previous: PreviousSnapshot | None,
    ledger: QuotaLedger,
    elapsed_s: float,
    out_of_bbox_final: int,
    reused_streak: int,
    content_hash: str,
    replayed_from: str | None = None,
) -> dict:
    places = curated.places
    total = len(places)
    completeness = {f: _ratio(sum(1 for p in places if getattr(p, f)), total) for f in COMPLETENESS_FIELDS}
    non_course = [p for p in places if p.category != "course"]
    completeness["coords"] = _ratio(sum(_has_coords(p) for p in non_course), len(non_course))

    by_cat: dict[str, list[Place]] = {}
    for p in places:
        by_cat.setdefault(p.category, []).append(p)
    years = Counter(
        str(p.date_year) if p.date_year is not None else "unknown" for p in by_cat.get("festival", [])
    )
    pending = sum(
        1
        for p in places
        for s in p.sources
        if s.source.startswith("tourapi") and s.raw.get("detail_pending")
    )
    return {
        "run_id": run_id,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "out_of_bbox_final": out_of_bbox_final,
        "reused_streak": reused_streak,
        "content_hash": content_hash,
        "replayed_from": replayed_from,  # run_id whose stored raw records were replayed (run --from-raw)
        "sources": [
            {"source": r.source, "status": r.status, "records": len(r.records), "calls": r.calls, "error": r.error}
            for r in results
        ],
        "cleaned_count": len(cleaned.records),
        "dropped": dict(cleaned.dropped),
        "merge": {"pairs": len(merged.log), "by_reason": dict(Counter(e["reason"] for e in merged.log))},
        "final_count": total,
        "category_counts": {c: len(v) for c, v in by_cat.items()},
        "completeness": completeness,
        "coords_by_category": {c: _ratio(sum(_has_coords(p) for p in v), len(v)) for c, v in by_cat.items()},
        "coords_thresholds": dict(COORDS_MIN_BY_CATEGORY),
        "festival_years": dict(sorted(years.items())),
        "detail_pending": pending,
        "quota_used": ledger.used_this_run(),
        "unresolved_curation": [u for u in curated.unresolved if not u.startswith("tags:")],
        "unresolved_tags": [u for u in curated.unresolved if u.startswith("tags:")],
        "elapsed_s": round(elapsed_s, 2),
    }


@dataclass
class GateResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def evaluate_gate(
    report: dict,
    previous: PreviousSnapshot | None,
    *,
    min_first_run: int = 300,
    previous_source_counts: dict[str, int] | None = None,
) -> GateResult:
    """``previous_source_counts``: records per source in the previous published report.json. A source that
    contributed records to the previous DB must still deliver records (ok or reused), otherwise publishing
    would silently drop its places (e.g. TourAPI skipped because DATA_GO_KR_KEY is missing)."""
    failures: list[str] = []
    warnings: list[str] = []
    final = report["final_count"]

    if previous is not None:
        if final < DROP_FLOOR * previous.place_count:
            failures.append(f"final_count {final} < 80% of previous {previous.place_count}")
        current = {s["source"]: s for s in report["sources"]}
        for source, count in sorted((previous_source_counts or {}).items()):
            now = current.get(source)
            if count > 0 and (now is None or now["records"] == 0):
                detail = "missing" if now is None else now["status"] + (f" ({now['error']})" if now["error"] else "")
                failures.append(f"source {source} contributed {count} records to the previous DB "
                                f"but has 0 records in this run: {detail}")
    elif final < min_first_run:
        failures.append(f"final_count {final} < first-run minimum {min_first_run}")

    counts = report["category_counts"]
    for cat in REQUIRED_CATEGORIES:
        if counts.get(cat, 0) < 1:
            failures.append(f"category {cat} has no places")

    for cat, minimum in COORDS_MIN_BY_CATEGORY.items():
        ratio = report["coords_by_category"].get(cat, 0.0)
        if counts.get(cat, 0) == 0:
            warnings.append(f"category {cat} has no records; coords ratio not checked")
        elif ratio < minimum:
            failures.append(f"coords ratio for {cat} {ratio:.2f} < {minimum}")

    if report["out_of_bbox_final"] != 0:
        failures.append(f"out_of_bbox_final = {report['out_of_bbox_final']}")
    if report["unresolved_curation"]:
        failures.append(f"unresolved curation entries: {report['unresolved_curation']}")
    if report.get("unresolved_tags"):
        warnings.append(f"unresolved tags entries: {report['unresolved_tags']}")

    streak = report["reused_streak"]
    if streak >= 2:
        failures.append(f"sources reused from previous run {streak} runs in a row")
    elif streak == 1:
        warnings.append("some sources were reused from the previous run")

    return GateResult(passed=not failures, failures=failures, warnings=warnings)


def _table(headers: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]
    return out + [""]


def write_report(report: dict, gate: GateResult, json_path: Path, md_path: Path) -> None:
    json_path, md_path = Path(json_path), Path(md_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [f"# 품질 리포트 / Quality report ({report['run_id']})", ""]
    md.append(f"- generated_at: {report['generated_at']}")
    md.append(f"- final_count: {report['final_count']} (cleaned {report['cleaned_count']})")
    md.append(f"- quota_used: {report['quota_used']} / elapsed_s: {report['elapsed_s']}")
    md.append(f"- reused_streak: {report['reused_streak']} / out_of_bbox_final: {report['out_of_bbox_final']}")
    md.append(f"- detail_pending: {report['detail_pending']}")
    md.append(f"- content_hash: {report['content_hash']}")
    md.append("")
    md += ["## 소스 / Sources", ""]
    md += _table(
        ["source", "status", "records", "calls", "error"],
        [[s["source"], s["status"], s["records"], s["calls"], s["error"]] for s in report["sources"]],
    )
    md += ["## 드롭 / Dropped", ""]
    md += _table(["reason", "count"], [[k, v] for k, v in report["dropped"].items()])
    md += ["## 병합 / Merge", ""]
    md += _table(
        ["reason", "count"],
        [["(total pairs)", report["merge"]["pairs"]]] + [[k, v] for k, v in report["merge"]["by_reason"].items()],
    )
    md += ["## 카테고리 / Categories", ""]
    md += _table(
        ["category", "count", "coords"],
        [[c, n, report["coords_by_category"].get(c)] for c, n in report["category_counts"].items()],
    )
    md += ["## 결측률 / Completeness (ratio filled)", ""]
    md += _table(["field", "ratio"], [[k, v] for k, v in report["completeness"].items()])
    md += ["## 축제 연도 / Festival years", ""]
    md += _table(["year", "count"], [[k, v] for k, v in report["festival_years"].items()])
    if report["unresolved_curation"] or report.get("unresolved_tags"):
        md += ["## 미해결 큐레이션 / Unresolved curation", ""]
        md += [f"- {u}" for u in report["unresolved_curation"] + report.get("unresolved_tags", [])] + [""]
    md += ["## 게이트 / Gate", "", f"**{'PASS' if gate.passed else 'FAIL'}**", ""]
    thresholds = report.get("coords_thresholds") or COORDS_MIN_BY_CATEGORY
    md += ["- 좌표 보유율 기준(첫 실데이터 후 조정, DATA.md 참조): "
           + ", ".join(f"{c} ≥ {v:.2f}" for c, v in thresholds.items()),
           "  - 근거: 2026-11-04 첫 실행(진주시 API만) sight 0.98 · culture 0.65 · stay 0.48 — 좌표 없는 문화재(묘·비석)·"
           "모텔이 많아 culture/stay는 그보다 약 10%p 낮춘 회귀 감시선(스펙 시작값 0.85)", ""]
    md += [f"- FAIL: {f}" for f in gate.failures] + [f"- WARN: {w}" for w in gate.warnings]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
