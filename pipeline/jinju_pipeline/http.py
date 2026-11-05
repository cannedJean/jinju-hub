"""HTTP layer: rate limiter, retrying fetch_json, daily/run quota ledger."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import date
from pathlib import Path

import httpx
import tenacity


class QuotaExceeded(Exception):
    """Daily/run request budget (or upstream gateway quota) exhausted."""


class ConfigError(Exception):
    """Misconfiguration such as an unregistered or expired API key (CLI exit code 2)."""


class UpstreamError(Exception):
    def __init__(self, message: str, *, status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status = status
        self.retryable = retryable


class RateLimiter:
    """`async with` limiter: caps concurrency and spaces request starts by min_interval."""

    def __init__(self, concurrency: int, min_interval: float):
        self._sem = asyncio.Semaphore(concurrency)
        self._min_interval = min_interval
        self._start_lock = asyncio.Lock()
        self._last_start: float | None = None

    async def __aenter__(self) -> "RateLimiter":
        await self._sem.acquire()
        try:
            async with self._start_lock:
                if self._last_start is not None:
                    delay = self._last_start + self._min_interval - time.monotonic()
                    if delay > 0:
                        await asyncio.sleep(delay)
                self._last_start = time.monotonic()
        except BaseException:
            self._sem.release()
            raise
        return self

    async def __aexit__(self, *exc) -> None:
        self._sem.release()


class QuotaLedger:
    def __init__(self, path: Path | None, daily_limit: int, run_limit: int | None = None, *, today: date):
        self._path = Path(path) if path is not None else None
        self._daily_limit = daily_limit
        self._run_limit = run_limit
        self._today = today.isoformat()
        self._base = self._load_base()
        self._run = 0
        self._by_source: dict[str, int] = {}

    def _load_base(self) -> int:
        if self._path is None or not self._path.exists():
            return 0
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            return int(data.get(self._today, 0))
        except (OSError, ValueError, TypeError, AttributeError):
            return 0

    def consume(self, n: int = 1, source: str | None = None) -> None:
        if self._base + self._run + n > self._daily_limit:
            raise QuotaExceeded(f"daily limit {self._daily_limit} reached")
        if self._run_limit is not None and self._run + n > self._run_limit:
            raise QuotaExceeded(f"run limit {self._run_limit} reached")
        self._run += n
        if source is not None:
            self._by_source[source] = self._by_source.get(source, 0) + n

    def record_unmetered(self, n: int = 1, source: str | None = None) -> None:
        """Count calls per source without spending the key quota (sources that need no key)."""
        if source is not None:
            self._by_source[source] = self._by_source.get(source, 0) + n

    def unmetered(self) -> "UnmeteredLedger":
        return UnmeteredLedger(self)

    def used_today(self) -> int:
        return self._base + self._run

    def used_this_run(self) -> int:
        return self._run

    def used_by_source(self) -> dict[str, int]:
        return dict(self._by_source)

    def save(self) -> None:
        if self._path is None:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({self._today: self.used_today()}), encoding="utf-8")


class UnmeteredLedger:
    """``fetch_json`` ledger view that only counts calls per source (never raises QuotaExceeded)."""

    def __init__(self, ledger: QuotaLedger):
        self._ledger = ledger

    def consume(self, n: int = 1, source: str | None = None) -> None:
        self._ledger.record_unmetered(n, source)


def _raise_for_non_json(text: str, status: int) -> None:
    if "LIMITED_NUMBER_OF_SERVICE_REQUESTS" in text or "<returnReasonCode>22<" in text:
        raise QuotaExceeded("upstream gateway quota exceeded")
    if "<returnReasonCode>30<" in text or "<returnReasonCode>31<" in text:
        raise ConfigError("API key not registered or expired")
    raise UpstreamError(f"non-JSON response: {text[:200]}", status=status, retryable=False)


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict,
    *,
    limiter: RateLimiter,
    ledger: QuotaLedger | UnmeteredLedger | None = None,
    source: str | None = None,
    max_attempts: int = 4,
    wait: tenacity.wait.wait_base | None = None,
) -> dict:
    async def attempt() -> dict:
        if ledger is not None:
            ledger.consume(1, source)
        async with limiter:
            resp = await client.get(url, params=params)
        status = resp.status_code
        if status >= 500:
            raise UpstreamError(f"HTTP {status}", status=status, retryable=True)
        if status >= 400:
            raise UpstreamError(f"HTTP {status}: {resp.text[:200]}", status=status, retryable=False)
        try:
            body = resp.json()
        except ValueError:
            _raise_for_non_json(resp.text, status)
            raise  # unreachable
        if not isinstance(body, dict):
            raise UpstreamError(f"unexpected JSON type: {resp.text[:200]}", status=status, retryable=False)
        return body

    retrying = tenacity.AsyncRetrying(
        stop=tenacity.stop_after_attempt(max_attempts),
        wait=wait or tenacity.wait_exponential(multiplier=0.5, max=8),
        retry=tenacity.retry_if_exception(
            lambda e: getattr(e, "retryable", False) or isinstance(e, httpx.TransportError)
        ),
        reraise=True,
    )
    return await retrying(attempt)


def make_client(timeout: float = 20.0, transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=timeout,
        transport=transport,
        follow_redirects=True,
        headers={"User-Agent": "JinjuHub-pipeline/0.1 (education project)"},
    )
