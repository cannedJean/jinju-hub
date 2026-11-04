"""Pipeline settings (env vars and pipeline/.env)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_ROOT = REPO_ROOT / "pipeline"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PIPELINE_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    data_go_kr_key: SecretStr | None = None
    repo_root: Path = REPO_ROOT
    region_path: Path = REPO_ROOT / "config" / "region.yaml"
    raw_dir: Path = PIPELINE_ROOT / "data" / "raw"
    work_dir: Path = PIPELINE_ROOT / "data" / "work"
    state_dir: Path = PIPELINE_ROOT / "data" / "state"
    curation_dir: Path = PIPELINE_ROOT / "curation"
    output_db: Path = REPO_ROOT / "backend" / "app" / "data" / "places.db"
    output_report: Path = REPO_ROOT / "backend" / "app" / "data" / "report.json"
    # Previous snapshot (ID inheritance, aliases, 80% gate). None = output_db. `run --out` keeps it on the
    # canonical db so writing elsewhere (e.g. while the backend locks places.db) loses nothing.
    previous_db: Path | None = None
    daily_quota: int = 900
    run_quota: int | None = None
    city_concurrency: int = 4
    city_min_interval: float = 0.25
    tour_concurrency: int = 5
    gate_min_first_run: int = 300

    @field_validator("data_go_kr_key", mode="before")
    @classmethod
    def _blank_secret_is_unset(cls, v):
        # `DATA_GO_KR_KEY=` (empty template line) or whitespace must behave like an unset key.
        if isinstance(v, str) and not v.strip():
            return None
        if isinstance(v, SecretStr) and not v.get_secret_value().strip():
            return None
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
