"""CLI: ``python -m jinju_pipeline run [--incremental | --from-raw]|verify-codes|report``.

Exit codes: 0 gate passed, 1 gate failed, 2 configuration error (ConfigError, locked places.db,
missing report).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Mapping

import httpx
from pydantic import ValidationError

from jinju_pipeline.http import ConfigError, make_client
from jinju_pipeline.raw_store import KST
from jinju_pipeline.region import load_region
from jinju_pipeline.runner import run_pipeline
from jinju_pipeline.settings import Settings, get_settings
from jinju_pipeline.sources.tourapi import verify_codes
from jinju_pipeline.state import STATE_FILE

RUNNER_RUN_QUOTA = 300


def settings_for_env(settings: Settings, env: Mapping[str, str]) -> Settings:
    """On a GitHub Actions runner the per-run quota is capped (the key is shared with local runs)."""
    if env.get("GITHUB_ACTIONS") == "true" and settings.run_quota is None:
        return settings.model_copy(update={"run_quota": RUNNER_RUN_QUOTA})
    return settings


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m jinju_pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="collect -> clean -> merge -> load -> report")
    mode = run.add_mutually_exclusive_group()
    mode.add_argument("--incremental", action="store_true")
    mode.add_argument("--from-raw", action="store_true",
                      help="no collection/network: replay the raw records stored in the previous places.db")
    run.add_argument("--today", type=date.fromisoformat, help="YYYY-MM-DD (default: today, KST)")
    run.add_argument("--out", type=Path, help="places.db path (report.json, refresh_state.json next to it)")
    run.add_argument("--until", choices=("clean", "merge"))
    sub.add_parser("verify-codes", help="check lDong codes and per-type counts via TourAPI")
    rep = sub.add_parser("report", help="print the report.md of a past run")
    rep.add_argument("--run-id", required=True)
    return ap


def configure_logging() -> None:
    """INFO logging for the CLI. httpx/httpcore log full request URLs (TourAPI's carry serviceKey) at INFO."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _cmd_run(args, settings: Settings, transport) -> int:
    if args.out is not None:
        settings = settings.model_copy(update={
            "previous_db": settings.previous_db or settings.output_db,  # still the canonical snapshot
            "output_db": args.out,
            "output_report": args.out.parent / "report.json",
            "previous_state_file": settings.previous_state_file or settings.state_file,
            "state_file": args.out.parent / STATE_FILE,
        })
    now = datetime.now(KST)
    today = args.today or now.date()
    report, gate = asyncio.run(run_pipeline(
        settings, incremental=args.incremental, today=today, now=now, transport=transport, until=args.until,
        from_raw=args.from_raw,
    ))
    if args.until:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    print(f"run_id={report['run_id']} final_count={report['final_count']} "
          f"gate={'PASS' if gate.passed else 'FAIL'}")
    for f in gate.failures:
        print(f"  FAIL: {f}")
    for w in gate.warnings:
        print(f"  WARN: {w}")
    print(f"  report: {Path(settings.work_dir) / report['run_id'] / 'report.md'}")
    return 0 if gate.passed else 1


def _cmd_verify_codes(settings: Settings, transport) -> int:
    if settings.data_go_kr_key is None or not settings.data_go_kr_key.get_secret_value():
        _err("설정 오류: DATA_GO_KR_KEY가 설정되지 않았습니다. data.go.kr에서 TourAPI(KorService2) 키를 "
             "발급받아 pipeline/.env 또는 환경변수 DATA_GO_KR_KEY로 지정한 뒤 다시 실행하세요.")
        return 2

    async def go() -> dict:
        async with make_client(transport=transport) as client:
            return await verify_codes(client, settings, load_region(settings.region_path))

    result = asyncio.run(go())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["signgu_ok"] else 1


def _cmd_report(args, settings: Settings) -> int:
    path = Path(settings.work_dir) / args.run_id / "report.md"
    if not path.exists():
        _err(f"report not found: {path}")
        return 2
    print(path.read_text(encoding="utf-8"))
    return 0


def main(argv: list[str] | None = None, *, settings: Settings | None = None,
         transport: httpx.AsyncBaseTransport | None = None) -> int:
    """``settings``/``transport`` are injection points for tests (default: env settings, real network)."""
    args = _parser().parse_args(argv)
    try:
        settings = settings_for_env(settings or get_settings(), os.environ)
    except ValidationError as e:  # bad env/.env values
        _err(f"설정 오류: {e}")
        return 2
    try:
        if args.cmd == "run":
            return _cmd_run(args, settings, transport)
        if args.cmd == "verify-codes":
            return _cmd_verify_codes(settings, transport)
        return _cmd_report(args, settings)
    except ConfigError as e:
        _err(f"설정 오류: {e}")
        return 2
    except sqlite3.OperationalError as e:
        if "locked" not in str(e):
            raise
        _err(f"설정 오류: places.db가 잠겨 있습니다 ({e}). 백엔드를 중지하거나 `--out`을 사용하세요")
        return 2
    except SystemExit as e:  # write_places_db exits 2 when places.db cannot be replaced
        return e.code if isinstance(e.code, int) else 2


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):  # Windows consoles (cp949) cannot encode every character
        stream.reconfigure(errors="replace")
    configure_logging()
    sys.exit(main())
