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
from app.services.places_repo import PlacesRepo, _haversine_m
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


@pytest.fixture(autouse=True)
def _fresh_daily_budget():
    chat_service.reset_daily_budget()
    yield
    chat_service.reset_daily_budget()


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
    assert res.answer == chat_service._fallback_answer(
        asyncio.run(chat_service.gather_context("진주성 근처 냉면집", repo, db, TODAY))
    )
    assert HAYEON in {s.id for s in res.sources}
    assert "[place:" not in res.answer
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
    history = [{"role": "assistant" if i % 2 else "user", "content": f"q{i}"} for i in range(16)]
    _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED), history)
    kw = fake.calls[0]
    assert kw["model"] == "claude-opus-5-5"
    assert kw["output_config"] == {"effort": "low"}
    assert kw["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in kw["betas"]
    assert kw["max_tokens"] == 1024
    assert kw["system"] == chat_service.SYSTEM_PROMPT
    msgs = kw["messages"]
    assert len(msgs) == 11 and msgs[0]["content"] == "q6"
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


def test_upstream_error_returns_flagged_fallback(db_client, monkeypatch):
    # C22: a Claude failure or timeout answers 200 with the deterministic fallback, flagged for the UI.
    import anthropic
    import httpx

    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    errors = [
        anthropic.APIConnectionError(request=req),
        anthropic.APITimeoutError(request=req),
        anthropic.RateLimitError("rl", response=httpx.Response(429, request=req), body=None),
        anthropic.InternalServerError("ise", response=httpx.Response(500, request=req), body=None),
        anthropic.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None),
    ]
    c = db_client(places_db_path=FIXTURE_DB, **KEYED)
    for err in errors:
        _patch(monkeypatch, FakeClient(exc=err))
        r = c.post("/api/chat", json={"message": "진주성 근처 냉면집", "history": []})
        assert r.status_code == 200, type(err)
        body = r.json()
        assert body["fallback"] is True and body["answer"] and body["sources"], type(err)
        assert "sk-ant" not in r.text


def test_claude_answer_is_not_flagged_fallback(repo, db, monkeypatch):
    _patch(monkeypatch, FakeClient(text="네"))
    assert _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED)).fallback is False
    assert _answer("진주성 근처 냉면집", repo, db, _settings()).fallback is True  # no key


def test_daily_limit_switches_to_fallback_without_calling_claude(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    s = _settings(chat_daily_limit=2, **KEYED)
    results = [_answer("진주성 근처 냉면집", repo, db, s) for _ in range(4)]
    assert len(fake.calls) == 2
    assert [r.fallback for r in results] == [False, False, True, True]


def test_daily_limit_resets_on_a_new_kst_day(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    s = _settings(chat_daily_limit=1, **KEYED)
    monkeypatch.setattr(chat_service, "kst_today", lambda: date(2026, 11, 5))
    _answer("진주성 근처 냉면집", repo, db, s)
    _answer("진주성 근처 냉면집", repo, db, s)
    monkeypatch.setattr(chat_service, "kst_today", lambda: date(2026, 11, 6))
    _answer("진주성 근처 냉면집", repo, db, s)
    assert len(fake.calls) == 2


def test_daily_limit_setting_from_env(monkeypatch):
    monkeypatch.setenv("CHAT_DAILY_LIMIT", "7")
    assert Settings(_env_file=None).chat_daily_limit == 7
    monkeypatch.delenv("CHAT_DAILY_LIMIT")
    assert Settings(_env_file=None).chat_daily_limit == 200


def _frontend_chat_timeout_seconds() -> float:
    import re

    src = Path(__file__).resolve().parents[2] / "frontend" / "src" / "api" / "chat.js"
    if not src.is_file():
        pytest.skip("frontend sources not present")
    m = re.search(r"timeout:\s*([\d_]+)", src.read_text(encoding="utf-8"))
    assert m, "postChat must set an explicit timeout"
    return int(m.group(1).replace("_", "")) / 1000


def test_claude_budget_fits_inside_frontend_timeout():
    # M1/M13: retrieval + the weather wait + the Claude call must finish before the browser's chat timeout.
    frontend_chat_timeout = _frontend_chat_timeout_seconds()
    s = _settings()
    assert s.anthropic_timeout_seconds + chat_service.WEATHER_TIMEOUT_SECONDS + 5 <= frontend_chat_timeout
    assert s.anthropic_max_tokens <= 1024


def test_max_tokens_clamped_to_1024(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    _answer("진주성 근처 냉면집", repo, db, _settings(anthropic_max_tokens=4096, **KEYED))
    assert fake.calls[0]["max_tokens"] == 1024


def test_long_message_never_500(db_client):
    # C5/C20: a 500-char message (the input limit) of many words or one long token must not crash.
    c = db_client(places_db_path=FIXTURE_DB)
    words = " ".join(f"단어{i:03d}" for i in range(90))[:500]
    for msg in (words, "가" * 500, "진주성 근처 " + "냉면" * 240):
        r = c.post("/api/chat", json={"message": msg[:500]})
        assert r.status_code == 200, msg[:20]
        assert r.json()["answer"]
    assert c.post("/api/chat", json={"message": "가" * 1000}).status_code == 422  # over the input limit


def test_long_message_terms_capped():
    terms = chat_service._analyze_terms(" ".join(f"단어{i:03d}" for i in range(200)) + " " + "가" * 900)
    assert len(terms) <= chat_service.MAX_TERMS
    assert all(len(t.text) <= chat_service.MAX_TERM_CHARS for t in terms)
    assert len(" ".join(t.text for t in terms)) <= 200


def test_long_assistant_history_is_truncated_not_rejected(db_client, monkeypatch):
    # M2/M9: one long answer must not break every later request in the session with 422.
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    c = db_client(places_db_path=FIXTURE_DB, **KEYED)
    history = [{"role": "user", "content": "냉면"}, {"role": "assistant", "content": "가" * 5000}]
    r = c.post("/api/chat", json={"message": "진주성 근처 냉면집", "history": history})
    assert r.status_code == 200
    sent = fake.calls[0]["messages"][1]["content"]
    assert sent.startswith("가") and len(sent) <= 2000


def test_demo_date_honoured_only_in_demo_mode(db_client, monkeypatch):
    # C3/C21: the chat uses the demo reference date the same way /api/festivals does.
    seen = []
    orig = chat_service.gather_context

    async def spy(message, repo, db, today, settings=None):
        seen.append(today)
        return await orig(message, repo, db, today, settings)

    monkeypatch.setattr(chat_service, "gather_context", spy)
    on = db_client(places_db_path=FIXTURE_DB)
    assert on.post("/api/chat", json={"message": "축제 알려줘", "today": "2026-10-10"}).status_code == 200
    assert seen[-1] == date(2026, 10, 10)
    assert on.post("/api/chat", json={"message": "축제 알려줘", "today": "10월 10일"}).status_code == 422
    from app.services.festival_status import kst_today
    off = db_client(places_db_path=FIXTURE_DB, demo_date_override_enabled=False)
    assert off.post("/api/chat", json={"message": "축제 알려줘", "today": "2026-10-10"}).status_code == 200
    assert seen[-1] == kst_today()
    assert on.post("/api/chat", json={"message": "축제 알려줘"}).status_code == 200
    assert seen[-1] == kst_today()


def test_demo_date_reaches_festival_context(db_client):
    c = db_client(places_db_path=FIXTURE_DB)
    a = c.post("/api/chat", json={"message": "진행 중인 축제 있어?", "today": "2026-11-04"}).json()["answer"]
    b = c.post("/api/chat", json={"message": "진행 중인 축제 있어?", "today": "2025-01-01"}).json()["answer"]
    assert a != b


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


def test_history_leading_assistant_dropped_and_roles_alternate(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    history = [
        {"role": "assistant", "content": "a0"},
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
    ]
    _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED), history)
    roles = [m["role"] for m in fake.calls[0]["messages"]]
    assert roles == ["user", "assistant", "user"]


def test_history_consecutive_user_turns_collapsed(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    history = [{"role": "user", "content": "u1"}, {"role": "user", "content": "u2"}]
    _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED), history)
    msgs = fake.calls[0]["messages"]
    assert [m["role"] for m in msgs] == ["user"]
    assert "u1" in msgs[0]["content"] and "[질문]\n진주성 근처 냉면집" in msgs[0]["content"]


def test_history_system_role_rejected_422(db_client):
    c = db_client(places_db_path=FIXTURE_DB)
    r = c.post("/api/chat", json={"message": "안녕", "history": [{"role": "system", "content": "x"}]})
    assert r.status_code == 422


def test_generic_recommendation_has_context(repo, db, monkeypatch):
    fake = FakeClient(text="네")
    _patch(monkeypatch, fake)
    ctx, _ = asyncio.run(build_context("가볼 만한 곳 추천해줘", repo, db, TODAY))
    assert _place_ids(ctx)
    _answer("가볼 만한 곳 추천해줘", repo, db, _settings(**KEYED))
    assert len(fake.calls) == 1
    _answer("안녕하세요", repo, db, _settings(**KEYED))
    assert len(fake.calls) == 2


def test_marker_with_inner_whitespace(repo, db, monkeypatch):
    _patch(monkeypatch, FakeClient(text=f"하연옥 [place: {HAYEON} ] 추천"))
    res = _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED))
    assert [s.id for s in res.sources] == [HAYEON] and "[place" not in res.answer


def test_board_table_unavailable_does_not_break_chat(make_client, tmp_path, caplog):
    # Board DB exists but has no tables -> search_posts raises OperationalError.
    c = make_client(places_db_path=FIXTURE_DB, database_url=f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    with caplog.at_level(logging.WARNING, logger="jinjuhub.chat"):
        r = c.post("/api/chat", json={"message": "냉면 후기 알려줘"})
    assert r.status_code == 200
    assert r.json()["sources"] and all(s["type"] == "place" for s in r.json()["sources"])
    assert any("post context unavailable" in rec.getMessage() for rec in caplog.records)


def test_slow_weather_is_skipped(repo, db, monkeypatch):
    async def slow(settings):
        await asyncio.sleep(2)
        return SimpleNamespace(condition="맑음", temperature=18.0, recommendation_reason="x")

    monkeypatch.setattr(chat_service, "fetch_weather", slow)
    monkeypatch.setattr(chat_service, "WEATHER_TIMEOUT_SECONDS", 0.05, raising=False)
    ctx, _ = asyncio.run(build_context("오늘 날씨 어때", repo, db, TODAY, _settings()))
    assert "[날씨]" not in ctx


def test_search_terms_strip_particles_and_fillers():
    assert chat_service._search_terms("진주성 근처에서 저녁으로 먹을 만한 냉면집 추천해줘") == ["진주성", "냉면"]


def test_food_query_returns_naengmyeon_place(repo, db):
    ret = chat_service._retrieve("진주성 근처에서 저녁으로 먹을 만한 냉면집 추천해줘", repo, db, TODAY)
    ids = [i.id for i in ret.items if i.group == "place"]
    assert HAYEON in ids
    assert "냉면" in ret.items[0].title or ret.items[0].id == HAYEON


def test_search_terms_particle_before_jip_suffix():
    assert chat_service._search_terms("냉면집에서 먹고 싶어") == ["냉면"]
    assert chat_service._search_terms("촉석루에서 가까운 카페") == ["촉석루", "카페"]


# --- synthetic DB shaped like the real one: landmark sight, same-name food row, look-alike rows ---
_COLS = ("id", "category", "title", "overview", "addr", "lat", "lng", "menu", "jinju8_rank")
_LM_LAT, _LM_LNG = 35.1895, 128.0800  # 진주성 sight row
_CH_LAT, _CH_LNG = 35.1895, 128.0819  # 촉석루 sight row


def _rows():
    rows = [
        ("s-castle", "sight", "진주성", "성곽", "진주시 남강로 626", _LM_LAT, _LM_LNG, None, 2),
        ("s-chok", "sight", "촉석루", "누각", "진주시 남강로 626", _CH_LAT, _CH_LNG, None, 1),
        ("f-castle", "food", "진주성", "진주성 이름의 식당", "진주시 먼동 1", 35.30, 128.20, "백반", None),
        ("f-chok", "food", "촉석루", "촉석루 이름의 식당", "진주시 먼동 2", 35.30, 128.21, "백반", None),
    ]
    for k in range(3):  # near the landmark, mention it, do not serve the dish
        rows.append((f"f-chick{k}", "food", f"치킨{k}", "진주성 바로 앞 치킨집", f"진주성로 {k}",
                     _LM_LAT + 0.0002 * (k + 1), _LM_LNG, "치킨", None))
    # (title, offset in 0.001 deg lat): famous 하연옥 is 4th nearest but sorts last alphabetically
    for title, off in [("가냉면", 30), ("나냉면", 2), ("다냉면", 1), ("라냉면", 25), ("마냉면", 3),
                       ("바냉면", 40), ("하연옥", 2.5), ("사냉면", 20)]:
        rows.append((f"f-{title}", "food", title, "물냉면과 비빔냉면", "진주시 어딘가", _LM_LAT + 0.001 * off,
                     _LM_LNG, "물냉면", None))
    # nearest of all, match only the adjective / only mention 카페 in the overview
    rows.append(("f-famous", "food", "유명식당", "진주성 앞 유명한 맛있는 집", "진주시 성안", _LM_LAT + 0.00005,
                 _LM_LNG, "백반", None))
    rows.append(("f-mention", "food", "한식당", "근처에 카페 많음", "진주시 남강로", _CH_LAT + 0.00005, _CH_LNG,
                 "백반", None))
    for k in range(3):
        rows.append((f"c-cafe{k}", "food", f"커피{k} 카페", "분위기 좋은 카페", "진주시 남강로",
                     _CH_LAT + 0.001 * (k + 1), _CH_LNG, "커피", None))
    for k in range(3):
        rows.append((f"f-noise{k}", "food", f"분식{k}", "촉석루 바로 옆 분식집", "진주시 남강로",
                     _CH_LAT + 0.0003 * (k + 1), _CH_LNG, "떡볶이", None))
    return rows


@pytest.fixture
def real_like_repo(tmp_path):
    import shutil
    import sqlite3

    path = tmp_path / "places.db"
    shutil.copy(FIXTURE_DB, path)
    con = sqlite3.connect(path)
    con.execute("DELETE FROM places")
    con.executemany(
        f"INSERT INTO places ({','.join(_COLS)}, title_norm) VALUES ({','.join('?' * len(_COLS))}, '')",
        _rows(),
    )
    con.execute("INSERT INTO places_fts(places_fts) VALUES('rebuild')")
    con.commit()
    con.close()
    r = PlacesRepo(path)
    yield r
    r.close()


def _titles(repo, message):
    cats = [c for c in chat_service._detect_categories(message) if c != "festival"]
    found = chat_service._search_places(repo, cats, chat_service._analyze_terms(message), [])
    return [(p.id, p.title) for p in found], found


def test_dish_near_landmark_sorted_by_distance(real_like_repo):
    pairs, found = _titles(real_like_repo, "진주성 근처에서 저녁으로 먹을 만한 냉면집 추천해줘")
    titles = [t for _, t in pairs]
    assert len(titles) == chat_service.MAX_PLACES
    assert all("냉면" in t or t == "하연옥" for t in titles)
    assert titles == ["다냉면", "나냉면", "하연옥", "마냉면", "사냉면", "라냉면"]
    assert "하연옥" in titles
    dists = [_haversine_m(_LM_LAT, _LM_LNG, p.lat, p.lng) for p in found]
    assert dists == sorted(dists)


def test_cafe_near_landmark_only_cafes(real_like_repo):
    pairs, _ = _titles(real_like_repo, "촉석루 근처 카페")
    titles = [t for _, t in pairs]
    assert titles[:3] == ["커피0 카페", "커피1 카페", "커피2 카페"]  # title matches before overview-only mentions
    assert titles[3] == "한식당"
    pairs, _ = _titles(real_like_repo, "촉석루에서 가까운 카페")
    assert [t for _, t in pairs][:3] == titles[:3]


@pytest.mark.parametrize("msg", ["진주성 근처 유명한 냉면집", "진주성 근처 맛있는 냉면집 추천해줘"])
def test_adjectives_do_not_widen_dish_filter(real_like_repo, msg):
    pairs, _ = _titles(real_like_repo, msg)
    assert [t for _, t in pairs] == ["다냉면", "나냉면", "하연옥", "마냉면", "사냉면", "라냉면"]


def test_particle_or_keeps_both_dishes():
    terms = chat_service._analyze_terms("진주성 근처 냉면이나 국밥")
    assert [t.text for t in terms] == ["진주성", "냉면", "국밥"]


def test_noodle_words_are_targets_and_admin_areas_locations():
    by = {t.text: t for t in chat_service._analyze_terms("가좌동 근처 볶음면")}
    assert chat_service._has_location_shape("가좌동") and not chat_service._has_location_shape("볶음면")
    assert not chat_service._has_location_shape("쫄면") and chat_service._has_location_shape("금곡면")
    assert by["가좌동"].marked


def test_generic_noun_never_anchors(real_like_repo):
    assert chat_service._resolve_landmark(real_like_repo, "카페") is None
    assert chat_service._resolve_landmark(real_like_repo, "공원") is None


def test_anchor_fallback_when_no_target_hits(real_like_repo):
    pairs, found = _titles(real_like_repo, "진주성 근처 볶음면")
    assert pairs and all(_haversine_m(_LM_LAT, _LM_LNG, p.lat, p.lng) <= 3000 for p in found)


def test_home_word_never_anchors_and_is_not_a_target(real_like_repo, monkeypatch):
    asked = []
    orig = chat_service._resolve_landmark
    monkeypatch.setattr(chat_service, "_resolve_landmark",
                        lambda repo, term, strict=False: asked.append(term) or orig(repo, term, strict))
    assert chat_service._search_terms("우리집 근처 카페") == ["우리집", "카페"]
    pairs, found = _titles(real_like_repo, "우리집 근처 카페")
    assert all(p.category == "food" for p in found) and "커피0 카페" in [t for _, t in pairs]
    assert "우리" not in asked


def test_restaurant_not_over_stripped():
    assert chat_service._search_terms("진주성 근처 레스토랑") == ["진주성", "레스토랑"]
    assert chat_service._search_terms("코로나 사랑") == ["코로나", "사랑"]


def test_fallback_keeps_food_intent(real_like_repo):
    _, found = _titles(real_like_repo, "진주성 근처 볶음면")
    assert found and all(p.category == "food" for p in found)


def test_activity_word_is_target_not_location():
    assert not chat_service._has_location_shape("체험활동")
    assert chat_service._has_location_shape("가좌동")
    assert [t.text for t in chat_service._analyze_terms("체험활동 알려줘")] == ["체험활동"]


def test_anchored_question_without_nearby_match_says_so(real_like_repo, db, monkeypatch):
    # M0: nothing within the cap of the anchor -> no far places presented as near, and the answer says so.
    monkeypatch.setattr(chat_service, "_ANCHOR_CAP_M", 1)
    ret = chat_service._retrieve("진주성 근처 냉면집", real_like_repo, db, TODAY)
    assert not [i for i in ret.items if i.group == "place"]
    assert "찾지 못함" in ret.context()
    assert "찾지 못함" in chat_service._fallback_answer(ret)


def test_anchored_lines_carry_distance(real_like_repo, db):
    ret = chat_service._retrieve("진주성 근처 냉면집", real_like_repo, db, TODAY)
    lines = [i.line for i in ret.items if i.group == "place"]
    assert lines and all("진주성에서 약 " in ln for ln in lines)
    assert all(ln.count(" | ") == 3 for ln in lines)


def test_unexpected_client_error_returns_flagged_fallback(repo, db, monkeypatch, caplog):
    # Last resort: any other exception from the Claude call answers with the fallback, logging its type only.
    _patch(monkeypatch, FakeClient(exc=ValueError("boom sk-ant-secret")))
    with caplog.at_level(logging.WARNING, logger="jinjuhub.chat"):
        res = _answer("진주성 근처 냉면집", repo, db, _settings(**KEYED))
    assert res.fallback is True and res.answer
    logged = " ".join(r.getMessage() for r in caplog.records)
    assert "ValueError" in logged and "sk-ant" not in logged and "boom" not in logged


def test_upstream_error_class_removed():
    assert not hasattr(chat_service, "ChatUpstreamError")


def test_negated_term_is_excluded():
    by = {t.text: t for t in chat_service._analyze_terms("비빔밥 말고 다른 냉면")}
    assert by["비빔밥"].excluded and not by["냉면"].excluded
    assert "말고" not in by and "다른" not in by


def test_category_word_used_as_location_is_not_an_intent():
    assert chat_service._detect_categories("숙소 근처 맛집") == ["food"]
    assert chat_service._detect_categories("진주성 근처 냉면집") == ["food"]
    assert chat_service._detect_categories("숙소 추천") == ["stay"]


def test_photo_night_and_kid_words_are_not_text_terms():
    q = chat_service._analyze_query("촉석루 야경 사진 찍기 좋은 곳")
    assert [t.text for t in q.terms] == ["촉석루"] and q.night
    q = chat_service._analyze_query("아이들과 밤에 갈만한 곳")
    assert q.kids and q.night and q.terms == []


def test_intent_lexicon_matches_prefix_plus_particles_only():
    q = chat_service._analyze_query("국립진주박물관 근처 점심 먹을 곳")
    assert q.categories == ["food"] and [t.text for t in q.terms] == ["국립진주박물관"]
    assert not chat_service._analyze_query("아이스크림 맛집").kids  # 아이 + 스크림 is not 아이 + particles
    assert not chat_service._analyze_query("밤라떼 카페").night
    assert chat_service._analyze_query("먹을만한 곳").categories == ["food"]  # loose prefix for verb forms


def test_negation_is_applied_before_intents():
    q = chat_service._analyze_query("축제 말고 다른 볼거리")
    assert q.excluded == ["축제"] and "festival" not in q.categories
    q = chat_service._analyze_query("카페 말고 진주 명소")
    assert q.categories == ["sight"] and q.excluded == ["카페"]
    q = chat_service._analyze_query("카페 말고도 맛집")  # 말고도 = besides: not a negation
    assert q.excluded == [] and "food" in q.categories


def test_new_particles_need_a_two_char_stem():
    assert chat_service._search_terms("박물관과 공원까지") == ["박물관", "공원"]
    assert chat_service._search_terms("함께 사과") == ["함께", "사과"]


def test_english_cafe_sets_food_intent():
    assert chat_service._detect_categories("진주성 근처 coffee") == ["food"]
    assert chat_service._detect_categories("cafe 추천") == ["food"]


def test_festival_without_venues_anchors_on_its_own_row(repo, db):
    fest = next(r for r in repo.festival_rows() if not r["venue_place_ids"] and r["lat"] is not None)
    v = chat_service._festival_venue(repo, fest)
    assert v is not None and v.id == fest["id"]


def test_place_results_skip_festival_rows_without_festival_intent(repo, db):
    ret = chat_service._retrieve("진주성 근처 갈만한 곳", repo, db, TODAY)
    fest_ids = {r["id"] for r in repo.festival_rows()}
    assert not [i for i in ret.items if i.group == "place" and i.id in fest_ids]


def test_excluded_word_drops_rows_mentioning_it_or_a_synonym(tmp_path):
    rows = [
        ("x-cafe", "food", "커피집", "디저트", "x", 35.1, 128.1, None, None),
        ("x-ov", "food", "한식당", "옆에 카페가 있다", "x", 35.1, 128.1, None, None),
        ("x-ok", "food", "국밥집", "국밥", "x", 35.1, 128.1, "국밥", None),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, ["food"], chat_service._analyze_terms("카페 말고 맛집"), [])
        assert [p.id for p in found] == ["x-ok"]
    finally:
        r.close()


def test_overview_only_question_gets_the_curated_order(tmp_path):
    rows = [
        ("o-1", "sight", "가나다 공원", "처음 오는데 좋은 곳", "x", 35.1, 128.1, None, None),
        ("o-8", "sight", "제1경 성", "성곽", "x", 35.1, 128.1, None, 1),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, [], chat_service._analyze_terms("처음 오는데 가볼 곳"), [])
        assert found[0].id == "o-8"
    finally:
        r.close()


def _extra_rows_repo(tmp_path, rows):
    import shutil
    import sqlite3

    path = tmp_path / "extra.db"
    shutil.copy(FIXTURE_DB, path)
    con = sqlite3.connect(path)
    con.execute("DELETE FROM places")
    con.executemany(
        f"INSERT INTO places ({','.join(_COLS)}, title_norm) VALUES ({','.join('?' * len(_COLS))}, '')", rows)
    con.execute("INSERT INTO places_fts(places_fts) VALUES('rebuild')")
    con.commit()
    con.close()
    return PlacesRepo(path)


def test_duplicate_exact_landmark_resolves_near_its_jinju8_row(tmp_path):
    # Two rows titled exactly 호수 (one a 4 km outlier with the smaller id): the one near the jinju8 row wins.
    rows = [
        ("a-outlier", "sight", "호수", "호수", "x", 35.18, 127.99, None, None),
        ("z-centre", "sight", "호수", "호수", "x", 35.17, 128.03, None, None),
        ("j-8", "sight", "제8경 호수 노을", "노을", "x", 35.171, 128.031, None, 8),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        assert chat_service._resolve_landmark(r, "호수").id == "z-centre"
        assert chat_service._resolve_landmark(r, "호수", strict=True).id == "z-centre"
    finally:
        r.close()


def test_duplicate_exact_landmark_without_jinju8_uses_centroid(tmp_path):
    rows = [
        ("a-outlier", "sight", "서원", "서원", "x", 35.30, 127.80, None, None),
        ("m-main", "culture", "진주 서원(書院)", "서원", "x", 35.20, 128.00, None, None),
        ("n-gate", "sight", "서원 정문", "문", "x", 35.201, 128.001, None, None),
        ("n-wall", "sight", "서원 담장", "담", "x", 35.199, 127.999, None, None),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        assert chat_service._resolve_landmark(r, "서원").id == "m-main"
    finally:
        r.close()


def test_anchored_ranking_ignores_location_text_hits(tmp_path):
    # "진주성 맛집": a row 3 km away that mentions 진주성 must not outrank one 100 m away (distance does proximity).
    rows = [
        ("s-castle", "sight", "진주성", "성곽", "x", _LM_LAT, _LM_LNG, None, 2),
        ("f-far", "food", "먼식당", "진주성이 보이는 식당", "x", _LM_LAT + 0.027, _LM_LNG, "백반", None),
        ("f-near", "food", "가까운식당", "한식", "x", _LM_LAT + 0.0009, _LM_LNG, "백반", None),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, ["food"], chat_service._analyze_terms("진주성 맛집"), [])
        assert [p.id for p in found] == ["f-near", "f-far"]
    finally:
        r.close()


def test_coordination_prefers_rows_hitting_every_target(tmp_path):
    # A row hitting one rare word in its title must not outrank a row hitting both words of the question.
    rows = [
        ("t-junk", "culture", "단청 묘", "묘소", "x", 35.1, 128.1, None, None),
        ("t-both", "sight", "촉석루 누각", "단청이 아름답다", "x", 35.1, 128.1, None, None),
        ("t-one", "sight", "촉석루 앞 광장", "광장", "x", 35.1, 128.1, None, None),
        ("t-one2", "sight", "촉석루 표지석", "돌", "x", 35.1, 128.1, None, None),
        ("t-one3", "sight", "촉석루 쉼터", "쉼터", "x", 35.1, 128.1, None, None),
        ("t-none", "sight", "다른 곳", "없음", "x", 35.1, 128.1, None, None),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, [], chat_service._analyze_terms("촉석루 단청"), [])
        ids = [p.id for p in found]
        assert ids[0] == "t-both" and ids.index("t-junk") > 0
    finally:
        r.close()


def test_unmatched_compound_backs_off_to_its_head_noun(tmp_path):
    rows = [
        ("h-market", "sight", "중앙시장", "오래된 시장", "x", 35.1, 128.1, None, None),
        ("h-8", "sight", "제1경 성", "전통시장 옆 성곽", "x", 35.1, 128.1, None, 1),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, [], chat_service._analyze_terms("전통시장 구경"), [])
        assert found[0].id == "h-market"
    finally:
        r.close()


def test_excluded_words_are_normalized_like_search_terms():
    assert chat_service._analyze_query("냉면집 말고 다른 맛집").excluded == ["냉면"]
    assert chat_service._analyze_query("축제는 말고 다른 곳").excluded == ["축제"]


def test_term_cap_keeps_priority_terms_then_the_last_ones():
    msg = "안녕하세요 이번 주말에 처음으로 진주에 놀러 가는데요 혹시 진주성 근처에 분위기 좋은 카페가 있을까요"
    terms = chat_service._search_terms(msg)
    assert len(terms) <= chat_service.MAX_TERMS and "진주성" in terms and "카페" in terms
    assert "안녕하세요" not in terms  # the first filler words are dropped, not the head-final ones


def test_time_of_day_sets_food_only_with_a_food_word_or_alone():
    cats = chat_service._detect_categories
    assert "food" not in cats("아침에 산책하기 좋은 곳")
    assert "food" not in cats("저녁에 가볼 만한 곳")
    assert cats("저녁 추천해줘") == ["food"]
    assert cats("점심 먹을 곳") == ["food"]
    assert cats("밥집 추천") == ["food"]


def test_keyword_inside_a_proper_noun_sets_no_category():
    titles = ["국립진주박물관", "진주성"]
    assert chat_service._analyze_query("국립진주박물관 휴관일", titles).categories == []
    assert chat_service._analyze_query("박물관 추천", titles).categories == ["culture"]


def test_scenic_overview_mention_is_a_real_match(tmp_path):
    rows = [
        ("s-maple", "sight", "어느 산", "가을 단풍이 아름답다", "x", 35.1, 128.1, None, None),
        ("s-8", "sight", "제1경 성", "성곽", "x", 35.1, 128.1, None, 1),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, ["sight"], chat_service._analyze_terms("단풍 명소"), [])
        assert found[0].id == "s-maple"
    finally:
        r.close()


def test_unresolved_marked_location_is_noted(real_like_repo, db):
    ret = chat_service._retrieve("진주썽 근처 맛집", real_like_repo, db, TODAY)
    assert "'진주썽' 위치를 찾지 못함" in ret.context()
    assert not any("에서 약 " in i.line for i in ret.items)  # nothing is presented as "near"


def test_night_ask_survives_a_festival_question_and_boosts_within_a_category(tmp_path):
    rows = [
        ("n-view", "sight", "별빛길", "강변", "x", 35.1, 128.1, None, None),
        ("st-plain", "stay", "가나호텔", "객실", "x", 35.1, 128.1, None, None),
        ("st-night", "stay", "하늘호텔", "야경이 보이는 객실", "x", 35.1, 128.1, None, None),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        import sqlite3
        con = sqlite3.connect(r._con.execute("PRAGMA database_list").fetchone()[2])
        con.execute("UPDATE places SET tags='[\"night_view\"]' WHERE id='n-view'")
        con.commit()
        con.close()
        r._chat_rows = None
        got = chat_service._rank_places(r, [], [_T("나서")], [], specific_only=True,
                                        hints=chat_service.NIGHT_HINTS)
        assert [p.id for p in got.places] == ["n-view"]
        got = chat_service._rank_places(r, ["stay"], [], [], hints=chat_service.NIGHT_HINTS)
        assert [p.id for p in got.places] == ["st-night", "st-plain"]
    finally:
        r.close()


def _T(text):
    return chat_service._Term(text)


def test_any_meok_form_sets_food_intent():
    assert chat_service._detect_categories("점심 뭐 먹지") == ["food"]
    assert chat_service._detect_categories("진주에서 꼭 먹어봐야 할 것") == ["food"]


def test_filler_words_do_not_claim_nothing_matched_near_the_anchor(real_like_repo, db):
    ret = chat_service._retrieve("진주성 보고 나서 근처 냉면집", real_like_repo, db, TODAY)
    assert "찾지 못함" not in ret.context()


# ---- fix round 4 ----

def test_time_word_next_to_a_location_means_food_near_it(real_like_repo, db):
    for msg in ("진주성 근처 점심", "촉석루 근처 저녁 어디가 좋아?", "진주성 점심"):
        ret = chat_service._retrieve(msg, real_like_repo, db, TODAY)
        places = [i for i in ret.items if i.group == "place"]
        assert places and all(i.id.startswith(("f-", "c-")) for i in places), (msg, [i.title for i in places])
    # an outing word still wins over the meal reading
    assert "food" not in chat_service._detect_categories("진주성 근처 저녁 산책")


def test_proper_noun_suppression_only_for_culture_keywords():
    titles = ["국립진주박물관", "진주냉면산홍 본점"]
    assert chat_service._analyze_query("진주냉면 추천", titles).categories == ["food"]
    assert chat_service._analyze_query("국립진주박물관 휴관일", titles).categories == []


def test_drink_words_mean_food_and_match_the_pub_group():
    q = chat_service._analyze_query("축제 끝나고 한잔할 술집 추천")
    assert "food" in q.categories
    assert "술집" in [t.text for t in q.terms]
    assert "food" in chat_service._analyze_query("맥주 마시기 좋은 곳").categories
    pub = _place_text(title="동네 이자카야")
    branch = _place_text(title="아웃백스테이크하우스 진주점", overview="롯데몰 진주점 안에 있다")
    assert chat_service._hit_weight(pub, "술집", False) >= chat_service._W_TITLE
    assert chat_service._hit_weight(branch, "주점", False) == 0.0  # 진주점 is a branch, not a 주점


def test_english_food_words_set_food_intent():
    for msg in ("restaurant 추천", "good food", "where to eat", "dinner", "lunch near 진주성"):
        assert chat_service._detect_categories(msg) == ["food"], msg
    assert chat_service._search_terms("진주성 근처 restaurant") == ["진주성"]


def test_shop_suffix_may_leave_a_one_char_dish_or_season():
    assert chat_service._analyze_terms("빵집 어디예요") == [chat_service._Term("빵", shop=True)]
    assert chat_service._search_terms("봄에 가볼 곳") == ["봄"]
    assert chat_service._search_terms("가을에 가볼 곳") == ["가을"]


def test_seasons_are_scenic_synonyms():
    maple = _place_text(overview="단풍이 아름답다")
    blossom = _place_text(overview="벚꽃 명소")
    assert chat_service._hit_weight(maple, "가을", False) > 0
    assert chat_service._hit_weight(blossom, "봄", False) > 0
    assert chat_service._hit_weight(maple, "봄", False) == 0


def test_late_night_words_set_night():
    for msg in ("밤늦게 갈 곳", "밤늦은 시간 식당", "심야 식당"):
        assert chat_service._analyze_query(msg).night, msg


def test_generic_festival_question_returns_no_places(real_like_repo, db):
    for msg in ("밤에 하는 축제 있어?", "아이랑 갈 만한 축제 있어?", "비 오는데 축제 하나요?"):
        ret = chat_service._retrieve(msg, real_like_repo, db, TODAY)
        assert not [i for i in ret.items if i.group == "place"], msg


def test_parking_question_prefers_rows_with_parking_info(tmp_path, db):
    rows = [(f"s-{k}", "sight", f"명소{k}", "볼거리", "x", 35.1, 128.1, None, None) for k in range(4)]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        import sqlite3
        con = sqlite3.connect(r._con.execute("PRAGMA database_list").fetchone()[2])
        con.execute("UPDATE places SET parking='전화문의' WHERE id='s-0'")
        con.execute("UPDATE places SET parking='가능 (소형 약 20대) 무료' WHERE id='s-3'")
        con.commit()
        con.close()
        ret = chat_service._retrieve("주차하기 편한 관광지", r, db, TODAY)
        places = [i for i in ret.items if i.group == "place"]
        assert places[0].id == "s-3"
        assert "주차: 가능 (소형 약 20대) 무료" in places[0].line
        assert "주차" not in "".join(i.line for i in places[1:])
        assert not any(t.startswith("주차") for t in chat_service._search_terms("주차하기 편한 관광지"))
    finally:
        r.close()


def test_accessibility_question_gets_a_not_available_note(real_like_repo, db):
    ret = chat_service._retrieve("휠체어나 유모차로 다니기 편한 곳 있을까요?", real_like_repo, db, TODAY)
    assert "접근성" in ret.context() and "없음" in ret.context()
    assert "접근성" not in chat_service._retrieve("진주성 근처 냉면", real_like_repo, db, TODAY).context()


def test_info_question_with_a_time_word_keeps_the_place(real_like_repo, db):
    # "저녁 운영시간" asks about the place, not for dinner
    for msg in ("진주성 저녁 운영시간 알려줘", "진주성 저녁 입장료", "진주성 아침 일찍 열어요?"):
        q = chat_service._analyze_query(msg)
        assert q.info, msg
        assert not chat_service._time_means_meal(q, real_like_repo, {}), msg


def test_diet_question_gets_a_not_available_note(real_like_repo, db):
    ret = chat_service._retrieve("채식하는 사람도 먹을 수 있는 식당 있어요?", real_like_repo, db, TODAY)
    assert "식단" in ret.context() and "없음" in ret.context()
    assert "식단" not in chat_service._retrieve("진주성 근처 냉면", real_like_repo, db, TODAY).context()


def test_unknown_english_word_near_an_anchor_is_noted(real_like_repo, db):
    ret = chat_service._retrieve("진주성 근처 bakery", real_like_repo, db, TODAY)
    assert "찾지 못함" in ret.context()


def _place_text(title="이름", overview="", menu="", category="food"):
    from app.services.places_repo import PlaceText
    return PlaceText(id="x", category=category, title=title, summary=None, addr=None, lat=None, lng=None, tags=(),
                     jinju8_rank=None, is_collection=False, title_l=title.lower(), menu_l=menu.lower(),
                     overview_l=overview.lower(), addr_l="")


def test_english_filler_and_near_marker(real_like_repo, db):
    assert chat_service._analyze_terms("good food near 진주성") == [chat_service._Term("진주성", marked=True)]
    ret = chat_service._retrieve("good food near 진주성", real_like_repo, db, TODAY)
    places = [i for i in ret.items if i.group == "place"]
    assert places and all(i.id.startswith(("f-", "c-")) for i in places) and "찾지 못함" not in ret.context()


def test_one_syllable_word_names_a_place_only_as_a_whole_word():
    assert chat_service._hit_weight(_place_text(title="비봉산의 봄"), "봄", False) >= chat_service._W_TITLE
    assert chat_service._hit_weight(_place_text(title="누리봄 농장"), "봄", False) == 0.0
    assert chat_service._hit_weight(_place_text(menu="꽃갈비"), "꽃", False) == 0.0
    assert chat_service._hit_weight(_place_text(title="수복빵집"), "빵", False) >= chat_service._W_TITLE


def test_scenic_words_alone_look_among_sights(tmp_path):
    rows = [
        ("f-flower", "food", "꽃 식당", "꽃이 핀 정원", "x", 35.1, 128.1, None, None),
        ("s-flower", "sight", "꽃 동산", "꽃이 핀 언덕", "x", 35.1, 128.1, None, None),
    ]
    r = _extra_rows_repo(tmp_path, rows)
    try:
        found = chat_service._search_places(r, [], chat_service._analyze_terms("꽃 구경하기 좋은 곳"), [])
        assert [p.id for p in found] == ["s-flower"]
    finally:
        r.close()


def test_an_outing_done_first_does_not_block_the_meal():
    q = chat_service._analyze_query("진주성 구경하고 점심")
    assert q.time_word and not q.activity
    assert chat_service._analyze_query("진주성 구경하고 싶은데 저녁").activity
    assert chat_service._analyze_query("오늘 저녁 뭐하지").activity


def test_drink_question_without_bars_says_nothing_matched(real_like_repo, db):
    ret = chat_service._retrieve("술집 추천", real_like_repo, db, TODAY)
    assert "찾지 못함" in ret.context()
