import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.core.config import Settings
from app.core.region import load_region
from app.schemas.weather import WeatherResponse
from app.services.kma_grid import latlng_to_grid

KST = timezone(timedelta(hours=9))
KMA_ULTRA_SHORT_FORECAST_URL = (
    "https://apihub.kma.go.kr/api/typ02/openApi/"
    "VilageFcstInfoService_2.0/getUltraSrtFcst"
)
CACHE_TTL_SECONDS = 600


class WeatherConfigurationError(RuntimeError):
    pass


class WeatherUpstreamError(RuntimeError):
    pass


_cache: dict[tuple[int, int], tuple[float, WeatherResponse]] = {}
_cache_lock = asyncio.Lock()


def clear_weather_cache() -> None:
    _cache.clear()


def _latest_base_datetime(now: datetime) -> datetime:
    # 초단기예보는 매시 30분 생성되고 약 45분 이후 조회가 안정적이다.
    available = now.astimezone(KST) - timedelta(minutes=45)
    return available.replace(minute=30, second=0, microsecond=0)


def _condition(values: dict[str, str]) -> tuple[str, str]:
    pty = values.get("PTY", "0")
    precipitation = {
        "1": ("비", "rain"),
        "2": ("비/눈", "rain-snow"),
        "3": ("눈", "snow"),
        "5": ("빗방울", "rain"),
        "6": ("빗방울/눈날림", "rain-snow"),
        "7": ("눈날림", "snow"),
    }
    if pty in precipitation:
        return precipitation[pty]

    return {
        "1": ("맑음", "clear"),
        "3": ("구름많음", "partly-cloudy"),
        "4": ("흐림", "cloudy"),
    }.get(values.get("SKY", ""), ("기상 상태 미상", "unknown"))


def _recommendation(temperature: float, icon_code: str) -> tuple[str, str]:
    if icon_code in {"rain", "rain-snow", "snow"}:
        return "indoor", "강수 가능성이 있어 실내 활동을 권장합니다."
    if temperature < 5:
        return "indoor", "기온이 낮아 따뜻한 실내 활동을 권장합니다."
    if temperature >= 33:
        return "indoor", "기온이 매우 높아 한낮의 야외 활동을 피하는 것이 좋습니다."
    if icon_code in {"partly-cloudy", "cloudy", "unknown"}:
        return "mixed", "날씨 변화를 확인하며 실내외 활동을 함께 계획해 보세요."
    return "outdoor", "강수 신호가 없고 기온이 무난해 야외 활동에 적합합니다."


def _parse_payload(payload: dict[str, Any], city: str, now: datetime) -> WeatherResponse:
    response = payload.get("response") or {}
    header = response.get("header") or {}
    if str(header.get("resultCode", "")) != "00":
        raise WeatherUpstreamError(str(header.get("resultMsg") or "기상청 API 오류"))

    raw_items = (((response.get("body") or {}).get("items") or {}).get("item") or [])
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    if not isinstance(raw_items, list) or not raw_items:
        raise WeatherUpstreamError("기상청 응답에 예보 항목이 없습니다.")

    forecasts: dict[datetime, dict[str, str]] = {}
    for item in raw_items:
        try:
            forecast_at = datetime.strptime(
                f"{item['fcstDate']}{item['fcstTime']}", "%Y%m%d%H%M"
            ).replace(tzinfo=KST)
        except (KeyError, TypeError, ValueError):
            continue
        forecasts.setdefault(forecast_at, {})[str(item.get("category", ""))] = str(
            item.get("fcstValue", "")
        )

    candidates = [entry for entry in sorted(forecasts.items()) if "T1H" in entry[1]]
    if not candidates:
        raise WeatherUpstreamError("기온 예보를 찾을 수 없습니다.")

    current = now.astimezone(KST)
    selected_at, values = next(
        ((at, values) for at, values in candidates if at >= current), candidates[-1]
    )
    try:
        temperature = float(values["T1H"])
    except (TypeError, ValueError) as exc:
        raise WeatherUpstreamError("기온 값이 올바르지 않습니다.") from exc

    condition, icon_code = _condition(values)
    recommendation, reason = _recommendation(temperature, icon_code)

    return WeatherResponse(**{
        "city": city,
        "observed_at": selected_at.isoformat(),
        "temperature": temperature,
        "condition": condition,
        "icon_code": icon_code,
        "recommendation": recommendation,
        "recommendation_reason": reason,
        "source": "기상청 단기예보 조회서비스(초단기예보)",
    })


async def fetch_weather(
    settings: Settings,
    *,
    client: httpx.AsyncClient | None = None,
    now: datetime | None = None,
    force_refresh: bool = False,
) -> WeatherResponse:
    center = load_region(settings.region_path)["center"]
    nx, ny = latlng_to_grid(center["lat"], center["lng"])
    key = (nx, ny)

    async with _cache_lock:
        cached = _cache.get(key)
    if not force_refresh and cached and time.monotonic() - cached[0] < CACHE_TTL_SECONDS:
        return cached[1]

    api_key = settings.weather_api_key.get_secret_value().strip() if settings.weather_api_key else ""
    if not api_key:
        raise WeatherConfigurationError("WEATHER_API_KEY is not configured")

    current = now or datetime.now(KST)
    base = _latest_base_datetime(current)
    params = {
        "authKey": api_key,
        "pageNo": 1,
        "numOfRows": 1000,
        "dataType": "JSON",
        "base_date": base.strftime("%Y%m%d"),
        "base_time": base.strftime("%H%M"),
        "nx": nx,
        "ny": ny,
    }

    owns_client = client is None
    http_client = client or httpx.AsyncClient(timeout=settings.weather_timeout_seconds)
    try:
        response = await http_client.get(KMA_ULTRA_SHORT_FORECAST_URL, params=params)
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        # Do not chain: httpx errors embed the request URL (with authKey).
        raise WeatherUpstreamError("기상청 API 요청에 실패했습니다.") from None
    finally:
        if owns_client:
            await http_client.aclose()

    result = _parse_payload(payload, "jinju", current)
    async with _cache_lock:
        _cache[key] = (time.monotonic(), result)
    return result
