"""Blank or whitespace-only secrets behave exactly like unset ones (Task K1)."""
import logging

import pytest

from jinju_pipeline.collect import default_sources
from jinju_pipeline.settings import Settings


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_key_is_none(blank):
    assert Settings(_env_file=None, data_go_kr_key=blank).data_go_kr_key is None


def test_real_looking_key_is_kept():
    s = Settings(_env_file=None, data_go_kr_key="abc")
    assert s.data_go_kr_key is not None
    assert s.data_go_kr_key.get_secret_value() == "abc"


def test_blank_env_var_is_none(monkeypatch):
    monkeypatch.setenv("DATA_GO_KR_KEY", "  ")
    assert Settings(_env_file=None).data_go_kr_key is None


def test_blank_env_file_line_is_none(tmp_path, monkeypatch):
    monkeypatch.delenv("DATA_GO_KR_KEY", raising=False)
    env = tmp_path / ".env"
    env.write_text("DATA_GO_KR_KEY=\n", encoding="utf-8")
    assert Settings(_env_file=env).data_go_kr_key is None


@pytest.mark.parametrize("blank", ["", "   "])
def test_default_sources_blank_key_excludes_tourapi(blank, caplog):
    s = Settings(_env_file=None, data_go_kr_key=blank)
    with caplog.at_level(logging.WARNING):
        names = [x.name for x in default_sources(s)]
    assert not any(n.startswith("tourapi") for n in names)
    assert "DATA_GO_KR_KEY" in caplog.text
