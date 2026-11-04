"""Phone number formatting."""
from __future__ import annotations

import re

_SPLIT = re.compile(r"[,;/]|\s{2,}|\sor\s", re.IGNORECASE)


def _format_digits(d: str) -> str | None:
    if d.startswith("02"):
        if len(d) == 9:
            return f"02-{d[2:5]}-{d[5:]}"
        if len(d) == 10:
            return f"02-{d[2:6]}-{d[6:]}"
    elif d.startswith("0"):
        if len(d) == 10:
            return f"{d[:3]}-{d[3:6]}-{d[6:]}"
        if len(d) == 11:
            return f"{d[:3]}-{d[3:7]}-{d[7:]}"
    elif d.startswith("1"):
        if len(d) == 8:
            return f"{d[:4]}-{d[4:]}"
        if len(d) == 4:
            return d
    return None


def format_phone(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    first = _SPLIT.split(s)[0].strip()
    digits = re.sub(r"\D", "", first)
    return (_format_digits(digits) if digits else None) or first or s
