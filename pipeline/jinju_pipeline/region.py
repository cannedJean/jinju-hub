"""Region definition loaded from config/region.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class Region(BaseModel):
    id: str
    name: str
    center_lat: float
    center_lng: float
    min_lat: float
    max_lat: float
    min_lng: float
    max_lng: float
    margin: float
    regn_cd: str
    signgu_cd: str
    address_keyword: str

    def contains(self, lat: float, lng: float) -> bool:
        """True if (lat, lng) lies within the bbox expanded by `margin` degrees."""
        m = self.margin
        return (
            self.min_lat - m <= lat <= self.max_lat + m
            and self.min_lng - m <= lng <= self.max_lng + m
        )


def load_region(path: Path) -> Region:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Region(
        id=data["id"],
        name=data["name"],
        center_lat=data["center"]["lat"],
        center_lng=data["center"]["lng"],
        min_lat=data["bbox"]["min_lat"],
        max_lat=data["bbox"]["max_lat"],
        min_lng=data["bbox"]["min_lng"],
        max_lng=data["bbox"]["max_lng"],
        margin=data["bbox_margin_deg"],
        regn_cd=str(data["ldong"]["regn_cd"]),
        signgu_cd=str(data["ldong"]["signgu_cd"]),
        address_keyword=data["address_keyword"],
    )
