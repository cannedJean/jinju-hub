from datetime import date

import pytest

from jinju_pipeline.clean.category import map_category
from jinju_pipeline.clean.coords import normalize_coords
from jinju_pipeline.clean.festival import parse_date, parse_undecided
from jinju_pipeline.clean.phone import format_phone
from jinju_pipeline.clean.text import clean_text
from jinju_pipeline.clean.urls import extract_homepage, normalize_url


@pytest.mark.parametrize("a,b,addr,exp", [
    ("35.1925", "128.0845", None, (35.1925, 128.0845, "ok", False)),
    ("128.0845", "35.1925", None, (35.1925, 128.0845, "ok", False)),   # 진주시 API 뒤바뀜
    ("0", "0", None, (None, None, "missing", False)),
    ("", None, None, (None, None, "missing", False)),
    ("36.35", "127.38", "경남 진주시 진주대로 1", (None, None, "out_of_region", False)),
    ("36.35", "127.38", "대전광역시 중구", (None, None, "out_of_region", True)),
    ("35.1", "35.2", None, (None, None, "missing", False)),
    ("abc", "128.0", None, (None, None, "missing", False)),
    (35.1925, 128.0845, None, (35.1925, 128.0845, "ok", False)),
])
def test_normalize_coords(region, a, b, addr, exp):
    assert normalize_coords(a, b, region, addr) == exp


def test_clean_text():
    assert clean_text("진주성<br/>촉석루 &amp; 의암<p> </p>") == "진주성\n촉석루 & 의암"


def test_clean_text_edge_cases():
    assert clean_text(None) is None
    assert clean_text("  <br> ") is None
    assert clean_text("a<br>b") == "a\nb"
    assert clean_text("a\r\n\r\n\r\n\r\nb") == "a\n\nb"
    assert clean_text("  x  \n  y ") == "x\ny"


@pytest.mark.parametrize("raw,exp", [
    ("055-749-2054", "055-749-2054"), ("0557492054", "055-749-2054"),
    ("055)746-0000, 010-1111-2222", "055-746-0000"), ("1330", "1330"), (None, None),
    ("02-123-4567", "02-123-4567"), ("0212345678", "02-1234-5678"),
    ("010-1111-2222", "010-1111-2222"), ("15881234", "1588-1234"),
    ("", None), ("문의 요망", "문의 요망"),
])
def test_format_phone(raw, exp):
    assert format_phone(raw) == exp


def test_normalize_url():
    assert normalize_url("http://tong.visitkorea.or.kr/a.jpg") == "https://tong.visitkorea.or.kr/a.jpg"
    assert normalize_url("/CmsMultiFile/view.do?id=1", "http://www.jinju.go.kr") == "https://www.jinju.go.kr/CmsMultiFile/view.do?id=1"


def test_normalize_url_other_hosts_untouched():
    assert normalize_url("http://example.com/a") == "http://example.com/a"
    assert normalize_url("  ") is None
    assert normalize_url(None) is None
    assert normalize_url("/rel") == "/rel"  # no base: left as is


def test_extract_homepage():
    assert extract_homepage('<a href="http://www.jinju.go.kr/x" target="_blank">링크</a>') == "https://www.jinju.go.kr/x"
    assert extract_homepage("http://example.com") == "http://example.com"
    assert extract_homepage("없음") == "없음"
    assert extract_homepage("") is None


@pytest.mark.parametrize("s,exp", [
    ("20261003", date(2026, 10, 3)), ("2026-10-18", date(2026, 10, 18)),
    ("2026. 10. 9", date(2026, 10, 9)), ("2026.10.09", date(2026, 10, 9)),
    ("미정", None), (None, None), ("", None), ("20261399", None),
])
def test_parse_date(s, exp):
    assert parse_date(s) == exp


@pytest.mark.parametrize("v,exp", [
    ("2024년 8월 중", True), ("매년 10월 개최", True), ("", False), (None, False),
    ("N", False), ("0", False), ("Y", True),
])
def test_parse_undecided(v, exp):
    assert parse_undecided(v) is exp


def test_map_category_tourapi():
    assert map_category("tourapi.area", {"list": {"contenttypeid": "39"}}) == "food"
    assert map_category("tourapi.festival", {"contenttypeid": "15"}) == "festival"
    assert map_category("tourapi.area", {"list": {"contenttypeid": "99"}}) is None


@pytest.mark.parametrize("src,payload,exp", [
    ("jinju_city.tourinfo", {"category": "관광명소"}, "sight"),
    ("jinju_city.tourinfo", {"category": "문화체험"}, "culture"),
    ("jinju_city.tourinfo", {"category": "박물관"}, "culture"),
    ("jinju_city.tourinfo", {"category": "전시관"}, "culture"),
    ("jinju_city.restaurant", {}, "food"),
    ("jinju_city.festival", {}, "festival"),
    ("jinju_city.heritage", {}, "culture"),
    ("jinju_city.lodging", {}, "stay"),
    ("unknown.x", {}, None),
])
def test_map_category_city(src, payload, exp):
    assert map_category(src, payload) == exp
