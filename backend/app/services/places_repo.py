"""Read-only access to places.db (contract: pipeline/jinju_pipeline/schema.sql)."""
import json
import math
import sqlite3
import threading
from datetime import date
from functools import wraps
from pathlib import Path

from fastapi import HTTPException, Request

from app.schemas.places import (
    BadgeOut, CategoryCount, CollectionOut, CollectionPlace, ImageOut, Jinju8Item, Marker, MetaOut,
    PlaceDetail, PlacePage, PlaceQuery, PlaceSummary, SourceOut,
)

CATEGORY_LABELS = {
    "sight": "명소", "culture": "문화·역사", "food": "맛집", "stay": "숙박",
    "festival": "축제·행사", "shopping": "쇼핑", "leisure": "레포츠", "course": "여행코스",
}
_M_PER_DEG = 111_320.0
_MAX_ALIAS_HOPS = 5
_NEARBY_M = 1000
_NEARBY_N = 6
_LIKE_ANY = "(p.title LIKE ? ESCAPE '\\' OR p.addr LIKE ? ESCAPE '\\' OR p.overview LIKE ? ESCAPE '\\' OR p.menu LIKE ? ESCAPE '\\')"
_LIKE_RANK = "CASE WHEN p.title LIKE ? ESCAPE '\\' THEN 0 WHEN p.addr LIKE ? ESCAPE '\\' THEN 1 ELSE 2 END, p.title"


def _loads(text, default):
    try:
        v = json.loads(text) if text else default
    except (TypeError, ValueError):
        return default
    return v if v is not None else default


def _haversine_m(lat1, lng1, lat2, lng2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def _like_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _parse_date(s):
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None


def _deg_box(lat: float, meters: float) -> tuple[float, float]:
    return meters / _M_PER_DEG, meters / (_M_PER_DEG * max(math.cos(math.radians(lat)), 1e-6))


def _locked(fn):
    @wraps(fn)
    def wrapper(self, *a, **kw):
        with self._lock:
            return fn(self, *a, **kw)
    return wrapper


class PlacesRepo:
    """Read-only places.db access.

    Threading model: one sqlite connection is shared (check_same_thread=False) by the FastAPI threadpool
    workers. Every public query method holds a re-entrant lock for its whole run, so queries are serialized
    and cursors never interleave. The DB is small and read-only, so contention is negligible.
    """

    def __init__(self, db_path: Path, report_path: Path | None = None):
        self._lock = threading.RLock()
        self._con = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self.report_path = report_path
        row = self._con.execute("SELECT value FROM meta WHERE key='fts'").fetchone()
        self.fts_mode = row[0] if row else "none"
        self.last_search_mode: str | None = None

    def close(self) -> None:
        with self._lock:
            self._con.close()

    def _meta(self, key, default=None):
        row = self._con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row and row[0] is not None else default

    @staticmethod
    def _summary(r: sqlite3.Row, distance=None) -> PlaceSummary:
        return PlaceSummary(
            id=r["id"], category=r["category"], title=r["title"], summary=r["summary"], addr=r["addr"],
            lat=r["lat"], lng=r["lng"], hero_image=r["hero_image"], tags=_loads(r["tags"], []),
            is_collection=bool(r["is_collection"]), jinju8_rank=r["jinju8_rank"],
            distance_m=None if distance is None else round(distance),
        )

    @_locked
    def meta(self) -> MetaOut:
        counts = _loads(self._meta("category_counts"), {})
        return MetaOut(
            region=_loads(self._meta("region"), {}),
            categories=[CategoryCount(code=c, label=lb, count=int(counts.get(c, 0)))
                        for c, lb in CATEGORY_LABELS.items()],
            data_version=self._meta("data_version", ""),
            generated_at=self._meta("generated_at", ""),
        )

    @_locked
    def search(self, q: PlaceQuery) -> PlacePage:
        tokens = (q.q or "").split()
        where: list[str] = []
        params: list = []
        order_params: list = []
        use_fts = bool(tokens) and self.fts_mode == "trigram" and all(len(t) >= 3 for t in tokens)
        self.last_search_mode = "fts" if use_fts else "like"  # introspection for tests
        if use_fts:
            frm = "places_fts JOIN places p ON p.rowid = places_fts.rowid"
            where.append("places_fts MATCH ?")
            params.append(" ".join('"' + t.replace('"', '""') + '"' for t in tokens))
            order = "bm25(places_fts, 10.0, 3.0, 1.0), p.title"
        else:
            frm = "places p"
            for t in tokens:
                pat = "%" + _like_escape(t) + "%"
                where.append(_LIKE_ANY)
                params += [pat, pat, pat, pat]
            if tokens:
                pat = "%" + _like_escape(tokens[0]) + "%"
                order, order_params = _LIKE_RANK, [pat, pat]
            else:
                order = "p.title"
        if q.category:
            where.append(f"p.category IN ({','.join('?' * len(q.category))})")
            params += q.category
        for tag in q.tags:
            where.append("EXISTS (SELECT 1 FROM json_each(p.tags) WHERE value = ?)")
            params.append(tag)
        if q.bbox:
            min_lng, min_lat, max_lng, max_lat = q.bbox
            where.append("p.lat BETWEEN ? AND ? AND p.lng BETWEEN ? AND ?")
            params += [min_lat, max_lat, min_lng, max_lng]
        if q.near and q.radius:
            dlat, dlng = _deg_box(q.near[0], q.radius)
            where.append("p.lat BETWEEN ? AND ? AND p.lng BETWEEN ? AND ?")
            params += [q.near[0] - dlat, q.near[0] + dlat, q.near[1] - dlng, q.near[1] + dlng]
        sql = f"SELECT p.* FROM {frm}" + (" WHERE " + " AND ".join(where) if where else "")

        sort = q.sort
        if sort == "distance" and not q.near:
            sort = "relevance"
        if sort == "name":
            order, order_params = "p.title", []
        elif sort == "collection":
            order = "(p.jinju8_rank IS NULL), p.jinju8_rank, (p.is_collection = 0), p.title"
            order_params = []
        elif sort == "distance":
            order, order_params = "p.title", []

        if sort == "distance" or (q.near and q.radius):
            # Exact radius filtering / distance ordering needs the python-side haversine.
            rows = self._con.execute(sql + " ORDER BY " + order, params + order_params).fetchall()
            scored = []
            for r in rows:
                d = None
                if q.near and r["lat"] is not None and r["lng"] is not None:
                    d = _haversine_m(q.near[0], q.near[1], r["lat"], r["lng"])
                if q.near and q.radius and (d is None or d > q.radius):
                    continue
                scored.append((r, d))
            if sort == "distance":
                scored.sort(key=lambda x: (x[1] is None, x[1] or 0))
            total = len(scored)
            start = (q.page - 1) * q.size
            items = [self._summary(r, d) for r, d in scored[start:start + q.size]]
        else:
            total = self._con.execute(f"SELECT COUNT(*) FROM ({sql})", params).fetchone()[0]
            rows = self._con.execute(sql + " ORDER BY " + order + " LIMIT ? OFFSET ?",
                                     params + order_params + [q.size, (q.page - 1) * q.size]).fetchall()
            items = []
            for r in rows:
                d = None
                if q.near and r["lat"] is not None and r["lng"] is not None:
                    d = _haversine_m(q.near[0], q.near[1], r["lat"], r["lng"])
                items.append(self._summary(r, d))
        return PlacePage(items=items, total=total, page=q.page, size=q.size,
                         totalPages=math.ceil(total / q.size) if total else 0)

    @_locked
    def markers(self, categories: list[str] | None) -> list[Marker]:
        sql = ("SELECT id, lat, lng, category, title, is_collection FROM places "
               "WHERE lat IS NOT NULL AND lng IS NOT NULL")
        params: list = []
        if categories:
            sql += f" AND category IN ({','.join('?' * len(categories))})"
            params += categories
        return [Marker(id=r["id"], lat=r["lat"], lng=r["lng"], category=r["category"], title=r["title"],
                       is_collection=bool(r["is_collection"]))
                for r in self._con.execute(sql + " ORDER BY id", params)]

    def _resolve(self, place_id: str) -> str | None:
        """Follow alias chains (bounded); None if unknown, dangling or looping."""
        cur = place_id
        for _ in range(_MAX_ALIAS_HOPS + 1):
            if self._con.execute("SELECT 1 FROM places WHERE id=?", (cur,)).fetchone():
                return cur
            row = self._con.execute("SELECT new_id FROM place_aliases WHERE old_id=?", (cur,)).fetchone()
            if not row or row[0] == cur:
                return None
            cur = row[0]
        return None

    @_locked
    def get(self, place_id: str) -> PlaceDetail | None:
        cid = self._resolve(place_id)
        if cid is None:
            return None
        r = self._con.execute("SELECT * FROM places WHERE id=?", (cid,)).fetchone()
        images = [ImageOut(url=i["url"], license=i["license"], source=i["source"]) for i in self._con.execute(
            "SELECT url, license, source FROM place_images WHERE place_id=? ORDER BY sort", (cid,))]
        sources = [SourceOut(source=s["source"], source_url=s["source_url"], fetched_at=s["fetched_at"])
                   for s in self._con.execute(
                       "SELECT source, source_url, fetched_at FROM place_sources WHERE place_id=? ORDER BY rowid",
                       (cid,))]
        nearby = self._nearby(cid, r["lat"], r["lng"]) if r["lat"] is not None and r["lng"] is not None else []
        return PlaceDetail(
            **self._summary(r).model_dump(), overview=r["overview"], phone=r["phone"], homepage=r["homepage"],
            hours=r["hours"], closed_days=r["closed_days"], fee=r["fee"], parking=r["parking"], menu=r["menu"],
            start_date=r["start_date"], end_date=r["end_date"], date_undecided=bool(r["date_undecided"]),
            images=images, sources=sources, nearby=nearby, canonical_id=cid,
        )

    def _nearby(self, cid: str, lat: float, lng: float) -> list[PlaceSummary]:
        dlat, dlng = _deg_box(lat, _NEARBY_M)
        rows = self._con.execute(
            "SELECT * FROM places WHERE id != ? AND lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?",
            (cid, lat - dlat, lat + dlat, lng - dlng, lng + dlng)).fetchall()
        scored = sorted(((_haversine_m(lat, lng, x["lat"], x["lng"]), x) for x in rows), key=lambda t: t[0])
        return [self._summary(x, d) for d, x in scored if d <= _NEARBY_M][:_NEARBY_N]

    @_locked
    def collection(self) -> CollectionOut:
        rows = self._con.execute(
            "SELECT id, category, title, tags, jinju8_rank FROM places "
            "WHERE is_collection=1 OR jinju8_rank IS NOT NULL ORDER BY id").fetchall()
        jinju8 = sorted((Jinju8Item(rank=r["jinju8_rank"], id=r["id"], title=r["title"])
                         for r in rows if r["jinju8_rank"] is not None), key=lambda x: x.rank)
        badges = []
        for b in self._con.execute("SELECT * FROM badges ORDER BY rowid"):
            rule = _loads(b["rule_json"], {})
            badges.append(BadgeOut(id=b["id"], label=b["label"], description=b["description"],
                                   required=b["required"], eligible_place_ids=rule.get("eligible_place_ids", []),
                                   festival_windows=rule.get("festival_windows", [])))
        return CollectionOut(
            collection_ids=[r["id"] for r in rows], jinju8=jinju8, badges=badges,
            places=[CollectionPlace(id=r["id"], category=r["category"], tags=_loads(r["tags"], [])) for r in rows])

    @_locked
    def festival_rows(self) -> list[dict]:
        programs = _loads(self._meta("festival_programs"), {})
        out = []
        for r in self._con.execute(
                "SELECT * FROM places WHERE category='festival' ORDER BY (start_date IS NULL), start_date, title"):
            out.append({
                "id": r["id"], "title": r["title"], "summary": r["summary"], "hero_image": r["hero_image"],
                "addr": r["addr"], "lat": r["lat"], "lng": r["lng"],
                "start_date": _parse_date(r["start_date"]), "end_date": _parse_date(r["end_date"]),
                "date_undecided": bool(r["date_undecided"]),
                "venue_place_ids": _loads(r["venue_place_ids"], []),
                "programs": list(programs.get(r["id"], [])),
            })
        return out

    def report(self) -> dict | None:
        if not self.report_path:
            return None
        try:
            return json.loads(Path(self.report_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None


_REPO_INIT_LOCK = threading.Lock()


def open_places_repo(settings) -> PlacesRepo:
    """Open the repo from settings; raise 503 data_unavailable when the DB is missing or unreadable."""
    try:
        if not Path(settings.places_db_path).is_file():
            raise FileNotFoundError(settings.places_db_path)
        return PlacesRepo(settings.places_db_path, settings.report_path)
    except (OSError, sqlite3.Error):
        raise HTTPException(status_code=503, detail="data_unavailable") from None


def get_places_repo(request: Request) -> PlacesRepo:
    """FastAPI dependency: one repo per app (built eagerly by the lifespan, lazily here as a locked fallback)."""
    state = request.app.state
    repo = getattr(state, "places_repo", None)
    if repo is None:
        with _REPO_INIT_LOCK:
            repo = getattr(state, "places_repo", None)
            if repo is None:
                repo = state.places_repo = open_places_repo(state.settings)
    return repo
