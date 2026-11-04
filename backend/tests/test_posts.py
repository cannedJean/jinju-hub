from sqlalchemy import text

from app.core.ratelimit import limiter
from app.core.security import hash_password, verify_password
from app.services.database import normalize_db_url

PAYLOAD = {"category": "tour", "title": "진주성 후기", "content": "좋았어요", "password": "1234"}


def _create(c, **kw):
    r = c.post("/api/posts", json={**PAYLOAD, **kw})
    assert r.status_code == 201, r.text
    return r.json()


def test_crud_flow(db_client):
    c = db_client()
    created = _create(c)
    assert "password" not in created and created["views"] == 0 and created["updated_at"] is None
    pid = created["id"]
    assert c.get(f"/api/posts/{pid}").json()["views"] == 1
    r = c.put(f"/api/posts/{pid}", json={**PAYLOAD, "title": "수정됨"})
    assert r.status_code == 200 and r.json()["title"] == "수정됨" and r.json()["updated_at"]
    listing = c.get("/api/posts", params={"keyword": "수정"}).json()
    assert listing["total"] == 1 and listing["totalPages"] == 1
    assert c.request("DELETE", f"/api/posts/{pid}", json={"password": "1234"}).status_code == 204
    assert c.get(f"/api/posts/{pid}").status_code == 404


def test_password_stored_hashed(db_client):
    c = db_client()
    _create(c)
    with c.app.state.db_engine.connect() as conn:
        stored = conn.execute(text("select password from board_posts")).scalar_one()
    assert stored != "1234" and stored.startswith("$2b$")


def test_wrong_password_403(db_client):
    c = db_client()
    pid = _create(c)["id"]
    assert c.put(f"/api/posts/{pid}", json={**PAYLOAD, "password": "9999"}).status_code == 403
    assert c.request("DELETE", f"/api/posts/{pid}", json={"password": "9999"}).status_code == 403
    assert c.get(f"/api/posts/{pid}", params={"count_view": "false"}).status_code == 200


def test_count_view_false_does_not_increment(db_client):
    c = db_client()
    pid = _create(c)["id"]
    assert c.get(f"/api/posts/{pid}", params={"count_view": "false"}).json()["views"] == 0
    assert c.get(f"/api/posts/{pid}").json()["views"] == 1


def test_rate_limit_429(db_client):
    c = db_client(rate_limit="2/minute")
    limiter.enabled = True
    codes = [c.post("/api/posts", json=PAYLOAD).status_code for _ in range(3)]
    assert codes == [201, 201, 429]
    assert c.post("/api/posts", json=PAYLOAD).json() == {"detail": "rate_limited"}


def test_normalize_db_url():
    assert normalize_db_url("postgres://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalize_db_url("postgresql://u:p@h/db?sslmode=require") == "postgresql+psycopg://u:p@h/db?sslmode=require"
    assert normalize_db_url("sqlite:///./x.db") == "sqlite:///./x.db"


def test_hash_and_verify():
    h = hash_password("abcd")
    assert h.startswith("$2b$12$") and verify_password("abcd", h) and not verify_password("abce", h)
    assert verify_password("abcd", "not-a-hash") is False
