"""Offline end-to-end runs of the whole pipeline over the recorded fixtures (no network)."""
import asyncio
import json
import sqlite3
from contextlib import closing
from datetime import date, datetime

import httpx
import pytest
from pydantic import SecretStr

from jinju_pipeline.__main__ import main, settings_for_env
from jinju_pipeline.raw_store import KST, new_run_id
from jinju_pipeline.runner import run_pipeline

NOW = datetime(2026, 11, 4, 3, 0, tzinfo=KST)
NOW2 = datetime(2026, 11, 11, 3, 0, tzinfo=KST)
TODAY = date(2026, 11, 4)


def all_ids(db) -> list[str]:
    with closing(sqlite3.connect(db)) as con:
        return [r[0] for r in con.execute("select id from places order by id")]


async def test_pipeline_end_to_end_offline(tmp_settings, recorded_transport):
    report, gate = await run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW,
                                      transport=recorded_transport)
    assert gate.passed, gate.failures
    with closing(sqlite3.connect(tmp_settings.output_db)) as con:
        assert con.execute("select count(*) from places").fetchone()[0] == report["final_count"] > 0
        assert con.execute("select count(*) from badges").fetchone()[0] == 6
        meta = dict(con.execute("select key, value from meta"))
    assert json.loads(meta["category_counts"])
    assert meta["data_version"] == report["run_id"] == new_run_id(NOW)
    assert meta["content_hash"] == report["content_hash"]
    assert meta["reused_streak"] == "0"
    assert json.loads(tmp_settings.output_report.read_text(encoding="utf-8"))["run_id"] == report["run_id"]
    work = tmp_settings.work_dir / report["run_id"]
    for name in ("clean.jsonl", "merge.jsonl", "merge_log.jsonl", "report.json", "report.md"):
        assert (work / name).exists(), name
    assert sum(1 for _ in (work / "clean.jsonl").open(encoding="utf-8")) == report["cleaned_count"]
    assert (tmp_settings.state_dir / "quota.json").exists()


async def test_second_run_keeps_ids(tmp_settings, recorded_transport):
    await run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW, transport=recorded_transport)
    ids1 = all_ids(tmp_settings.output_db)
    _, gate = await run_pipeline(tmp_settings, incremental=True, today=TODAY, now=NOW2,
                                 transport=recorded_transport)
    assert gate.passed, gate.failures
    assert all_ids(tmp_settings.output_db) == ids1
    with closing(sqlite3.connect(tmp_settings.output_db)) as con:
        seqs = dict(con.execute("select place_id, issued_seq from id_order"))
    assert set(ids1) <= set(seqs) and len(set(seqs.values())) == len(seqs)


def test_gate_failure_keeps_previous_db(tmp_settings, recorded_transport, transport_returning_few):
    asyncio.run(run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW, transport=recorded_transport))
    before_db = tmp_settings.output_db.read_bytes()
    before_report = tmp_settings.output_report.read_bytes()
    code = main(["run", "--today", "2026-11-11"], settings=tmp_settings, transport=transport_returning_few)
    assert code == 1
    assert tmp_settings.output_db.read_bytes() == before_db
    assert tmp_settings.output_report.read_bytes() == before_report
    failed = [d for d in tmp_settings.work_dir.iterdir() if d.name != new_run_id(NOW)]
    assert len(failed) == 1
    rep = json.loads((failed[0] / "report.json").read_text(encoding="utf-8"))
    assert rep["final_count"] < 0.8 * len(all_ids(tmp_settings.output_db))


async def test_until_clean_and_merge_stop_without_publishing(tmp_settings, recorded_transport):
    report, gate = await run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW,
                                      transport=recorded_transport, until="clean")
    work = tmp_settings.work_dir / report["run_id"]
    assert gate.passed and report["stage"] == "clean" and report["cleaned_count"] > 0
    assert (work / "clean.jsonl").exists() and not (work / "merge.jsonl").exists()
    report, gate = await run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW,
                                      transport=recorded_transport, until="merge")
    assert report["stage"] == "merge" and report["merged_count"] > 0
    assert (work / "merge.jsonl").exists()
    assert not tmp_settings.output_db.exists() and not tmp_settings.output_report.exists()


async def test_pipeline_with_tourapi_sources_offline(tmp_settings, recorded_transport):
    settings = tmp_settings.model_copy(update={"data_go_kr_key": SecretStr("test-key")})
    report, gate = await run_pipeline(settings, incremental=False, today=TODAY, now=NOW,
                                      transport=recorded_transport)
    assert gate.passed, gate.failures
    status = {s["source"]: s["status"] for s in report["sources"]}
    assert status["tourapi.area"] == "ok" and status["tourapi.festival"] == "ok"
    with closing(sqlite3.connect(settings.output_db)) as con:
        n = con.execute("select count(*) from place_sources where source like 'tourapi.%'").fetchone()[0]
    assert n == 57 + 8  # recorded areaBasedList2 type 12 (57) + searchFestival2 (8)


def test_cli_run_exit_0_and_out_path(tmp_settings, recorded_transport, tmp_path, capsys):
    out = tmp_path / "alt" / "places.db"
    assert main(["run", "--today", "2026-11-04", "--out", str(out)], settings=tmp_settings,
                transport=recorded_transport) == 0
    assert out.exists() and (out.parent / "report.json").exists()
    assert not tmp_settings.output_db.exists()
    assert "PASS" in capsys.readouterr().out


def test_cli_verify_codes_without_key_exits_2(tmp_settings, capsys):
    assert main(["verify-codes"], settings=tmp_settings) == 2
    assert "DATA_GO_KR_KEY" in capsys.readouterr().err


def test_cli_config_error_exits_2(tmp_settings, capsys):
    def handler(request):
        if request.url.host == "apis.data.go.kr":
            return httpx.Response(200, json={"response": {"header": {
                "resultCode": "30", "resultMsg": "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"}}})
        return httpx.Response(200, json={"record_count": 0, "results": []})

    settings = tmp_settings.model_copy(update={"data_go_kr_key": SecretStr("bad-key")})
    assert main(["run"], settings=settings, transport=httpx.MockTransport(handler)) == 2
    assert "설정 오류" in capsys.readouterr().err
    assert not settings.output_db.exists()


def test_cli_report_prints_markdown(tmp_settings, recorded_transport, capsys):
    assert main(["run", "--today", "2026-11-04"], settings=tmp_settings, transport=recorded_transport) == 0
    run_id = json.loads(tmp_settings.output_report.read_text(encoding="utf-8"))["run_id"]
    capsys.readouterr()
    assert main(["report", "--run-id", run_id], settings=tmp_settings) == 0
    assert "# 품질 리포트" in capsys.readouterr().out
    assert main(["report", "--run-id", "nope"], settings=tmp_settings) == 2


@pytest.mark.parametrize("env, expected", [({"GITHUB_ACTIONS": "true"}, 300), ({}, None)])
def test_runner_environment_caps_run_quota(tmp_settings, env, expected):
    assert settings_for_env(tmp_settings, env).run_quota == expected


def test_cli_out_still_reads_previous_from_canonical_db(tmp_settings, recorded_transport,
                                                       transport_returning_few, tmp_path):
    # --out is the workaround for a locked places.db: ids, aliases and the 80% gate must still come from it.
    asyncio.run(run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW, transport=recorded_transport))
    keep = all_ids(tmp_settings.output_db)[0]
    with closing(sqlite3.connect(tmp_settings.output_db)) as con:
        con.execute("insert into place_aliases values ('jh-gone000001', ?)", (keep,))
        con.commit()
        first_order = dict(con.execute("select place_id, issued_seq from id_order"))
    alt = tmp_path / "alt" / "places.db"
    assert main(["run", "--out", str(alt)], settings=tmp_settings, transport=recorded_transport) == 0
    with closing(sqlite3.connect(alt)) as con:
        assert dict(con.execute("select old_id, new_id from place_aliases")) == {"jh-gone000001": keep}
        alt_order = dict(con.execute("select place_id, issued_seq from id_order"))
    assert alt_order == first_order
    assert all_ids(alt) == all_ids(tmp_settings.output_db)

    few = tmp_path / "few" / "places.db"
    assert main(["run", "--out", str(few)], settings=tmp_settings, transport=transport_returning_few) == 1
    assert not few.exists()
    failed = sorted(tmp_settings.work_dir.glob("*/report.md"), key=lambda p: p.stat().st_mtime)[-1]
    assert "80% of previous" in failed.read_text(encoding="utf-8")


def test_cli_invalid_settings_exit_2(monkeypatch, capsys):
    import jinju_pipeline.__main__ as cli
    from jinju_pipeline.settings import Settings

    monkeypatch.setattr(cli, "get_settings", lambda: Settings(_env_file=None, daily_quota="many"))
    assert main(["report", "--run-id", "x"]) == 2
    assert "설정 오류" in capsys.readouterr().err


# ---- review fixes B: missing sources, per-source watermark, persisted reuse streak, offline rebuild ----

NOW3 = datetime(2026, 11, 18, 3, 0, tzinfo=KST)


def _state(settings) -> dict:
    return json.loads(settings.state_file.read_text(encoding="utf-8"))


def test_refresh_state_lives_outside_backend_and_frontend(tmp_settings):
    """Render deploys rootDir=backend: a weekly state commit there would redeploy the API (M1)."""
    from jinju_pipeline.settings import PIPELINE_ROOT, REPO_ROOT, Settings

    default = Settings(_env_file=None).state_file
    assert default == PIPELINE_ROOT / "state" / "refresh_state.json"
    assert not default.is_relative_to(REPO_ROOT / "backend") and not default.is_relative_to(REPO_ROOT / "frontend")
    assert not tmp_settings.state_file.is_relative_to(REPO_ROOT)  # tests never write the tracked file


def test_cli_from_raw_and_incremental_are_mutually_exclusive(tmp_settings, capsys):
    with pytest.raises(SystemExit) as ei:
        main(["run", "--from-raw", "--incremental"], settings=tmp_settings)
    assert ei.value.code == 2 and "not allowed with" in capsys.readouterr().err


def test_cli_out_writes_state_next_to_out_but_reads_canonical(tmp_settings, recorded_transport, tmp_path):
    asyncio.run(run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW, transport=recorded_transport))
    canonical = tmp_settings.state_file.read_bytes()
    alt = tmp_path / "alt" / "places.db"
    assert main(["run", "--out", str(alt)], settings=tmp_settings, transport=recorded_transport) == 0
    assert (alt.parent / "refresh_state.json").exists()
    assert tmp_settings.state_file.read_bytes() == canonical


def _blocking(host: str, recorded):
    """Recorded fixtures, except that ``host`` answers 403 (non-retryable) - e.g. a runner IP block."""
    def handler(request):
        if request.url.host == host:
            return httpx.Response(403, text="blocked")
        return recorded(request)

    return httpx.MockTransport(handler)


def _keyed(settings):
    return settings.model_copy(update={"data_go_kr_key": SecretStr("test-key")})


def test_missing_key_after_a_tourapi_build_keeps_the_previous_db(tmp_settings, recorded_transport, capsys):
    from conftest import _recorded_handler

    keyed = _keyed(tmp_settings)
    asyncio.run(run_pipeline(keyed, incremental=False, today=TODAY, now=NOW, transport=recorded_transport))
    before_db = keyed.output_db.read_bytes()
    before_report = keyed.output_report.read_bytes()
    capsys.readouterr()

    code = main(["run", "--incremental", "--today", "2026-11-11"], settings=tmp_settings,
                transport=httpx.MockTransport(_recorded_handler()))
    out = capsys.readouterr().out
    assert code == 1
    assert "tourapi.area" in out and "skipped: no key" in out
    assert keyed.output_db.read_bytes() == before_db
    assert keyed.output_report.read_bytes() == before_report


async def test_state_file_keeps_tourapi_watermark_until_tourapi_succeeds(tmp_settings, recorded_transport):
    from conftest import _recorded_handler

    keyed = _keyed(tmp_settings)
    await run_pipeline(keyed, incremental=False, today=TODAY, now=NOW, transport=recorded_transport)
    first = _state(keyed)
    assert first["synced_at"]["tourapi.area"] == NOW.isoformat(timespec="seconds")
    assert first["reused_streak"] == 0

    def tour_down(request):
        if request.url.host == "apis.data.go.kr":
            return httpx.Response(200, json={"response": {"header": {"resultCode": "10", "resultMsg": "ERR"}}})
        return _recorded_handler()(request)

    report, gate = await run_pipeline(keyed, incremental=True, today=date(2026, 11, 11), now=NOW2,
                                      transport=httpx.MockTransport(tour_down))
    assert gate.passed, gate.failures
    assert {s["source"]: s["status"] for s in report["sources"]}["tourapi.area"] == "reused_previous"
    second = _state(keyed)
    assert second["synced_at"]["tourapi.area"] == NOW.isoformat(timespec="seconds")  # not advanced
    assert second["synced_at"]["jinju_city.tourinfo"] == NOW2.isoformat(timespec="seconds")
    assert second["reused_streak"] == 1


async def test_reuse_streak_survives_an_unchanged_content_hash(tmp_settings, recorded_transport):
    """The workflow only commits places.db when content_hash changes; refresh_state.json is committed
    on every run, so two blocked runs in a row fail the gate even though the data never changed."""
    from conftest import _recorded_handler

    await run_pipeline(tmp_settings, incremental=False, today=TODAY, now=NOW, transport=recorded_transport)
    committed_db = tmp_settings.output_db.read_bytes()
    committed_report = tmp_settings.output_report.read_bytes()
    first_hash = json.loads(committed_report)["content_hash"]

    blocked = _blocking("www.jinju.go.kr", _recorded_handler())
    report, gate = await run_pipeline(tmp_settings, incremental=True, today=date(2026, 11, 11), now=NOW2,
                                      transport=blocked)
    assert gate.passed and report["reused_streak"] == 1
    assert report["content_hash"] == first_hash  # nothing new: the workflow keeps the committed db
    tmp_settings.output_db.write_bytes(committed_db)
    tmp_settings.output_report.write_bytes(committed_report)
    assert _state(tmp_settings)["reused_streak"] == 1

    report, gate = await run_pipeline(tmp_settings, incremental=True, today=date(2026, 11, 18), now=NOW3,
                                      transport=blocked)
    assert report["reused_streak"] == 2
    assert not gate.passed and any("2 runs in a row" in f for f in gate.failures)


def test_from_raw_rebuilds_offline_with_same_content(tmp_settings, recorded_transport, capsys):
    keyed = _keyed(tmp_settings)
    asyncio.run(run_pipeline(keyed, incremental=False, today=TODAY, now=NOW, transport=recorded_transport))
    before = json.loads(keyed.output_report.read_text(encoding="utf-8"))
    ids = all_ids(keyed.output_db)
    state = _state(keyed)

    requests = []

    def no_network(request):
        requests.append(request)
        raise AssertionError(f"network call in --from-raw: {request.url}")

    # no key needed, and whatever transport is injected is never used
    code = main(["run", "--from-raw", "--today", "2026-11-11"], settings=tmp_settings,
                transport=httpx.MockTransport(no_network))
    assert code == 0, capsys.readouterr()
    after = json.loads(keyed.output_report.read_text(encoding="utf-8"))
    assert requests == []
    assert after["content_hash"] == before["content_hash"] and after["run_id"] != before["run_id"]
    assert all_ids(keyed.output_db) == ids
    assert {s["source"] for s in after["sources"]} == {s["source"] for s in before["sources"] if s["records"]}
    assert all(s["calls"] == 0 and s["status"] == "ok" for s in after["sources"])
    assert after["replayed_from"] == before["run_id"]
    assert _state(keyed) == state  # an offline rebuild neither advances watermarks nor resets the streak


def test_from_raw_without_previous_db_exits_2(tmp_settings, capsys):
    assert main(["run", "--from-raw"], settings=tmp_settings) == 2
    assert "--from-raw" in capsys.readouterr().err
    assert not tmp_settings.output_db.exists()
