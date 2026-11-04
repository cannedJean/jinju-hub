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
    verify_codes,
)

KEY = {"data_go_kr_key": "test-key"}


def ok(items, total=None):
    n = len(items)
    return {"response": {"header": {"resultCode": "0000", "resultMsg": "OK"},
                         "body": {"items": {"item": items} if items else "", "numOfRows": n, "pageNo": 1,
                                  "totalCount": n if total is None else total}}}


def err(code, msg):
    return {"response": {"header": {"resultCode": code, "resultMsg": msg}}}


class FakeTour:
    """Routes KorService2 operations to fixtures; records every request."""

    def __init__(self, fixture_json, *, area_types=(12,), delay=0.0):
        self.fj = fixture_json
        self.area_types = area_types
        self.delay = delay
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
                    if p.get("numOfRows") == "1":
                        body["response"]["body"]["totalCount"] = 7
                    return httpx.Response(200, json=body)
                return httpx.Response(200, json=ok([]))
            if op == "detailCommon2":
                body = self.fj("tourapi/detail_common_126508.json")
                body["response"]["body"]["items"]["item"][0]["contentid"] = p["contentId"]
                return httpx.Response(200, json=body)
            if op == "detailIntro2":
                return httpx.Response(200, json=self.fj("tourapi/detail_intro_126508_12.json"))
            if op == "detailImage2":
                return httpx.Response(200, json=self.fj("tourapi/detail_image_126508.json"))
            if op == "searchFestival2":
                return httpx.Response(200, json=self.fj("tourapi/festival_p1.json"))
            if op == "areaBasedSyncList2":
                return httpx.Response(200, json=self.fj("tourapi/sync_p1.json"))
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
    assert len(recs) == 12
    assert len(fake.ops("detailCommon2")) == 12 and len(fake.ops("detailIntro2")) == 12
    assert 2 <= fake.max_in_flight <= 5
    r = next(x for x in recs if x.source_id == "126508")
    assert r.source == "tourapi.area" and set(r.payload) >= {"list", "common", "intro", "images"}
    assert r.payload["common"]["title"] == "진주성" and r.payload["intro"]["usetime"] == "09:00~18:00"
    assert r.payload["images"] == []


async def test_detail_image_called_for_missing_firstimage(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    assert [r.url.params["contentId"] for r in fake.ops("detailImage2")] == ["2733960"]
    assert fake.ops("detailImage2")[0].url.params["imageYN"] == "Y"
    r = next(x for x in recs if x.source_id == "2733960")
    assert r.payload["images"][0]["originimgurl"].startswith("https://")


async def test_detail_image_called_for_collection_keys(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.collection_keys.add("tourapi.area:126508")
    await TourApiAreaSource().collect(ctx)
    assert {r.url.params["contentId"] for r in fake.ops("detailImage2")} == {"126508", "2733960"}


def _prev_record(fixture_json, cid="126508", mod="20260901120000"):
    item = fixture_json("tourapi/area_12_p1.json")["response"]["body"]["items"]["item"][0]
    item = {**item, "contentid": cid, "modifiedtime": mod}
    return RawRecord(source="tourapi.area", source_id=cid, fetched_at=datetime(2026, 11, 1, tzinfo=KST),
                     payload={"list": item, "common": {"title": "prev"}, "intro": {}, "images": []})


def _prev_all(fixture_json):
    items = fixture_json("tourapi/area_12_p1.json")["response"]["body"]["items"]["item"]
    return [_prev_record(fixture_json, i["contentid"], i["modifiedtime"]) for i in items]


async def test_area_source_reuses_previous_when_modifiedtime_same(ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.previous = previous_snapshot({"tourapi.area": [_prev_record(fixture_json)]})
    recs = await TourApiAreaSource().collect(ctx)
    assert len(fake.ops("detailCommon2")) == 11  # 126508 reused
    r = next(x for x in recs if x.source_id == "126508")
    assert r.payload["common"] == {"title": "prev"}


async def test_all_unchanged_means_zero_detail_calls(ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.previous = previous_snapshot({"tourapi.area": _prev_all(fixture_json)})
    recs = await TourApiAreaSource().collect(ctx)
    assert len(recs) == 12 and not fake.ops("detailCommon2") and not fake.ops("detailIntro2")


async def test_quota_exceeded_marks_detail_pending(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.ledger = QuotaLedger(None, 10**9, run_limit=9, today=date.today())  # 8 list calls + 1 detail
    recs = await TourApiAreaSource().collect(ctx)  # must not raise
    assert len(recs) == 12
    pending = [r for r in recs if r.payload.get("detail_pending") is True]
    assert len(pending) == 12 and all("list" in r.payload for r in pending)
    assert len(fake.ops("detailCommon2")) + len(fake.ops("detailIntro2")) <= 1


async def test_detail_pending_is_retried_next_run(ctx_factory, fixture_json, previous_snapshot):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.previous = previous_snapshot(
        {"tourapi.area": [_prev_record(fixture_json)]}, pending={"tourapi.area:126508"}
    )
    await TourApiAreaSource().collect(ctx)
    assert "126508" in [r.url.params["contentId"] for r in fake.ops("detailCommon2")]
    assert len(fake.ops("detailCommon2")) == 12


async def test_detail_upstream_error_marks_item_and_continues(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)

    async def handler(request):
        if request.url.path.endswith("detailIntro2") and request.url.params["contentId"] == "126508":
            return httpx.Response(200, json=err("10", "INVALID_REQUEST_PARAMETER_ERROR"))
        return await fake(request)

    ctx = ctx_factory(httpx.MockTransport(handler), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    bad = next(r for r in recs if r.source_id == "126508")
    assert "INVALID" in bad.payload["detail_error"] and "list" in bad.payload
    assert all("detail_error" not in r.payload for r in recs if r.source_id != "126508")


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
    base = fixture_json("tourapi/area_12_p1.json")["response"]["body"]["items"]["item"]
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
    pending_id = "2733965"
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.incremental = True
    ctx.previous = previous_snapshot(
        {"tourapi.area": _prev_all(fixture_json)}, pending={f"tourapi.area:{pending_id}"}
    )
    recs = await TourApiAreaSource().collect(ctx)
    assert not fake.ops("areaBasedList2")
    sync = fake.ops("areaBasedSyncList2")
    assert sync and sync[0].url.params["modifiedtime"] == "20261101"
    assert sync[0].url.params["lDongRegnCd"] == "48" and sync[0].url.params["lDongSignguCd"] == "170"
    detailed = sorted(r.url.params["contentId"] for r in fake.ops("detailCommon2"))
    assert detailed == sorted(["126508", "2900001", pending_id])  # changed + new + pending; hidden skipped
    by_id = {r.source_id: r for r in recs}
    assert by_id["2733961"].payload["hidden"] is True
    assert "hidden" not in by_id["2733962"].payload and by_id["2733962"].payload["common"] == {"title": "prev"}
    assert "2900001" in by_id and len(recs) == 13


async def test_incremental_without_previous_falls_back_to_full(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.incremental = True
    recs = await TourApiAreaSource().collect(ctx)
    assert fake.ops("areaBasedList2") and not fake.ops("areaBasedSyncList2") and len(recs) == 12


async def test_festival_source(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)
    ctx = ctx_factory(httpx.MockTransport(fake), **KEY)
    ctx.today = date(2026, 11, 4)
    recs = await TourApiFestivalSource().collect(ctx)
    p = fake.ops("searchFestival2")[0].url.params
    assert p["eventStartDate"] == "20260101" and p["lDongRegnCd"] == "48" and p["lDongSignguCd"] == "170"
    assert len(recs) == 3 and recs[0].source == "tourapi.festival" and recs[0].source_id == "2500001"
    assert recs[0].payload["eventenddate"] == "20261014"


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
    assert "126508" in [r.url.params["contentId"] for r in fake.ops("detailCommon2")]
    r = next(x for x in recs if x.source_id == "126508")
    assert "detail_error" not in r.payload and r.payload["common"]["title"] == "진주성"


async def test_transport_error_marks_item_and_continues(ctx_factory, fixture_json):
    fake = FakeTour(fixture_json)

    async def handler(request):
        if request.url.path.endswith("detailCommon2") and request.url.params["contentId"] == "126508":
            raise httpx.ConnectTimeout("boom", request=request)
        return await fake(request)

    ctx = ctx_factory(httpx.MockTransport(handler), **KEY)
    recs = await TourApiAreaSource().collect(ctx)
    assert len(recs) == 12
    bad = next(r for r in recs if r.source_id == "126508")
    assert "detail_error" in bad.payload and "common" not in bad.payload
    assert all("common" in r.payload and "detail_error" not in r.payload for r in recs if r.source_id != "126508")
