from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query, Request

from app.schemas.festivals import FestivalList, FestivalOut
from app.services.festival_status import STATUS_LABELS, STATUS_ORDER, festival_status, kst_today
from app.services.places_repo import PlacesRepo, get_places_repo

router = APIRouter()


@router.get("/festivals", response_model=FestivalList)
def list_festivals(
    request: Request,
    status: Literal["all", "ongoing", "upcoming", "ended"] = "all",
    today: date | None = Query(default=None, description="YYYY-MM-DD; honoured only in demo mode"),
    repo: PlacesRepo = Depends(get_places_repo),
):
    use_override = request.app.state.settings.demo_date_override_enabled and today is not None
    day = today if use_override else kst_today()
    items = []
    for r in repo.festival_rows():
        st = festival_status(r["start_date"], r["end_date"], r["date_undecided"], day)
        if status != "all" and st != status:
            continue
        items.append(FestivalOut(**{k: v for k, v in r.items() if k != "date_undecided"},
                                 status=st, status_label=STATUS_LABELS[st]))
    items.sort(key=lambda i: (STATUS_ORDER[i.status], i.start_date or date.max, i.title))
    return FestivalList(today=day.isoformat(), items=items)
