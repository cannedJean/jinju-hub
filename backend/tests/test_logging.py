import logging

from fastapi import APIRouter

from app.core.logging import SecretMaskFilter


def test_request_log_has_path_status_latency(make_client, tmp_path, caplog):
    client = make_client(places_db_path=tmp_path / "m.db")
    with caplog.at_level(logging.INFO, logger="jinjuhub.request"):
        client.get("/api/health")
    text = " ".join(r.getMessage() for r in caplog.records)
    assert '"path": "/api/health"' in text
    assert '"status": 200' in text
    assert "latency_ms" in text


def test_secret_masked_in_logs(caplog):
    logger = logging.getLogger("jinjuhub.test")
    flt = SecretMaskFilter()
    logger.addFilter(flt)
    try:
        with caplog.at_level(logging.INFO, logger="jinjuhub.test"):
            logger.info("x?serviceKey=SECRET&a=1")
            logger.info("y authKey=SECRET2 x-api-key: SECRET3 api_key=SECRET4 sk-ant-api03-SECRET5")
    finally:
        logger.removeFilter(flt)
    text = " ".join(r.getMessage() for r in caplog.records)
    for s in ("SECRET", "SECRET2", "SECRET3", "SECRET4", "SECRET5"):
        assert s not in text
    assert "serviceKey=***" in text and "&a=1" in text


def test_unhandled_error_returns_500_json(make_client, tmp_path, caplog):
    client = make_client(places_db_path=tmp_path / "m.db")
    boom = APIRouter()

    @boom.get("/boom")
    def _boom():
        raise RuntimeError("secret detail")

    client.app.include_router(boom)
    with caplog.at_level(logging.ERROR):
        r = client.get("/boom")
    assert r.status_code == 500
    assert r.json() == {"detail": "internal_error"}
    assert "secret detail" not in r.text
