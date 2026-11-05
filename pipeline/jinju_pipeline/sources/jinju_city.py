"""Jinju city OpenAPI sources (S1~S5) with parallel paging.

Endpoints and response shape verified live 2026-11-04 (spec pages 06575/06578/06579):
heritage = asset.do, lodging = lodging.do.
"""
from __future__ import annotations

import asyncio
import hashlib
import math
from datetime import datetime

from jinju_pipeline.http import fetch_json
from jinju_pipeline.models import RawRecord
from jinju_pipeline.raw_store import KST
from jinju_pipeline.sources.base import CollectContext

BASE_URL = "https://www.jinju.go.kr/openapi/tour/"
PAGE_PARAM = "page"
SIZE_PARAM = "pageunit"
PAGE_SIZE = 10
TOTAL_KEY = "record_count"
ITEMS_KEY = "results"

CITY_ENDPOINTS: dict[str, str] = {
    "tourinfo": "tourinfo.do",
    "restaurant": "restaurant.do",
    "festival": "festival.do",
    "heritage": "asset.do",
    "lodging": "lodging.do",
}


def parse_page(body: dict) -> tuple[list[dict], int]:
    items = body.get(ITEMS_KEY) or []
    total = int(body.get(TOTAL_KEY) or 0)
    return list(items), total


def _source_id(item: dict) -> str:
    idx = item.get("idx")
    if idx not in (None, ""):
        return str(idx)
    key = f"{item.get('name', '')}|{item.get('address', '')}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


class JinjuCitySource:
    def __init__(self, kind: str):
        self.kind = kind
        self.name = f"jinju_city.{kind}"
        self._url = BASE_URL + CITY_ENDPOINTS[kind]

    async def _page(self, ctx: CollectContext, page: int) -> dict:
        params = {PAGE_PARAM: page, SIZE_PARAM: PAGE_SIZE}
        body = await fetch_json(
            ctx.client, self._url, params,
            # spec 5.9: the city API needs no key, so its pages are counted but never spend the key quota
            limiter=ctx.limiters["jinju_city"], ledger=ctx.ledger.unmetered(), source=self.name,
        )
        ctx.store.write_page(self.name, page, body, {"url": self._url, "params": params})
        return body

    async def collect(self, ctx: CollectContext) -> list[RawRecord]:
        first = await self._page(ctx, 1)
        items, total = parse_page(first)
        pages = max(1, math.ceil(total / PAGE_SIZE))
        bodies = [first]
        if pages > 1:
            bodies += await asyncio.gather(*(self._page(ctx, p) for p in range(2, pages + 1)))
        fetched_at = datetime.now(KST)
        records: list[RawRecord] = []
        for body in bodies:
            for item in parse_page(body)[0]:
                records.append(
                    RawRecord(source=self.name, source_id=_source_id(item), payload=item, fetched_at=fetched_at)
                )
        return records
