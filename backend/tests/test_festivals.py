from datetime import date

import pytest

from app.services.festival_status import kst_today, festival_status


@pytest.fixture
def client(make_client, fixture_db_path):
    c = make_client(places_db_path=fixture_db_path)
    yield c
    repo = getattr(c.app.state, "places_repo", None)
    if repo:
        repo.close()


@pytest.fixture
def client_no_demo(make_client, fixture_db_path):
    c = make_client(places_db_path=fixture_db_path, demo_date_override_enabled=False)
    yield c
    repo = getattr(c.app.state, "places_repo", None)
    if repo:
        repo.close()


@pytest.mark.parametrize("s,e,u,today,exp", [
    (date(2026, 11, 4), date(2026, 11, 8), False, date(2026, 11, 4), "ongoing"),
    (date(2026, 10, 3), date(2026, 10, 18), False, date(2026, 11, 4), "ended"),
    (date(2024, 5, 1), date(2024, 5, 3), False, date(2026, 11, 4), "stale"),
    (date(2026, 12, 1), date(2026, 12, 3), False, date(2026, 11, 4), "upcoming"),
    (None, None, True, date(2026, 11, 4), "undecided"),
    (date(2026, 11, 4), date(2026, 11, 8), True, date(2026, 11, 4), "undecided"),
    (None, date(2026, 11, 8), False, date(2026, 11, 4), "undecided"),
])
def test_status_table(s, e, u, today, exp):
    assert festival_status(s, e, u, today) == exp


def test_status_undecided_and_open_end():
    assert festival_status(date(2026, 11, 4), None, False, date(2026, 11, 4)) == "ongoing"
    assert festival_status(date(2026, 11, 4), None, False, date(2026, 11, 5)) == "ended"


def test_status_cross_year():
    assert festival_status(date(2026, 12, 31), date(2027, 1, 2), False, date(2027, 1, 1)) == "ongoing"


def test_kst_today_is_date():
    assert isinstance(kst_today(), date)


def test_today_override_enabled(client):
    assert client.get("/api/festivals?today=2026-10-10").json()["today"] == "2026-10-10"


def test_today_override_disabled(client_no_demo):
    assert client_no_demo.get("/api/festivals?today=2026-10-10").json()["today"] != "2026-10-10"


def test_lantern_festival_ongoing_on_demo_date(client):
    items = client.get("/api/festivals?today=2026-10-10").json()["items"]
    assert any("유등" in i["title"] and i["status"] == "ongoing" and i["status_label"] == "진행 중" for i in items)


def test_filter_and_ordering(client):
    all_items = client.get("/api/festivals?today=2026-10-10").json()["items"]
    order = ["ongoing", "upcoming", "ended", "stale", "undecided"]
    ranks = [order.index(i["status"]) for i in all_items]
    assert ranks == sorted(ranks)
    ong = client.get("/api/festivals?status=ongoing&today=2026-10-10").json()["items"]
    assert ong and {i["status"] for i in ong} == {"ongoing"}


def test_bad_params_422(client):
    assert client.get("/api/festivals?status=nope").status_code == 422
    assert client.get("/api/festivals?today=garbage").status_code == 422
