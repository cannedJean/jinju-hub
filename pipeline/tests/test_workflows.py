"""GitHub workflow contracts: least-privilege tokens and the data-refresh commit step (review fixes B)."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"


def _load(name: str) -> dict:
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(p.name for p in WORKFLOWS.glob("*.yml")))
def test_every_workflow_declares_permissions(name):
    assert "permissions" in _load(name), f"{name} must declare a least-privilege permissions block"


def test_reachability_token_is_read_only():
    perms = _load("reachability.yml")["permissions"]
    assert perms in ({}, {"contents": "read"})


# ---- data-refresh "Commit changed data": run the real step script against a scratch git repo ----

DATA = "backend/app/data"


def _commit_script() -> str:
    steps = _load("data-refresh.yml")["jobs"]["refresh"]["steps"]
    script = next(s["run"] for s in steps if s.get("name") == "Commit changed data")
    return script.replace("${{ github.run_id }}", "4242")


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def _bash() -> str | None:
    if os.name == "nt":
        git = shutil.which("git")
        if git:
            candidate = Path(git).resolve().parents[1] / "bin" / "bash.exe"
            if candidate.exists():
                return str(candidate)
    return shutil.which("bash")


@pytest.fixture
def repo(tmp_path):
    if not shutil.which("git") or not _bash():
        pytest.skip("git and bash are needed to run the workflow step")
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(work)], check=True, capture_output=True)
    _git(work, "config", "user.name", "t")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "checkout", "-b", "main")
    (work / DATA).mkdir(parents=True)
    (work / DATA / "places.db").write_bytes(b"db-v1")
    (work / DATA / "report.json").write_text('{"content_hash": "h1"}', encoding="utf-8")
    (work / DATA / "refresh_state.json").write_text('{"reused_streak": 0}', encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-m", "init")
    _git(work, "push", "origin", "main")
    return work


def _run_step(work: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "OLD_HASH": "h1", "REF_NAME": "main"}
    return subprocess.run([_bash(), "-e", "-c", _commit_script()], cwd=work, env=env,
                          capture_output=True, text=True)


def _remote_files(work: Path) -> dict[str, str]:
    _git(work, "fetch", "origin")
    return {name: _git(work, "show", f"origin/main:{DATA}/{name}")
            for name in ("places.db", "report.json", "refresh_state.json")}


def test_unchanged_hash_still_commits_refresh_state(repo):
    (repo / DATA / "places.db").write_bytes(b"db-v1-new-meta")  # same content, new meta/timestamps
    (repo / DATA / "report.json").write_text('{"content_hash": "h1", "run_id": "r2"}', encoding="utf-8")
    (repo / DATA / "refresh_state.json").write_text('{"reused_streak": 1}', encoding="utf-8")
    res = _run_step(repo)
    assert res.returncode == 0, res.stdout + res.stderr
    files = _remote_files(repo)
    assert files["refresh_state.json"] == '{"reused_streak": 1}'
    assert files["places.db"] == "db-v1" and files["report.json"] == '{"content_hash": "h1"}'
    assert _git(repo, "status", "--porcelain") == ""


def test_nothing_changed_makes_no_commit(repo):
    head = _git(repo, "rev-parse", "HEAD")
    (repo / DATA / "places.db").write_bytes(b"db-v1-new-meta")
    res = _run_step(repo)
    assert res.returncode == 0, res.stdout + res.stderr
    assert _git(repo, "rev-parse", "origin/main") == head


def test_changed_hash_commits_db_report_and_state(repo):
    (repo / DATA / "places.db").write_bytes(b"db-v2")
    (repo / DATA / "report.json").write_text('{"content_hash": "h2"}', encoding="utf-8")
    (repo / DATA / "refresh_state.json").write_text('{"reused_streak": 0, "x": 1}', encoding="utf-8")
    res = _run_step(repo)
    assert res.returncode == 0, res.stdout + res.stderr
    files = _remote_files(repo)
    assert files == {"places.db": "db-v2", "report.json": '{"content_hash": "h2"}',
                     "refresh_state.json": '{"reused_streak": 0, "x": 1}'}


def test_refresh_step_does_not_touch_secrets_handling():
    steps = _load("data-refresh.yml")["jobs"]["refresh"]["steps"]
    run = next(s for s in steps if s.get("name") == "Run incremental pipeline")
    assert run["env"] == {"DATA_GO_KR_KEY": "${{ secrets.DATA_GO_KR_KEY }}"}
    assert re.search(r"jinju_pipeline run --incremental", run["run"])
