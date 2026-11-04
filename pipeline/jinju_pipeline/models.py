"""Core data models for the pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

Category = Literal["sight", "culture", "food", "stay", "festival", "shopping", "leisure", "course"]
GeoStatus = Literal["ok", "missing", "out_of_region"]


class RawRecord(BaseModel):
    source: str
    source_id: str
    payload: dict[str, Any]
    fetched_at: datetime

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"


class SourceResult(BaseModel):
    source: str
    status: Literal["ok", "failed", "reused_previous"]
    records: list[RawRecord]
    calls: int = 0
    error: str | None = None


class ImageRef(BaseModel):
    url: str
    source: str
    license: str
    sort: int = 0


class CleanRecord(BaseModel):
    source: str
    source_id: str
    source_url: str | None = None
    category: Category
    title: str
    addr: str | None = None
    lat: float | None = None
    lng: float | None = None
    geo_status: GeoStatus
    phone: str | None = None
    homepage: str | None = None
    overview: str | None = None
    hours: str | None = None
    closed_days: str | None = None
    fee: str | None = None
    parking: str | None = None
    menu: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    date_undecided: bool = False
    images: list[ImageRef] = Field(default_factory=list)
    raw: dict[str, Any] = Field(default_factory=dict)
    fetched_at: datetime

    @property
    def key(self) -> str:
        return f"{self.source}:{self.source_id}"


class Place(BaseModel):
    id: str
    category: Category
    title: str
    title_norm: str
    summary: str | None = None
    overview: str | None = None
    addr: str | None = None
    lat: float | None = None
    lng: float | None = None
    geo_status: GeoStatus
    phone: str | None = None
    homepage: str | None = None
    hours: str | None = None
    closed_days: str | None = None
    fee: str | None = None
    parking: str | None = None
    menu: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    date_undecided: bool = False
    date_year: int | None = None
    hero_image: str | None = None
    images: list[ImageRef] = Field(default_factory=list)
    sources: list[CleanRecord] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_collection: bool = False
    jinju8_rank: int | None = None
    venue_place_ids: list[str] = Field(default_factory=list)
    updated_at: str


@dataclass
class PreviousSnapshot:
    """State read back from the previous run's output (reader implemented in A10)."""

    generated_at: datetime
    place_count: int
    source_index: dict[str, str]  # source key -> place id
    id_order: dict[str, int]  # place id -> issue sequence (smaller = issued earlier)
    aliases: dict[str, str]
    raw_by_source: dict[str, list[RawRecord]]
    modified_by_key: dict[str, str]
    detail_pending_keys: set[str]
    reused_streak: int = 0
