from pathlib import Path

from app.core.config import Settings

EXAMPLE = Path(__file__).resolve().parents[1] / ".env.example"


def test_env_example_loads_as_settings_with_defaults(tmp_path):
    # Copy the committed example verbatim, as the README tells developers to do.
    copy = tmp_path / ".env"
    copy.write_text(EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    s = Settings(_env_file=copy)
    assert s.demo_date_override_enabled is True
    assert s.database_url.startswith("sqlite")
    assert s.rate_limit == "10/minute"
    assert s.anthropic_model
    assert s.anthropic_api_key is None and s.weather_api_key is None
    assert s.allowed_origins
    assert s.places_db_path.name == "places.db"
