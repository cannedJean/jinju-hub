import asyncio
import logging
import time
from datetime import datetime

import httpx
import pytest

from jinju_pipeline.collect import collect_all, default_sources, run_source
from jinju_pipeline.http import ConfigError
from jinju_pipeline.models import RawRecord
from jinju_pipeline.raw_store import KST
from jinju_pipeline.settings import Settings


def rec(source: str, sid: str) -> RawRecord:
    return RawRecord(source=source, source_id=sid, payload={"n": sid}, fetched_at=datetime(2026, 11, 4, tzinfo=KST))


class FakeSource:
    def __init__(self, name, delay=0.0, records=None, exc=None):
        self.name = name
        self.delay = delay
        self.records = records or []
        self.exc = exc

    async def collect(self, ctx):
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.exc:
            raise self.exc
        return self.records


@pytest.fixture
def ctx(ctx_factory):
    return ctx_factory(httpx.MockTransport(lambda r: httpx.Response(200, json={})))


@pytest.fixture
def ctx_with_previous(ctx_factory, previous_snapshot):
    c = ctx_factory(httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    c.previous = previous_snapshot(raw_by_source={"jinju_city.tourinfo": [rec("jinju_city.tourinfo", "9")]})
    return c


async def test_one_failure_does_not_cancel_others(ctx):
    slow_ok = FakeSource("a", delay=0.05, records=[rec("a", "1")])
    boom = FakeSource("b", exc=RuntimeError("x"))
    res = {r.source: r for r in await collect_all([slow_ok, boom], ctx)}
    assert res["a"].status == "ok" and len(res["a"].records) == 1
    assert res["b"].status == "failed" and "RuntimeError" in res["b"].error


async def test_sources_run_concurrently(ctx):
    srcs = [FakeSource(str(i), delay=0.1) for i in range(5)]
    t0 = time.perf_counter()
    await collect_all(srcs, ctx)
    assert time.perf_counter() - t0 < 0.3


async def test_failed_source_reuses_previous(ctx_with_previous):
    res = await collect_all(
        [FakeSource("jinju_city.tourinfo", exc=httpx.ConnectError("blocked"))], ctx_with_previous
    )
    assert res[0].status == "reused_previous" and res[0].records
    assert "ConnectError" in res[0].error


async def test_failed_without_previous_data_stays_failed(ctx_with_previous):
    res = await run_source(FakeSource("other", exc=RuntimeError("x")), ctx_with_previous)
    assert res.status == "failed" and res.records == []


async def test_config_error_propagates(ctx):
    with pytest.raises(ConfigError):
        await collect_all([FakeSource("a", exc=ConfigError("bad key")), FakeSource("b")], ctx)


async def test_calls_come_from_ledger(ctx):
    ctx.ledger.consume(1, "a")
    ctx.ledger.consume(1, "a")
    res = await run_source(FakeSource("a", records=[rec("a", "1")]), ctx)
    assert res.calls == 2


CITY_NAMES = [f"jinju_city.{k}" for k in ("tourinfo", "restaurant", "festival", "heritage", "lodging")]


async def test_without_key_tourapi_sources_report_skipped(ctx_factory, previous_snapshot, caplog):
    """A missing key must show up as a skipped source (never silently absent, never reused)."""
    ctx = ctx_factory(httpx.MockTransport(lambda r: httpx.Response(500)), data_go_kr_key=None)
    ctx.previous = previous_snapshot(raw_by_source={"tourapi.area": [rec("tourapi.area", "1")]})
    sources = default_sources(ctx.settings)
    assert [x.name for x in sources] == CITY_NAMES + ["tourapi.area", "tourapi.festival"]
    with caplog.at_level(logging.WARNING):
        res = {r.source: r for r in await collect_all(sources[-2:], ctx)}
    for name in ("tourapi.area", "tourapi.festival"):
        assert res[name].status == "skipped" and res[name].records == []
        assert res[name].error == "skipped: no key" and res[name].calls == 0
    assert any("DATA_GO_KR_KEY" in m for m in caplog.messages)


async def test_quota_hit_on_tourapi_does_not_fail_city_sources(ctx_factory):
    """City pages are not metered against the TourAPI key quota, so an exhausted run budget only
    affects the TourAPI source that hit it."""
    from jinju_pipeline.http import QuotaLedger
    from jinju_pipeline.sources.jinju_city import JinjuCitySource
    from jinju_pipeline.sources.tourapi import TourApiFestivalSource

    def handler(request):
        if request.url.host == "www.jinju.go.kr":
            page = int(request.url.params["page"])
            return httpx.Response(200, json={"record_count": 30, "results": [{"idx": page, "name": "n"}]})
        return httpx.Response(200, json={"response": {"header": {"resultCode": "0000"},
                                                      "body": {"items": "", "totalCount": 0}}})

    from datetime import date

    ctx = ctx_factory(httpx.MockTransport(handler), data_go_kr_key="k")
    ctx.ledger = QuotaLedger(None, daily_limit=10**9, run_limit=0, today=date.today())
    res = {r.source: r for r in await collect_all([JinjuCitySource("tourinfo"), TourApiFestivalSource()], ctx)}
    assert res["jinju_city.tourinfo"].status == "ok" and len(res["jinju_city.tourinfo"].records) == 3
    assert res["jinju_city.tourinfo"].calls == 3
    assert res["tourapi.festival"].status == "failed" and "QuotaExceeded" in res["tourapi.festival"].error
    assert ctx.ledger.used_this_run() == 0


def test_default_sources_with_key_includes_tourapi():
    s = Settings(_env_file=None, data_go_kr_key="k")
    names = [x.name for x in default_sources(s)]
    assert names[-2:] == ["tourapi.area", "tourapi.festival"] and len(names) == 7


async def test_source_error_text_is_scrubbed(ctx, ctx_with_previous):
    leak = RuntimeError("GET https://apis.data.go.kr/x?serviceKey=LEAKED-KEY&pageNo=1 failed")
    failed = await run_source(FakeSource("b", exc=leak), ctx)
    assert failed.status == "failed" and "LEAKED-KEY" not in failed.error and "serviceKey=***" in failed.error
    reused = await run_source(FakeSource("jinju_city.tourinfo", exc=leak), ctx_with_previous)
    assert reused.status == "reused_previous" and "LEAKED-KEY" not in reused.error
