from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.schemas.places import Marker, PlaceDetail, PlacePage, PlaceQuery
from app.services.places_repo import PlacesRepo, get_places_repo

router = APIRouter()


def _floats(raw: str | None, n: int, name: str) -> tuple[float, ...] | None:
    if raw is None or raw == "":
        return None
    try:
        vals = tuple(float(x) for x in raw.split(","))
    except ValueError:
        vals = ()
    if len(vals) != n or not all(v == v and abs(v) != float("inf") for v in vals):
        raise HTTPException(status_code=422, detail=f"invalid_{name}")
    return vals


def place_query(
    q: Annotated[str | None, Query(max_length=200)] = None,
    category: Annotated[list[str] | None, Query()] = None,
    tags: Annotated[list[str] | None, Query()] = None,
    bbox: Annotated[str | None, Query(description="minLng,minLat,maxLng,maxLat")] = None,
    near: Annotated[str | None, Query(description="lat,lng")] = None,
    radius: Annotated[int | None, Query(ge=1, le=20000)] = None,
    sort: Literal["relevance", "distance", "name", "collection"] = "relevance",
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> PlaceQuery:
    return PlaceQuery(
        q=q, category=category or [], tags=tags or [], bbox=_floats(bbox, 4, "bbox"),
        near=_floats(near, 2, "near"), radius=radius, sort=sort, page=page, size=size)


@router.get("/places", response_model=PlacePage)
def list_places(query: PlaceQuery = Depends(place_query), repo: PlacesRepo = Depends(get_places_repo)):
    return repo.search(query)


# Registered before /places/{place_id} so "markers" is not captured as an id.
@router.get("/places/markers", response_model=list[Marker])
def list_markers(
    response: Response,
    category: Annotated[list[str] | None, Query()] = None,
    repo: PlacesRepo = Depends(get_places_repo),
):
    response.headers["Cache-Control"] = "public, max-age=600"
    response.headers["ETag"] = repo.meta().data_version
    return repo.markers(category or None)


@router.get("/places/{place_id}", response_model=PlaceDetail)
def get_place(place_id: str, repo: PlacesRepo = Depends(get_places_repo)):
    place = repo.get(place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="place_not_found")
    return place
