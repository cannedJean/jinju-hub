"""Text cleaning for free-text fields."""
from __future__ import annotations

import html
import re

from selectolax.parser import HTMLParser

_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
_BLOCK = re.compile(r"</?(?:p|div|li|ul|ol|tr|table|h[1-6])\b[^>]*>", re.IGNORECASE)
_MANY_BLANKS = re.compile(r"\n{3,}")


def clean_text(s: str | None) -> str | None:
    if s is None:
        return None
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    if "<" in s:
        s = _BR.sub("\n", s)
        s = _BLOCK.sub("\n", s)
        tree = HTMLParser(s)
        s = tree.body.text(deep=True, separator="") if tree.body is not None else ""
    s = html.unescape(s).replace("\xa0", " ")
    lines = [ln.strip() for ln in s.split("\n")]
    out = _MANY_BLANKS.sub("\n\n", "\n".join(lines)).strip()
    return out or None
