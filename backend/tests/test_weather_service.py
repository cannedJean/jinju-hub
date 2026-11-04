import asyncio
from datetime import datetime

import httpx
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.services import weather_service
from app.services.weather_service import WeatherConfigurationError, WeatherUpstreamError

NOW = datetime.fromisoformat("2026-07-15T12:15:00+09:00")


def _payload():
    items = []
    for time, values in {
        "1200": {"T1H": "26", "SKY": "3", "PTY": "0"},
        "1300": {"T1H": "27.4", "SKY": "1", "PTY": "0"},
    }.items():
        for category, value in values.items():
            items.append({"fcstDate": "20260715", "fcstTime": time,
                          "category": category, "fcstValue": value})
    return {"response": {"header": {"resultCode": "00", "resultMsg": "NORMAL_SERVICE"},
                         "body": {"items": {"item": items}}}}


@pytest.fixture(autouse=True)
def _clear_cache():
    weather_service.clear_weather_cache()
    yield
    weather_service.clear_weather_cache()


def _settings(key="decoded-test-key"):
    return Settings(_env_file=None, weather_api_key=SecretStr(key) if key else None)


def _fetch(handler, settings, **kw):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await weather_service.fetch_weather(settings, client=client, now=NOW, **kw)
    return asyncio.run(run())


def test_fetch_weather_parses_kma_forecast_and_sends_grid():
    requested = {}

    def handler(request: httpx.Request):
        requested["url"] = str(request.url)
        return httpx.Response(200, json=_payload())

    result = _fetch(handler, _settings())
    assert result.city == "jinju"
    assert result.temperature == 27.4
    assert result.condition == "맑음"
    assert result.icon_code == "clear"
    assert result.recommendation == "outdoor"
    assert "nx=81" in requested["url"]
    assert "ny=75" in requested["url"]
    assert "authKey=decoded-test-key" in requested["url"]


def test_cache_hit_skips_second_http_call():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(200, json=_payload())

    _fetch(handler, _settings())
    _fetch(handler, _settings())
    assert len(calls) == 1


def test_missing_key_raises_configuration_error():
    with pytest.raises(WeatherConfigurationError):
        _fetch(lambda r: httpx.Response(200, json=_payload()), _settings(None))


def test_upstream_http_error_raises_upstream_error():
    with pytest.raises(WeatherUpstreamError):
        _fetch(lambda r: httpx.Response(500), _settings())


def test_latest_base_time_crosses_midnight_safely():
    now = datetime.fromisoformat("2026-07-15T00:20:00+09:00")
    assert weather_service._latest_base_datetime(now).isoformat() == "2026-07-14T23:30:00+09:00"


def test_weather_endpoint_missing_key_is_503(make_client):
    r = make_client().get("/api/weather")
    assert r.status_code == 503


def test_weather_endpoint_ok_and_upstream_failure(make_client, monkeypatch):
    c = make_client(weather_api_key="k")

    async def ok(settings, **kw):
        return weather_service._parse_payload(_payload(), "jinju", NOW)

    monkeypatch.setattr("app.api.v1.endpoints.weather.fetch_weather", ok)
    r = c.get("/api/weather")
    assert r.status_code == 200 and r.json()["city"] == "jinju" and r.json()["temperature"] == 27.4

    async def bad(settings, **kw):
        raise WeatherUpstreamError("x")

    monkeypatch.setattr("app.api.v1.endpoints.weather.fetch_weather", bad)
    assert c.get("/api/weather").status_code == 502
