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


@pytest.fixture
def previous_snapshot():
    """Factory: previous_snapshot(raw_by_source=..., pending=..., generated_at=...)."""
    from datetime import datetime

    from jinju_pipeline.models import PreviousSnapshot
    from jinju_pipeline.raw_store import KST

    def _make(raw_by_source=None, pending=(), generated_at=None):
        raw = raw_by_source or {}
        return PreviousSnapshot(
            generated_at=generated_at or datetime(2026, 11, 1, 3, 0, tzinfo=KST),
            place_count=sum(len(v) for v in raw.values()),
            source_index={},
            id_order={},
            aliases={},
            raw_by_source=raw,
            modified_by_key={
                r.key: r.payload["list"]["modifiedtime"]
                for v in raw.values() for r in v if "list" in r.payload
            },
            detail_pending_keys=set(pending),
        )

    return _make


@pytest.fixture
def region(repo_root):
    from jinju_pipeline.region import load_region

    return load_region(repo_root / "config" / "region.yaml")


@pytest.fixture
def city_raws():
    from helpers import city_raws_from_fixture

    return city_raws_from_fixture("tourinfo")


@pytest.fixture
def tour_raw_126508():
    from helpers import make_tour_raw_126508

    return make_tour_raw_126508()


@pytest.fixture
def tour_raw_hidden():
    from helpers import make_tour_raw_hidden

    return make_tour_raw_hidden()
