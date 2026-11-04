import sqlite3

from fastapi import APIRouter, Request

from app.services.places_repo import get_places_repo

router = APIRouter()


@router.get("/health", summary="Health check")
def health_check(request: Request):
    """data_version is None when the DB is missing or unreadable."""
    try:
        version = get_places_repo(request).meta().data_version
    except (sqlite3.Error, OSError, ValueError):
        version = None
    return {"status": "ok", "data_version": version}
