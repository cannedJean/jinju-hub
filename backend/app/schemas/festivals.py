from datetime import date

from pydantic import BaseModel, Field

from app.services.festival_status import FestivalStatus


class FestivalOut(BaseModel):
    id: str
    title: str
    summary: str | None = None
    hero_image: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: FestivalStatus
    status_label: str
    venue_place_ids: list[str] = Field(default_factory=list)
    programs: list[str] = Field(default_factory=list)
    addr: str | None = None
    lat: float | None = None
    lng: float | None = None


class FestivalList(BaseModel):
    today: str
    items: list[FestivalOut]
