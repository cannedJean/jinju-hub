from alembic import context
from sqlalchemy import create_engine

from app.models.base import Base
from app.models import board  # noqa: F401  (register models)
from app.services.database import build_engine, normalize_db_url

config = context.config
target_metadata = Base.metadata


def _engine():
    # An explicit URL (tests) wins; otherwise use the app's Settings (DATABASE_URL / backend/.env).
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return create_engine(normalize_db_url(url))
    from app.core.config import Settings

    return build_engine(Settings().database_url)


def run_migrations_offline() -> None:
    context.configure(url=str(_engine().url), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = _engine()
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
