"""Date parsing and festival date flags."""
from __future__ import annotations

import re
from datetime import date

_DATE = re.compile(r"^\s*(\d{4})\s*[-./]?\s*(\d{1,2})\s*[-./]?\s*(\d{1,2})\s*\.?\s*$")
_FALSE_FLAGS = {"", "n", "no", "0", "false", "f"}


def parse_date(s: str | None) -> date | None:
    """Accepts YYYYMMDD, YYYY-MM-DD, YYYY.MM.DD and 'YYYY. M. D'."""
    if not s:
        return None
    m = _DATE.match(s)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def parse_undecided(v: object) -> bool:
    """Jinju festival `undecided` holds free text (e.g. '2024년 8월 중', '매년 10월 개최') when the
    date is not fixed and '' otherwise (verified on the recorded fixture). Non-empty text means
    undecided; explicit negatives (N/0/false) mean decided."""
    if v is None:
        return False
    return str(v).strip().lower() not in _FALSE_FLAGS
