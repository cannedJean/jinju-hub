"""Request logging, secret masking and the global exception handler."""
import json
import logging
import re
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

request_logger = logging.getLogger("jinjuhub.request")
error_logger = logging.getLogger("jinjuhub.error")

_MASK_PATTERNS = [
    re.compile(r"(?i)(serviceKey\s*=\s*)[^&\s\"']+"),
    re.compile(r"(?i)(authKey\s*=\s*)[^&\s\"']+"),
    re.compile(r"(?i)(api[_-]?key[\"']?\s*[=:]\s*[\"']?)[^&\s\"',]+"),
    re.compile(r"(?i)(x-api-key[\"']?\s*[=:]\s*[\"']?)[^&\s\"',]+"),
]
_SK_ANT = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")


def mask_secrets(text: str) -> str:
    for p in _MASK_PATTERNS:
        text = p.sub(r"\1***", text)
    return _SK_ANT.sub("***", text)


class SecretMaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask_secrets(record.getMessage())
        record.args = None
        return True


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            request_logger.info(json.dumps({
                "method": request.method,
                "path": request.url.path,
                "status": status,
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }))


def install_secret_mask() -> None:
    """Attach the mask to every handler on the root logger (and uvicorn's), idempotently."""
    for name in ("", "uvicorn", "uvicorn.error", "uvicorn.access"):
        for h in logging.getLogger(name).handlers:
            if not any(isinstance(f, SecretMaskFilter) for f in h.filters):
                h.addFilter(SecretMaskFilter())
    for lg in (request_logger, error_logger):
        if not any(isinstance(f, SecretMaskFilter) for f in lg.filters):
            lg.addFilter(SecretMaskFilter())


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        error_logger.error(
            "unhandled error on %s %s", request.method, request.url.path, exc_info=(type(exc), exc, exc.__traceback__)
        )
        return JSONResponse(status_code=500, content={"detail": "internal_error"})
