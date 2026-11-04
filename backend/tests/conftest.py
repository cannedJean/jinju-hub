import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings

FIXTURE_DB = Path(__file__).parent / "fixtures" / "places_fixture.db"


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Tests never read backend/.env or real secrets from the environment."""
    for k in ("ANTHROPIC_API_KEY", "WEATHER_API_KEY", "DATABASE_URL", "ALLOWED_ORIGINS",
              "PLACES_DB_PATH", "RATE_LIMIT", "ANTHROPIC_MODEL", "DEMO_DATE_OVERRIDE_ENABLED"):
        monkeypatch.delenv(k, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def fixture_db_path() -> Path:
    return FIXTURE_DB


@pytest.fixture
def fixture_data_version() -> str:
    con = sqlite3.connect(FIXTURE_DB)
    try:
        return con.execute("SELECT value FROM meta WHERE key='data_version'").fetchone()[0]
    finally:
        con.close()


@pytest.fixture
def make_client():
    """Build a started TestClient (lifespan runs, repo closed on teardown) with Settings(_env_file=None, **overrides)."""
    from app.main import create_app

    clients = []

    def _make(**overrides) -> TestClient:
        c = TestClient(create_app(Settings(_env_file=None, **overrides)), raise_server_exceptions=False)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
