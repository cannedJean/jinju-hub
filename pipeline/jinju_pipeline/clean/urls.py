"""URL normalisation and homepage extraction."""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit, urlunsplit

from selectolax.parser import HTMLParser

from jinju_pipeline.clean.text import clean_text

HTTPS_UPGRADE_HOSTS = {"tong.visitkorea.or.kr", "www.jinju.go.kr"}
_HREF = re.compile(r"href\s*=", re.IGNORECASE)


def normalize_url(u: str | None, base: str | None = None) -> str | None:
    if u is None:
        return None
    u = u.strip()
    if not u:
        return None
    if base:
        u = urljoin(base, u)
    parts = urlsplit(u)
    if parts.scheme == "http" and (parts.hostname or "") in HTTPS_UPGRADE_HOSTS:
        u = urlunsplit(("https",) + tuple(parts)[1:])
    return u


def extract_homepage(s: str | None) -> str | None:
    """TourAPI homepage fields hold HTML anchors: take the href, else cleaned text."""
    if not s or not s.strip():
        return None
    if _HREF.search(s):
        for a in HTMLParser(s).css("a[href]"):
            href = normalize_url(a.attributes.get("href"))
            if href:
                return href
    text = clean_text(s)
    return normalize_url(text) if text and text.lower().startswith("http") else text
