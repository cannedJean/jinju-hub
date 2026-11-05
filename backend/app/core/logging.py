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
    re.compile(r"(://[^:/\s@]+:)[^@\s]+(?=@)"),  # DSN password: scheme://user:***@host
]
_SK_ANT = re.compile(r"sk-ant-[A-Za-z0-9_\-]+")


def mask_secrets(text: str) -> str:
    for p in _MASK_PATTERNS:
        text = p.sub(r"\1***", text)
    return _SK_ANT.sub("***", text)


def _mask_args(args):
    """Mask str elements of record.args, keeping its shape (uvicorn's access formatter needs a 5-tuple)."""
    if isinstance(args, tuple):
        return tuple(mask_secrets(a) if isinstance(a, str) else a for a in args)
    if isinstance(args, dict):
        return {k: mask_secrets(v) if isinstance(v, str) else v for k, v in args.items()}
    return args


class SecretMaskFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not record.args:
            text = record.msg if isinstance(record.msg, str) else str(record.msg)
            masked = mask_secrets(text)
            if masked != text:
                record.msg = masked
        else:
            # Masking a %-template could drop its placeholders, so mask args and check the rendered text.
            record.args = _mask_args(record.args)
            try:
                rendered = record.getMessage()
            except Exception:
                rendered = None
            if rendered is not None and mask_secrets(rendered) != rendered:
                # Never reached for uvicorn.access records (their full path is masked as one arg).
                # A secret only appears once msg and args are combined; flatten as a last resort.
                record.msg = mask_secrets(rendered)
                record.args = ()
        if record.exc_info:
            # Formatter appends exc_text later; render and mask it here so tracebacks cannot leak keys.
            record.exc_text = mask_secrets(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        elif record.exc_text:
            record.exc_text = mask_secrets(record.exc_text)
        if record.stack_info:
            record.stack_info = mask_secrets(record.stack_info)
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
