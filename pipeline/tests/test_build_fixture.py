"""Backend fixture DB: built offline from the recorded fixtures; content contract for Phase B tests.

Build: ``$env:BUILD_FIXTURE_OUT="..\\backend\\tests\\fixtures\\places_fixture.db"; python -m pytest tests/test_build_fixture.py``
"""
import json
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

import pytest

from jinju_pipeline.raw_store import KST
from jinju_pipeline.runner import run_pipeline

NOW = datetime(2026, 11, 4, 3, 0, tzinfo=KST)


def assert_fixture_db_contract(db: Path) -> None:
    with closing(sqlite3.connect(db)) as con:
        one = lambda sql, *a: con.execute(sql, a).fetchone()[0]  # noqa: E731
        assert one("select count(*) from places where title like '%냉면%'") >= 1
        assert one("select count(*) from places where category='food' and title like '%하연옥%' "
                   "and menu like '%냉면%'") == 1
        assert one("select count(*) from places where title like '%촉석루%'") >= 1
        lat, lng = con.execute("select lat, lng from places where title='진주성' and category='sight'").fetchone()
        assert abs(lat - 35.19) < 0.01 and abs(lng - 128.08) < 0.01
        assert one("select count(*) from places where title='국립진주박물관' and category='culture' "
                   "and tags like '%\"indoor\"%'") == 1
        assert one("select start_date from places where category='festival' and title like '%유등%'") == "2026-10-03"
        assert one("select end_date from places where category='festival' and title like '%유등%'") == "2026-10-18"
        assert one("select count(*) from places where tags like '%\"indoor\"%'") >= 1
        ranks = [r[0] for r in con.execute("select jinju8_rank from places where jinju8_rank is not null")]
        assert sorted(ranks) == list(range(1, 9))
        assert one("select count(*) from badges") == 6
        assert one("select count(*) from places where category='food'") >= 3
        assert one("select count(*) from places where category='stay'") >= 1
        assert json.loads(one("select value from meta where key='festival_programs'"))


async def _build(settings, transport) -> Path:
    _, gate = await run_pipeline(settings, incremental=False, today=date(2026, 11, 4), now=NOW,
                                 transport=transport)
    assert gate.passed, gate.failures
    return settings.output_db


async def test_fixture_db_contract(tmp_settings, recorded_transport):
    assert_fixture_db_contract(await _build(tmp_settings, recorded_transport))


@pytest.mark.skipif(not os.environ.get("BUILD_FIXTURE_OUT"), reason="set BUILD_FIXTURE_OUT to build the backend fixture")
async def test_build_backend_fixture(tmp_settings, recorded_transport):
    out = Path(os.environ["BUILD_FIXTURE_OUT"]).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(await _build(tmp_settings, recorded_transport), out)
    assert_fixture_db_contract(out)
