"""Cleaning: RawRecord -> CleanRecord."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from jinju_pipeline.clean.category import map_category
from jinju_pipeline.clean.coords import normalize_coords
from jinju_pipeline.clean.festival import parse_date, parse_undecided
from jinju_pipeline.clean.mapping import (
    CITY_FIELDS,
    CITY_OVERVIEW_FALLBACK,
    CITY_SOURCE_URL_TYPE,
    TOUR_INTRO_FIELDS,
)
from jinju_pipeline.clean.phone import format_phone
from jinju_pipeline.clean.text import clean_text
from jinju_pipeline.clean.urls import extract_homepage, normalize_url
from jinju_pipeline.models import CleanRecord, ImageRef, RawRecord
from jinju_pipeline.region import Region

CITY_BASE = "http://www.jinju.go.kr"
CITY_LICENSE = "jinju_city_unverified"
TOUR_DEFAULT_LICENSE = "Type3"  # conservative when the license code is missing
TOUR_DETAIL_URL = "https://korean.visitkorea.or.kr/detail/ms_detail.do?cotid={}"
CITY_DETAIL_URL = "https://www.jinju.go.kr/tour/move_detail.do?type={}&idx={}"

__all__ = ["CleanResult", "clean_record", "clean_all"]


@dataclass
class CleanResult:
    records: list[CleanRecord] = field(default_factory=list)
    dropped: Counter[str] = field(default_factory=Counter)


def _s(v: Any) -> str | None:
    """Stringify and strip; empty -> None."""
    if v is None:
        return None
    v = str(v).strip()
    return v or None


def _intro_value(intro: dict, spec: str | None) -> str | None:
    if not spec:
        return None
    if "|" in spec:
        for k in spec.split("|"):
            if (v := clean_text(_s(intro.get(k)))):
                return v
        return None
    for sep, joiner in (("~", " ~ "), ("+", "\n")):
        if sep in spec:
            parts = [clean_text(_s(intro.get(k))) for k in spec.split(sep)]
            return joiner.join(p for p in parts if p) or None
    return clean_text(_s(intro.get(spec)))


def _dedupe_images(pairs: list[tuple[str | None, str]], source: str) -> list[ImageRef]:
    seen: set[str] = set()
    out: list[ImageRef] = []
    for url, lic in pairs:
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(ImageRef(url=url, source=source, license=lic, sort=len(out)))
    return out


def _clean_tourapi(raw: RawRecord, region: Region) -> CleanRecord | str:
    p = raw.payload
    if p.get("hidden") or str((p.get("list") or {}).get("showflag", "1")) == "0":
        return "hidden"
    lst: dict = p.get("list") or p  # tourapi.festival: the payload is the list item itself
    common: dict = p.get("common") or {}
    intro: dict = p.get("intro") or {}

    title = clean_text(_s(lst.get("title")) or _s(common.get("title")))
    if not title:
        return "no_title"
    category = map_category(raw.source, p)
    if category is None:
        return "no_category"

    addr = " ".join(x for x in (_s(lst.get("addr1")), _s(lst.get("addr2"))) if x) or None
    if addr is None:
        addr = " ".join(x for x in (_s(common.get("addr1")), _s(common.get("addr2"))) if x) or None
    lat, lng, geo, drop = normalize_coords(
        lst.get("mapx") or common.get("mapx"), lst.get("mapy") or common.get("mapy"), region, addr)
    if drop:
        return "out_of_region"

    spec = TOUR_INTRO_FIELDS.get(str(lst.get("contenttypeid", "")).strip(), {})
    f = {k: _intro_value(intro, spec.get(k)) for k in ("hours", "closed_days", "parking", "fee", "menu")}
    start = parse_date(_s(intro.get(spec.get("start_date") or "")) or _s(lst.get("eventstartdate")))
    end = parse_date(_s(intro.get(spec.get("end_date") or "")) or _s(lst.get("eventenddate")))

    phone = _s(common.get("tel")) or _s(lst.get("tel")) or _intro_value(intro, spec.get("phone"))
    first_lic = _s(lst.get("cpyrhtDivCd")) or TOUR_DEFAULT_LICENSE
    imgs: list[tuple[str | None, str]] = [(normalize_url(lst.get("firstimage")), first_lic)]
    for it in p.get("images") or []:
        imgs.append((normalize_url(it.get("originimgurl")), _s(it.get("cpyrhtDivCd")) or TOUR_DEFAULT_LICENSE))

    return CleanRecord(
        source=raw.source, source_id=raw.source_id,
        source_url=TOUR_DETAIL_URL.format(_s(lst.get("contentid")) or raw.source_id),
        category=category, title=title, addr=addr, lat=lat, lng=lng, geo_status=geo,
        phone=format_phone(phone),
        homepage=extract_homepage(common.get("homepage") or lst.get("homepage")),
        overview=clean_text(common.get("overview")),
        start_date=start, end_date=end,
        images=_dedupe_images(imgs, raw.source), raw=p, fetched_at=raw.fetched_at,
        **f,
    )


_CITY_SKIP = {"title", "addr", "coords", "images", "phone", "homepage"}


def _clean_city(raw: RawRecord, region: Region) -> CleanRecord | str:
    p = raw.payload
    kind = raw.source.split(".", 1)[1] if "." in raw.source else ""
    title = clean_text(_s(p.get("name")))
    if not title:
        return "no_title"
    category = map_category(raw.source, p)
    if category is None or kind not in CITY_FIELDS:
        return "no_category"

    addr = clean_text(_s(p.get("address")))
    lat, lng, geo, drop = normalize_coords(p.get("xposition"), p.get("yposition"), region, addr)
    if drop:
        return "out_of_region"

    out: dict[str, Any] = {}
    for src_key, field_name in CITY_FIELDS[kind].items():
        if field_name in _CITY_SKIP:
            continue
        val = p.get(src_key)
        if field_name == "date_undecided":
            out[field_name] = parse_undecided(val)
        elif field_name in ("start_date", "end_date"):
            out[field_name] = parse_date(_s(val))
        else:
            out[field_name] = clean_text(_s(val))
    fallback = CITY_OVERVIEW_FALLBACK.get(kind)
    if fallback and not out.get("overview"):
        out["overview"] = clean_text(_s(p.get(fallback)))

    imgs = [(normalize_url(u, CITY_BASE), CITY_LICENSE) for u in (p.get("images") or [])]
    idx = _s(p.get("idx")) or raw.source_id
    return CleanRecord(
        source=raw.source, source_id=raw.source_id,
        source_url=CITY_DETAIL_URL.format(CITY_SOURCE_URL_TYPE[kind], idx),
        category=category, title=title, addr=addr, lat=lat, lng=lng, geo_status=geo,
        phone=format_phone(p.get("phone")), homepage=extract_homepage(p.get("homepage")),
        images=_dedupe_images(imgs, raw.source), raw=p, fetched_at=raw.fetched_at,
        **out,
    )


def clean_record(raw: RawRecord, region: Region) -> CleanRecord | str:
    """The CleanRecord, or a drop reason: no_title / no_category / out_of_region / hidden."""
    if raw.source.startswith("tourapi."):
        return _clean_tourapi(raw, region)
    if raw.source.startswith("jinju_city."):
        return _clean_city(raw, region)
    return "no_category"


def clean_all(raws: list[RawRecord], region: Region) -> CleanResult:
    res = CleanResult()
    for raw in raws:
        r = clean_record(raw, region)
        if isinstance(r, str):
            res.dropped[r] += 1
        else:
            res.records.append(r)
    return res
