"""Region config (config/region.yaml copy) loader."""
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.config import get_settings


def load_region(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else get_settings().region_path
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache()
def get_region() -> dict[str, Any]:
    return load_region()
