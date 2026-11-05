from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded


def client_ip(request: Request) -> str:
    """Rate-limit key that a client cannot spoof behind Render's proxy.

    Prefer True-Client-IP (set by Render's edge), else the LAST X-Forwarded-For hop (appended by the
    proxy in front of us; earlier entries are client-controlled), else the socket peer.
    """
    true_ip = request.headers.get("true-client-ip", "").strip()
    if true_ip:
        return true_ip
    hops = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
    if hops:
        return hops[-1]
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=client_ip, default_limits=[])


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
