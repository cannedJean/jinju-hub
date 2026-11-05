"""Golden eval: chat retrieval (_retrieve) against the committed real places.db.

Every built-in suggestion chip, the spec §7 example and the review regressions run on the real data with
today=2026-11-05. The test prints a table of every query and fails if any row fails its criterion.
Run with `-s` to see the table when everything passes.
"""
import math
import re
import sqlite3
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from app.models import board  # noqa: F401
from app.models.base import Base
from app.services import chat_service
from app.services.database import build_engine
from app.services.places_repo import PlacesRepo

REAL_DB = Path(__file__).resolve().parents[1] / "app" / "data" / "places.db"
TODAY = date(2026, 11, 5)
pytestmark = pytest.mark.skipif(not REAL_DB.is_file(), reason="real places.db not present")

CASTLE = "jh-14496674c7"  # 진주성 (sight)
CASTLE_SIGHTS = {CASTLE, "jh-515e2bff18", "jh-ecd8569ad9"}  # 진주성, 진주 촉석루, 제1경 진주성 촉석루
LANTERN_FESTIVAL = "jh-0994890048"  # 진주남강유등축제 (2026-10-03..18, ended on TODAY)
GAECHEON = "jh-e696901ecd"  # 개천예술제
NATIONAL_MUSEUM = "jh-4b637200e6"  # 국립진주박물관
INDOOR_TITLE = re.compile(r"박물관|전시|미술|과학|기념관|체험관|문화관|관$")
NOT_INDOOR_TITLE = re.compile(r"묘|고분|비석|비명|신도비|송덕비|공덕비|기념비|봉수대|화석산지|비$|비\(")
CAFE_TITLE_MENU = re.compile(r"카페|커피|cafe|coffee|라떼|아메리카노|에스프레소", re.I)
NIGHT = re.compile(r"남강|야경|야간|조명")


@pytest.fixture(scope="module")
def env():
    repo = PlacesRepo(REAL_DB)
    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    con = sqlite3.connect(REAL_DB.resolve().as_uri() + "?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    rows = {r["id"]: dict(r) for r in con.execute("SELECT * FROM places")}
    con.close()
    yield repo, session, rows
    session.close()
    engine.dispose()
    repo.close()


def _dist(a, b):
    if a["lat"] is None or b["lat"] is None:
        return math.inf
    dy = (a["lat"] - b["lat"]) * 111_320
    dx = (a["lng"] - b["lng"]) * 111_320 * math.cos(math.radians(a["lat"]))
    return math.hypot(dx, dy)


def _text(row, *fields):
    return " ".join((row.get(f) or "") for f in fields).lower()


def _matches(row, word):
    return word in _text(row, "title", "menu", "overview")


def _is_cafe(row):
    return row["category"] == "food" and (
        bool(CAFE_TITLE_MENU.search(_text(row, "title", "menu"))) or "카페" in _text(row, "overview"))


def _venue_ids(rows):
    out = set()
    for r in rows.values():
        if r["category"] == "festival":
            import json
            out.update(json.loads(r["venue_place_ids"] or "[]"))
        elif "festival_venue" in (r["tags"] or ""):
            out.add(r["id"])
    return out


# ---- criteria: (ret, places, rows) -> (ok, note) ----

def _all_match(*words, category=None, nonempty=True):
    def check(ret, places, rows):
        if nonempty and not places:
            return False, "no places"
        bad = [p["title"] for p in places
               if not any(_matches(p, w) for w in words) or (category and p["category"] != category)]
        return not bad, f"off-target: {bad}" if bad else ""
    return check


def _naengmyeon_near_castle(ret, places, rows):
    ok, note = _all_match("냉면", category="food")(ret, places, rows)
    if not ok:
        return ok, note
    castle = rows[CASTLE]
    strong = [r for r in rows.values() if r["category"] == "food" and "냉면" in _text(r, "title", "menu")]
    nearest = min(strong, key=lambda r: _dist(castle, r))
    if places[0]["id"] != nearest["id"]:
        return False, f"first={places[0]['title']} nearest={nearest['title']}"
    if not any("하연옥" in p["title"] for p in places[:6]):
        return False, "하연옥 not in top 6"
    return True, ""


def _rainy_indoor(ret, places, rows):
    good = [p for p in places if p["category"] in ("sight", "culture") and INDOOR_TITLE.search(p["title"])]
    bad = [p["title"] for p in places if NOT_INDOOR_TITLE.search(p["title"])]
    if bad:
        return False, f"not indoor: {bad}"
    return len(good) >= 4, f"{len(good)}/6 indoor-titled (judged by title: culture is all indoor-tagged)"


def _festival_now(ret, places, rows):
    fest = [i for i in ret.items if i.group == "festival"]
    ctx = ret.context()
    if not fest and "축제 없음" not in ctx:
        return False, "festival group empty without a note"
    venues = _venue_ids(rows)
    bad = [p["title"] for p in places if p["id"] not in venues]
    return not bad, f"unrelated places: {bad}" if bad else ""


def _night_view(ret, places, rows):
    hits = [p for p in places if NIGHT.search(_text(p, "title", "overview"))]
    bad = [p["title"] for p in places
           if (p["category"] == "food" or "시장" in p["title"]) and not re.search("야경", _text(p, "title", "overview"))]
    if bad:
        return False, f"restaurants/markets: {bad}"
    return len(places) >= 3 and len(hits) >= 3, f"{len(hits)}/{len(places)} mention 남강/야경"


def _has_ended_lantern_festival(ret, places, rows):
    line = next((i.line for i in ret.items if i.id == LANTERN_FESTIVAL), None)
    if line is None:
        return False, "진주남강유등축제 not in context"
    return "올해 종료" in line, line[:80]


def _includes(*ids):
    def check(ret, places, rows):
        got = {p["id"] for p in places} | {i.id for i in ret.items}
        return bool(got & set(ids)), "" if got & set(ids) else f"missing any of {sorted(ids)}"
    return check


def _landmark_not_branches(*ids):
    # A shop branch named after the landmark ("LG전자 베스트샵 진주성점") is not about the landmark.
    def check(ret, places, rows):
        ok, note = _includes(*ids)(ret, places, rows)
        branches = [p["title"] for p in places if p["category"] == "shopping"]
        return ok and not branches, note or (f"branches: {branches}" if branches else "")
    return check


def _all_cafes(ret, places, rows):
    bad = [p["title"] for p in places if not _is_cafe(p)]
    return bool(places) and not bad, f"not cafés: {bad}" if bad else ("no places" if not places else "")


def _all_category(cat):
    def check(ret, places, rows):
        bad = [p["title"] for p in places if p["category"] != cat]
        return bool(places) and not bad, f"wrong category: {bad}" if bad else ""
    return check


def _nonempty(ret, places, rows):
    return bool(places), ""


JINYANGHO = "jh-94e71d068d"  # 진양호 (lake centre; a second row titled 진양호, jh-0d5956629a, is a 4.2 km outlier)
LABEL = re.compile(r"약 [\d.,]+ ?(m|km)")


def _place_lines(ret):
    return {i.id: i.line for i in ret.items if i.group == "place"}


def _near_jinyangho_gukbap(ret, places, rows):
    lines = _place_lines(ret)
    lake = rows[JINYANGHO]
    hayeon = [p for p in places if "하연옥" in p["title"]]
    if not hayeon:
        return False, "하연옥 missing"
    far = [p["title"] for p in places if _dist(lake, p) > 5000]
    bad = [p["title"] for p in hayeon if not LABEL.search(lines[p["id"]])]
    return not far and not bad, f"far={far} unlabelled={bad}"


def _near_jinyangho_food(ret, places, rows):
    lines = _place_lines(ret)
    lake = rows[JINYANGHO]
    food = [p for p in places if p["category"] == "food"]
    far = [p["title"] for p in places if _dist(lake, p) > 5000]
    unlabelled = [p["title"] for p in places if not LABEL.search(lines[p["id"]])]
    ok = len(food) >= 4 and len(food) == len(places) and not far and not unlabelled
    return ok, f"{len(food)} food, far={far} unlabelled={unlabelled}"


def _lantern_festival_food(ret, places, rows):
    import json
    line = next((i.line for i in ret.items if i.id == LANTERN_FESTIVAL), None)
    if line is None or "종료" not in line and "진행" not in line and "예정" not in line:
        return False, "진주남강유등축제 row with status missing"
    venues = [rows[v] for v in json.loads(rows[LANTERN_FESTIVAL]["venue_place_ids"])]
    near = [p for p in places if p["category"] == "food" and min(_dist(v, p) for v in venues) <= 2000]
    return len(near) >= 3, f"{len(near)} food places within 2 km of a venue"


def _min_category(cat, n):
    def check(ret, places, rows):
        got = sum(p["category"] == cat for p in places)
        return got >= n, f"{got} {cat}"
    return check


def _chokseokru_night_photo(ret, places, rows):
    bad = [p["title"] for p in places if "묘" in p["title"] or "진사" in p["title"]]
    night = [p for p in places if "night_view" in (p["tags"] or "") or re.search("야경|야간|조명", _text(p, "title", "overview"))]
    return not bad and len(night) >= 2, f"bad={bad} night={len(night)}"


KID = re.compile("어린이|체험|박물관|공원|놀이")


def _with_kids(ret, places, rows):
    top_bad = [p["title"] for p in places[:3] if p["category"] in ("food", "shopping")]
    kid = [p for p in places if KID.search(_text(p, "title", "overview"))]
    return not top_bad and len(kid) >= 2, f"top3 food/shopping={top_bad} kid={len(kid)}"


def _not_bibimbap(ret, places, rows):
    bib = [p["title"] for p in places if "비빔밥" in _text(p, "title", "menu")]
    ok = bool(places) and len(bib) <= 1 and all(p["category"] == "food" for p in places)
    return ok, f"비빔밥={bib}"


def _no_corp_prefix_top3(ret, places, rows):
    bad = [p["title"] for p in places[:3] if p["title"].startswith(("(유)", "(주)"))]
    return bool(places) and not bad, f"prefixed={bad}"


def _namgang_walk(ret, places, rows):
    def walkish(p):
        t = _text(p, "title", "overview")
        riverside = "남강" in t or "남강" in (p["addr"] or "") or re.search("강변|둔치", t)
        return bool(re.search("산책|길|공원|둘레", t)) and bool(riverside)
    good = [p for p in places if walkish(p)]
    hotels = [p["title"] for p in places[:3] if p["category"] == "stay" or "호텔" in p["title"]]
    return len(good) >= 3 and not hotels, f"{len(good)}/{len(places)} walk+남강, top3 hotels={hotels}"


def _castle_food_close(ret, places, rows):
    castle = rows[CASTLE]
    top = places[:3]
    far = [(p["title"], round(_dist(castle, p))) for p in top if _dist(castle, p) > 1000]
    return len(top) == 3 and not far, f"far={far}"


def _no_crash(ret, places, rows):
    return True, f"{len(places)} places"


CASES = [
    # built-in suggestion chips (frontend/src/data/chatSuggestions.js)
    ("chip", "진주성 근처 냉면집 알려줘", _naengmyeon_near_castle),
    ("chip", "비 오는 날 실내에서 갈 만한 곳은?", _rainy_indoor),
    ("chip", "지금 진행 중인 축제 있어?", _festival_now),
    ("chip", "남강 야경 보기 좋은 곳 추천해줘", _night_view),
    # spec §7 example
    ("spec", "유등축제 끝났는데 지금 볼 만한 축제 있어?", _has_ended_lantern_festival),
    # regressions
    ("reg", "진주성 근처 유명한 냉면집", _all_match("냉면", category="food")),
    ("reg", "촉석루 근처 카페", _all_cafes),
    ("reg", "진주성 근처 냉면이나 국밥", _all_match("냉면", "국밥", category="food")),
    ("reg", "진주 비빔밥 맛집 알려줘", _all_match("비빔밥", category="food")),
    ("reg", "우리집 근처 카페", _all_cafes),
    ("reg", "숙소 추천해줘", _all_category("stay")),
    ("reg", "가족 여행 추천", _nonempty),
    # landmark questions keep the landmark (C1)
    ("C1", "진주성 야경", _includes(*CASTLE_SIGHTS)),
    ("C1", "진주성 가볼만해?", _landmark_not_branches(*CASTLE_SIGHTS)),
    ("C1", "국립진주박물관 휴관일 알려줘", _includes(NATIONAL_MUSEUM)),
    # other review findings
    ("C2", "칼국수 맛집 추천해줘", _all_match("칼국수", category="food")),
    ("C16", "유등축제 언제야?", _includes(LANTERN_FESTIVAL)),
    ("C16", "개천예술제 언제 해?", _includes(GAECHEON)),
    ("C17", "비 오는 날 냉면 맛집", _all_match("냉면", category="food")),
    ("C17", "비 오는 날 숙소 추천", _all_category("stay")),
    ("M0", "진양호 근처 국밥", _near_jinyangho_gukbap),
    # fix round 1 (controller-defined rows)
    ("R1", "진양호 근처 맛집", _near_jinyangho_food),
    ("R1", "유등축제 근처 맛집", _lantern_festival_food),
    ("R1", "축제 기간 숙소 추천", _min_category("stay", 3)),
    ("R1", "촉석루 야경 사진 찍기 좋은 곳", _chokseokru_night_photo),
    ("R1", "아이랑 갈만한 곳", _with_kids),
    ("R1", "비빔밥 말고 다른 진주 음식", _not_bibimbap),
    ("R1", "숙소 근처 맛집", _no_corp_prefix_top3),
    ("R1", "남강 산책로", _namgang_walk),
    ("R1", "진주성 맛집", _castle_food_close),
    ("C5", "진주 " * 200 + "냉면 국밥 비빔밥 카페 숙소 축제 야경 박물관", _no_crash),
]


def test_golden_retrieval_on_real_db(env):
    repo, session, rows = env
    table, failures = [], []
    for kind, msg, check in CASES:
        try:
            ret = chat_service._retrieve(msg, repo, session, TODAY)
            places = [rows[i.id] for i in ret.items if i.group == "place"]
            ok, note = check(ret, places, rows)
            titles = ", ".join(p["title"][:14] for p in places) or "-"
            fest = ", ".join(i.title[:12] for i in ret.items if i.group == "festival")
            if fest:
                titles += f" || 축제: {fest}"
        except Exception as exc:  # noqa: BLE001 - a crash is a failed row, keep evaluating the rest
            ok, note, titles = False, f"{type(exc).__name__}: {exc}"[:120], "-"
        table.append(f"{'PASS' if ok else 'FAIL'} [{kind:4}] {msg[:34]:<34} | {titles[:150]}"
                     + (f"\n       -> {note}" if note else ""))
        if not ok:
            failures.append(msg[:34])
    report = "\n".join(table)
    print("\n" + report)
    assert not failures, f"{len(failures)} golden queries failed:\n{report}"
