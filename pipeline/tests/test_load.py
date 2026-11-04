import json
import sqlite3
from contextlib import closing
from datetime import date, datetime

import pytest

from jinju_pipeline import load
from jinju_pipeline.curation import BadgeDef
from jinju_pipeline.load import (
    compute_content_hash,
    fts_trigram_supported,
    read_previous,
    write_places_db,
)
from jinju_pipeline.models import CleanRecord, ImageRef, Place, RawRecord
from jinju_pipeline.raw_store import KST

NOW = datetime(2026, 11, 4, 3, 0, tzinfo=KST)


def _clean(source, sid, raw, title="촉석루"):
    return CleanRecord(source=source, source_id=sid, source_url=f"https://x/{sid}", category="sight",
                       title=title, geo_status="ok", raw=raw, fetched_at=NOW)


@pytest.fixture
def sample_places():
    p1 = Place(
        id="jh-aaa", category="sight", title="촉석루", title_norm="촉석루", overview="진주성 안의 누각",
        addr="진주시 남강로 626", lat=35.19, lng=128.08, geo_status="ok", tags=["night_view", "outdoor"],
        images=[ImageRef(url="https://img/1.jpg", source="tourapi.area", license="Type1", sort=0)],
        hero_image="https://img/1.jpg", is_collection=True, jinju8_rank=1, updated_at="2026-11-04T09:00:00+09:00",
        sources=[
            _clean("tourapi.area", "126508", {"list": {"modifiedtime": "20260101120000"}, "common": {}}),
            _clean("jinju_city.tourinfo", "7", {"idx": 7}),
        ],
    )
    p2 = Place(
        id="jh-bbb", category="festival", title="진주남강유등축제", title_norm="진주남강유등축제",
        geo_status="missing", start_date=date(2026, 10, 1), end_date=date(2026, 10, 14), date_year=2026,
        venue_place_ids=["jh-aaa"], updated_at="2026-11-04T09:00:00+09:00",
        sources=[
            _clean("tourapi.area", "999", {"list": {"modifiedtime": "20260202"}, "detail_pending": True}),
            _clean("tourapi.area", "998", {"list": {"modifiedtime": "20260203"}, "detail_error": "boom"}),
            _clean("curation", "fest", {"curated": True}),
        ],
    )
    return [p1, p2]


@pytest.fixture
def sample_badges():
    return [BadgeDef(id="b1", label="배지", description="설명", required=2,
                     eligible_place_ids=["jh-aaa"], festival_windows=[{"start": "2026-10-01"}])]


META = {"data_version": "R1", "generated_at": "2026-11-04T09:00:00+09:00", "reused_streak": "1"}


def _write(db, places, badges, aliases=None):
    aliases = aliases if aliases is not None else {"jh-old": places[0].id}
    write_places_db(db, places, aliases, badges, dict(META), {p.id: i for i, p in enumerate(places)})


def test_write_and_read_roundtrip(tmp_path, sample_places, sample_badges):
    db = tmp_path / "places.db"
    _write(db, sample_places, sample_badges)
    prev = read_previous(db)
    assert prev.place_count == len(sample_places) and prev.aliases == {"jh-old": sample_places[0].id}
    assert prev.source_index[sample_places[0].sources[0].key] == sample_places[0].id
    assert prev.raw_by_source and all(isinstance(r, RawRecord) for rs in prev.raw_by_source.values() for r in rs)
    assert "curation" not in prev.raw_by_source
    assert prev.id_order == {"jh-aaa": 0, "jh-bbb": 1}
    assert prev.modified_by_key == {
        "tourapi.area:126508": "20260101120000",
        "tourapi.area:999": "20260202",
        "tourapi.area:998": "20260203",
    }
    assert prev.detail_pending_keys == {"tourapi.area:999", "tourapi.area:998"}
    assert prev.reused_streak == 1
    assert prev.generated_at == datetime(2026, 11, 4, 9, 0, tzinfo=KST)
    rec = prev.raw_by_source["jinju_city.tourinfo"][0]
    assert rec.source_id == "7" and rec.payload == {"idx": 7}


def test_schema_contract(tmp_path, sample_places, sample_badges):
    db = tmp_path / "places.db"
    _write(db, sample_places, sample_badges)
    with closing(sqlite3.connect(db)) as con:
        meta = dict(con.execute("select key, value from meta"))
        assert meta["schema_version"] == "1" and meta["data_version"] == "R1"
        assert meta["fts"] in ("trigram", "none")
        row = con.execute("select tags, venue_place_ids, start_date, date_undecided, is_collection from places "
                          "where id='jh-bbb'").fetchone()
        assert json.loads(row[1]) == ["jh-aaa"] and row[2] == "2026-10-01"
        assert json.loads(con.execute("select tags from places where id='jh-aaa'").fetchone()[0]) == ["night_view", "outdoor"]
        b = con.execute("select id, label, description, required, rule_json from badges").fetchone()
        assert b[3] == 2 and json.loads(b[4]) == {"eligible_place_ids": ["jh-aaa"],
                                                  "festival_windows": [{"start": "2026-10-01"}]}
        assert con.execute("select count(*) from place_sources").fetchone()[0] == 5
        assert con.execute("select place_id,url,source,license,sort from place_images").fetchall() == [
            ("jh-aaa", "https://img/1.jpg", "tourapi.area", "Type1", 0)]
        idx = {r[1] for r in con.execute("select * from sqlite_master where type='index'")}
        assert any("category" in (n or "") for n in idx) and any("lat" in (n or "") for n in idx)


def test_fts_query_korean_trigram(tmp_path, sample_places, sample_badges):
    db = tmp_path / "places.db"
    _write(db, sample_places, sample_badges)
    with closing(sqlite3.connect(db)) as con:
        if fts_trigram_supported(con):
            assert con.execute("select count(*) from places_fts where places_fts match ?", ("촉석루",)).fetchone()[0] >= 1
            assert dict(con.execute("select key, value from meta"))["fts"] == "trigram"


def test_atomic_replace_keeps_old_on_failure(tmp_path, monkeypatch, sample_places, sample_badges):
    db = tmp_path / "places.db"
    _write(db, sample_places, sample_badges)
    before = db.read_bytes()
    monkeypatch.setattr(load, "_integrity_ok", lambda conn: False)
    with pytest.raises(RuntimeError):
        _write(db, sample_places[:1], sample_badges)
    assert db.read_bytes() == before
    assert not db.with_suffix(".db.tmp").exists()


def test_replace_permission_error_exits_2(tmp_path, monkeypatch, sample_places, sample_badges, capsys):
    db = tmp_path / "places.db"
    calls = []

    def boom(a, b):
        calls.append(1)
        raise PermissionError("locked")

    monkeypatch.setattr(load.os, "replace", boom)
    monkeypatch.setattr(load.time, "sleep", lambda s: None)
    with pytest.raises(SystemExit) as e:
        _write(db, sample_places, sample_badges)
    assert e.value.code == 2 and len(calls) == 4
    assert "places.db가 다른 프로세스" in capsys.readouterr().err
    assert not db.with_suffix(".db.tmp").exists()


def test_read_previous_missing_returns_none(tmp_path):
    assert read_previous(tmp_path / "nope.db") is None


def test_content_hash_stable_and_sensitive(sample_places, sample_badges):
    h1 = compute_content_hash(sample_places, {"a": "b"}, sample_badges)
    assert h1 == compute_content_hash(list(reversed(sample_places)), {"a": "b"}, sample_badges)
    changed = [sample_places[0].model_copy(update={"updated_at": "2030-01-01T00:00:00+09:00"}), sample_places[1]]
    assert h1 == compute_content_hash(changed, {"a": "b"}, sample_badges)
    changed2 = [sample_places[0].model_copy(update={"title": "다른"}), sample_places[1]]
    assert h1 != compute_content_hash(changed2, {"a": "b"}, sample_badges)
    assert h1 != compute_content_hash(sample_places, {"a": "c"}, sample_badges)
