"""places.db writer (atomic) and previous-snapshot reader. The schema is the backend contract."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
import time
from contextlib import closing
from datetime import datetime
from pathlib import Path
from typing import Any

from .curation import BadgeDef
from .models import Place, PreviousSnapshot, RawRecord
from .raw_store import KST

SCHEMA_VERSION = "1"
_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_LOCKED_MSG = "places.db가 다른 프로세스(로컬 백엔드)에서 열려 있습니다 — 백엔드를 중지하거나 `--out`을 사용하세요"

_PLACE_COLS = (
    "id", "category", "title", "title_norm", "summary", "overview", "addr", "lat", "lng", "geo_status",
    "phone", "homepage", "hours", "closed_days", "fee", "parking", "menu", "start_date", "end_date",
    "date_undecided", "date_year", "hero_image", "is_collection", "jinju8_rank", "tags", "venue_place_ids",
)


def _j(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _place_row(p: Place) -> tuple:
    return (
        p.id, p.category, p.title, p.title_norm, p.summary, p.overview, p.addr, p.lat, p.lng, p.geo_status,
        p.phone, p.homepage, p.hours, p.closed_days, p.fee, p.parking, p.menu,
        p.start_date.isoformat() if p.start_date else None,
        p.end_date.isoformat() if p.end_date else None,
        int(p.date_undecided), p.date_year, p.hero_image, int(p.is_collection), p.jinju8_rank,
        _j(p.tags), _j(p.venue_place_ids),
    )


def _image_rows(p: Place) -> list[tuple]:
    return [(p.id, i.url, i.source, i.license, i.sort) for i in p.images]


def _badge_row(b: BadgeDef) -> tuple:
    rule = {"eligible_place_ids": list(b.eligible_place_ids), "festival_windows": list(b.festival_windows)}
    return (b.id, b.label, b.description, int(b.required), _j(rule))


def compute_content_hash(places: list[Place], aliases: dict[str, str], badges: list[BadgeDef]) -> str:
    """sha256 over canonical sorted rows of places/images/aliases/badges (no timestamps)."""
    doc = {
        "places": sorted((list(_place_row(p)) for p in places), key=lambda r: r[0]),
        "images": sorted((list(r) for p in places for r in _image_rows(p)), key=_j),
        "aliases": sorted([k, v] for k, v in aliases.items()),
        "badges": sorted((list(_badge_row(b)) for b in badges), key=lambda r: r[0]),
    }
    return hashlib.sha256(json.dumps(doc, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def fts_trigram_supported(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("CREATE VIRTUAL TABLE temp._fts_probe USING fts5(x, tokenize='trigram')")
        conn.execute("DROP TABLE temp._fts_probe")
        return True
    except sqlite3.Error:
        return False


def _integrity_ok(conn: sqlite3.Connection) -> bool:
    return conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def _build(tmp: Path, places, aliases, badges, meta, id_order) -> None:
    with closing(sqlite3.connect(tmp)) as con:
        con.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
        fts = fts_trigram_supported(con)
        if fts:
            con.execute(
                "CREATE VIRTUAL TABLE places_fts USING fts5(title, addr, overview, content='places', "
                "content_rowid='rowid', tokenize='trigram')"
            )
        marks = ",".join("?" * len(_PLACE_COLS))
        con.executemany(
            f"INSERT INTO places ({','.join(_PLACE_COLS)}, updated_at) VALUES ({marks},?)",
            [_place_row(p) + (p.updated_at,) for p in places],
        )
        con.executemany("INSERT INTO place_images VALUES (?,?,?,?,?)", [r for p in places for r in _image_rows(p)])
        con.executemany(
            "INSERT INTO place_sources VALUES (?,?,?,?,?,?)",
            [(p.id, s.source, s.source_id, s.source_url, s.fetched_at.isoformat(), _j(s.raw))
             for p in places for s in p.sources],
        )
        con.executemany("INSERT INTO place_aliases VALUES (?,?)", sorted(aliases.items()))
        con.executemany("INSERT INTO badges VALUES (?,?,?,?,?)", [_badge_row(b) for b in badges])
        con.executemany("INSERT INTO id_order VALUES (?,?)", sorted(id_order.items()))
        full_meta = {**meta, "fts": "trigram" if fts else "none", "schema_version": SCHEMA_VERSION}
        con.executemany("INSERT INTO meta VALUES (?,?)", [(k, str(v)) for k, v in full_meta.items()])
        if fts:
            con.execute("INSERT INTO places_fts(places_fts) VALUES('rebuild')")
        con.commit()
        if not _integrity_ok(con):
            raise RuntimeError("places.db integrity_check failed; existing file left untouched")


def write_places_db(
    path: Path,
    places: list[Place],
    aliases: dict[str, str],
    badges: list[BadgeDef],
    meta: dict[str, str],
    id_order: dict[str, int],
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".db.tmp")
    tmp.unlink(missing_ok=True)
    try:
        _build(tmp, places, aliases, badges, meta, id_order)
        for attempt in range(4):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 3:
                    print(_LOCKED_MSG, file=sys.stderr)
                    raise SystemExit(2) from None
                time.sleep(0.5)
    finally:
        tmp.unlink(missing_ok=True)


def read_previous(path: Path) -> PreviousSnapshot | None:
    path = Path(path)
    if not path.exists():
        return None
    with closing(sqlite3.connect(path)) as con:
        meta = dict(con.execute("SELECT key, value FROM meta"))
        place_count = con.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        id_order = {pid: seq for pid, seq in con.execute("SELECT place_id, issued_seq FROM id_order")}
        aliases = dict(con.execute("SELECT old_id, new_id FROM place_aliases"))
        source_index: dict[str, str] = {}
        raw_by_source: dict[str, list[RawRecord]] = {}
        modified_by_key: dict[str, str] = {}
        pending: set[str] = set()
        seen: set[str] = set()
        for pid, source, sid, fetched_at, raw_json in con.execute(
            "SELECT place_id, source, source_id, fetched_at, raw_json FROM place_sources"
        ):
            key = f"{source}:{sid}"
            source_index.setdefault(key, pid)
            if source == "curation" or key in seen:
                continue
            seen.add(key)
            payload = json.loads(raw_json) if raw_json else {}
            raw_by_source.setdefault(source, []).append(
                RawRecord(source=source, source_id=sid, payload=payload, fetched_at=datetime.fromisoformat(fetched_at))
            )
            if source == "tourapi.area":
                mt = (payload.get("list") or {}).get("modifiedtime")
                if mt:
                    modified_by_key[key] = mt
            if payload.get("detail_pending") or "detail_error" in payload:
                pending.add(key)
    try:
        generated_at = datetime.fromisoformat(meta["generated_at"])
    except (KeyError, ValueError):
        generated_at = datetime.fromtimestamp(0, KST)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=KST)
    return PreviousSnapshot(
        generated_at=generated_at,
        place_count=place_count,
        source_index=source_index,
        id_order=id_order,
        aliases=aliases,
        raw_by_source=raw_by_source,
        modified_by_key=modified_by_key,
        detail_pending_keys=pending,
        reused_streak=int(meta.get("reused_streak") or 0),
    )
