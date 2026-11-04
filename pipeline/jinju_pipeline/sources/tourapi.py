"""TourAPI KorService2 sources: area list + detail workers (+ incremental sync), festivals, code check.

Region filter is lDongRegnCd/lDongSignguCd only (never areaCode/sigunguCode).
Raw storage: only list/search/sync *pages* are written to the raw store (with the service key
stripped from the recorded params). Detail responses are merged into each RawRecord payload and
are not stored as separate raw pages.
"""
from __future__ import annotations

import asyncio
import itertools
import math
from datetime import datetime

import httpx

from jinju_pipeline.http import (
    ConfigError,
    QuotaExceeded,
    RateLimiter,
    UpstreamError,
    fetch_json,
)
from jinju_pipeline.models import RawRecord
from jinju_pipeline.raw_store import KST
from jinju_pipeline.settings import Settings
from jinju_pipeline.sources.base import CollectContext

TOURAPI_BASE = "https://apis.data.go.kr/B551011/KorService2"
CONTENT_TYPES = (12, 14, 15, 25, 28, 32, 38, 39)
PAGE_ROWS = 1000
AREA = "tourapi.area"
FESTIVAL = "tourapi.festival"

_KEY_ERROR_CODES = {"30", "31", "32", "33"}


class TourApiError(UpstreamError):
    def __init__(self, message: str, code: str):
        super().__init__(message, retryable=False)
        self.code = code


def check_body(body: dict) -> dict:
    header = (body.get("response") or {}).get("header") or {}
    code = str(header.get("resultCode", ""))
    msg = str(header.get("resultMsg", ""))
    if code == "0000":
        return body
    if code == "22" or "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in msg:
        raise QuotaExceeded(f"TourAPI gateway quota exceeded ({code} {msg})")
    if code in _KEY_ERROR_CODES or "SERVICE_KEY" in msg:
        raise ConfigError(f"TourAPI key rejected ({code} {msg})")
    raise TourApiError(f"TourAPI error {code}: {msg}", code)


def items_of(body: dict) -> tuple[list[dict], int]:
    b = (body.get("response") or {}).get("body") or {}
    total = int(b.get("totalCount") or 0)
    items = b.get("items")
    if not items:  # "" or None on empty results
        return [], total
    item = items.get("item") if isinstance(items, dict) else None
    if item is None:
        return [], total
    return ([item] if isinstance(item, dict) else list(item)), total


def _service_key(settings: Settings) -> str:
    if settings.data_go_kr_key is None or not settings.data_go_kr_key.get_secret_value():
        raise ConfigError("DATA_GO_KR_KEY is not set")
    return settings.data_go_kr_key.get_secret_value()


def _base_params(settings: Settings) -> dict:
    return {
        "serviceKey": _service_key(settings),
        "MobileOS": "ETC",
        "MobileApp": "JinjuHub",
        "_type": "json",
    }


def _region_params(region) -> dict:
    return {"lDongRegnCd": region.regn_cd, "lDongSignguCd": region.signgu_cd}


async def _call(ctx: CollectContext, source: str, op: str, params: dict) -> dict:
    body = await fetch_json(
        ctx.client, f"{TOURAPI_BASE}/{op}", {**_base_params(ctx.settings), **params},
        limiter=ctx.limiters["tourapi"], ledger=ctx.ledger, source=source,
    )
    return check_body(body)


async def _paged(ctx: CollectContext, source: str, op: str, params: dict, page_no) -> list[dict]:
    """Fetch every page of a list-style operation; page count derives from the rows actually returned."""

    async def one(page: int) -> tuple[list[dict], int]:
        p = {**params, "numOfRows": PAGE_ROWS, "pageNo": page}
        body = await _call(ctx, source, op, p)
        ctx.store.write_page(source, next(page_no), body, {"url": f"{TOURAPI_BASE}/{op}", "params": p})
        return items_of(body)

    first, total = await one(1)
    items = list(first)
    if first and total > len(first):
        pages = math.ceil(total / len(first))
        for rest, _ in await asyncio.gather(*(one(p) for p in range(2, pages + 1))):
            items += rest
    return items


class TourApiFestivalSource:
    name = FESTIVAL

    async def collect(self, ctx: CollectContext) -> list[RawRecord]:
        params = {"eventStartDate": f"{ctx.today.year}0101", **_region_params(ctx.region)}
        items = await _paged(ctx, self.name, "searchFestival2", params, itertools.count(1))
        now = datetime.now(KST)
        return [
            RawRecord(source=self.name, source_id=str(i["contentid"]), payload=i, fetched_at=now)
            for i in items
        ]


class TourApiAreaSource:
    name = AREA

    async def collect(self, ctx: CollectContext) -> list[RawRecord]:
        _service_key(ctx.settings)  # fail fast with ConfigError
        prev = {r.source_id: r for r in (ctx.previous.raw_by_source.get(self.name, []) if ctx.previous else [])}
        pending_ids = {
            k.split(":", 1)[1] for k in (ctx.previous.detail_pending_keys if ctx.previous else set())
            if k.startswith(self.name + ":")
        }
        incremental = ctx.incremental and ctx.previous is not None
        page_no = itertools.count(1)
        results: dict[str, RawRecord] = {}
        queue_items: list[dict] = []
        now = datetime.now(KST)

        if incremental:
            since = ctx.previous.generated_at.astimezone(KST).strftime("%Y%m%d")
            changed = await _paged(
                ctx, self.name, "areaBasedSyncList2",
                {"modifiedtime": since, **_region_params(ctx.region)}, page_no,
            )
            for item in changed:
                cid = str(item["contentid"])
                if str(item.get("showflag", "1")) == "0":
                    results[cid] = RawRecord(source=self.name, source_id=cid, fetched_at=now,
                                             payload={"list": item, "hidden": True})
                else:
                    queue_items.append(item)
            seen = {str(i["contentid"]) for i in changed}
            for cid in pending_ids - seen:  # unfinished detail from last run
                if cid in prev and "list" in prev[cid].payload:
                    queue_items.append(prev[cid].payload["list"])
            for cid, rec in prev.items():  # restore everything untouched
                if cid not in results and cid not in {str(i["contentid"]) for i in queue_items}:
                    results[cid] = rec
        else:
            lists = await asyncio.gather(*(
                _paged(ctx, self.name, "areaBasedList2",
                       {"contentTypeId": t, **_region_params(ctx.region)}, page_no)
                for t in CONTENT_TYPES
            ))
            seen_ids: set[str] = set()
            for item in (i for chunk in lists for i in chunk):
                cid = str(item["contentid"])
                if cid not in seen_ids:
                    seen_ids.add(cid)
                    queue_items.append(item)

        # reuse previous detail when unchanged and not pending
        todo: list[dict] = []
        for item in queue_items:
            cid = str(item["contentid"])
            old = prev.get(cid)
            if (
                old is not None and cid not in pending_ids
                and (old.payload.get("list") or {}).get("modifiedtime") == item.get("modifiedtime")
                and not old.payload.get("detail_pending")
            ):
                results[cid] = old
            else:
                todo.append(item)

        for rec in await self._run_workers(ctx, todo):
            results[rec.source_id] = rec
        return list(results.values())

    async def _run_workers(self, ctx: CollectContext, todo: list[dict]) -> list[RawRecord]:
        queue: asyncio.Queue[dict] = asyncio.Queue()
        for item in todo:
            queue.put_nowait(item)
        out: list[RawRecord] = []
        state = {"quota": False}

        async def worker() -> None:
            while True:
                try:
                    item = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return
                out.append(await self._detail(ctx, item, state))

        tasks = [asyncio.create_task(worker()) for _ in range(max(1, ctx.settings.tour_concurrency))]
        try:
            await asyncio.gather(*tasks)
        except BaseException:
            for t in tasks:
                t.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        return out

    async def _detail(self, ctx: CollectContext, item: dict, state: dict) -> RawRecord:
        cid = str(item["contentid"])
        payload: dict = {"list": item}
        record = lambda: RawRecord(source=self.name, source_id=cid, payload=payload, fetched_at=datetime.now(KST))
        if state["quota"]:
            payload["detail_pending"] = True
            return record()
        try:
            common = await _call(ctx, self.name, "detailCommon2", {"contentId": cid})
            payload["common"] = (items_of(common)[0] or [{}])[0]
            intro = await _call(ctx, self.name, "detailIntro2",
                                {"contentId": cid, "contentTypeId": item.get("contenttypeid")})
            payload["intro"] = (items_of(intro)[0] or [{}])[0]
            payload["images"] = []
            if not item.get("firstimage") or f"{self.name}:{cid}" in ctx.collection_keys:
                imgs = await _call(ctx, self.name, "detailImage2", {"contentId": cid, "imageYN": "Y"})
                payload["images"] = items_of(imgs)[0]
        except QuotaExceeded:
            state["quota"] = True
            payload["detail_pending"] = True
        except UpstreamError as e:  # ConfigError is not an UpstreamError and propagates
            payload["detail_error"] = str(e)
        return record()


async def verify_codes(client: httpx.AsyncClient, settings: Settings, region) -> dict:
    base = _base_params(settings)
    limiter = RateLimiter(settings.tour_concurrency, 0.0)

    async def get(op: str, params: dict) -> dict:
        return check_body(await fetch_json(client, f"{TOURAPI_BASE}/{op}", {**base, **params},
                                           limiter=limiter, source="tourapi.verify"))

    ldong = await get("ldongCode2", {"lDongRegnCd": region.regn_cd, "lDongListYn": "Y", "numOfRows": 100, "pageNo": 1})
    name = ""
    for it in items_of(ldong)[0]:
        if str(it.get("lDongSignguCd", it.get("code", ""))) == region.signgu_cd:
            name = str(it.get("lDongSignguNm", it.get("name", "")))
            break
    bodies = await asyncio.gather(*(
        get("areaBasedList2", {"contentTypeId": t, "numOfRows": 1, "pageNo": 1, **_region_params(region)})
        for t in CONTENT_TYPES
    ))
    counts = {t: items_of(b)[1] for t, b in zip(CONTENT_TYPES, bodies)}
    return {"signgu_ok": name == "진주시", "signgu_name": name, "counts": counts}
