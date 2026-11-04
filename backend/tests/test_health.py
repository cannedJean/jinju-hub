from pathlib import Path

from app.core.config import Settings


def test_health_reports_data_version(make_client, fixture_db_path, fixture_data_version):
    client = make_client(places_db_path=fixture_db_path)
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "data_version": fixture_data_version}


def test_health_without_db(make_client, tmp_path):
    client = make_client(places_db_path=tmp_path / "missing.db")
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "data_version": None}


def test_blank_secrets_are_none():
    s = Settings(_env_file=None, anthropic_api_key="  ", weather_api_key="")
    assert s.anthropic_api_key is None and s.weather_api_key is None
    assert Settings(_env_file=None, weather_api_key="k").weather_api_key.get_secret_value() == "k"


def test_settings_defaults_and_env(monkeypatch):
    s = Settings(_env_file=None)
    assert (s.app_name, s.api_prefix, s.anthropic_model, s.rate_limit) == ("JinjuHub API", "/api", "claude-opus-5-5", "10/minute")
    assert s.region_path.name == "region.yaml" and s.region_path.parent.name == "data"
    monkeypatch.setenv("PLACES_DB_PATH", "/tmp/x.db")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.com/, http://b.com")
    s = Settings(_env_file=None)
    assert s.places_db_path == Path("/tmp/x.db")
    assert s.allowed_origins == ["http://a.com", "http://b.com"]


def test_cors_only_allowed_origins(make_client, tmp_path):
    client = make_client(places_db_path=tmp_path / "m.db", allowed_origins=["http://ok.test"])
    ok = client.get("/api/health", headers={"Origin": "http://ok.test"})
    bad = client.get("/api/health", headers={"Origin": "http://evil.test"})
    assert ok.headers.get("access-control-allow-origin") == "http://ok.test"
    assert "access-control-allow-origin" not in bad.headers
