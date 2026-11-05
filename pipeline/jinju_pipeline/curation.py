"""Curation: Jinju 8 views, collection list, tags, badges, festival venues.

Operates on the merged ``Place`` list and the YAML files in ``pipeline/curation``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from .merge import haversine_m, normalize_name
from .models import CleanRecord, Place
from .raw_store import KST

CURATION_FILES = ("jinju8", "collection30", "tags", "badges", "festival_programs")
DEFAULT_WITHIN_M = 1500


@dataclass
class BadgeDef:
    id: str
    label: str
    description: str
    required: int
    eligible_place_ids: list[str] = field(default_factory=list)
    festival_windows: list[dict] = field(default_factory=list)


@dataclass
class CurationResult:
    places: list[Place]
    badges: list[BadgeDef]
    unresolved: list[str]
    festival_programs: dict[str, list[str]]


def load_curation(dir: Path) -> dict:
    """Load the five curation YAMLs keyed by file stem (missing file -> empty dict)."""
    out: dict[str, Any] = {}
    for stem in CURATION_FILES:
        path = Path(dir) / f"{stem}.yaml"
        out[stem] = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}) if path.exists() else {}
    return out


def collection_source_keys(cur: dict) -> set[str]:
    """Source keys ("<source>:<source_id>") named by collection30 items (``source_keys``)."""
    keys: set[str] = set()
    for item in (cur.get("collection30") or {}).get("items", []):
        keys.update(item.get("source_keys") or [])
    return keys


# ---------------------------------------------------------------- matching

def _needles(match: dict) -> list[str]:
    t = match.get("title_contains")
    return [t] if isinstance(t, str) else list(t or [])


def match_label(match: dict) -> str:
    return "/".join(_needles(match))


def _title_hit(p: Place, needles: list[str]) -> bool:
    for n in needles:
        nn = normalize_name(n)
        if n in p.title or (nn and nn in p.title_norm):
            return True
    return False


def find_place(places: list[Place], match: dict, exclude: set[str] = frozenset()) -> Place | None:
    """Closest place satisfying ``match`` (title_contains, near, within_m, category)."""
    needles = _needles(match)
    near = match.get("near")
    within = match.get("within_m", DEFAULT_WITHIN_M)
    cat = match.get("category")
    best: tuple[float, str, Place] | None = None
    for p in places:
        if p.id in exclude or (cat and p.category != cat) or not _title_hit(p, needles):
            continue
        if near:
            if p.lat is None or p.lng is None:
                continue
            d = haversine_m(near[0], near[1], p.lat, p.lng)
            if d > within:
                continue
        else:
            d = 0.0
        if best is None or (d, p.id) < best[:2]:
            best = (d, p.id, p)
    return best[2] if best else None


# ---------------------------------------------------------------- jinju8

def _fallback_place(item: dict, default_url: str | None, now: datetime) -> Place:
    fb, rank = item["fallback"], item["rank"]
    rec = CleanRecord(
        source="curation", source_id=f"jinju8-{rank}", source_url=fb.get("source_url") or default_url,
        category="sight", title=fb["title"], lat=fb["lat"], lng=fb["lng"], geo_status="ok",
        overview=fb.get("overview"), fetched_at=now,
    )
    return Place(
        id=f"jh-cur-{rank}", category="sight", title=fb["title"], title_norm=normalize_name(fb["title"]),
        overview=fb.get("overview"), lat=fb["lat"], lng=fb["lng"], geo_status="ok",
        sources=[rec], updated_at=now.isoformat(timespec="seconds"),
    )


def _apply_jinju8(places: list[Place], spec: dict, unresolved: list[str], now: datetime) -> None:
    taken: set[str] = set()
    for item in spec.get("items", []):
        p = find_place(places, item["match"], exclude=taken) if item.get("match") else None
        if p is None:
            if not item.get("fallback"):
                unresolved.append(f"jinju8:{match_label(item.get('match', {}))}")
                continue
            p = _fallback_place(item, spec.get("source_url"), now)
            places.append(p)
        p.jinju8_rank = item["rank"]
        taken.add(p.id)


# ---------------------------------------------------------------- collection

def _apply_collection(places: list[Place], spec: dict, unresolved: list[str]) -> None:
    keys = collection_source_keys({"collection30": spec})
    for p in places:
        if keys and any(s.key in keys for s in p.sources):
            p.is_collection = True
    for item in spec.get("items", []):
        if not item.get("match"):
            continue  # source_keys-only item
        p = find_place(places, item["match"])
        if p is None:
            unresolved.append(f"collection30:{match_label(item['match'])}")
        else:
            p.is_collection = True


# ---------------------------------------------------------------- tags

def _add_tags(p: Place, tags: list[str]) -> None:
    for t in tags:
        if t not in p.tags:
            p.tags.append(t)


def _apply_tags(places: list[Place], spec: dict, unresolved: list[str]) -> None:
    defaults = spec.get("category_defaults") or {}
    keywords = spec.get("keyword_tags") or {}
    excludes = spec.get("keyword_excludes") or {}  # tag -> title words that veto it (manual entries still win)
    for p in places:
        found = list(defaults.get(p.category, []))
        text = f"{p.title} {p.menu or ''}"
        found += [tag for tag, words in keywords.items() if any(w in text for w in words)]
        _add_tags(p, [t for t in found if not any(w in p.title for w in excludes.get(t, []))])
    for entry in spec.get("manual", []):
        p = find_place(places, entry["match"])
        if p is None:
            unresolved.append(f"tags:{match_label(entry['match'])}")
        else:
            _add_tags(p, entry["tags"])


# ---------------------------------------------------------------- festivals

def _apply_festival_programs(
    places: list[Place], spec: dict, unresolved: list[str]
) -> dict[str, list[str]]:
    programs: dict[str, list[str]] = {}
    for item in spec.get("items", []):
        fm = item["match_festival"]
        festivals = [p for p in places if p.category == "festival" and _title_hit(p, _needles(fm))]
        if not festivals:
            unresolved.append(f"festival_programs:{match_label(fm)}")
            continue
        venues: list[Place] = []
        for vm in item.get("venues", []):
            v = find_place(places, vm)
            if v is None:
                unresolved.append(f"festival_programs:{match_label(vm)}")
            elif v not in venues:
                venues.append(v)
        for v in venues:
            _add_tags(v, ["festival_venue"])
        for f in festivals:
            f.venue_place_ids = [v.id for v in venues]
            programs[f.id] = list(item.get("programs", []))
    return programs


# ---------------------------------------------------------------- badges

def _festival_windows(places: list[Place]) -> list[dict]:
    windows = []
    for f in places:
        if f.category != "festival" or not f.start_date:
            continue  # undated festivals cannot define a window
        venues = list(f.venue_place_ids) or ([f.id] if f.geo_status == "ok" else [])
        if not venues:
            continue
        windows.append({
            "festival_id": f.id,
            "start": f.start_date.isoformat(),
            "end": (f.end_date or f.start_date).isoformat(),
            "venue_place_ids": venues,
        })
    return windows


def _build_badges(places: list[Place], spec: dict) -> list[BadgeDef]:
    out = []
    for b in spec.get("items", []):
        kind, value = b["eligible"]["kind"], b["eligible"].get("value")
        windows: list[dict] = []
        if kind == "any":
            ids = [p.id for p in places if p.geo_status == "ok"]
        elif kind == "jinju8":
            ids = [p.id for p in places if p.jinju8_rank]
        elif kind == "category":
            ids = [p.id for p in places if p.category == value]
        elif kind == "tag":
            ids = [p.id for p in places if value in p.tags]
        elif kind == "festival":
            windows = _festival_windows(places)
            ids = list(dict.fromkeys(v for w in windows for v in w["venue_place_ids"]))
        else:
            raise ValueError(f"unknown badge eligible kind: {kind}")
        out.append(BadgeDef(b["id"], b["label"], b["description"], b["required"], ids, windows))
    return out


# ---------------------------------------------------------------- entry point

def apply_curation(places: list[Place], cur: dict) -> CurationResult:
    """Return curated copies of ``places`` (input is not mutated) plus badges/diagnostics."""
    now = datetime.now(KST)
    work = [p.model_copy(deep=True) for p in places]
    unresolved: list[str] = []
    _apply_jinju8(work, cur.get("jinju8") or {}, unresolved, now)
    _apply_collection(work, cur.get("collection30") or {}, unresolved)
    _apply_tags(work, cur.get("tags") or {}, unresolved)
    programs = _apply_festival_programs(work, cur.get("festival_programs") or {}, unresolved)
    badges = _build_badges(work, cur.get("badges") or {})
    return CurationResult(work, badges, unresolved, programs)
