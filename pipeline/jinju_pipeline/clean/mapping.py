"""Per-source field mapping tables.

CITY_FIELDS: jinju_city kind -> {source key: CleanRecord field}. Notes:
- xposition/yposition -> coords (order is auto-detected, the API sometimes swaps them).
- lodging: overview falls back to `information` when `content` is empty (CITY_OVERVIEW_FALLBACK).
- heritage asset* fields are kept in `raw` only.

TOUR_INTRO_FIELDS: contenttypeid -> {field: spec}. Spec syntax: "a|b" first non-empty,
"a~b" both joined with " ~ ", "a+b" both joined with a newline, None = not available.
"phone" is the fallback when detailCommon2/list `tel` is empty (recorded 2026-11-04: list `tel` was
empty for all 57 type-12 items; the number lives in the intro `infocenter*` field).
"""
from __future__ import annotations

_COMMON = {
    "name": "title", "address": "addr", "phone": "phone", "homepage": "homepage",
    "content": "overview", "images": "images", "xposition": "coords", "yposition": "coords",
}

CITY_FIELDS: dict[str, dict[str, str]] = {
    "tourinfo": {**_COMMON, "usehour": "hours", "fee": "fee", "parking": "parking"},
    "restaurant": {**_COMMON, "businesshour": "hours", "holiday": "closed_days", "menuprice": "menu"},
    "festival": {**_COMMON, "sdate": "start_date", "edate": "end_date", "undecided": "date_undecided",
                 "fee": "fee", "parking": "parking"},
    "heritage": {**_COMMON, "usehour": "hours", "fee": "fee", "parking": "parking"},
    "lodging": {**_COMMON, "checktime": "hours", "park": "parking"},
}
CITY_OVERVIEW_FALLBACK = {"lodging": "information"}

CITY_SOURCE_URL_TYPE = {
    "tourinfo": "tourinfo", "restaurant": "restaurant", "festival": "festival",
    "heritage": "asset", "lodging": "lodging",
}

TOUR_INTRO_FIELDS: dict[str, dict[str, str | None]] = {
    "12": {"phone": "infocenter", "hours": "usetime", "closed_days": "restdate", "parking": "parking", "fee": "usefee"},
    "14": {"phone": "infocenterculture", "hours": "usetimeculture", "closed_days": "restdateculture", "parking": "parkingculture",
           "fee": "usefee"},
    "15": {"phone": "sponsor1tel|sponsor2tel", "hours": "playtime|usetimefestival", "closed_days": None, "parking": None,
           "fee": "usetimefestival", "start_date": "eventstartdate", "end_date": "eventenddate"},
    "28": {"phone": "infocenterleports", "hours": "usetimeleports", "closed_days": "restdateleports", "parking": "parkingleports",
           "fee": "usefeeleports"},
    "32": {"phone": "infocenterlodging", "hours": "checkintime~checkouttime", "closed_days": None, "parking": "parkinglodging",
           "fee": None},
    "38": {"phone": "infocentershopping", "hours": "opentime", "closed_days": "restdateshopping", "parking": "parkingshopping",
           "fee": None},
    "39": {"phone": "infocenterfood", "hours": "opentimefood", "closed_days": "restdatefood", "parking": "parkingfood",
           "fee": None, "menu": "firstmenu+treatmenu"},
    "25": {"phone": "infocentertourcourse"},
}
