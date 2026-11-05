import asyncio
import json

import httpx
import pytest

from jinju_pipeline.sources.jinju_city import CITY_ENDPOINTS, JinjuCitySource, parse_page


def test_parse_page_tourinfo(fixture_json):
    items, total = parse_page(fixture_json("jinju_city/tourinfo_p1.json"))
    # the recorded page 1 (10 items) plus real items from later pages appended in A12 for e2e content
    assert total >= 150 and len(items) >= 10
    assert {"name", "xposition", "yposition"} <= set(items[0])


@pytest.mark.parametrize("kind", ["tourinfo", "restaurant", "festival", "heritage", "lodging"])
def test_parse_page_all_fixtures(fixture_json, kind):
    items, total = parse_page(fixture_json(f"jinju_city/{kind}_p1.json"))
    assert total > 0 and items and kind in CITY_ENDPOINTS


async def test_collect_fetches_all_pages_in_parallel(ctx_factory):
    state = {"in_flight": 0, "max": 0}
    sizes = {1: 10, 2: 10, 3: 3}

    async def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        assert request.url.params["pageunit"] == "10"
        assert request.url.path.endswith("/openapi/tour/tourinfo.do")
        state["in_flight"] += 1
        state["max"] = max(state["max"], state["in_flight"])
        await asyncio.sleep(0.05)
        state["in_flight"] -= 1
        results = [{"idx": page * 100 + i, "name": f"n{page}-{i}"} for i in range(sizes[page])]
        return httpx.Response(200, json={"record_count": 23, "page": page, "results": results})

    ctx = ctx_factory(httpx.MockTransport(handler))
    recs = await JinjuCitySource("tourinfo").collect(ctx)
    assert len(recs) == 23 and 2 <= state["max"] <= 4
    assert all(r.source == "jinju_city.tourinfo" for r in recs)
    assert len({r.source_id for r in recs}) == 23
    assert recs[0].source_id == "100"
    files = list((ctx.settings.raw_dir / "jinju_city.tourinfo").rglob("page-*.json"))
    assert len(files) == 3
    assert ctx.ledger.used_by_source() == {"jinju_city.tourinfo": 3}


async def test_source_id_fallback_hash_when_no_idx(ctx_factory):
    def handler(request):
        return httpx.Response(200, json={"record_count": 1, "results": [{"name": "a", "address": "b"}]})

    recs = await JinjuCitySource("lodging").collect(ctx_factory(httpx.MockTransport(handler)))
    import hashlib

    assert recs[0].source_id == hashlib.sha1("a|b".encode()).hexdigest()[:12]


async def test_empty_total_makes_single_call(ctx_factory):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json={"record_count": 0, "results": []})

    recs = await JinjuCitySource("festival").collect(ctx_factory(httpx.MockTransport(handler)))
    assert recs == [] and len(calls) == 1


def test_unknown_kind_rejected():
    with pytest.raises(KeyError):
        JinjuCitySource("nope")


async def test_city_pages_do_not_consume_tourapi_quota(ctx_factory):
    """Spec 5.9: the key quota (daily/run cap) is TourAPI's; city pages are only counted per source."""
    from datetime import date

    from jinju_pipeline.http import QuotaLedger

    def handler(request):
        page = int(request.url.params["page"])
        return httpx.Response(200, json={"record_count": 25, "results": [{"idx": page, "name": "n"}]})

    ctx = ctx_factory(httpx.MockTransport(handler))
    ctx.ledger = QuotaLedger(None, daily_limit=1, run_limit=1, today=date.today())
    recs = await JinjuCitySource("heritage").collect(ctx)
    assert len(recs) == 3
    assert ctx.ledger.used_this_run() == 0 and ctx.ledger.used_today() == 0
    assert ctx.ledger.used_by_source() == {"jinju_city.heritage": 3}
