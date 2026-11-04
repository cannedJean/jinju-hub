"""Concurrent collection orchestrator: per-source isolation and previous-data reuse."""
from __future__ import annotations

import asyncio
import logging

from jinju_pipeline.http import ConfigError
from jinju_pipeline.models import SourceResult
from jinju_pipeline.settings import Settings
from jinju_pipeline.sources.base import CollectContext, Source
from jinju_pipeline.sources.jinju_city import CITY_ENDPOINTS, JinjuCitySource
from jinju_pipeline.sources.tourapi import TourApiAreaSource, TourApiFestivalSource

log = logging.getLogger(__name__)


def default_sources(settings: Settings) -> list[Source]:
    sources: list[Source] = [JinjuCitySource(kind) for kind in CITY_ENDPOINTS]
    if settings.data_go_kr_key is None:
        log.warning("DATA_GO_KR_KEY is not set; skipping TourAPI sources")
    else:
        sources += [TourApiAreaSource(), TourApiFestivalSource()]
    return sources


async def run_source(source: Source, ctx: CollectContext) -> SourceResult:
    try:
        records = await source.collect(ctx)
    except ConfigError:
        raise
    except Exception as e:  # per-source isolation: one failure must not cancel the others
        error = f"{type(e).__name__}: {e}"
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
