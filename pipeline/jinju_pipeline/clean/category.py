"""Source payload -> unified category."""
from __future__ import annotations

from jinju_pipeline.models import Category

CITY_CATEGORY: dict[str, Category] = {
    "jinju_city.tourinfo": "sight",
    "jinju_city.restaurant": "food",
    "jinju_city.festival": "festival",
    "jinju_city.heritage": "culture",
    "jinju_city.lodging": "stay",
}
CULTURE_WORDS = ("문화", "박물관", "전시")

CONTENT_TYPE_CATEGORY: dict[str, Category] = {
    "12": "sight", "14": "culture", "15": "festival", "25": "course",
    "28": "leisure", "32": "stay", "38": "shopping", "39": "food",
}


def map_category(source: str, payload: dict) -> Category | None:
    if source.startswith("tourapi."):
        item = payload.get("list") or payload  # festival records carry the list item itself
        return CONTENT_TYPE_CATEGORY.get(str(item.get("contenttypeid", "")).strip())
    cat = CITY_CATEGORY.get(source)
    if cat == "sight":
        label = str(payload.get("category") or "")
        if any(w in label for w in CULTURE_WORDS):
            return "culture"
    return cat
