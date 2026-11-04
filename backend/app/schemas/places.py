from typing import Literal

from pydantic import BaseModel, Field


class PlaceQuery(BaseModel):
    q: str | None = None
    category: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    bbox: tuple[float, float, float, float] | None = None  # (min_lng, min_lat, max_lng, max_lat)
    near: tuple[float, float] | None = None  # (lat, lng)
    radius: int | None = Field(default=None, le=20000)
    sort: Literal["relevance", "distance", "name", "collection"] = "relevance"
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=50)


class ImageOut(BaseModel):
    url: str
    license: str | None = None
    source: str | None = None


class PlaceSummary(BaseModel):
    id: str
    category: str
    title: str
    summary: str | None = None
    addr: str | None = None
    lat: float | None = None
    lng: float | None = None
    hero_image: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_collection: bool = False
    jinju8_rank: int | None = None
    distance_m: int | None = None


class PlacePage(BaseModel):
    items: list[PlaceSummary]
    total: int
    page: int
    size: int
    totalPages: int


class Marker(BaseModel):
    id: str
    lat: float
    lng: float
    category: str
    title: str
    is_collection: bool = False


class SourceOut(BaseModel):
    source: str
    source_url: str | None = None
    fetched_at: str | None = None


class PlaceDetail(PlaceSummary):
    overview: str | None = None
    phone: str | None = None
    homepage: str | None = None
    hours: str | None = None
    closed_days: str | None = None
    fee: str | None = None
    parking: str | None = None
    menu: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    date_undecided: bool = False
    images: list[ImageOut] = Field(default_factory=list)
    sources: list[SourceOut] = Field(default_factory=list)
    nearby: list[PlaceSummary] = Field(default_factory=list)
    canonical_id: str


class CategoryCount(BaseModel):
    code: str
    label: str
    count: int


class MetaOut(BaseModel):
    region: dict
    categories: list[CategoryCount]
    data_version: str
    generated_at: str
    attribution: str = "한국관광공사 TourAPI · 진주시 공공데이터"


class BadgeOut(BaseModel):
    id: str
    label: str
    description: str | None = None
    required: int = 0
    eligible_place_ids: list[str] = Field(default_factory=list)
    festival_windows: list = Field(default_factory=list)


class Jinju8Item(BaseModel):
    rank: int
    id: str
    title: str


class CollectionPlace(BaseModel):
    id: str
    category: str
    tags: list[str] = Field(default_factory=list)


class CollectionOut(BaseModel):
    collection_ids: list[str]
    jinju8: list[Jinju8Item]
    badges: list[BadgeOut]
    places: list[CollectionPlace]
