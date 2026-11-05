from sqlalchemy import text

from app.core.ratelimit import limiter
from app.core.security import hash_password, verify_password
from app.services.database import normalize_db_url

PAYLOAD = {"category": "tour", "title": "진주성 후기", "content": "좋았어요", "password": "123456"}


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
    assert c.request("DELETE", f"/api/posts/{pid}", json={"password": "123456"}).status_code == 204
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


def _req(headers: dict[str, str], host: str = "10.0.0.9"):
    from starlette.requests import Request

    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (host, 1234),
    }
    return Request(scope)


def test_client_ip_prefers_true_client_ip_then_last_forwarded_hop():
    from app.core.ratelimit import client_ip

    assert client_ip(_req({"True-Client-IP": "1.1.1.1", "X-Forwarded-For": "6.6.6.6, 2.2.2.2"})) == "1.1.1.1"
    assert client_ip(_req({"X-Forwarded-For": "6.6.6.6, 7.7.7.7,  2.2.2.2 "})) == "2.2.2.2"
    assert client_ip(_req({"X-Forwarded-For": "2.2.2.2"})) == "2.2.2.2"
    assert client_ip(_req({})) == "10.0.0.9"
    assert client_ip(_req({"True-Client-IP": "  ", "X-Forwarded-For": " , "})) == "10.0.0.9"


def test_rate_limit_ignores_spoofed_leftmost_forwarded_for(db_client):
    c = db_client(rate_limit="2/minute")
    limiter.enabled = True
    codes = [
        c.post("/api/posts", json=PAYLOAD, headers={"X-Forwarded-For": f"9.9.9.{i}, 2.2.2.2"}).status_code
        for i in range(3)
    ]
    assert codes == [201, 201, 429]
    # A different real last hop is a different client with its own bucket.
    assert c.post("/api/posts", json=PAYLOAD, headers={"X-Forwarded-For": "9.9.9.1, 3.3.3.3"}).status_code == 201


def test_rate_limit_keys_on_true_client_ip(db_client):
    c = db_client(rate_limit="2/minute")
    limiter.enabled = True
    codes = [
        c.post("/api/posts", json=PAYLOAD, headers={"True-Client-IP": "4.4.4.4", "X-Forwarded-For": f"5.5.5.{i}"})
        .status_code
        for i in range(3)
    ]
    assert codes == [201, 201, 429]
    assert c.post("/api/posts", json=PAYLOAD, headers={"True-Client-IP": "8.8.8.8"}).status_code == 201


def test_list_order_breaks_created_at_ties_by_id_desc(db_client):
    c = db_client()
    for i in range(3):
        _create(c, title=f"글{i}")
    with c.app.state.db_engine.begin() as conn:
        conn.execute(text("update board_posts set created_at = '2026-11-05 10:00:00'"))
    ids = [p["id"] for p in c.get("/api/posts").json()["items"]]
    assert ids == sorted(ids, reverse=True)


def test_new_post_password_min_length_6(db_client):
    c = db_client()
    assert c.post("/api/posts", json={**PAYLOAD, "password": "12345"}).status_code == 422
    assert c.post("/api/posts", json={**PAYLOAD, "password": "123456"}).status_code == 201


def test_existing_short_password_post_still_editable_and_deletable(db_client):
    c = db_client()
    pid = _create(c)["id"]
    with c.app.state.db_engine.begin() as conn:
        conn.execute(text("update board_posts set password = :p"), {"p": hash_password("1234")})
    assert c.put(f"/api/posts/{pid}", json={**PAYLOAD, "password": "1234"}).status_code == 200
    assert c.request("DELETE", f"/api/posts/{pid}", json={"password": "1234"}).status_code == 204


def test_put_and_delete_share_one_bucket_per_ip_and_post(db_client):
    c = db_client(rate_limit="3/minute")
    limiter.enabled = True
    pid = _create(c)["id"]
    other = _create(c)["id"]
    limiter.reset()
    bad = {**PAYLOAD, "password": "wrong-pw"}
    codes = [
        c.put(f"/api/posts/{pid}", json=bad).status_code,
        c.request("DELETE", f"/api/posts/{pid}", json={"password": "wrong-pw"}).status_code,
        c.put(f"/api/posts/{pid}", json=bad).status_code,
        c.request("DELETE", f"/api/posts/{pid}", json={"password": "wrong-pw"}).status_code,
    ]
    assert codes == [403, 403, 403, 429], codes
    # A different post has its own bucket.
    assert c.put(f"/api/posts/{other}", json=bad).status_code == 403


def test_keyword_search_escapes_like_wildcards(db_client):
    c = db_client()
    _create(c, title="할인 100% 후기", content="a")
    _create(c, title="plain", content="b")
    _create(c, title="under_score", content="c")
    _create(c, title="underXscore", content="d")
    _create(c, title="back\\slash", content="e")
    titles = lambda kw: {p["title"] for p in c.get("/api/posts", params={"keyword": kw}).json()["items"]}
    assert titles("%") == {"할인 100% 후기"}
    assert titles("_") == {"under_score"}
    assert titles("\\") == {"back\\slash"}
    assert titles("under_s") == {"under_score"}
