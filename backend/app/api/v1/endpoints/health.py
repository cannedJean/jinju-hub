import sqlite3
from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter()


def read_data_version(path: Path) -> str | None:
    """data_version from places.db meta (read-only); None when the DB is missing or unreadable."""
    try:
        if not path.is_file():
            return None
        con = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=False)
        try:
            row = con.execute("SELECT value FROM meta WHERE key='data_version'").fetchone()
        finally:
            con.close()
        return row[0] if row else None
    except sqlite3.Error:
        return None


@router.get("/health", summary="Health check")
def health_check(request: Request):
    return {"status": "ok", "data_version": read_data_version(request.app.state.settings.places_db_path)}
