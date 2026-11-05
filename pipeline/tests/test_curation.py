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


def _src(source, raw):
    from datetime import datetime

    from jinju_pipeline.models import CleanRecord

    return CleanRecord(source=source, source_id="1", category="sight", title="t", geo_status="ok", raw=raw,
                       fetched_at=datetime(2026, 11, 4))


@pytest.mark.parametrize("source, raw", [
    ("jinju_city.tourinfo", {"category": "극장"}),
    ("jinju_city.tourinfo", {"category": "박물관"}),
    ("jinju_city.tourinfo", {"category": "공연장"}),
    ("tourapi.area", {"list": {"contenttypeid": "14"}}),
])
def test_operational_source_category_marks_indoor_and_drops_outdoor(repo_root, source, raw):
    p = apply_curation([_p(1, "어떤 시설", "sight", sources=[_src(source, raw)])], _operational_tags(repo_root)).places[0]
    assert "indoor" in p.tags and "outdoor" not in p.tags  # M2: never both


@pytest.mark.parametrize("source, raw", [
    ("jinju_city.tourinfo", {"category": "일반명소"}),
    ("tourapi.area", {"list": {"contenttypeid": "12"}}),
    ("jinju_city.heritage", {"category": "박물관"}),  # rule is per source
])
def test_operational_source_category_other_values_stay_outdoor(repo_root, source, raw):
    p = apply_curation([_p(1, "어떤 시설", "sight", sources=[_src(source, raw)])], _operational_tags(repo_root)).places[0]
    assert "indoor" not in p.tags and "outdoor" in p.tags


@pytest.mark.parametrize("title", ["경상남도교육청 과학교육원", "OO 갤러리", "갤러리아백화점 진주점", "OO 프리미엄 아울렛",
                                   "롯데몰 진주점", "롯데시네마 진주", "메가박스 진주", "CGV 진주", "OO영화관",
                                   "중앙지하도상가", "OO 문화예술회관", "OO 수학체험센터"])
def test_operational_keywords_for_indoor_facilities(repo_root, title):
    p = apply_curation([_p(1, title, "sight")], _operational_tags(repo_root)).places[0]
    assert "indoor" in p.tags and "outdoor" not in p.tags


@pytest.mark.parametrize("title, raw", [("진주 야외극장", {"category": "극장"}), ("OO 야외전시장", {})])
def test_operational_outdoor_word_vetoes_indoor(repo_root, title, raw):
    p = apply_curation([_p(1, title, "sight", sources=[_src("jinju_city.tourinfo", raw)])],
                       _operational_tags(repo_root)).places[0]
    assert "indoor" not in p.tags and "outdoor" in p.tags


@pytest.mark.parametrize("title", ["OO박물관 앞 석탑", "OO기념관 묘역", "화석산지 전시관 터", "OO 고분 전시",
                                   "봉수대 기념관", "OO비(碑) 전시관", "진주성 산성 체험관",
                                   "야외전시장"])
def test_operational_never_indoor_words_veto_keywords(repo_root, title):
    p = apply_curation([_p(1, title, "culture")], _operational_tags(repo_root)).places[0]
    assert "indoor" not in p.tags


@pytest.mark.parametrize("title, category", [("아비꼬롯데몰진주점", "food"), ("유니클로 롯데몰 진주점", "shopping"),
                                             ("솔하우스&갤러리", "stay")])
def test_operational_indoor_rules_skip_mall_tenants(repo_root, title, category):
    p = apply_curation([_p(1, title, category)], _operational_tags(repo_root)).places[0]
    assert "indoor" not in p.tags


def test_local_food_keywords_still_tag_food(repo_root):
    p = apply_curation([_p(1, "진주냉면", "food")], _operational_tags(repo_root)).places[0]
    assert "local_food" in p.tags


def test_manual_tag_by_id():
    c = {}
    c["tags"] = {"manual": [{"match": {"id": "jh-t2", "title_contains": "센터"}, "tags": ["indoor"]}]}
    places = [_p(1, "센터", "sight"), _p(2, "센터", "sight")]
    res = apply_curation(places, c)
    assert ["indoor" in p.tags for p in res.places] == [False, True] and not res.unresolved
    c["tags"]["manual"][0]["match"]["id"] = "jh-nope"
    assert apply_curation(places, c).unresolved == ["tags:센터"]


def test_operational_manual_indoor_ids_resolve(repo_root):
    """The manual indoor entries name stable place ids that exist in the published DB."""
    import sqlite3

    tags = _operational_tags(repo_root)["tags"]
    entries = [e for e in tags["manual"] if "indoor" in e["tags"]]
    assert len(entries) >= 3 and all(e["match"].get("id") for e in entries)
    db = repo_root / "backend" / "app" / "data" / "places.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        for e in entries:
            row = con.execute("select title from places where id = ?", (e["match"]["id"],)).fetchone()
            assert row and e["match"]["title_contains"] in row[0], e
    finally:
        con.close()


def test_published_db_has_no_outdoor_heritage_tagged_indoor(repo_root):
    """M5 contract on the built DB: no tomb, stele, beacon, fortress, pagoda, burial mound or fossil site
    carries the indoor tag, and indoor never comes with outdoor."""
    import json
    import re
    import sqlite3

    db = repo_root / "backend" / "app" / "data" / "places.db"
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        rows = [(t, json.loads(tags)) for t, tags in con.execute("select title, tags from places")]
    finally:
        con.close()
    indoor = [(t, tags) for t, tags in rows if "indoor" in tags]
    assert 30 <= len(indoor) <= 60, len(indoor)
    bad = [t for t, _ in indoor if re.search(r"묘|비\(|봉수대|산성|석탑|고분|화석", t)]
    assert bad == []
    assert [t for t, tags in indoor if "outdoor" in tags] == []
