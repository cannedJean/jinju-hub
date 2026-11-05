"""Concurrent collection orchestrator: per-source isolation and previous-data reuse."""
from __future__ import annotations

import asyncio
import logging

from jinju_pipeline.http import ConfigError
from jinju_pipeline.models import PreviousSnapshot, RawRecord, SourceResult
from jinju_pipeline.raw_store import scrub_secrets
from jinju_pipeline.settings import Settings
from jinju_pipeline.sources.base import CollectContext, Source, SourceSkipped
from jinju_pipeline.sources.jinju_city import CITY_ENDPOINTS, JinjuCitySource
from jinju_pipeline.sources.tourapi import TourApiAreaSource, TourApiFestivalSource

log = logging.getLogger(__name__)


def default_sources(settings: Settings) -> list[Source]:
    """Every configured source. Without DATA_GO_KR_KEY the TourAPI sources still run and report
    ``skipped: no key`` so the gate can refuse to publish a DB that silently lost them."""
    if settings.data_go_kr_key is None:
        log.warning("DATA_GO_KR_KEY is not set; TourAPI sources will be reported as skipped")
    return [JinjuCitySource(kind) for kind in CITY_ENDPOINTS] + [TourApiAreaSource(), TourApiFestivalSource()]


class ReplaySource:
    """Re-emits the raw records stored in the previous snapshot (``run --from-raw``: no network)."""

    def __init__(self, name: str, records: list[RawRecord]):
        self.name = name
        self._records = list(records)

    async def collect(self, ctx: CollectContext) -> list[RawRecord]:
        return list(self._records)


def replay_sources(previous: PreviousSnapshot) -> list[Source]:
    """One ReplaySource per source stored in the snapshot, in the default source order."""
    order = [f"jinju_city.{k}" for k in CITY_ENDPOINTS] + [TourApiAreaSource.name, TourApiFestivalSource.name]
    names = sorted(previous.raw_by_source, key=lambda n: (order.index(n) if n in order else len(order), n))
    return [ReplaySource(n, previous.raw_by_source[n]) for n in names]


async def run_source(source: Source, ctx: CollectContext) -> SourceResult:
    try:
        records = await source.collect(ctx)
    except ConfigError:
        raise
    except SourceSkipped as e:
        log.warning("source %s skipped: %s", source.name, e)
        return SourceResult(source=source.name, status="skipped", records=[], calls=0, error=f"skipped: {e}")
    except Exception as e:  # per-source isolation: one failure must not cancel the others
        error = scrub_secrets(f"{type(e).__name__}: {e}")
        calls = ctx.ledger.used_by_source().get(source.name, 0)
        previous = ctx.previous.raw_by_source.get(source.name) if ctx.previous else None
        if previous:
            log.warning("source %s failed (%s); reusing previous data", source.name, error)
            return SourceResult(source=source.name, status="reused_previous",
                                records=list(previous), calls=calls, error=error)
        log.error("source %s failed: %s", source.name, error)
        return SourceResult(source=source.name, status="failed", records=[], calls=calls, error=error)
    return SourceResult(source=source.name, status="ok", records=records,
                        calls=ctx.ledger.used_by_source().get(source.name, 0))


async def collect_all(sources: list[Source], ctx: CollectContext) -> list[SourceResult]:
    return list(await asyncio.gather(*(run_source(s, ctx) for s in sources)))
