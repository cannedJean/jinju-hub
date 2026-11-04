import asyncio
import logging
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.models import board  # noqa: F401
from app.models.base import Base
from app.schemas.chatbot import ChatRequest
from app.services import chat_service
from app.services.chat_service import answer_chat, build_context
from app.services.database import build_engine
from app.services.places_repo import PlacesRepo
FIXTURE_DB = Path(__file__).parent / "fixtures" / "places_fixture.db"

TODAY = date(2026, 11, 4)
HAYEON = "jh-016bfa03dd"  # 하연옥 하대점 (food, local_food) in the fixture DB
KEYED = dict(anthropic_api_key="sk-ant-test-not-real")


@pytest.fixture
def repo():
    r = PlacesRepo(FIXTURE_DB)
    yield r
    r.close()


@pytest.fixture
def db():
    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _settings(**kw) -> Settings:
    return Settings(_env_file=None, **kw)


class FakeClient:
    """Stands in for AsyncAnthropic: records kwargs, returns a canned response or raises."""

    def __init__(self, text="", stop_reason="end_turn", exc=None, blocks=None):
        self.calls: list[dict] = []
        self._exc = exc
        self._response = SimpleNamespace(
            content=blocks if blocks is not None else [SimpleNamespace(type="text", text=text)],
            stop_reason=stop_reason,
            stop_details=SimpleNamespace(category="x") if stop_reason == "refusal" else None,
        )
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._exc:
            raise self._exc
        return self._response


def _patch(monkeypatch, client):
    monkeypatch.setattr(chat_service, "get_anthropic_client", lambda settings: client)


def _answer(msg, repo, db, settings, history=()):
    req = ChatRequest(message=msg, history=list(history))
    return asyncio.run(answer_chat(req, repo, db, TODAY, settings))


def _place_ids(ctx: str) -> list[str]:
    return [ln.split("]")[0][len("[place:"):] for ln in ctx.splitlines() if ln.startswith("[place:")]


def test_context_food_intent(repo, db):
    ctx, sources = asyncio.run(build_context("진주성 근처 냉면집", repo, db, TODAY))
    place_lines = [ln for ln in ctx.splitlines() if ln.startswith("[place:")]
    assert place_lines
    assert any("맛집" in ln for ln in place_lines)
    assert all(ln.count(" | ") == 3 for ln in place_lines)
    assert {s.id for s in sources} >= set(_place_ids(ctx))


def test_context_limits_places_to_six(repo, db):
    ctx, _ = asyncio.run(build_context("맛집 추천해줘", repo, db, TODAY))
    assert 1 <= len(_place_ids(ctx)) <= 6


def test_context_festival_lists_ongoing(repo, db):
    ctx, sources = asyncio.run(build_context("이번 주 축제 알려줘", repo, db, TODAY))
    assert "jh-5049756acf" in ctx  # ongoing on 2026-11-04
    assert "진행 중" in ctx
    assert any(s.id == "jh-5049756acf" for s in sources)


def test_context_rain_prefers_indoor(repo, db):
    ctx, _ = asyncio.run(build_context("비 오는 날 갈만한 곳", repo, db, TODAY))
    ids = _place_ids(ctx)
    assert ids
    for pid in ids:
        assert "indoor" in repo.get(pid).tags


def test_context_posts_only_when_mentioned(repo, db):
    from app.schemas.board import PostCreate
    from app.services import board_service

    board_service.create_post(
        db, PostCreate(category="food", title="냉면 후기", content="하연옥 냉면 맛있어요", password="1234")
    )
    ctx, sources = asyncio.run(build_context("냉면 후기 알려줘", repo, db, TODAY))
    assert "[post:1]" in ctx and any(s.type == "post" and s.id == "1" for s in sources)
    ctx2, _ = asyncio.run(build_context("냉면집 알려줘", repo, db, TODAY))
    assert "[post:" not in ctx2


def test_context_weather_line_and_failure_ignored(repo, db, monkeypatch):
    async def ok(settings):
        return SimpleNamespace(condition="맑음", temperature=18.0, recommendation_reason="야외 활동에 적합합니다.")

    monkeypatch.setattr(chat_service, "fetch_weather", ok)
    ctx, _ = asyncio.run(build_context("오늘 날씨 어때", repo, db, TODAY, _settings()))
    assert "[날씨]" in ctx and "맑음" in ctx

    async def boom(settings):
        raise RuntimeError("down")

    monkeypatch.setattr(chat_service, "fetch_weather", boom)
    ctx, _ = asyncio.run(build_context("오늘 날씨 어때", repo, db, TODAY, _settings()))
    assert "[날씨]" not in ctx


def test_sources_only_from_answer_markers(repo, db, monkeypatch):
    fake = FakeClient(text=f"하연옥 [place:{HAYEON}] 추천합니다. 방문 전 운영시간을 확인하세요.")
    _patch(monkeypatch, fake)
    res = _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED))
    assert [s.id for s in res.sources] == [HAYEON]
    assert res.sources[0].type == "place" and res.sources[0].label
    assert "[place:" not in res.answer
    assert res.answer.startswith("하연옥 추천합니다")


def test_unknown_marker_ignored(repo, db, monkeypatch):
    _patch(monkeypatch, FakeClient(text=f"가세요 [place:jh-nope] 그리고 [place:{HAYEON}]"))
    res = _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED))
    assert [s.id for s in res.sources] == [HAYEON]
    assert "jh-nope" not in res.answer and "[place:" not in res.answer


def test_refusal_returns_fallback(repo, db, monkeypatch, caplog):
    _patch(monkeypatch, FakeClient(text="", stop_reason="refusal"))
    with caplog.at_level(logging.WARNING, logger="jinjuhub.chat"):
        res = _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED))
    assert res.answer and "[place:" not in res.answer
    assert "refusal" in " ".join(r.getMessage() for r in caplog.records)


def test_no_key_fallback(repo, db, monkeypatch):
    def must_not_call(settings):
        raise AssertionError("client must not be built without a key")

    monkeypatch.setattr(chat_service, "get_anthropic_client", must_not_call)
    res = _answer("진주성 근처 냉면집", repo, db, _settings())
    assert res.answer and "[place:" not in res.answer
    assert res.sources and all(s.type == "place" for s in res.sources)


def test_fallback_when_nothing_found(repo, db):
    res = _answer("zzzqqq", repo, db, _settings())
    assert res.answer


def test_call_parameters(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    history = [{"role": "user", "content": f"q{i}"} for i in range(15)]
    _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED), history)
    kw = fake.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"] == {"effort": "low"}
    assert kw["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in kw["betas"]
    assert kw["max_tokens"] == 4096
    assert kw["system"] == chat_service.SYSTEM_PROMPT
    msgs = kw["messages"]
    assert len(msgs) == 11 and msgs[0]["content"] == "q5"
    assert msgs[-1]["role"] == "user" and msgs[-1]["content"].startswith("[컨텍스트]\n")
    assert msgs[-1]["content"].endswith("[질문]\n진주성 근처 냉면집")


def test_text_blocks_joined_non_text_ignored(repo, db, monkeypatch):
    blocks = [
        SimpleNamespace(type="thinking", text="secret"),
        SimpleNamespace(type="text", text="가"),
        SimpleNamespace(type="fallback"),
        SimpleNamespace(type="text", text="나"),
    ]
    _patch(monkeypatch, FakeClient(blocks=blocks))
    res = _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED))
    assert res.answer == "가나"


def test_system_prompt_rules():
    p = chat_service.SYSTEM_PROMPT
    assert "[place:" in p and "컨텍스트에 없는" in p and "방문 전" in p


def test_upstream_error_502(db_client, monkeypatch):
    import anthropic
    import httpx

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    errors = [
        anthropic.APIConnectionError(request=req),
        anthropic.RateLimitError("rl", response=httpx.Response(429, request=req), body=None),
        anthropic.InternalServerError("ise", response=httpx.Response(500, request=req), body=None),
    ]
    c = db_client(places_db_path=FIXTURE_DB, **KEYED)
    for err in errors:
        _patch(monkeypatch, FakeClient(exc=err))
        r = c.post("/api/chat", json={"message": "진주성 근처 냉면집", "history": []})
        assert r.status_code == 502, type(err)
        assert "sk-ant" not in r.text


def test_chat_endpoint_ok(db_client, monkeypatch):
    _patch(monkeypatch, FakeClient(text=f"하연옥 [place:{HAYEON}]"))
    c = db_client(places_db_path=FIXTURE_DB, **KEYED)
    r = c.post("/api/chat", json={"message": "진주성 근처 냉면집"})
    assert r.status_code == 200
    body = r.json()
    assert body["sources"][0]["id"] == HAYEON and "[place:" not in body["answer"]


def test_chat_endpoint_validation(db_client):
    c = db_client(places_db_path=FIXTURE_DB)
    assert c.post("/api/chat", json={"message": "   "}).status_code == 422


def test_chat_endpoint_503_without_data(db_client, tmp_path):
    c = db_client(places_db_path=tmp_path / "missing.db")
    assert c.post("/api/chat", json={"message": "안녕"}).status_code == 503


def test_chat_rate_limit_429(db_client):
    from app.core.ratelimit import limiter

    c = db_client(places_db_path=FIXTURE_DB, rate_limit="2/minute")
    limiter.enabled = True
    codes = [c.post("/api/chat", json={"message": "진주성 냉면"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_get_anthropic_client_uses_settings_and_caches():
    s = _settings(anthropic_api_key="sk-ant-test-not-real", anthropic_timeout_seconds=12.5)
    chat_service._build_client.cache_clear()
    c1 = chat_service.get_anthropic_client(s)
    assert c1 is chat_service.get_anthropic_client(s)
    assert c1.timeout == 12.5
    chat_service._build_client.cache_clear()


def test_httpx_loggers_quiet(make_client, tmp_path):
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.DEBUG)
    make_client(places_db_path=tmp_path / "m.db")
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
