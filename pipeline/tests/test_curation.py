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


def test_operational_collection30_draft_has_30_matchable_items(repo_root):
    c = load_curation(repo_root / "pipeline" / "curation")["collection30"]
    assert c["status"] == "draft"
    assert len(c["items"]) == 30 and all(i.get("match") for i in c["items"])
    assert len({i["key"] for i in c["items"]}) == 30


def test_operational_jinju8_fallbacks_and_venues_are_clean(repo_root):
    c = load_curation(repo_root / "pipeline" / "curation")
    for item in c["jinju8"]["items"]:
        assert "근사" not in item["fallback"]["overview"] and "(" not in item["fallback"]["overview"]
    for prog in c["festival_programs"]["items"]:
        assert all(v.get("category") for v in prog["venues"])  # never match festival rows themselves


# ---- operational tags.yaml: indoor only for museum-type rows (review finding C18) ----

NOT_INDOOR_WORDS = ("묘", "비석", "석탑", "봉수대", "고분", "화석산지")


def _p(i, title, category, **kw):
    from jinju_pipeline.merge import normalize_name
    from jinju_pipeline.models import Place

    return Place(id=f"jh-t{i}", category=category, title=title, title_norm=normalize_name(title),
                 geo_status="ok", lat=35.18, lng=128.1, updated_at="2026-11-04", **kw)


def _operational_tags(repo_root):
    return {"tags": load_curation(repo_root / "pipeline" / "curation")["tags"]}


@pytest.mark.parametrize("title, category", [
    ("국립진주박물관", "culture"),
    ("진주남강유등전시관", "culture"),
    ("진주시립이성자미술관", "culture"),
    ("진주익룡발자국전시관", "sight"),
    ("향토민속관", "culture"),
    ("유등체험관", "culture"),
    ("진주목공예전수관", "culture"),
    ("경남수학문화관 진주수학체험센터", "culture"),
    ("OO과학관", "culture"),
    ("OO기념관", "culture"),
])
def test_operational_tags_indoor_for_museum_type_rows(repo_root, title, category):
    p = apply_curation([_p(1, title, category)], _operational_tags(repo_root)).places[0]
    assert "indoor" in p.tags


@pytest.mark.parametrize("title", [
    "성재처사김해허공휘관지묘(誠齋處士金海許公諱寬之墓)",
    "전의관김공정식시혜불망비(前議官金公正植施惠不忘碑)",
    "관찰사조공시영청덕선정비(觀察使曺公始永淸德善政碑)",
    "진주 묘엄사지 삼층석탑",
    "망진산 봉수대",
    "진주 OO 비석군",
    "진주 OO리 고분군",
    "진주 정촌면 뿌리산단 공룡 화석산지",
    "진주 문산성당(晋州 文山聖堂)",
    "박효근 효행관련고문서(朴孝根 孝行關聯古文書)",
])
def test_operational_tags_no_blanket_indoor_for_culture(repo_root, title):
    p = apply_curation([_p(1, title, "culture")], _operational_tags(repo_root)).places[0]
    assert "indoor" not in p.tags


def test_operational_tags_exhibition_keyword_does_not_hit_place_names(repo_root):
    p = apply_curation([_p(1, "초전시민체육공원", "sight")], _operational_tags(repo_root)).places[0]
    assert "indoor" not in p.tags and "outdoor" in p.tags


def test_operational_tags_never_mark_outdoor_heritage_indoor(repo_root):
    """Contract: even a museum-type word in the title cannot make a tomb/stele/pagoda/fossil site indoor."""
    titles = ["OO박물관 앞 석탑", "OO기념관 묘역", "화석산지 전시관 터", "OO 고분 전시", "봉수대 기념관 비석"]
    places = [_p(i, t, "culture") for i, t in enumerate(titles)]
    for p in apply_curation(places, _operational_tags(repo_root)).places:
        if any(w in p.title for w in NOT_INDOOR_WORDS):
            assert "indoor" not in p.tags, p.title
