from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


def normalize_db_url(url: str) -> str:
    """postgres:// and postgresql:// -> postgresql+psycopg:// (psycopg v3 driver)."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


def build_engine(database_url: str) -> Engine:
    """Create an engine lazily (no connection is opened here)."""
    url = normalize_db_url(database_url)
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if make_url(url).database in (None, "", ":memory:"):
            kwargs["poolclass"] = StaticPool  # one shared connection so in-memory data is visible
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db(request: Request) -> Iterator[Session]:
    db = request.app.state.session_factory()
    try:
        yield db
    finally:
        db.close()
