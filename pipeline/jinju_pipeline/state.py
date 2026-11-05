"""Refresh state committed with the data (``pipeline/state/refresh_state.json``, ``Settings.state_file``).

The scheduled workflow commits places.db only when its content_hash changes, but commits this small file
on every published run, so state that must survive a run with unchanged data lives here:

- ``reused_streak``: consecutive published runs that reused previous data for some source (gate: 2 fails).
- ``synced_at``: per source, the start time of its last successful (``ok``) collection. TourAPI's
  incremental sync uses its own entry as the watermark.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jinju_pipeline.models import SourceResult
from jinju_pipeline.raw_store import KST

log = logging.getLogger(__name__)

STATE_FILE = "refresh_state.json"  # file name; `run --out` writes it next to the output places.db


@dataclass
class RefreshState:
    reused_streak: int = 0
    synced_at: dict[str, datetime] = field(default_factory=dict)


def read_state(path: Path) -> RefreshState | None:
    """None when the file is missing or unreadable (callers fall back to the snapshot's meta)."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        streak = int(data.get("reused_streak") or 0)
        raw_synced = data.get("synced_at") or {}
    except (OSError, ValueError, TypeError, AttributeError) as e:
        log.warning("ignoring unreadable %s: %s", path, e)
        return None
    synced: dict[str, datetime] = {}
    for source, value in raw_synced.items():
        try:
            ts = datetime.fromisoformat(str(value))
        except ValueError:
            log.warning("ignoring bad synced_at for %s in %s: %r", source, path, value)
            continue
        synced[source] = ts if ts.tzinfo else ts.replace(tzinfo=KST)
    return RefreshState(reused_streak=streak, synced_at=synced)


def write_state(path: Path, state: RefreshState) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "reused_streak": state.reused_streak,
        "synced_at": {s: t.astimezone(KST).isoformat(timespec="seconds") for s, t in sorted(state.synced_at.items())},
    }
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def advance_synced_at(prior: dict[str, datetime], results: list[SourceResult], now: datetime) -> dict[str, datetime]:
    """Move the watermark of every source that finished ``ok``; reused/failed/skipped keep their old one."""
    synced = dict(prior)
    for r in results:
        if r.status == "ok":
            synced[r.source] = now
    return synced
