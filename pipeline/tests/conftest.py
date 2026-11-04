from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture_text():
    base = Path(__file__).resolve().parent / "fixtures"

    def _read(relpath: str) -> str:
        return (base / relpath).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def fixture_json():
    import json

    base = Path(__file__).resolve().parent / "fixtures"

    def _read(relpath: str):
        return json.loads((base / relpath).read_text(encoding="utf-8"))

    return _read


@pytest.fixture
def ctx_factory(tmp_path):
    from datetime import date, datetime

    import httpx

    from jinju_pipeline.http import QuotaLedger
    from jinju_pipeline.raw_store import KST, RawStore, new_run_id
    from jinju_pipeline.region import load_region
    from jinju_pipeline.settings import Settings
    from jinju_pipeline.sources.base import make_context

    repo = Path(__file__).resolve().parents[2]

    def _make(transport, **settings_overrides):
        overrides = {"city_min_interval": 0.0, "raw_dir": tmp_path / "raw"}
        overrides.update(settings_overrides)
        settings = Settings(_env_file=None, **overrides)
        now = datetime.now(KST)
        return make_context(
            client=httpx.AsyncClient(transport=transport, follow_redirects=True),
            store=RawStore(settings.raw_dir, new_run_id(now)),
            ledger=QuotaLedger(None, 10**9, today=date.today()),
            settings=settings,
            region=load_region(repo / "config" / "region.yaml"),
        )

    return _make
