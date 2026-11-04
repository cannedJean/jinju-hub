from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"


class Settings(BaseSettings):
    app_name: str = "JinjuHub API"
    api_prefix: str = "/api"
    database_url: str = "sqlite:///./jinjuhub.db"
    # ALLOWED_ORIGINS: comma-separated (or JSON list) in the environment.
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    places_db_path: Path = DATA_DIR / "places.db"
    report_path: Path = DATA_DIR / "report.json"
    # Copy of config/region.yaml so Render can deploy backend/ alone.
    region_path: Path = DATA_DIR / "region.yaml"
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-opus-5-5"
    anthropic_effort: str = "low"
    anthropic_max_tokens: int = 4096
    anthropic_timeout_seconds: float = 30.0
    weather_api_key: SecretStr | None = None
    weather_timeout_seconds: float = 10.0
    rate_limit: str = "10/minute"
    demo_date_override_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("anthropic_api_key", "weather_api_key", mode="before")
    @classmethod
    def _blank_secret_is_unset(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        if isinstance(v, SecretStr) and not v.get_secret_value().strip():
            return None
        return v

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            s = v.strip()
            if s.startswith("["):
                import json

                v = json.loads(s)
            else:
                v = s.split(",")
        return [o.strip().rstrip("/") for o in v if o and o.strip()]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
