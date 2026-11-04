"""Cross-source duplicate merge with stable place ids and aliases."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from rapidfuzz import fuzz

from .models import CleanRecord, ImageRef, Place, PreviousSnapshot

CITY_PREFIX = "jinju_city."
FIELD_PRIORITY = {
    "hours": "CITY", "closed_days": "CITY", "fee": "CITY", "parking": "CITY", "menu": "CITY",
    "phone": "CITY", "lat/lng": "CITY", "overview": "LONGEST", "title": "CITY", "addr": "CITY",
    "start_date/end_date": "CITY>tourapi.festival>tourapi.area",
}
SAME_NAME_M, FUZZY_M, PHONE_M = 300.0, 150.0, 500.0
SHARED_PHONE_MIN = 3  # a number on this many distinct records of ONE source is a department/office line
GRID = 0.006  # degrees (~550m lat / ~490m lng): a 3x3 neighbourhood covers 500m
_PREFIXES = ("경상남도", "경남", "진주")
_SUFFIX = "본점"
_SC = {"sight", "culture"}


@dataclass
class MergeResult:
    places: list[Place]
    aliases: dict[str, str]
    log: list[dict] = field(default_factory=list)


def normalize_name(title: str) -> str:
    s = unicodedata.normalize("NFKC", title or "")
    s = re.sub(r"[(\[{][^)\]}]*[)\]}]?", "", s)
    s = re.sub(r"[\W_]+", "", s)
    for p in _PREFIXES:
        if s.startswith(p) and len(s) - len(p) >= 2:
            s = s[len(p):]
            break
    if s.endswith(_SUFFIX) and len(s) > len(_SUFFIX):
        s = s[: -len(_SUFFIX)]
    return s.lower()


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(h))


def _group_of(cat: str) -> str:
    return "sc" if cat in _SC else cat


def _has_geo(r: CleanRecord) -> bool:
    return r.lat is not None and r.lng is not None


def _norm_addr(a: str | None) -> str:
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", a or "")).lower()


def _digits(p: str | None) -> str:
    return re.sub(r"\D+", "", p or "")


def match_reason(a: CleanRecord, b: CleanRecord, shared_phones: frozenset[str] = frozenset()) -> str | None:
    """Merge evidence for a pair, or None. Phone evidence needs two different sources and a number
    outside ``shared_phones`` (the city API lists managing-department numbers on many records)."""
    if _group_of(a.category) != _group_of(b.category):
        return None
    na, nb = normalize_name(a.title), normalize_name(b.title)
    if not (_has_geo(a) and _has_geo(b)):
        if na and na == nb:
            aa = _norm_addr(a.addr)
            if aa and aa == _norm_addr(b.addr):
                return "same_name_addr"
        return None
    d = haversine_m(a.lat, a.lng, b.lat, b.lng)
    if na and na == nb and d <= SAME_NAME_M:
        return "same_name"
    ta, tb = unicodedata.normalize("NFKC", a.title), unicodedata.normalize("NFKC", b.title)
    if d <= FUZZY_M and fuzz.token_set_ratio(ta, tb) >= 90:
        return "fuzzy_name"
    pa = _digits(a.phone)
    if pa and pa == _digits(b.phone) and a.source != b.source and pa not in shared_phones and d <= PHONE_M:
        return "same_phone"
    return None


def _shared_phones(records: list[CleanRecord]) -> frozenset[str]:
    """Numbers that one source lists on >= SHARED_PHONE_MIN distinct records (by key).

    Counting per source keeps a single place's own number usable even when the place appears in
    several sources (city + tourapi.area + tourapi.festival) or twice on the city API's pages."""
    keys: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in records:
        if (d := _digits(r.phone)):
            keys[(r.source, d)].add(r.key)
    return frozenset(d for (_, d), ks in keys.items() if len(ks) >= SHARED_PHONE_MIN)


def load_overrides(path) -> dict:
    p = Path(path)
    data = {}
    if p.exists():
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return {"force_merge": list(data.get("force_merge") or []),
            "force_split": list(data.get("force_split") or [])}


def _candidate_pairs(records: list[CleanRecord]) -> list[tuple[int, int]]:
    """Index pairs worth comparing (i<j), sorted. Blocked by category group, grid cell, name."""
    groups: dict[str, list[int]] = defaultdict(list)
    for i, r in enumerate(records):
        groups[_group_of(r.category)].append(i)
    seen: set[tuple[int, int]] = set()
    for idxs in groups.values():
        cells: dict[tuple[int, int], list[int]] = defaultdict(list)
        names: dict[str, list[int]] = defaultdict(list)
        for i in idxs:
            r = records[i]
            names[normalize_name(r.title)].append(i)
            if _has_geo(r):
                cells[(math.floor(r.lat / GRID), math.floor(r.lng / GRID))].append(i)
        for i in idxs:
            r = records[i]
            near: list[int] = []
            if _has_geo(r):
                cx, cy = math.floor(r.lat / GRID), math.floor(r.lng / GRID)
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        near.extend(cells.get((cx + dx, cy + dy), ()))
            for j in set(near) | set(names[normalize_name(r.title)]):
                if j != i:
                    seen.add((min(i, j), max(i, j)))
    return sorted(seen)


class _UF:
    def __init__(self, n: int):
        self.p = list(range(n))
        self.members: dict[int, set[int]] = {i: {i} for i in range(n)}

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if len(self.members[ra]) < len(self.members[rb]):
            ra, rb = rb, ra
        self.p[rb] = ra
        self.members[ra] |= self.members.pop(rb)


# Among city sources the tourism listings name a merged place; heritage rows (artifacts housed at a
# temple, steles inside 진주성) only contribute fields when the listing lacks them.
_CITY_ORDER = {"jinju_city.tourinfo": 0, "jinju_city.festival": 1, "jinju_city.restaurant": 2,
               "jinju_city.lodging": 3, "jinju_city.heritage": 4}


def _rank(r: CleanRecord) -> tuple:
    if r.source.startswith(CITY_PREFIX):
        return (0, _CITY_ORDER.get(r.source, 5), r.source, r.source_id)
    return ({"tourapi.area": 1, "tourapi.festival": 2}.get(r.source, 3), 0, r.source, r.source_id)


def _date_rank(r: CleanRecord) -> tuple:
    if r.source.startswith(CITY_PREFIX):
        return (0, r.source, r.source_id)
    return ({"tourapi.festival": 1, "tourapi.area": 2}.get(r.source, 3), r.source, r.source_id)


def _first(recs: list[CleanRecord], attr: str):
    for r in recs:
        v = getattr(r, attr)
        if v not in (None, ""):
            return v
    return None


def _summary(overview: str | None) -> str | None:
    if not overview:
        return None
    text = overview.strip()
    m = re.search(r"[.!?。]\s|\n", text)
    first = text[: m.start() + 1].strip() if m else text
    return first if len(first) <= 120 else first[:120]


def _pick_overview(recs: list[CleanRecord]) -> str | None:
    city_ovs = [r.overview for r in recs if r.overview and r.source.startswith(CITY_PREFIX)]
    tour_ovs = [r.overview for r in recs if r.overview and not r.source.startswith(CITY_PREFIX)]
    if not city_ovs and not tour_ovs:
        return None
    if not tour_ovs or (city_ovs and max(map(len, city_ovs)) >= 40):
        return max(city_ovs + tour_ovs, key=len)
    return max(tour_ovs, key=len)


def _build_place(pid: str, recs: list[CleanRecord], now_iso: str) -> Place:
    recs = sorted(recs, key=_rank)
    overview = _pick_overview(recs)
    geo = next((r for r in recs if _has_geo(r)), None)
    date_order = sorted(recs, key=_date_rank)
    dsrc = next((r for r in date_order if r.start_date is not None), None)
    start = dsrc.start_date if dsrc else None
    end = dsrc.end_date if dsrc else _first(date_order, "end_date")
    undecided = dsrc.date_undecided if dsrc else any(r.date_undecided for r in recs)
    images: list[ImageRef] = []
    urls: set[str] = set()
    for r in recs:
        for im in sorted(r.images, key=lambda x: x.sort):
            if im.url not in urls:
                urls.add(im.url)
                images.append(im)
    title = _first(recs, "title")
    return Place(
        id=pid, category=recs[0].category, title=title, title_norm=normalize_name(title),
        summary=_summary(overview), overview=overview, addr=_first(recs, "addr"),
        lat=geo.lat if geo else None, lng=geo.lng if geo else None,
        geo_status=geo.geo_status if geo else recs[0].geo_status,
        phone=_first(recs, "phone"), homepage=_first(recs, "homepage"), hours=_first(recs, "hours"),
        closed_days=_first(recs, "closed_days"), fee=_first(recs, "fee"),
        parking=_first(recs, "parking"), menu=_first(recs, "menu"),
        start_date=start, end_date=end, date_undecided=undecided,
        date_year=start.year if start else None,
        hero_image=images[0].url if images else None, images=images, sources=recs,
        updated_at=now_iso,
    )


def merge_records(records: list[CleanRecord], overrides: dict, previous: PreviousSnapshot | None,
                  now_iso: str) -> MergeResult:
    overrides = overrides or {}
    records = sorted(records, key=lambda r: r.key)
    idx = {r.key: i for i, r in enumerate(records)}
    log: list[dict] = []
    uf = _UF(len(records))
    splits: dict[int, set[int]] = defaultdict(set)
    for a, b in overrides.get("force_split") or []:
        if a in idx and b in idx:
            splits[idx[a]].add(idx[b])
            splits[idx[b]].add(idx[a])

    def blocked(i: int, j: int) -> bool:
        if not splits:
            return False
        ra, rb = uf.find(i), uf.find(j)
        small, other = (ra, rb) if len(uf.members[ra]) <= len(uf.members[rb]) else (rb, ra)
        om = uf.members[other]
        return any(splits[m] & om for m in uf.members[small] if m in splits)

    for a, b in overrides.get("force_merge") or []:
        if a in idx and b in idx and uf.find(idx[a]) != uf.find(idx[b]):
            uf.union(idx[a], idx[b])
            log.append({"a": a, "b": b, "reason": "force_merge", "override": True})
    shared_phones = _shared_phones(records)
    for i, j in _candidate_pairs(records):
        if uf.find(i) == uf.find(j):
            continue
        reason = match_reason(records[i], records[j], shared_phones)
        if reason and not blocked(i, j):
            uf.union(i, j)
            log.append({"a": records[i].key, "b": records[j].key, "reason": reason})

    comps: dict[int, list[CleanRecord]] = defaultdict(list)
    for i, r in enumerate(records):
        comps[uf.find(i)].append(r)
    groups = sorted(comps.values(), key=lambda g: min(r.key for r in g))

    src_index = previous.source_index if previous else {}
    id_order = previous.id_order if previous else {}
    taken: set[str] = set()
    final_ids: list[str] = []
    olds_per_group: list[set[str]] = []
    for g in groups:
        olds = {src_index[r.key] for r in g if r.key in src_index}
        olds_per_group.append(olds)
        cands = sorted(olds, key=lambda x: (id_order.get(x, math.inf), x))
        pid = next((c for c in cands if c not in taken), None)
        if pid is None:
            pid = "jh-" + hashlib.sha1(min(r.key for r in g).encode("utf-8")).hexdigest()[:10]
        taken.add(pid)
        final_ids.append(pid)

    aliases: dict[str, str] = {}
    for pid, olds in zip(final_ids, olds_per_group):
        for old in olds:
            if old != pid and old not in taken:
                aliases[old] = pid
    for old, tgt in (previous.aliases if previous else {}).items():
        if old not in taken and old not in aliases:
            aliases[old] = tgt
    resolved: dict[str, str] = {}
    for old, tgt in aliases.items():
        hops = 0
        while tgt in aliases and hops < 20:
            tgt, hops = aliases[tgt], hops + 1
        if tgt != old:
            resolved[old] = tgt

    places = [_build_place(pid, g, now_iso) for pid, g in zip(final_ids, groups)]
    return MergeResult(places=places, aliases=resolved, log=log)
