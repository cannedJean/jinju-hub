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
    b = rec("전혀다른이름", 35.192, 128.082, cat="food", phone="0557411234")
    assert match_reason(a, b) == "same_phone"


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
