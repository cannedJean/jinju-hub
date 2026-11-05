"""Shared source interfaces: CollectContext, Source protocol, make_context."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol

import httpx

from jinju_pipeline.http import QuotaLedger, RateLimiter
from jinju_pipeline.models import PreviousSnapshot, RawRecord
from jinju_pipeline.raw_store import RawStore
from jinju_pipeline.region import Region
from jinju_pipeline.settings import Settings


@dataclass
class CollectContext:
    client: httpx.AsyncClient
    store: RawStore
    ledger: QuotaLedger
    settings: Settings
    region: Region
    previous: PreviousSnapshot | None
    incremental: bool
    today: date
    limiters: dict[str, RateLimiter]
    collection_keys: set[str] = field(default_factory=set)
    # source -> start of that source's last successful collection (refresh_state.json); incremental watermark
    synced_at: dict[str, datetime] = field(default_factory=dict)


class SourceSkipped(Exception):
    """A source cannot run in this configuration (e.g. no API key). Reported as ``skipped``; its previous
    records are not reused, so the gate sees that the source is missing."""


class Source(Protocol):
    name: str

    async def collect(self, ctx: CollectContext) -> list[RawRecord]: ...


def make_context(
    *,
    client: httpx.AsyncClient,
    store: RawStore,
    ledger: QuotaLedger,
    settings: Settings,
    region: Region,
    previous: PreviousSnapshot | None = None,
    incremental: bool = False,
    today: date | None = None,
    collection_keys: set[str] | None = None,
    synced_at: dict[str, datetime] | None = None,
) -> CollectContext:
    """Build a per-run context; limiters are created fresh each run (no module globals)."""
    return CollectContext(
        client=client,
        store=store,
        ledger=ledger,
        settings=settings,
        region=region,
        previous=previous,
        incremental=incremental,
        today=today or date.today(),
        limiters={
            "jinju_city": RateLimiter(settings.city_concurrency, settings.city_min_interval),
            "tourapi": RateLimiter(settings.tour_concurrency, 0.0),
        },
        collection_keys=set(collection_keys or ()),
        synced_at=dict(synced_at or {}),
    )
