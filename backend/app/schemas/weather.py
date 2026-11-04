from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class WeatherResponse(BaseModel):
    city: str
    observed_at: datetime
    temperature: float
    condition: str
    icon_code: str
    recommendation: Literal["outdoor", "indoor", "mixed"]
    recommendation_reason: str
    source: str
