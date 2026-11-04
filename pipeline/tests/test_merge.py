from jinju_pipeline.merge import (haversine_m, load_overrides, match_reason, merge_records,
                                  normalize_name)
from tests.helpers import NOW, city, rec, snapshot_from, snapshot_with, tour, tour2

NOW_ISO = NOW.isoformat()


def M(records, overrides=None, prev=None):
    return merge_records(records, overrides or {}, prev, NOW_ISO)


def test_normalize_name():
    assert normalize_name("진주성 (촉석루)") == "진주성"
    assert normalize_name("하연옥 본점") == normalize_name("하연옥")
    assert normalize_name("경상남도 진주박물관") == "진주박물관"


def test_haversine():
    assert 100 < haversine_m(35.19, 128.08, 35.191, 128.08) < 120


def test_match_same_name_within_300m():
    assert match_reason(rec("국립진주박물관", 35.1890, 128.0790), rec("국립 진주 박물관", 35.1905, 128.0800)) == "same_name"


def test_no_match_far_apart():
    assert match_reason(rec("중앙시장", 35.19, 128.08), rec("중앙시장", 35.25, 128.20)) is None


def test_prefix_strip_makes_same_name():
    assert match_reason(rec("진주남강유등전시관", 35.1880, 128.0890), rec("남강유등전시관", 35.1881, 128.0891)) == "same_name"


def test_match_fuzzy():
    assert match_reason(rec("남강 유등 전시관", 35.1880, 128.0890), rec("남강 유등 전시관 매표소", 35.1881, 128.0891)) == "fuzzy_name"


def test_same_phone():
    a = rec("가나식당", 35.19, 128.08, cat="food", phone="055-741-1234")
    b = rec("전혀다른이름", 35.192, 128.082, cat="food", phone="0557411234", source="tourapi.area")
    assert match_reason(a, b) == "same_phone"


def test_same_phone_within_one_source_is_not_evidence():
    # Jinju city lists the managing department's number (e.g. 석갑산/숙호산 share 055-749-5561).
    a = rec("석갑산", 35.19, 128.08, phone="055-749-5561")
    b = rec("숙호산", 35.192, 128.082, phone="055-749-5561")
    assert match_reason(a, b) is None


def test_shared_department_phone_does_not_chain_merges():
    # 055-749-5312 is shared by ~580 heritage/tourinfo records in the real data.
    recs = [rec(f"비석{i}", 35.19 + i * 0.002, 128.08, cat="culture", phone="055-749-5312",
                source="jinju_city.heritage", source_id=f"h{i}") for i in range(3)]
    recs.append(rec("다른이름 정자", 35.19, 128.08, cat="sight", phone="055-749-5312",
                    source="tourapi.area", source_id="t1"))
    assert match_reason(recs[0], recs[3], shared_phones=frozenset({"0557495312"})) is None
    assert len(M(recs).places) == 4


def test_no_coords_same_name_addr():
    a = rec("가나식당", None, None, cat="food", addr="진주시 중앙로 1")
    b = rec("가나식당", 35.19, 128.08, cat="food", addr="진주시 중앙로1")
    assert match_reason(a, b) == "same_name_addr"
    assert match_reason(a, rec("가나식당", 35.19, 128.08, cat="food", addr="다른주소")) is None


def test_cross_category_blocked():
    assert match_reason(rec("촉석루", 35.19, 128.08, cat="food"), rec("촉석루", 35.19, 128.08, cat="sight")) is None


def test_sight_culture_cross_allowed():
    assert match_reason(rec("촉석루", 35.19, 128.08, cat="culture"), rec("촉석루", 35.19, 128.08, cat="sight")) == "same_name"


def test_field_priority_city_hours_tour_overview():
    p = M([city("A", hours="09:00~18:00", overview="짧음"), tour("A", hours="상시", overview="긴 개요" * 10)]).places[0]
    assert p.hours == "09:00~18:00" and p.overview.startswith("긴 개요") and len(p.sources) == 2


def test_images_union_city_first():
    from jinju_pipeline.models import ImageRef
    ci = [ImageRef(url="http://x/1.jpg", source="jinju_city.tourinfo", license="c")]
    ti = [ImageRef(url="http://x/2.jpg", source="tourapi.area", license="t"),
          ImageRef(url="http://x/1.jpg", source="tourapi.area", license="t")]
    p = M([tour("A", images=ti), city("A", images=ci)]).places[0]
    assert [i.url for i in p.images] == ["http://x/1.jpg", "http://x/2.jpg"]
    assert p.hero_image == "http://x/1.jpg"


def test_id_stable_across_runs():
    r1 = M([city("A"), tour("A")]).places[0].id
    prev = snapshot_from(M([city("A"), tour("A")]))
    r2 = M([city("A"), tour("A"), tour2("A")], prev=prev).places[0].id
    assert r1 == r2 and r1.startswith("jh-")


def test_merge_of_two_existing_places_creates_alias():
    prev = snapshot_with({"jinju_city.tourinfo:1": "jh-aaa", "tourapi.area:9": "jh-bbb"}, order=["jh-aaa", "jh-bbb"])
    res = M([city("A", id="1"), tour("A", id="9")], prev=prev)
    assert res.places[0].id == "jh-aaa" and res.aliases == {"jh-bbb": "jh-aaa"}


def test_id_order_not_string_sort():
    prev = snapshot_with({"jinju_city.tourinfo:1": "jh-aaa", "tourapi.area:9": "jh-bbb"}, order=["jh-bbb", "jh-aaa"])
    res = M([city("A", id="1"), tour("A", id="9")], prev=prev)
    assert res.places[0].id == "jh-bbb" and res.aliases == {"jh-aaa": "jh-bbb"}


def test_previous_aliases_carried_and_chained():
    prev = snapshot_with({"jinju_city.tourinfo:1": "jh-aaa", "tourapi.area:9": "jh-bbb"}, order=["jh-aaa", "jh-bbb"],
                         aliases={"jh-old": "jh-bbb"})
    res = M([city("A", id="1"), tour("A", id="9")], prev=prev)
    assert res.aliases == {"jh-bbb": "jh-aaa", "jh-old": "jh-aaa"}


def test_force_split_override():
    res = M([city("A", id="1"), tour("A", id="9")], {"force_split": [["jinju_city.tourinfo:1", "tourapi.area:9"]]})
    assert len(res.places) == 2


def test_force_merge_override():
    res = M([city("가", id="1"), tour("나", id="9", lat=35.3, lng=128.2)],
            {"force_merge": [["jinju_city.tourinfo:1", "tourapi.area:9"]]})
    assert len(res.places) == 1
    assert any(e.get("override") for e in res.log)


def test_log_entries():
    res = M([city("A"), tour("A")])
    assert res.log == [{"a": "jinju_city.tourinfo:A", "b": "tourapi.area:A", "reason": "same_name"}]


def test_load_overrides(tmp_path):
    assert load_overrides(tmp_path / "none.yaml") == {"force_merge": [], "force_split": []}
    p = tmp_path / "o.yaml"
    p.write_text("force_merge: []\nforce_split: []\n", encoding="utf-8")
    assert load_overrides(p) == {"force_merge": [], "force_split": []}


def test_scales_to_1500_records():
    recs = [rec(f"장소{i}", 35.1 + (i % 50) * 0.004, 128.0 + (i // 50) * 0.004, source_id=str(i)) for i in range(1500)]
    assert len(M(recs).places) == 1500


def test_city_tourism_listing_names_a_merged_temple():
    # Real data: 청곡사 (tourinfo) absorbs several heritage artifacts housed there; the place keeps the
    # tourism listing's name and category rather than an artifact's.
    temple = rec("청곡사", 35.19, 128.08, cat="sight", source="jinju_city.tourinfo", source_id="493")
    art = rec("진주 청곡사 대웅전(晉州 靑谷寺大雄殿)", 35.1901, 128.0801, cat="culture",
              source="jinju_city.heritage", source_id="500")
    p = M([art, temple]).places[0]
    assert p.title == "청곡사" and p.category == "sight" and len(p.sources) == 2


def test_one_place_on_three_sources_keeps_phone_evidence():
    # A festival listed by the city, TourAPI area (type 15) and TourAPI festival: three records, one number.
    recs = [
        rec("진주남강유등축제", 35.1896, 128.0800, cat="festival", phone="055-761-9111",
            source="jinju_city.festival", source_id="660"),
        rec("남강 유등 페스티벌 2026", 35.1910, 128.0820, cat="festival", phone="0557619111",
            source="tourapi.area", source_id="2500001"),
        rec("Jinju Lantern Fest", 35.1880, 128.0790, cat="festival", phone="055-761-9111",
            source="tourapi.festival", source_id="2500001"),
    ]
    res = M(recs)
    assert len(res.places) == 1 and {e["reason"] for e in res.log} == {"same_phone"}


def test_shared_phone_boundary_through_merge_records():
    two = [rec("가나식당", 35.19, 128.08, cat="food", phone="055-741-1234", source_id="r1",
               source="jinju_city.restaurant"),
           rec("전혀다른이름", 35.192, 128.082, cat="food", phone="055-741-1234", source="tourapi.area",
               source_id="t1")]
    assert len(M(two).places) == 1
    # the same number on 3 distinct records of one source is a department line: no phone merges at all
    dept = [rec(f"관광지{i}", 35.19 + i * 0.004, 128.08, phone="055-749-5355", source_id=f"c{i}")
            for i in range(3)]
    tour = rec("다른 이름 명소", 35.19, 128.08, phone="055-749-5355", source="tourapi.area", source_id="t9")
    assert len(M(dept + [tour]).places) == 4
    # duplicates of one record (same idx on two pages) do not count as distinct records
    dup = [rec("관광지A", 35.19, 128.08, phone="055-749-1111", source_id="c1"),
           rec("관광지A", 35.19, 128.08, phone="055-749-1111", source_id="c1"),
           rec("관광지B", 35.1905, 128.0805, phone="055-749-1111", source_id="c2")]
    tour2_ = rec("완전히 다른 이름", 35.1902, 128.0802, phone="055-749-1111", source="tourapi.area", source_id="t2")
    assert len(M(dup + [tour2_]).places) == 1


def test_fuzzy_name_within_one_tourapi_source_is_not_evidence():
    # Recorded 2026-11-04: TourAPI lists every brand store inside a mall as its own content
    # ("아디다스 롯데몰 진주점" contains "롯데몰 진주점" -> token_set_ratio 100), which chained 17 records into one.
    mall = tour("롯데몰 진주점", id="3086012", cat="shopping", lat=35.2051, lng=128.1260)
    shop = tour("아디다스 롯데몰 진주점", id="4008310", cat="shopping", lat=35.2052, lng=128.1261)
    assert match_reason(mall, shop) is None
    assert len(M([mall, shop]).places) == 2
    assert match_reason(city("남강 유등 전시관"), tour("남강 유등 전시관 매표소")) == "fuzzy_name"
    assert match_reason(tour("롯데몰 진주점"), tour2("롯데몰 진주점")) == "same_name"


def _groups(res):
    return {frozenset(s.key for s in p.sources): p.id for p in res.places}


def _jinjuseong(a_id, b_id):
    # Real data (K3): city 605 "진주성", city 1163 "진주성 우물" (force_split), TourAPI 126833 "진주성".
    # "jinju_city.tourinfo:1163" sorts before "...:605", so a key-ordered greedy union joined T to the well.
    a = city("진주성", id=a_id, lat=35.1897, lng=128.0790)
    b = city("진주성 우물", id=b_id, lat=35.1899, lng=128.0793)
    t = tour("진주성", id="126833", lat=35.1898, lng=128.0791)
    split = {"force_split": [[a.key, b.key]]}
    return a, b, t, split


def test_union_prefers_stronger_evidence_under_split():
    for a_id, b_id in (("605", "1163"), ("100", "605")):  # both key orders: A after B, A before B
        a, b, t, split = _jinjuseong(a_id, b_id)
        groups = set(_groups(M([a, b, t], split)))
        assert groups == {frozenset({a.key, t.key}), frozenset({b.key})}, (a_id, b_id)


def test_merge_result_independent_of_input_order():
    a, b, t, split = _jinjuseong("605", "1163")
    recs = [a, b, t,
            city("남강 유등 전시관", id="7", lat=35.1880, lng=128.0890),
            tour("남강 유등 전시관 매표소", id="501", lat=35.1881, lng=128.0891),
            rec("가나식당", 35.19, 128.08, cat="food", phone="055-741-1234", source="jinju_city.restaurant",
                source_id="r1"),
            rec("전혀다른이름", 35.192, 128.082, cat="food", phone="0557411234", source="tourapi.area",
                source_id="t1")]
    orders = [recs, list(reversed(recs)), [recs[i] for i in (4, 0, 6, 2, 5, 1, 3)]]
    results = [_groups(M(o, split)) for o in orders]
    assert results[0] == results[1] == results[2]
    assert len(results[0]) == 4


def test_component_never_holds_two_contentids_of_one_tour_source():
    # tour A ~ city X ~ tour B by fuzzy names only: A and B are distinct TourAPI contents.
    x = city("남강 유등 전시관", id="7", lat=35.1880, lng=128.0890)
    ta = tour("남강 유등 전시관 매표소", id="501", lat=35.1881, lng=128.0891)
    tb = tour("남강 유등 전시관 주차장", id="502", lat=35.1879, lng=128.0889)
    res = M([x, ta, tb])
    assert not any({ta.key, tb.key} <= g for g in _groups(res))
    assert set(_groups(res)) == {frozenset({x.key, ta.key}), frozenset({tb.key})}  # ties: (key_a, key_b)
    # the same contentid on another TourAPI source (area + festival) is not a conflict
    fa = rec("남강 유등 전시관 매표소", 35.1881, 128.0891, source="tourapi.festival", source_id="501")
    assert {frozenset({x.key, ta.key, fa.key})} <= set(_groups(M([x, ta, tb, fa])))
    # two contentids with the same name are allowed together (TourAPI lists some places twice)
    same = [city("진주성", id="605"), tour("진주성", id="126833"), tour2("진주성", id="999")]
    assert len(M(same).places) == 1


def test_implicit_split_checks_every_contentid_already_in_the_component():
    # A and A' share a name (allowed together); B only fuzzy-matches the city record -> stays apart.
    x = city("남강 유등 전시관", id="7", lat=35.1880, lng=128.0890)
    a1 = tour("남강 유등 전시관", id="501", lat=35.1881, lng=128.0891)
    a2 = tour("남강유등전시관", id="503", lat=35.1880, lng=128.0890)
    b = tour("남강 유등 전시관 주차장", id="502", lat=35.1879, lng=128.0889)
    assert set(_groups(M([x, a1, a2, b]))) == {frozenset({x.key, a1.key, a2.key}), frozenset({b.key})}


def test_reason_reports_strongest_evidence():
    # a pair with both a similar name and the same phone is phone evidence (ranked above fuzzy)
    a = rec("남강 유등 전시관", 35.1880, 128.0890, phone="055-749-1111", source_id="c1")
    b = rec("남강 유등 전시관 매표소", 35.1881, 128.0891, phone="0557491111", source="tourapi.area",
            source_id="t1")
    assert match_reason(a, b) == "same_phone"
