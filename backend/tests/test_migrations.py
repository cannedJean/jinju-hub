from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.board import BoardPost
from app.scripts.seed_posts import SEED_POSTS, seed

BACKEND = Path(__file__).resolve().parents[1]


def _upgrade(url: str) -> None:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")


def test_alembic_upgrade_on_sqlite(tmp_path):
    url = f"sqlite:///{(tmp_path / 'm.db').as_posix()}"
    _upgrade(url)
    cols = {c["name"] for c in inspect(create_engine(url)).get_columns("board_posts")}
    assert cols == {"id", "category", "title", "content", "password", "views", "created_at", "updated_at"}


def test_seed_idempotent(tmp_path):
    url = f"sqlite:///{(tmp_path / 's.db').as_posix()}"
    _upgrade(url)
    with Session(create_engine(url)) as db:
        assert seed(db) == 8
        assert seed(db) == 0
        rows = db.scalars(select(BoardPost)).all()
    assert len(rows) == 8
    assert {r.category for r in rows} == {"tour", "food", "festival", "free"}
    assert all(r.password.startswith("$2b$") for r in rows)
    assert len(SEED_POSTS) == 8
