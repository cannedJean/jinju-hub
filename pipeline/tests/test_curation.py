from copy import deepcopy

import pytest

from jinju_pipeline.curation import (
    BadgeDef,
    CurationResult,
    apply_curation,
    collection_source_keys,
    load_curation,
)


def res_badge(res, badge_id):
    return next(b for b in res.badges if b.id == badge_id)


def test_jinju8_resolves_or_falls_back(places_fixture, cur):
    res = apply_curation(places_fixture, cur)
    ranks = sorted(p.jinju8_rank for p in res.places if p.jinju8_rank)
    assert ranks == list(range(1, 9)) and not res.unresolved


def test_jinju8_match_and_fallback_sources(places_fixture, cur):
    res = apply_curation(places_fixture, cur)
    by_rank = {p.jinju8_rank: p for p in res.places if p.jinju8_rank}
    assert by_rank[1].title == "촉석루"  # matched real place, not a fallback
    assert by_rank[8].title == "진양호 전망대"  # matched by title + near
    fb = by_rank[2]
    assert fb.id == "jh-cur-2" and fb.sources[0].source == "curation"
    assert fb.geo_status == "ok" and 35.05 <= fb.lat <= 35.33 and 127.93 <= fb.lng <= 128.30
    assert len(res.places) == len(places_fixture) + 6
    assert all(p.is_collection for p in by_rank.values())


def test_input_places_not_mutated(places_fixture, cur):
    before = [p.model_dump() for p in places_fixture]
    apply_curation(places_fixture, cur)
    assert [p.model_dump() for p in places_fixture] == before


def test_tags_defaults_and_keywords(places_fixture, cur):
    by = {p.title: p for p in apply_curation(places_fixture, cur).places}
    assert "indoor" in by["국립진주박물관"].tags and "local_food" in by["하연옥"].tags
    assert "outdoor" in by["진주성"].tags
    assert "night_view" in by["촉석루"].tags and "night_view" in by["진주교"].tags
    assert "night_view" not in by["하연옥"].tags


def test_badges_six_with_required(places_fixture, cur):
    res = apply_curation(places_fixture, cur)
    b = {x.id: x for x in res.badges}
    assert isinstance(res.badges[0], BadgeDef) and isinstance(res, CurationResult)
    assert [b[k].required for k in ["first_light", "jinju8", "food_explorer", "history_walk", "night_namgang", "festival_guest"]] == [1, 8, 3, 3, 2, 1]
    assert [x.label for x in res.badges] == ["첫 등불", "진주8경", "맛 탐험가", "역사 산책", "밤의 남강", "축제 손님"]
    assert len(b["jinju8"].eligible_place_ids) == 8
    assert len(b["history_walk"].eligible_place_ids) >= 3
    assert len(b["night_namgang"].eligible_place_ids) >= 2


def test_festival_venue_links(places_fixture, cur):
    res = apply_curation(places_fixture, cur)
    fest = next(p for p in res.places if "유등" in p.title and p.category == "festival")
    assert fest.venue_place_ids and all("festival_venue" in q.tags for q in res.places if q.id in fest.venue_place_ids)
    w = res_badge(res, "festival_guest").festival_windows[0]
    assert w["start"] == "2026-10-03" and w["end"] == "2026-10-18"
    assert w["festival_id"] == fest.id and w["venue_place_ids"] == fest.venue_place_ids
    assert res.festival_programs[fest.id]


def test_festival_without_dates_excluded_from_badge_windows(places_fixture, cur):
    for p in places_fixture:
        if p.category == "festival":
            p.start_date = p.end_date = None
            p.date_undecided = True
    res = apply_curation(places_fixture, cur)
    assert res_badge(res, "festival_guest").festival_windows == []


@pytest.fixture
def cur_with_bogus_match(cur):
    c = deepcopy(cur)
    c["collection30"]["items"].append({"key": "bogus", "label": "없음", "match": {"title_contains": "없는장소"}})
    return c


def test_unresolved_reported(cur_with_bogus_match, places_fixture):
    assert apply_curation(places_fixture, cur_with_bogus_match).unresolved == ["collection30:없는장소"]


def test_collection_source_keys(cur):
    c = deepcopy(cur)
    c["collection30"]["items"].append({"key": "x", "label": "x", "source_keys": ["tourapi:1", "jinju_city:2"]})
    assert collection_source_keys(c) == {"tourapi:1", "jinju_city:2"}
    assert collection_source_keys(cur) == set()


def test_collection_source_keys_mark_places(places_fixture, cur):
    c = deepcopy(cur)
    target = places_fixture[3]
    c["collection30"]["items"].append({"key": "x", "label": "x", "source_keys": ["tourapi:777"]})
    from jinju_pipeline.models import CleanRecord
    from datetime import datetime
    target.sources = [CleanRecord(source="tourapi", source_id="777", category="food", title=target.title,
                                  geo_status="ok", fetched_at=datetime(2026, 11, 4))]
    res = apply_curation(places_fixture, c)
    assert next(p for p in res.places if p.id == target.id).is_collection


def test_operational_yaml_loads(repo_root):
    c = load_curation(repo_root / "pipeline" / "curation")
    assert len(c["jinju8"]["items"]) == 8 and len(c["badges"]["items"]) == 6
    assert c["jinju8"]["source_url"].startswith("https://www.jinju.go.kr")
