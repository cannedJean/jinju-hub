from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture_text():
    base = Path(__file__).resolve().parent / "fixtures"

    def _read(relpath: str) -> str:
        return (base / relpath).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def fixture_json():
    import json

    base = Path(__file__).resolve().parent / "fixtures"

    def _read(relpath: str):
        return json.loads((base / relpath).read_text(encoding="utf-8"))

    return _read
