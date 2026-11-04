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
COORDS_GATED = ("sight", "culture", "stay")
COORDS_MIN = 0.85
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


def evaluate_gate(report: dict, previous: PreviousSnapshot | None, *, min_first_run: int = 300) -> GateResult:
    failures: list[str] = []
    warnings: list[str] = []
    final = report["final_count"]

    if previous is not None:
        if final < DROP_FLOOR * previous.place_count:
            failures.append(f"final_count {final} < 80% of previous {previous.place_count}")
    elif final < min_first_run:
        failures.append(f"final_count {final} < first-run minimum {min_first_run}")

    counts = report["category_counts"]
    for cat in REQUIRED_CATEGORIES:
        if counts.get(cat, 0) < 1:
            failures.append(f"category {cat} has no places")

    for cat in COORDS_GATED:
        ratio = report["coords_by_category"].get(cat, 0.0)
        if counts.get(cat, 0) == 0:
            warnings.append(f"category {cat} has no records; coords ratio not checked")
        elif ratio < COORDS_MIN:
            failures.append(f"coords ratio for {cat} {ratio:.2f} < {COORDS_MIN}")

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
    md += [f"- FAIL: {f}" for f in gate.failures] + [f"- WARN: {w}" for w in gate.warnings]
    md_path.write_text("\n".join(md) + "\n", encoding="utf-8")
