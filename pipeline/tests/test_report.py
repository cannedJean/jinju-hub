from __future__ import annotations

from collections import Counter
from datetime import date

from jinju_pipeline.clean import CleanResult
from jinju_pipeline.curation import CurationResult
from jinju_pipeline.merge import MergeResult
from jinju_pipeline.models import CleanRecord, Place, PreviousSnapshot, SourceResult
from jinju_pipeline.report import GateResult, build_report, evaluate_gate, write_report
from tests.helpers import NOW


def _rec(source="tourapi.area", pending=False) -> CleanRecord:
    return CleanRecord(source=source, source_id="1", category="sight", title="t", geo_status="ok",
                       raw={"detail_pending": True} if pending else {}, fetched_at=NOW)


def _place(i, cat, lat=35.18, lng=128.1, **kw) -> Place:
    return Place(id=f"jh-{i}", category=cat, title=f"t{i}", title_norm=f"t{i}", geo_status="ok",
                 lat=lat, lng=lng, updated_at="2026-11-04", **kw)


class _Ledger:
    def used_this_run(self):
        return 7

    def used_by_source(self):
        return {"tourapi.area": 7}


def _prev(n):
    return PreviousSnapshot(generated_at=NOW, place_count=n, source_index={}, id_order={}, aliases={},
                            raw_by_source={}, modified_by_key={}, detail_pending_keys=set())


def _build(places, unresolved=(), previous=None, **kw):
    results = [SourceResult(source="tourapi.area", status="ok", records=[], calls=3)]
    cleaned = CleanResult(records=[_rec()] * 2, dropped=Counter({"no_title": 2}))
    merged = MergeResult(places=places, aliases={}, log=[{"a": "x", "b": "y", "reason": "same_name"}])
    curated = CurationResult(places=places, badges=[], unresolved=list(unresolved), festival_programs={})
    args = dict(out_of_bbox_final=0, reused_streak=0, content_hash="abc")
    args.update(kw)
    return build_report("run1", results, cleaned, merged, curated, previous, _Ledger(), 1.5, **args)


def _healthy_places():
    return [_place(1, "sight"), _place(2, "food"), _place(3, "festival", date_year=2026)]


def test_build_report_keys_and_values():
    places = _healthy_places()
    places[0] = _place(1, "sight", hero_image="h.jpg", phone="1", sources=[_rec(pending=True)])
    places.append(_place(4, "course", lat=None, lng=None))
    rep = _build(places, unresolved=["jinju8:x", "tags:y"])
    assert rep["final_count"] == 4
    assert rep["category_counts"]["sight"] == 1
    assert rep["completeness"]["coords"] == 1.0  # course excluded
    assert rep["completeness"]["hero_image"] == 0.25
    assert rep["coords_by_category"]["course"] == 0.0
    assert rep["festival_years"] == {"2026": 1}
    assert rep["detail_pending"] == 1
    assert rep["merge"] == {"pairs": 1, "by_reason": {"same_name": 1}}
    assert rep["dropped"] == {"no_title": 2}
    assert rep["quota_used"] == 7
    assert rep["unresolved_curation"] == ["jinju8:x"]
    assert rep["unresolved_tags"] == ["tags:y"]
    assert rep["sources"][0]["source"] == "tourapi.area"


def test_gate_passes_on_healthy_report():
    g = evaluate_gate(_build(_healthy_places()), _prev(3))
    assert g.passed and g.failures == []


def test_gate_fails_on_drop_over_20pct():
    rep = _build(_healthy_places())
    rep["final_count"] = 390
    assert not evaluate_gate(rep, _prev(500)).passed
    rep["final_count"] = 400
    assert evaluate_gate(rep, _prev(500)).passed


def test_gate_first_run_min():
    rep = _build(_healthy_places())
    rep["final_count"] = 6
    assert evaluate_gate(rep, None, min_first_run=5).passed
    assert not evaluate_gate(rep, None, min_first_run=7).passed


def test_gate_fails_on_low_coords_for_sight():
    rep = _build(_healthy_places())
    rep["coords_by_category"]["sight"] = 0.80
    g = evaluate_gate(rep, _prev(3))
    assert not g.passed and any("sight" in f for f in g.failures)


def test_missing_category_coords_is_warning():
    rep = _build(_healthy_places())
    g = evaluate_gate(rep, _prev(3))
    assert g.passed and any("culture" in w for w in g.warnings)


def test_food_coords_not_gated():
    rep = _build(_healthy_places())
    rep["coords_by_category"]["food"] = 0.5
    assert evaluate_gate(rep, _prev(3)).passed


def test_required_categories():
    rep = _build([_place(1, "sight"), _place(2, "food")])
    g = evaluate_gate(rep, _prev(2))
    assert not g.passed and any("festival" in f for f in g.failures)


def test_reused_streak_warning_then_failure():
    g1 = evaluate_gate(_build(_healthy_places(), reused_streak=1), _prev(3))
    assert g1.passed and g1.warnings
    g2 = evaluate_gate(_build(_healthy_places(), reused_streak=2), _prev(3))
    assert not g2.passed


def test_out_of_bbox_final_fails():
    g = evaluate_gate(_build(_healthy_places(), out_of_bbox_final=1), _prev(3))
    assert not g.passed


def test_unresolved_curation_fails():
    rep = _build(_healthy_places(), unresolved=["jinju8:foo"])
    g = evaluate_gate(rep, _prev(3))
    assert not g.passed and any("unresolved" in f for f in g.failures)


def test_unresolved_tags_only_warns():
    rep = _build(_healthy_places(), unresolved=["tags:foo"])
    g = evaluate_gate(rep, _prev(3))
    assert g.passed and any("tags" in w for w in g.warnings)


def test_report_md_contains_tables(tmp_path):
    rep = _build(_healthy_places())
    for gate, word in ((evaluate_gate(rep, _prev(3)), "PASS"), (GateResult(False, ["boom"], []), "FAIL")):
        write_report(rep, gate, tmp_path / "r.json", tmp_path / "r.md")
        md = (tmp_path / "r.md").read_text(encoding="utf-8")
        assert "| source |" in md and word in md
    assert '"run_id": "run1"' in (tmp_path / "r.json").read_text(encoding="utf-8")


def test_coords_thresholds_per_category(tmp_path):
    # Adjusted after the first real run (2026-11-04, city API only): culture 0.55, stay 0.40.
    places = _healthy_places() + [_place(4, "culture"), _place(5, "stay")]
    rep = _build(places)
    assert rep["coords_thresholds"] == {"sight": 0.85, "culture": 0.55, "stay": 0.40}
    rep["coords_by_category"].update(culture=0.60, stay=0.45)
    assert evaluate_gate(rep, _prev(5)).passed
    rep["coords_by_category"].update(culture=0.50, stay=0.35)
    g = evaluate_gate(rep, _prev(5))
    assert not g.passed
    assert any("culture" in f and "0.55" in f for f in g.failures)
    assert any("stay" in f and "0.4" in f for f in g.failures)
    write_report(rep, g, tmp_path / "r.json", tmp_path / "r.md")
    md = (tmp_path / "r.md").read_text(encoding="utf-8")
    assert "culture ≥ 0.55" in md and "회귀 감시선" in md
