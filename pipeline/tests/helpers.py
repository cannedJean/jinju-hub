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
