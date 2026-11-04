from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import router as api_router
from app.core.config import Settings, get_settings
from app.services.places_repo import open_places_repo
from app.core.logging import RequestLogMiddleware, install_secret_mask, register_exception_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.places_repo = None
        try:
            app.state.places_repo = open_places_repo(settings)
        except HTTPException:
            pass  # missing DB must not crash startup; endpoints answer 503, health reports data_version None
        try:
            yield
        finally:
            repo, app.state.places_repo = app.state.places_repo, None
            if repo is not None:
                repo.close()

    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.places_repo = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestLogMiddleware)
    register_exception_handlers(app)
    install_secret_mask()
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


def __getattr__(name: str):
    # Lazy `app` so importing app.main (tests) never loads Settings/.env; `uvicorn main:app` still works.
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
