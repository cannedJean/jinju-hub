from fastapi import APIRouter, HTTPException, Request

from app.schemas.weather import WeatherResponse
from app.services.weather_service import (
    WeatherConfigurationError,
    WeatherUpstreamError,
    fetch_weather,
)

router = APIRouter()


@router.get("/weather", response_model=WeatherResponse, summary="Get Jinju weather")
async def get_weather(request: Request):
    try:
        return await fetch_weather(request.app.state.settings)
    except WeatherConfigurationError:
        raise HTTPException(status_code=503, detail="기상청 API가 아직 설정되지 않았습니다.") from None
    except WeatherUpstreamError:
        raise HTTPException(status_code=502, detail="날씨 정보를 불러올 수 없습니다.") from None
