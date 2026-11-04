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
    assert n == 12 + 3


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
