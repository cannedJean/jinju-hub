import asyncio
import time
from datetime import date

import httpx
import pytest
import tenacity

from jinju_pipeline.http import (
    ConfigError,
    QuotaExceeded,
    QuotaLedger,
    RateLimiter,
    UpstreamError,
    fetch_json,
    make_client,
)

TODAY = date(2026, 11, 4)


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_retries_5xx_then_succeeds():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503 if len(calls) < 3 else 200, json={"ok": 1})

    async with _client(handler) as c:
        body = await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert body == {"ok": 1} and len(calls) == 3


async def test_5xx_exhausted_raises_upstream_error():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503)

    async with _client(handler) as c:
        with pytest.raises(UpstreamError) as ei:
            await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert len(calls) == 4
    assert ei.value.status == 503 and ei.value.retryable is True


async def test_transport_error_retried():
    calls = []

    def handler(req):
        calls.append(1)
        if len(calls) < 2:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"ok": 2})

    async with _client(handler) as c:
        body = await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert body == {"ok": 2} and len(calls) == 2


async def test_gateway_xml_quota_becomes_quota_exceeded(fixture_text):
    xml = fixture_text("tourapi/gateway_quota.xml")
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(200, text=xml)

    async with _client(handler) as c:
        with pytest.raises(QuotaExceeded):
            await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert len(calls) == 1


@pytest.mark.parametrize("code", ["30", "31"])
async def test_gateway_xml_key_errors_become_config_error(code):
    xml = f"<OpenAPI_ServiceResponse><cmmMsgHeader><returnReasonCode>{code}</returnReasonCode></cmmMsgHeader></OpenAPI_ServiceResponse>"

    async with _client(lambda req: httpx.Response(200, text=xml)) as c:
        with pytest.raises(ConfigError):
            await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())


async def test_non_json_other_body_is_upstream_error_truncated():
    body = "<html>" + "x" * 500

    async with _client(lambda req: httpx.Response(200, text=body)) as c:
        with pytest.raises(UpstreamError) as ei:
            await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert ei.value.retryable is False
    assert body[:200] in str(ei.value) and body[:201] not in str(ei.value)


async def test_4xx_not_retried():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(400, text="bad")

    async with _client(handler) as c:
        with pytest.raises(UpstreamError) as ei:
            await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert ei.value.retryable is False and ei.value.status == 400
    assert len(calls) == 1


async def test_each_attempt_consumes_quota():
    ledger = QuotaLedger(None, 900, today=TODAY)
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(503 if len(calls) < 3 else 200, json={})

    async with _client(handler) as c:
        await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), ledger=ledger, source="s",
                         wait=tenacity.wait_none())
    assert ledger.used_today() == 3 and ledger.used_by_source() == {"s": 3}


async def test_per_source_counts():
    l = QuotaLedger(None, 900, today=TODAY)
    l.consume(1, "a")
    l.consume(2, "b")
    assert l.used_by_source() == {"a": 1, "b": 2}


async def test_ledger_blocks_over_limit(tmp_path):
    l = QuotaLedger(tmp_path / "q.json", daily_limit=2, today=TODAY)
    l.consume()
    l.consume()
    with pytest.raises(QuotaExceeded):
        l.consume()


async def test_ledger_run_limit():
    l = QuotaLedger(None, daily_limit=900, run_limit=1, today=TODAY)
    l.consume()
    with pytest.raises(QuotaExceeded):
        l.consume()
    assert l.used_this_run() == 1


async def test_ledger_persists_and_resumes_same_day(tmp_path):
    p = tmp_path / "q.json"
    l = QuotaLedger(p, 900, today=TODAY)
    l.consume(5)
    l.save()
    assert QuotaLedger(p, 900, today=TODAY).used_today() == 5
    assert QuotaLedger(p, 900, today=date(2026, 11, 5)).used_today() == 0
    assert QuotaLedger(p, 900, today=TODAY).used_this_run() == 0


async def test_ledger_corrupt_file_starts_fresh(tmp_path):
    p = tmp_path / "q.json"
    p.write_text("{not json", encoding="utf-8")
    assert QuotaLedger(p, 900, today=TODAY).used_today() == 0


async def test_limiter_min_interval():
    lim = RateLimiter(4, 0.05)
    t0 = time.monotonic()

    async def one():
        async with lim:
            pass

    await asyncio.gather(*(one() for _ in range(3)))
    assert time.monotonic() - t0 >= 0.08  # Windows timer resolution margin


async def test_limiter_concurrency_cap():
    lim = RateLimiter(2, 0)
    active = peak = 0

    async def one():
        nonlocal active, peak
        async with lim:
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1

    await asyncio.gather(*(one() for _ in range(6)))
    assert peak == 2


async def test_make_client_defaults():
    async with make_client() as c:
        assert c.headers["user-agent"] == "JinjuHub-pipeline/0.1 (education project)"
        assert c.follow_redirects is True


async def test_non_dict_json_is_upstream_error():
    async with _client(lambda req: httpx.Response(200, json=[1, 2])) as c:
        with pytest.raises(UpstreamError) as ei:
            await fetch_json(c, "https://x", {}, limiter=RateLimiter(2, 0), wait=tenacity.wait_none())
    assert ei.value.retryable is False
