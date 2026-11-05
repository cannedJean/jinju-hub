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


def _in_top(n, *ids):
    # an info question about a place ("진주성 저녁 운영시간") must keep that place near the top of the context
    def check(ret, places, rows):
        top = [p["id"] for p in places[:n]]
        ok = bool(set(top) & set(ids))
        return ok, "" if ok else f"top {n}: {[p['title'] for p in places[:n]]}"
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


CAFE_ANY = re.compile(r"카페|커피|cafe|coffee", re.I)


def _curated(p):
    return p["jinju8_rank"] is not None or bool(p["is_collection"])


def _labelled_food_near(ref_id, max_m, n, word_re=None):
    def check(ret, places, rows):
        lines = _place_lines(ret)
        ref = rows[ref_id]
        good = [p for p in places if p["category"] == "food"
                and (word_re is None or word_re.search(_text(p, "title", "menu", "overview")))
                and _dist(ref, p) <= max_m and LABEL.search(lines[p["id"]])]
        return len(good) >= n, f"{len(good)} food within {max_m} m, labelled"
    return check


def _gaecheon_cafe(ret, places, rows):
    if GAECHEON not in {i.id for i in ret.items}:
        return False, "개천예술제 row missing"
    return _labelled_food_near(GAECHEON, 5000, 3, CAFE_ANY)(ret, places, rows)


def _not_festival_sights(ret, places, rows):
    sights = [p for p in places if p["category"] in ("sight", "culture")]
    fest = [p["title"] for p in places if p["category"] == "festival"]
    return len(sights) >= 4 and not fest, f"{len(sights)} sight/culture, festival places={fest}"


def _night_photo(ret, places, rows):
    night = [p for p in places if "night_view" in (p["tags"] or "")
             or re.search("야경|야간|조명", _text(p, "title", "overview"))]
    return len(night) >= 3, f"{len(night)} night places"


def _museum_lunch(ret, places, rows):
    ok, note = _labelled_food_near(NATIONAL_MUSEUM, 2000, 3)(ret, places, rows)
    bad = [p["title"] for p in places if p["category"] in ("sight", "culture")]
    return ok and not bad, f"{note}; sight/culture={bad}"


def _castle_sights_near(ret, places, rows):
    castle = rows[CASTLE]
    fest = [p["title"] for p in places[:4] if p["category"] == "festival"]
    near = [p for p in places[:6] if p["category"] in ("sight", "culture") and _dist(castle, p) <= 1000]
    return not fest and len(near) >= 3, f"festival in top4={fest}, {len(near)} sights within 1 km"


def _first_visit(ret, places, rows):
    cur = [p for p in places if _curated(p)]
    return len(cur) >= 3, f"{len(cur)}/{len(places)} curated"


def _no_digit_titles_top3(ret, places, rows):
    bad = [p["title"] for p in places[:3] if p["title"][:1].isdigit() and not _curated(p)]
    return bool(places) and not bad, f"digit titles={bad}"


NIGHT_TEXT = re.compile("야경|야간|조명")


def _is_night(p):
    return "night_view" in (p["tags"] or "") or bool(NIGHT_TEXT.search(_text(p, "title", "overview")))


def _night_places(n, festival_id=None):
    def check(ret, places, rows):
        night = [p for p in places if _is_night(p)]
        if festival_id and festival_id not in {i.id for i in ret.items}:
            return False, f"festival row {festival_id} missing; {len(night)} night"
        return len(night) >= n, f"{len(night)} night places"
    return check


def _no_word_in_title_menu(word, category):
    def check(ret, places, rows):
        bad = [p["title"] for p in places if word in _text(p, "title", "menu")]
        wrong = [p["title"] for p in places if p["category"] != category]
        return bool(places) and not bad and not wrong, f"{word}={bad} not {category}={wrong}"
    return check


def _mention_count(pattern, n):
    rx = re.compile(pattern)

    def check(ret, places, rows):
        got = [p for p in places if rx.search(_text(p, "title", "overview"))]
        return len(got) >= n, f"{len(got)} mention {pattern}"
    return check


def _night_stay(ret, places, rows):
    wrong = [p["title"] for p in places if p["category"] != "stay"]
    top = [p for p in places[:3] if re.search("야경|전망|뷰|남강", _text(p, "title", "overview"))]
    return bool(places) and not wrong and len(top) >= 1, f"not stay={wrong}, top3 with view={len(top)}"


def _no_food(ret, places, rows):
    bad = [p["title"] for p in places if p["category"] == "food"]
    return not bad, f"food={bad}"


def _castle_cafes(ret, places, rows):
    castle = rows[CASTLE]
    good = [p for p in places if p["category"] == "food" and CAFE_ANY.search(_text(p, "title", "menu", "overview"))
            and _dist(castle, p) <= 2000]
    return len(good) >= 3, f"{len(good)} cafés within 2 km"


def _typo_castle(ret, places, rows):
    ctx = ret.context()
    if "진주썽" in ctx and "찾지 못" in ctx:
        return True, "noted"
    castle = rows[CASTLE]
    far = [p["title"] for p in places if _dist(castle, p) > 2000]
    return bool(places) and not far, f"no note; far={far}"


def _castle_and_museum(ret, places, rows):
    ids = {p["id"] for p in places}
    bad = [p["title"] for p in places if "묘" in p["title"] or "고문서" in p["title"]]
    ok = NATIONAL_MUSEUM in ids and bool(ids & CASTLE_SIGHTS) and not bad
    return ok, f"museum={NATIONAL_MUSEUM in ids} castle={bool(ids & CASTLE_SIGHTS)} bad={bad}"


def _no_crash(ret, places, rows):
    return True, f"{len(places)} places"


# ---- fix round 4 (controller-defined rows) ----

def _food_all_near(ref_ids, max_m, n, label=True):
    """At least n food rows, and every food row within max_m of one of ref_ids (labelled with a distance)."""
    def check(ret, places, rows):
        lines = _place_lines(ret)
        refs = [rows[i] for i in ref_ids(rows)] if callable(ref_ids) else [rows[i] for i in ref_ids]
        food = [p for p in places if p["category"] == "food"]
        far = [p["title"] for p in food if min(_dist(r, p) for r in refs) > max_m]
        unlabelled = [p["title"] for p in food if label and not LABEL.search(lines[p["id"]])]
        return len(food) >= n and not far and not unlabelled, f"{len(food)} food, far={far} unlabelled={unlabelled}"
    return check


def _lantern_venues(rows):
    import json
    return json.loads(rows[LANTERN_FESTIVAL]["venue_place_ids"])


def _lantern_dinner(ret, places, rows):
    if LANTERN_FESTIVAL not in {i.id for i in ret.items}:
        return False, "진주남강유등축제 row missing"
    return _food_all_near(_lantern_venues, 2000, 3)(ret, places, rows)


def _festival_only(no_culture_only=False):
    def check(ret, places, rows):
        fest = [i for i in ret.items if i.group == "festival"]
        if not fest and "축제 없음" not in ret.context():
            return False, "festival group empty without a note"
        if no_culture_only:
            bad = [p["title"] for p in places if p["category"] == "culture" or "박물관" in p["title"]]
            return not bad, f"museum/culture={bad}"
        return not places, f"places={[p['title'] for p in places]}"
    return check


def _food_matching(pattern, n):
    rx = re.compile(pattern)

    def check(ret, places, rows):
        wrong = [p["title"] for p in places if p["category"] != "food"]
        good = [p for p in places if rx.search(_text(p, "title", "menu", "overview").replace("진주점", ""))]
        return bool(places) and not wrong and len(good) >= n, f"not food={wrong}, {len(good)} match {pattern}"
    return check


def _pubs(ret, places, rows):
    # "진주점" is a branch suffix (아웃백 진주점), not a 주점.
    food = [p for p in places if p["category"] == "food"
            and re.search("주점|호프|맥주|포차|술집|이자카야", _text(p, "title", "menu", "overview").replace("진주점", ""))]
    return len(food) >= 3, f"{len(food)} food rows match a pub word"


def _bakeries(ret, places, rows):
    good = [p for p in places if re.search("빵|베이커리", _text(p, "title", "menu", "overview"))]
    return len(good) >= 3, f"{len(good)} match 빵/베이커리"


def _autumn(ret, places, rows):
    spring = [p["title"] for p in places if "봄" in p["title"]]
    good = [p for p in places if re.search("단풍|가을", _text(p, "title", "overview"))]
    return not spring and len(good) >= 2, f"봄 titles={spring}, {len(good)} mention 단풍/가을"


def _has_parking(p):
    return bool((p["parking"] or "").strip().strip("-").strip())


def _parking_sights(ret, places, rows):
    lines = _place_lines(ret)
    good = [p for p in places if p["category"] in ("sight", "culture") and _has_parking(p)
            and re.sub(r"\s+", " ", p["parking"]).strip()[:20] in lines[p["id"]]]
    return len(good) >= 3, f"{len(good)} sight/culture with parking text in the line"


def _accessibility_note(ret, places, rows):
    ctx = ret.context()
    ok = bool(re.search(r"접근성[^\n]*(없|않)", ctx))
    return ok, "" if ok else "no accessibility note"


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
    # fix round 2 (controller-defined rows)
    ("R2", "개천예술제 주변 카페", _gaecheon_cafe),
    ("R2", "축제 말고 다른 볼거리", _not_festival_sights),
    ("R2", "아이들과 체험할 수 있는 곳 추천해주세요", _with_kids),
    ("R2", "밤에 사진 찍기 예쁜 곳 어디야", _night_photo),
    ("R2", "진주성 근처 coffee", _labelled_food_near(CASTLE, 2000, 3, re.compile("카페|커피|coffee", re.I))),
    ("R2", "국립진주박물관 근처 점심 먹을 곳", _museum_lunch),
    ("R2", "진주성 근처 갈만한 곳", _castle_sights_near),
    ("R2", "진주 처음 오는데 하루 동안 꼭 가봐야 할 곳 좀 알려줄래요?", _first_visit),
    ("R2", "숙소 추천해줘", _no_digit_titles_top3),
    # fix round 3 (controller-defined rows)
    ("R3", "유등축제 끝나고 남강 근처에서 야경 보면서 산책할 곳", _night_places(3, LANTERN_FESTIVAL)),
    ("R3", "유등축제 보고 나서 야경 볼 곳", _night_places(3)),
    ("R3", "냉면집 말고 다른 맛집", _no_word_in_title_menu("냉면", "food")),
    ("R3", "단풍 명소", _mention_count("단풍", 3)),
    ("R3", "드라이브 코스 추천", _mention_count("드라이브|일주도로", 2)),
    ("R3", "야경 좋은 숙소", _night_stay),
    ("R3", "아침에 산책하기 좋은 곳", _no_food),
    ("R3", "밥집 추천", _all_category("food")),
    ("R3", "안녕하세요, 이번 주말에 처음으로 진주에 놀러 가는데요, 혹시 진주성 근처에 분위기 좋은 카페가 있을까요?",
     _castle_cafes),
    ("R3", "진주썽 근처 맛집", _typo_castle),
    ("R3", "진주성이랑 국립진주박물관 둘 다 보고 근처에서 묶어서 볼 만한 곳", _castle_and_museum),
    ("C5", "진주 " * 200 + "냉면 국밥 비빔밥 카페 숙소 축제 야경 박물관", _no_crash),
    # fix round 4 (controller-defined rows)
    ("R5", "진주성 저녁 운영시간 알려줘", _in_top(3, *CASTLE_SIGHTS)),
    ("R5", "국립진주박물관 저녁에도 열어?", _in_top(1, NATIONAL_MUSEUM)),
    ("R5", "진주성 아침 일찍 열어요?", _in_top(3, *CASTLE_SIGHTS)),
    ("R4", "진주성 근처 점심", _food_all_near((CASTLE,), 2000, 3)),
    ("R4", "유등축제 보고 저녁", _lantern_dinner),
    ("R4", "남강 근처 저녁 추천", _min_category("food", 3)),
    ("R4", "밤에 하는 축제 있어?", _festival_only()),
    ("R4", "비 오는데 축제 하나요?", _festival_only(no_culture_only=True)),
    ("R4", "진주냉면 추천", _food_matching("냉면", 3)),
    ("R4", "진주성 근처 restaurant 추천해줘", _food_all_near((CASTLE,), 2000, 3)),
    ("R4", "진주에 유명한 빵집 어디예요?", _bakeries),
    ("R4", "가을에 가볼 만한 곳 추천해줘", _autumn),
    ("R4", "주차하기 편한 관광지 알려주세요", _parking_sights),
    ("R4", "휠체어나 유모차로 다니기 편한 곳 있을까요?", _accessibility_note),
]


# Controller-defined rows the committed data cannot satisfy honestly. Kept failing (strict xfail): a row that
# starts passing means the data or the retrieval changed and the row should move into CASES.
# - Pubs: the whole DB has ONE food row naming a pub word (소담원, "음료와 맥주" in its overview); every other
#   "주점" hit is a chain's "진주점" branch suffix (아웃백스테이크하우스 진주점). Retrieval answers with
#   a "nothing matched" note instead of presenting branches or generic restaurants as bars.
DATA_LIMITED = [
    ("R4", "축제 끝나고 한잔할 술집 추천", _pubs),
]


def test_golden_retrieval_on_real_db(env):
    _run(CASES, env)


@pytest.mark.xfail(strict=True, reason="data limit: one food row in places.db names a pub word (see DATA_LIMITED)")
def test_golden_rows_the_data_cannot_satisfy(env):
    _run(DATA_LIMITED, env)


def _run(cases, env):
    repo, session, rows = env
    table, failures = [], []
    for kind, msg, check in cases:
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
