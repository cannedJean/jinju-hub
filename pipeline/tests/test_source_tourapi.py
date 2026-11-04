import asyncio
from datetime import date, datetime

import httpx
import pytest

from jinju_pipeline.http import ConfigError, QuotaExceeded, QuotaLedger, UpstreamError
from jinju_pipeline.models import RawRecord
from jinju_pipeline.raw_store import KST
from jinju_pipeline.sources.tourapi import (
    CONTENT_TYPES,
    TourApiAreaSource,
    TourApiError,
    TourApiFestivalSource,
    check_body,
    items_of,
    sync_month_prefixes,
    verify_codes,
)

KEY = {"data_go_kr_key": "test-key"}
JINJUSEONG = "126833"  # 진주성 in the recorded fixtures
NO_IMAGE = "128498"  # recorded list item whose firstimage a test blanks (every recorded item has one)
HIDDEN_FESTIVAL = "3037482"  # showflag 0 in the recorded areaBasedSyncList2 response


def _area_items(fixture_json) -> list[dict]:
    return fixture_json("tourapi/area_12_p1.json")["response"]["body"]["items"]["item"]


def ok(items, total=None):
    n = len(items)
    return {"response": {"header": {"resultCode": "0000", "resultMsg": "OK"},
                         "body": {"items": {"item": items} if items else "", "numOfRows": n, "pageNo": 1,
                                  "totalCount": n if total is None else total}}}


def err(code, msg):
    return {"response": {"header": {"resultCode": code, "resultMsg": msg}}}


class FakeTour:
    """Routes KorService2 operations to recorded fixtures; records every request.

    ``no_image_ids``: list items whose ``firstimage`` is blanked (to exercise the detailImage2 path).
    areaBasedSyncList2 mimics the real ``modifiedtime`` prefix match (YYYY / YYYYMM / YYYYMMDD).
    """

    def __init__(self, fixture_json, *, area_types=(12,), delay=0.0, no_image_ids=()):
        self.fj = fixture_json
        self.area_types = area_types
        self.delay = delay
        self.no_image_ids = set(no_image_ids)
        self.requests: list[httpx.Request] = []
        self.in_flight = 0
        self.max_in_flight = 0

    def ops(self, name):
        return [r for r in self.requests if r.url.path.endswith("/" + name)]

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            if self.delay:
                await asyncio.sleep(self.delay)
            op = request.url.path.rsplit("/", 1)[-1]
            p = request.url.params
            if op == "areaBasedList2":
                if int(p["contentTypeId"]) in self.area_types:
                    body = self.fj("tourapi/area_12_p1.json")
                    for item in body["response"]["body"]["items"]["item"]:
                        if item["contentid"] in self.no_image_ids:
                            item["firstimage"] = item["firstimage2"] = ""
                    if p.get("numOfRows") == "1":
                        body["response"]["body"]["totalCount"] = 7
                    return httpx.Response(200, json=body)
                return httpx.Response(200, json=ok([]))
            if op == "detailCommon2":
                body = self.fj("tourapi/detail_common_126833.json")
                body["response"]["body"]["items"]["item"][0]["contentid"] = p["contentId"]
                return httpx.Response(200, json=body)
            if op == "detailIntro2":
                return httpx.Response(200, json=self.fj("tourapi/detail_intro_126833_12.json"))
            if op == "detailImage2":
                return httpx.Response(200, json=self.fj("tourapi/detail_image_126833.json"))
            if op == "searchFestival2":
                return httpx.Response(200, json=self.fj("tourapi/festival_p1.json"))
            if op == "areaBasedSyncList2":
                body = self.fj("tourapi/sync_p1.json")
                items = [i for i in body["response"]["body"]["items"]["item"]
                         if i["modifiedtime"].startswith(p["modifiedtime"])]
                return httpx.Response(200, json=ok(items))
            if op == "ldongCode2":
                return httpx.Response(200, json=self.fj("tourapi/ldong_48.json"))
            return httpx.Response(404)
        finally:
            self.in_flight -= 1


def test_check_body_raises_on_error_code():
    with pytest.raises(TourApiError) as ei:
        check_body(err("10", "INVALID"))
    assert ei.value.code == "10" and isinstance(ei.value, UpstreamError)


def test_check_body_gateway_quota_and_key_errors():
    with pytest.raises(QuotaExceeded):
        check_body(err("22", "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"))
    with pytest.raises(QuotaExceeded):
        check_body(err("99", "LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR"))
    with pytest.raises(ConfigError):
        check_body(err("30", "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"))


def test_items_of_handles_empty_and_single():
    assert items_of({"response": {"header": {"resultCode": "0000"}, "body": {"items": "", "totalCount": 0}}}) == ([], 0)
    single = {"response": {"header": {"resultCode": "0000"}, "body": {"items": {"item": {"contentid": "1"}}, "totalCount": 1}}}
    assert items_of(single) == ([{"contentid": "1"}], 1)


def test_items_of_recorded_responses(fixture_json):
    assert items_of(fixture_json("tourapi/area_12_p1.json"))[1] == 57
    imgs, total = items_of(fixture_json("tourapi/detail_image_126833.json"))
    assert (len(imgs), total) == (10, 15)  # detailImage2 pages at numOfRows=10 by default
    assert len(items_of(fixture_json("tourapi/sync_p1.json"))[0]) == 2


async def test_missing_key_is_config_error(ctx_factory, fixture_json):
    ctx = ctx_factory(httpx.MockTransport(FakeTour(fixture_json)))
    with pytest.raises(ConfigError):
        await TourApiAreaSource().collect(ctx)


async def test_area_source_queries_ldong_only(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    await TourApiAreaSource().collect(ctx)
    assert fake.requests
    for r in fake.requests:
        p = r.url.params
        assert str(r.url).startswith("https://apis.data.go.kr/B551011/KorService2/")
        assert p["MobileOS"] == "ETC" and p["MobileApp"] == "JinjuHub" and p["_type"] == "json"
        assert p["serviceKey"] == "test-key"
        assert "areaCode" not in p and "sigunguCode" not in p
        if r.url.path.endswith("areaBasedList2"):
            assert p["lDongRegnCd"] == "48" and p["lDongSignguCd"] == "170" and p["numOfRows"] == "1000"
    assert {int(r.url.params["contentTypeId"]) for r in fake.ops("areaBasedList2")} == set(CONTENT_TYPES)


async def test_raw_pages_do_not_contain_service_key(ctx_factory, fixture_json):
    ctx = ctx_factory(httpx.MockTransport(FakeTour(fixture_json)), **KEY)
    await TourApiAreaSource().collect(ctx)
    files = list(ctx.settings.raw_dir.rglob("*.json"))
    assert files
    for f in files:
        assert "test-key" not in f.read_text(encoding="utf-8")


async def test_area_source_runs_detail_workers_concurrently(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json, delay=0.03)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    n = len(_area_items(fixture_json))
    assert len(recs) == n
    assert len(fake.ops("detailCommon2")) == n and len(fake.ops("detailIntro2")) == n
    assert 2 <= fake.max_in_flight <= 5
    r = next(x for x in recs if x.source_id == JINJUSEONG)
    assert r.source == "tourapi.area" and set(r.payload) >= {"list", "common", "intro", "images"}
    assert r.payload["common"]["title"] == "진주성" and r.payload["intro"]["restdate"] == "연중무휴"
    assert r.payload["images"] == []  # has a firstimage and is not a collection key


async def test_detail_image_called_for_missing_firstimage(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json, no_image_ids={NO_IMAGE})
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    assert [r.url.params["contentId"] for r in fake.ops("detailImage2")] == [NO_IMAGE]
    assert fake.ops("detailImage2")[0].url.params["imageYN"] == "Y"
    r = next(x for x in recs if x.source_id == NO_IMAGE)
    assert r.payload["images"][0]["originimgurl"].startswith("https://")


async def test_detail_image_called_for_collection_keys(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json, no_image_ids={NO_IMAGE})
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.collection_keys.add(f"tourapi.area:{JINJUSEONG}")
    await TourApiAreaSource().collect(ctx)
    assert {r.url.params["contentId"] for r in fake.ops("detailImage2")} == {JINJUSEONG, NO_IMAGE}


def _prev_record(fixture_json, cid=JINJUSEONG, mod="20260901120000"):
    items = _area_items(fixture_json)
    item = next((i for i in items if i["contentid"] == cid), items[0])
    item = {**item, "contentid": cid, "modifiedtime": mod}
    return RawRecord(source="tourapi.area", source_id=cid, fetched_at=datetime(2026, 11, 1, tzinfo=KST),
                     payload={"list": item, "common": {"title": "prev"}, "intro": {}, "images": []})


def _prev_all(fixture_json):
    items = _area_items(fixture_json)
    return [_prev_record(fixture_json, i["contentid"], i["modifiedtime"]) for i in items]


async def test_area_source_reuses_previous_when_modifiedtime_same(ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    item = next(i for i in _area_items(fixture_json) if i["contentid"] == JINJUSEONG)
    ctx.previous = previous_snapshot({"tourapi.area": [_prev_record(fixture_json, mod=item["modifiedtime"])]})
    recs = await TourApiAreaSource().collect(ctx)
    assert len(fake.ops("detailCommon2")) == len(_area_items(fixture_json)) - 1  # 진주성 reused
    r = next(x for x in recs if x.source_id == JINJUSEONG)
    assert r.payload["common"] == {"title": "prev"}


async def test_all_unchanged_means_zero_detail_calls(ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.previous = previous_snapshot({"tourapi.area": _prev_all(fixture_json)})
    recs = await TourApiAreaSource().collect(ctx)
    assert len(recs) == len(_area_items(fixture_json))
    assert not fake.ops("detailCommon2") and not fake.ops("detailIntro2")


async def test_quota_exceeded_marks_detail_pending(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.ledger = QuotaLedger(None, 10**9, run_limit=9, today=date.today())  # 8 list calls + 1 detail
    recs = await TourApiAreaSource().collect(ctx)  # must not raise
    n = len(_area_items(fixture_json))
    assert len(recs) == n
    pending = [r for r in recs if r.payload.get("detail_pending") is True]
    assert len(pending) == n and all("list" in r.payload for r in pending)
    assert len(fake.ops("detailCommon2")) + len(fake.ops("detailIntro2")) <= 1


async def test_detail_pending_is_retried_next_run(ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    item = next(i for i in _area_items(fixture_json) if i["contentid"] == JINJUSEONG)
    ctx.previous = previous_snapshot(
        {"tourapi.area": [_prev_record(fixture_json, mod=item["modifiedtime"])]},
        pending={f"tourapi.area:{JINJUSEONG}"},
    )
    await TourApiAreaSource().collect(ctx)
    assert JINJUSEONG in [r.url.params["contentId"] for r in fake.ops("detailCommon2")]
    assert len(fake.ops("detailCommon2")) == len(_area_items(fixture_json))


async def test_detail_upstream_error_marks_item_and_continues(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)

    async def handler(request):
        if request.url.path.endswith("detailIntro2") and request.url.params["contentId"] == JINJUSEONG:
            return httpx.Response(200, json=err("10", "INVALID_REQUEST_PARAMETER_ERROR"))
        return await fake(request)

    ctx = ctx_factory(httpx.MockTransport(handler), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    bad = next(r for r in recs if r.source_id == JINJUSEONG)
    assert "INVALID" in bad.payload["detail_error"] and "list" in bad.payload
    assert all("detail_error" not in r.payload for r in recs if r.source_id != JINJUSEONG)


async def test_config_error_propagates_from_workers(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)

    async def handler(request):
        if request.url.path.endswith("detailCommon2"):
            return httpx.Response(200, json=err("30", "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"))
        return await fake(request)

    ctx = ctx_factory(httpx.MockTransport(handler), **KEY)
    with pytest.raises(ConfigError):
        await TourApiAreaSource().collect(ctx)


async def test_list_paginates_by_actual_returned_count(ctx_factory, fixture_json):
    base = _area_items(fixture_json)[:12]
    seen = []

    async def handler(request):
        p = request.url.params
        op = request.url.path.rsplit("/", 1)[-1]
        if op == "areaBasedList2":
            page = int(p["pageNo"])
            seen.append((p["contentTypeId"], page))
            if p["contentTypeId"] != "12":
                return httpx.Response(200, json=ok([]))
            chunk = base[(page - 1) * 5: page * 5]  # server returns 5 per page although 1000 asked
            return httpx.Response(200, json=ok(chunk, total=12))
        if op == "detailCommon2":
            return httpx.Response(200, json=ok([{"contentid": p["contentId"], "title": "t"}]))
        return httpx.Response(200, json=ok([{"contentid": p["contentId"]}]))

    ctx = ctx_factory(httpx.MockTransport(handler), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    assert len(recs) == 12 and ("12", 3) in seen


async def test_incremental_uses_sync_list_and_hides(ctx_factory, fixture_json, previous_snapshot):
    """Recorded areaBasedSyncList2 (2026-10-23): 진주성 changed (showflag 1) + a hidden festival (showflag 0).

    ``modifiedtime`` is a prefix match, not "since": the source asks for every month from the previous
    run's month to today's and keeps items modified on/after the previous run's date.
    """
    items = _area_items(fixture_json)
    others = [i["contentid"] for i in items if i["contentid"] != JINJUSEONG]
    pending_id, untouched_id = others[0], others[1]
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.incremental = True
    ctx.today = date(2026, 11, 4)
    prev = [_prev_record(fixture_json, i["contentid"],
                         "20260901000000" if i["contentid"] == JINJUSEONG else i["modifiedtime"])
            for i in items]
    ctx.previous = previous_snapshot({"tourapi.area": prev}, pending={f"tourapi.area:{pending_id}"},
                                     generated_at=datetime(2026, 10, 20, 3, 0, tzinfo=KST))
    recs = await TourApiAreaSource().collect(ctx)
    assert not fake.ops("areaBasedList2")
    sync = fake.ops("areaBasedSyncList2")
    assert sorted(r.url.params["modifiedtime"] for r in sync) == ["202610", "202611"]
    assert all(r.url.params["lDongRegnCd"] == "48" and r.url.params["lDongSignguCd"] == "170" for r in sync)
    detailed = sorted(r.url.params["contentId"] for r in fake.ops("detailCommon2"))
    assert detailed == sorted([JINJUSEONG, pending_id])  # changed + pending; hidden skipped
    by_id = {r.source_id: r for r in recs}
    assert by_id[HIDDEN_FESTIVAL].payload["hidden"] is True
    assert by_id[JINJUSEONG].payload["common"]["title"] == "진주성"
    untouched = by_id[untouched_id].payload
    assert "hidden" not in untouched and untouched["common"] == {"title": "prev"}
    assert len(recs) == len(items) + 1


async def test_incremental_ignores_sync_items_modified_before_previous_run(
        ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.incremental = True
    ctx.today = date(2026, 11, 4)
    ctx.previous = previous_snapshot({"tourapi.area": _prev_all(fixture_json)},
                                     generated_at=datetime(2026, 10, 24, 3, 0, tzinfo=KST))
    recs = await TourApiAreaSource().collect(ctx)
    assert fake.ops("areaBasedSyncList2")  # the 202610 page still returns both 2026-10-23 items
    assert not fake.ops("detailCommon2")
    assert HIDDEN_FESTIVAL not in {r.source_id for r in recs}
    assert len(recs) == len(_area_items(fixture_json))


async def test_incremental_without_previous_falls_back_to_full(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.incremental = True
    recs = await TourApiAreaSource().collect(ctx)
    assert fake.ops("areaBasedList2") and not fake.ops("areaBasedSyncList2")
    assert len(recs) == len(_area_items(fixture_json))


async def test_festival_source(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.today = date(2026, 11, 4)
    recs = await TourApiFestivalSource().collect(ctx)
    p = fake.ops("searchFestival2")[0].url.params
    assert p["eventStartDate"] == "20260101" and p["lDongRegnCd"] == "48" and p["lDongSignguCd"] == "170"
    assert len(recs) == 8 and all(r.source == "tourapi.festival" for r in recs)
    lantern = next(r for r in recs if r.source_id == "506926")
    assert lantern.payload["title"] == "진주남강유등축제" and lantern.payload["eventenddate"] == "20261018"


async def test_verify_codes_reports_counts(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    res = await verify_codes(ctx.client, ctx.settings, ctx.region)
    assert res["signgu_ok"] is True and res["signgu_name"] == "진주시"
    assert set(res["counts"]) == set(CONTENT_TYPES) and res["counts"][12] == 7
    lp = fake.ops("ldongCode2")[0].url.params
    assert lp["lDongRegnCd"] == "48" and lp["lDongListYn"] == "Y"


async def test_previous_detail_error_is_refetched(ctx_factory, fixture_json, previous_snapshot):
    old = _prev_record(fixture_json)
    old.payload["detail_error"] = "HTTP 503"
    del old.payload["common"]
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.previous = previous_snapshot({"tourapi.area": [old]})
    recs = await TourApiAreaSource().collect(ctx)
    assert JINJUSEONG in [r.url.params["contentId"] for r in fake.ops("detailCommon2")]
    r = next(x for x in recs if x.source_id == JINJUSEONG)
    assert "detail_error" not in r.payload and r.payload["common"]["title"] == "진주성"


async def test_transport_error_marks_item_and_continues(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)

    async def handler(request):
        if request.url.path.endswith("detailCommon2") and request.url.params["contentId"] == JINJUSEONG:
            raise httpx.ConnectTimeout("boom", request=request)
        return await fake(request)

    ctx = ctx_factory(httpx.MockTransport(handler), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    assert len(recs) == len(_area_items(fixture_json))
    bad = next(r for r in recs if r.source_id == JINJUSEONG)
    assert "detail_error" in bad.payload and "common" not in bad.payload
    others = [r for r in recs if r.source_id != JINJUSEONG]
    assert all("common" in r.payload and "detail_error" not in r.payload for r in others)


def test_sync_month_prefixes_cross_year_and_same_month():
    assert sync_month_prefixes(date(2026, 11, 28), date(2027, 1, 5)) == ["202611", "202612", "202701"]
    assert sync_month_prefixes(date(2026, 11, 1), date(2026, 11, 4)) == ["202611"]
    assert sync_month_prefixes(date(2026, 11, 5), date(2026, 11, 4)) == ["202611"]  # clock skew: still one
