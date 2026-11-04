from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

FestivalStatus = Literal["ongoing", "upcoming", "ended", "stale", "undecided"]

STATUS_LABELS: dict[str, str] = {
    "ongoing": "진행 중",
    "upcoming": "예정",
    "ended": "올해 종료 · 내년 일정 미정",
    "stale": "작년 일정 · 올해 미정",
    "undecided": "일정 미정",
}
STATUS_ORDER = {"ongoing": 0, "upcoming": 1, "ended": 2, "stale": 3, "undecided": 4}
KST = ZoneInfo("Asia/Seoul")


def kst_today() -> date:
    return datetime.now(KST).date()


def festival_status(start: date | None, end: date | None, undecided: bool, today: date) -> FestivalStatus:
    if undecided or start is None:
        return "undecided"
    end = end or start
    if start.year < today.year and end < today:
        return "stale"
    if start <= today <= end:
        return "ongoing"
    if today < start:
        return "upcoming"
    return "ended"
