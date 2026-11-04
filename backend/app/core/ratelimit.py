from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address, default_limits=[])


_current_limit = "10/minute"


def set_rate_limit(value: str) -> None:
    """Called by create_app with the app's own Settings, so limits never depend on .env at request time."""
    global _current_limit
    _current_limit = value


def current_rate_limit() -> str:
    return _current_limit


def _rate_limited_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(status_code=429, content={"detail": "rate_limited"})


def register_rate_limit(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limited_handler)
