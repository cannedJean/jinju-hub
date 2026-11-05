"""Raw snapshot store: writes unmodified API page bodies plus a per-source manifest."""

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

KST = timezone(timedelta(hours=9))

_MASKED_KEYS = ("serviceKey", "authKey")
_MASK = "***"
_SECRET_PATTERNS = (
    re.compile(r"(?i)(serviceKey\s*=\s*)[^&\s\"']+"),
    re.compile(r"(?i)(authKey\s*=\s*)[^&\s\"']+"),
    re.compile(r"(://[^:/\s@]+:)[^@\s]+(?=@)"),  # DSN password: scheme://user:***@host
)


def new_run_id(now: datetime) -> str:
    return now.astimezone(KST).strftime("%Y%m%dT%H%M%S%z")


def mask_params(params: dict) -> dict:
    masked = dict(params)
    for key in _MASKED_KEYS:
        if key in masked:
            masked[key] = _MASK
    return masked


def scrub_secrets(text: str) -> str:
    """Mask API keys and DSN passwords in free text (upstream error messages often embed the request URL)."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(rf"\1{_MASK}", text)
    return text


def _records_count(body: Any) -> int | None:
    """Count items in a list under a common key; None when the body has no such list."""
    if isinstance(body, dict):
        results = body.get("results")
        if isinstance(results, list):
            return len(results)
        items = body.get("response", {}).get("body", {}).get("items", {})
        if isinstance(items, dict) and isinstance(items.get("item"), list):
            return len(items["item"])
    return None


class RawStore:
    def __init__(self, root: Path, run_id: str):
        self.root = Path(root)
        self.run_id = run_id
        self._pages: dict[str, list[dict]] = {}

    def write_page(self, source: str, page: int, body: dict | str, request: dict) -> Path:
        directory = self.root / source / self.run_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"page-{page:03d}.json"

        if isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        path.write_bytes(data)

        self._pages.setdefault(source, []).append(
            {
                "page": page,
                "file": path.name,
                "sha256": hashlib.sha256(data).hexdigest(),
                "request": mask_params(request),
                "records": _records_count(body),
            }
        )
        return path

    def finalize(self) -> dict[str, dict]:
        manifests: dict[str, dict] = {}
        written_at = datetime.now(KST).isoformat()
        for source, pages in self._pages.items():
            counts = [p["records"] for p in pages]
            records_hint = sum(counts) if all(c is not None for c in counts) else None
            manifest = {
                "run_id": self.run_id,
                "source": source,
                "pages": [
                    {"page": p["page"], "file": p["file"], "sha256": p["sha256"]}
                    for p in pages
                ],
                "records_hint": records_hint,
                "requests": [p["request"] for p in pages],
                "written_at": written_at,
            }
            path = self.root / source / self.run_id / "manifest.json"
            path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            manifests[source] = manifest
        return manifests
