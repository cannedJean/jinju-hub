from datetime import date

from helpers import NOW, city_raws_from_fixture

from jinju_pipeline.clean import CleanResult, clean_all, clean_record
from jinju_pipeline.models import RawRecord


def test_clean_city_tourinfo_fixture(region, city_raws):
    res = clean_all(city_raws, region)
    assert res.records and all(r.category in ("sight", "culture") for r in res.records)
    assert all(r.lat is None or region.contains(r.lat, r.lng) for r in res.records)


def test_clean_tourapi_detail_fields(region, tour_raw_126833):
    r = clean_record(tour_raw_126833, region)
    assert r.overview and "<" not in r.overview and r.images[0].license in ("Type1", "Type3")


def test_hidden_tourapi_dropped(region, tour_raw_hidden):
    assert clean_record(tour_raw_hidden, region) == "hidden"


def test_raw_preserved(region, tour_raw_126833):
    assert clean_record(tour_raw_126833, region).raw == tour_raw_126833.payload


def test_tourapi_full_mapping(region, tour_raw_126833):
    """Recorded 진주성 (contentid 126833): list + detailCommon2 + detailIntro2 + detailImage2."""
    r = clean_record(tour_raw_126833, region)
    assert (r.category, r.title, r.geo_status) == ("sight", "진주성", "ok")
    assert (r.lat, r.lng) == (35.1897050219, 128.0802537617)
    assert r.addr == "경상남도 진주시 남강로 626"
    assert r.phone == "055-749-5171"  # list/common tel are empty; detailIntro2 infocenter has it
    assert r.homepage == "https://www.jinju.go.kr/tour.web"  # real homepage is a bare http URL, not an <a>
    assert r.hours.startswith("[하절기(3월~10월)]") and r.closed_days == "연중무휴" and r.parking == "가능"
    assert r.fee is None
    assert r.source_url == "https://korean.visitkorea.or.kr/detail/ms_detail.do?cotid=126833"
    urls = [i.url for i in r.images]
    assert urls[0] == "https://tong.visitkorea.or.kr/cms/resource/65/4062165_image2_1.JPG"
    assert "https://tong.visitkorea.or.kr/cms/resource/86/3348486_image2_1.jpg" in urls
    assert len(r.images) == 11  # firstimage + 10 detailImage2 rows (detailImage2 default numOfRows=10)
    assert [i.sort for i in r.images] == list(range(len(r.images)))
    assert r.images[0].license == "Type1"
    assert next(i for i in r.images if i.url.endswith("3348486_image2_1.jpg")).license == "Type3"


def test_tourapi_http_firstimage_upgraded(region, fixture_json):
    item = next(i for i in fixture_json("tourapi/area_12_p1.json")["response"]["body"]["items"]["item"]
                if i["contentid"] == "128498")
    assert item["firstimage"].startswith("http://")  # 17 of 57 recorded list items use http://
    raw = RawRecord(source="tourapi.area", source_id="128498", payload={"list": item}, fetched_at=NOW)
    r = clean_record(raw, region)
    assert r.images[0].url == "https://tong.visitkorea.or.kr/cms/resource/69/3538169_image2_1.jpg"
    assert r.images[0].license == "Type1" and r.phone is None


def test_tourapi_festival_source(region, fixture_json):
    item = next(i for i in fixture_json("tourapi/festival_p1.json")["response"]["body"]["items"]["item"]
                if i["contentid"] == "506926")
    raw = RawRecord(source="tourapi.festival", source_id=item["contentid"], payload=item, fetched_at=NOW)
    r = clean_record(raw, region)
    assert r.category == "festival" and r.title == "진주남강유등축제"
    assert (r.start_date, r.end_date) == (date(2026, 10, 3), date(2026, 10, 18))
    assert r.phone == "055-761-9111"


def test_tourapi_no_title_and_no_category(region, tour_raw_126833):
    p = tour_raw_126833.model_copy(deep=True)
    p.payload["list"]["title"] = ""
    p.payload["common"]["title"] = ""
    assert clean_record(p, region) == "no_title"
    q = tour_raw_126833.model_copy(deep=True)
    q.payload["list"]["contenttypeid"] = "99"
    assert clean_record(q, region) == "no_category"


def test_tourapi_out_of_region_drop(region, tour_raw_126833):
    p = tour_raw_126833.model_copy(deep=True)
    p.payload["list"].update(mapx="127.38", mapy="36.35", addr1="대전광역시 중구")
    assert clean_record(p, region) == "out_of_region"


def test_city_festival_undecided_and_dates(region):
    res = clean_all(city_raws_from_fixture("festival"), region)
    assert res.records
    undecided = [r for r in res.records if r.date_undecided]
    dated = [r for r in res.records if r.start_date]
    assert undecided and dated
    assert all(r.start_date is None for r in undecided)
    assert all(r.category == "festival" for r in res.records)
    assert all("type=festival" in r.source_url for r in res.records)


def test_city_other_kinds(region):
    for kind, cat, urltype in [("restaurant", "food", "restaurant"), ("heritage", "culture", "asset"),
                               ("lodging", "stay", "lodging")]:
        res = clean_all(city_raws_from_fixture(kind), region)
        assert res.records and {r.category for r in res.records} == {cat}
        assert all(f"type={urltype}&idx=" in r.source_url for r in res.records)
        for r in res.records:
            for img in r.images:
                assert img.license == "jinju_city_unverified" and img.url.startswith("https://")


def test_clean_all_counts_drops(region, city_raws, tour_raw_hidden):
    res = clean_all(city_raws + [tour_raw_hidden], region)
    assert isinstance(res, CleanResult)
    assert res.dropped["hidden"] == 1
    assert len(res.records) + sum(res.dropped.values()) == len(city_raws) + 1
