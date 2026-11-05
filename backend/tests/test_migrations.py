from pathlib import Path

import pytest

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
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


def test_seed_uses_env_password_and_never_demo1234(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'p.db').as_posix()}"
    _upgrade(url)
    monkeypatch.setenv("SEED_POST_PASSWORD", "owner-secret-pw")
    with Session(create_engine(url)) as db:
        seed(db)
        rows = db.scalars(select(BoardPost)).all()
    assert all(verify_password("owner-secret-pw", r.password) for r in rows)
    assert not any(verify_password("demo1234", r.password) for r in rows)


def test_seed_without_env_password_is_random_and_not_printed(tmp_path, monkeypatch, capsys):
    url = f"sqlite:///{(tmp_path / 'r.db').as_posix()}"
    _upgrade(url)
    monkeypatch.delenv("SEED_POST_PASSWORD", raising=False)
    with Session(create_engine(url)) as db:
        seed(db)
        rows = db.scalars(select(BoardPost)).all()
    assert not any(verify_password("demo1234", r.password) for r in rows)
    assert all(r.password.startswith("$2b$") for r in rows)
    out = capsys.readouterr()
    assert "demo1234" not in out.out + out.err


def test_seed_skips_existing_titles_so_rebuilds_do_not_duplicate(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'd.db').as_posix()}"
    _upgrade(url)
    monkeypatch.setenv("SEED_POST_PASSWORD", "first-run-pw")
    with Session(create_engine(url)) as db:
        assert seed(db) == 8
    monkeypatch.setenv("SEED_POST_PASSWORD", "second-run-pw")
    with Session(create_engine(url)) as db:
        assert seed(db) == 0
        rows = db.scalars(select(BoardPost)).all()
    assert len(rows) == 8
    assert all(verify_password("first-run-pw", r.password) for r in rows)
