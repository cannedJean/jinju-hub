import json
import shutil
import sqlite3

import pytest

from app.services.places_repo import CATEGORY_LABELS


@pytest.fixture
def client(make_client, fixture_db_path, tmp_path):
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"total": 3}), encoding="utf-8")
    c = make_client(places_db_path=fixture_db_path, report_path=report)
    yield c
    repo = getattr(c.app.state, "places_repo", None)
    if repo:
        repo.close()


def test_places_query_parsing(client):
    r = client.get("/api/places?category=food&category=sight&bbox=128.07,35.18,128.10,35.20&size=5")
    assert r.status_code == 200
    body = r.json()
    assert body["size"] == 5
    assert {i["category"] for i in body["items"]} <= {"food", "sight"}


def test_near_and_tags_parse(client):
    r = client.get("/api/places?near=35.19,128.08&radius=3000&sort=distance&tags=outdoor&tags=indoor")
    assert r.status_code == 200


@pytest.mark.parametrize("qs", ["bbox=1,2,3", "bbox=a,b,c,d", "near=1", "near=x,y", "size=0", "size=51", "radius=0", "sort=bogus"])
def test_bad_params_422(client, qs):
    assert client.get(f"/api/places?{qs}").status_code == 422


def test_bad_bbox_422(client):
    assert client.get("/api/places?bbox=1,2,3").status_code == 422


def test_markers_etag(client):
    health = client.get("/api/health").json()["data_version"]
    r = client.get("/api/places/markers")
    assert r.status_code == 200
    assert r.headers["etag"] == health
    assert r.headers["cache-control"] == "public, max-age=600"
    assert len(r.json()) > 0
    only = client.get("/api/places/markers?category=food").json()
    assert only and {m["category"] for m in only} == {"food"}


def test_place_detail_and_404_body(client):
    pid = client.get("/api/places?q=촉석루").json()["items"][0]["id"]
    d = client.get(f"/api/places/{pid}")
    assert d.status_code == 200 and d.json()["canonical_id"] == pid
    r = client.get("/api/places/nope-nope")
    assert r.status_code == 404
    assert r.json() == {"detail": "place_not_found"}


def test_place_alias_resolves(make_client, fixture_db_path, tmp_path):
    p = tmp_path / "p.db"
    shutil.copy(fixture_db_path, p)
    c = make_client(places_db_path=p)
    pid = c.get("/api/places?q=촉석루").json()["items"][0]["id"]
    c.app.state.places_repo.close()
    c.app.state.places_repo = None
    con = sqlite3.connect(p)
    con.execute("INSERT INTO place_aliases(old_id,new_id) VALUES('jh-old',?)", (pid,))
    con.commit()
    con.close()
    d = c.get("/api/places/jh-old")
    assert d.status_code == 200 and d.json()["canonical_id"] == pid
    c.app.state.places_repo.close()


def test_meta_categories_eight_codes(client):
    m = client.get("/api/meta").json()
    assert sorted(c["code"] for c in m["categories"]) == sorted(CATEGORY_LABELS)
    assert len(m["categories"]) == 8
    total = client.get("/api/places?size=1").json()["total"]
    assert sum(c["count"] for c in m["categories"]) == total
    assert m["data_version"]


def test_collection_endpoint(client):
    c = client.get("/api/collection").json()
    assert set(c) == {"collection_ids", "jinju8", "badges", "places"}


def test_report_endpoint(client):
    r = client.get("/api/data/report")
    assert r.status_code == 200 and r.json() == {"total": 3}


def test_report_404(make_client, fixture_db_path, tmp_path):
    c = make_client(places_db_path=fixture_db_path, report_path=tmp_path / "none.json")
    assert c.get("/api/data/report").status_code == 404
    c.app.state.places_repo.close()
