"""Shared test helpers for the pipeline test suite."""
from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

from jinju_pipeline.models import RawRecord
from jinju_pipeline.raw_store import KST

FIXTURES = Path(__file__).resolve().parent / "fixtures"
NOW = datetime(2026, 11, 4, 3, 0, tzinfo=KST)


def _load(rel: str):
    return json.loads((FIXTURES / rel).read_text(encoding="utf-8"))


def _items(body: dict) -> list[dict]:
    return body["response"]["body"]["items"]["item"]


def city_raws_from_fixture(kind: str) -> list[RawRecord]:
    body = _load(f"jinju_city/{kind}_p1.json")
    return [
        RawRecord(source=f"jinju_city.{kind}", source_id=str(i["idx"]), payload=i, fetched_at=NOW)
        for i in body["results"]
    ]


def make_tour_raw_126508() -> RawRecord:
    """Full tourapi.area payload (list + common + intro + images) for contentid 126508."""
    lst = next(i for i in _items(_load("tourapi/area_12_p1.json")) if i["contentid"] == "126508")
    payload = {
        "list": copy.deepcopy(lst),
        "common": _items(_load("tourapi/detail_common_126508.json"))[0],
        "intro": _items(_load("tourapi/detail_intro_126508_12.json"))[0],
        "images": _items(_load("tourapi/detail_image_126508.json")),
    }
    return RawRecord(source="tourapi.area", source_id="126508", payload=payload, fetched_at=NOW)


def make_tour_raw_hidden() -> RawRecord:
    lst = make_tour_raw_126508().payload["list"]
    lst["showflag"] = "0"
    return RawRecord(source="tourapi.area", source_id="126508", payload={"list": lst, "hidden": True},
                     fetched_at=NOW)


# ---- A8 merge helpers ----
import itertools as _it
from datetime import datetime as _dt

from jinju_pipeline.models import CleanRecord, PreviousSnapshot

_seq = _it.count(1)


def rec(title, lat, lng, cat="sight", phone=None, addr=None, source="jinju_city.tourinfo",
        source_id=None, **kw) -> CleanRecord:
    return CleanRecord(
        source=source, source_id=source_id or f"u{next(_seq)}", category=cat, title=title,
        addr=addr, lat=lat, lng=lng, phone=phone,
        geo_status="ok" if lat is not None else "missing", fetched_at=NOW, **kw)


def city(name, id=None, lat=35.19, lng=128.08, **kw) -> CleanRecord:
    return rec(name, lat, lng, source="jinju_city.tourinfo", source_id=id or name, **kw)


def tour(name, id=None, lat=35.19, lng=128.08, **kw) -> CleanRecord:
    return rec(name, lat, lng, source="tourapi.area", source_id=id or name, **kw)


def tour2(name, id=None, lat=35.19, lng=128.08, **kw) -> CleanRecord:
    return rec(name, lat, lng, source="tourapi.area", source_id=id or f"{name}-2", **kw)


def snapshot_with(source_index: dict, order: list, aliases: dict | None = None) -> PreviousSnapshot:
    return PreviousSnapshot(
        generated_at=NOW, place_count=len(order), source_index=dict(source_index),
        id_order={i: n for n, i in enumerate(order)}, aliases=dict(aliases or {}),
        raw_by_source={}, modified_by_key={}, detail_pending_keys=set())


def snapshot_from(result) -> PreviousSnapshot:
    index = {s.key: p.id for p in result.places for s in p.sources}
    return snapshot_with(index, [p.id for p in result.places], result.aliases)
