"""Coordinate normalisation (the Jinju city API sometimes swaps x/y)."""
from __future__ import annotations

from jinju_pipeline.models import GeoStatus
from jinju_pipeline.region import Region

LAT_RANGE = (33.0, 39.0)
LNG_RANGE = (124.0, 132.0)


def _to_float(v: str | float | None) -> float | None:
    if v is None:
        return None
    try:
        f = float(str(v).strip())
    except ValueError:
        return None
    return f if f == f else None  # reject NaN


def _is(v: float, rng: tuple[float, float]) -> bool:
    return rng[0] <= v <= rng[1]


def normalize_coords(
    a: str | float | None, b: str | float | None, region: Region, addr: str | None
) -> tuple[float | None, float | None, GeoStatus, bool]:
    """Return (lat, lng, geo_status, drop). Argument order does not matter."""
    missing = (None, None, "missing", False)
    fa, fb = _to_float(a), _to_float(b)
    if not fa or not fb:  # None or 0
        return missing
    if _is(fa, LAT_RANGE) and _is(fb, LNG_RANGE):
        lat, lng = fa, fb
    elif _is(fb, LAT_RANGE) and _is(fa, LNG_RANGE):
        lat, lng = fb, fa
    else:
        return missing
    if region.contains(lat, lng):
        return lat, lng, "ok", False
    in_region_addr = bool(addr) and region.address_keyword in addr
    return None, None, "out_of_region", not in_region_addr
