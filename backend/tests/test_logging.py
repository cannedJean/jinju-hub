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


def test_exc_info_traceback_is_masked():
    import io

    stream = io.StringIO()
    h = logging.StreamHandler(stream)
    h.setFormatter(logging.Formatter("%(message)s"))
    h.addFilter(SecretMaskFilter())
    lg = logging.getLogger("jinjuhub.exc_test")
    lg.propagate = False
    lg.addHandler(h)
    try:
        try:
            raise RuntimeError("GET https://x/y?serviceKey=SECRETA&authKey=SECRETB failed sk-ant-api03-SECRETC")
        except RuntimeError:
            lg.error("boom", exc_info=True)
    finally:
        lg.removeHandler(h)
    out = stream.getvalue()
    assert "RuntimeError" in out and "Traceback" in out
    for s in ("SECRETA", "SECRETB", "SECRETC"):
        assert s not in out


def _uvicorn_access_record(full_path):
    return logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d', ("127.0.0.1:5000", "GET", full_path, "1.1", 200), None,
    )


def _format_access(record):
    from uvicorn.logging import AccessFormatter

    fmt = AccessFormatter(fmt='%(client_addr)s - "%(request_line)s" %(status_code)s')
    return fmt.format(record)


def test_uvicorn_access_log_formats_without_error():
    record = _uvicorn_access_record("/api/health")
    SecretMaskFilter().filter(record)
    out = _format_access(record)
    assert "/api/health" in out and "200" in out


def test_uvicorn_access_log_masks_query_secret():
    record = _uvicorn_access_record("/x?serviceKey=SECRET123&a=1")
    SecretMaskFilter().filter(record)
    assert isinstance(record.args, tuple) and len(record.args) == 5
    out = _format_access(record)
    assert "SECRET123" not in out
    assert "serviceKey=***" in out and "a=1" in out


def test_secret_split_across_msg_and_args_is_masked():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "call ?serviceKey=%s&a=1", ("SPLIT123",), None)
    SecretMaskFilter().filter(record)
    assert "SPLIT123" not in record.getMessage()


def test_non_str_msg_without_args_is_masked():
    record = logging.LogRecord("t", logging.ERROR, __file__, 1, Exception("GET ?serviceKey=SNONSTR"), (), None)
    SecretMaskFilter().filter(record)
    assert "SNONSTR" not in logging.Formatter("%(message)s").format(record)


def test_non_str_arg_object_is_masked_via_fallback():
    class Url:
        def __str__(self):
            return "http://x?authKey=KOBJ"

    record = logging.LogRecord("t", logging.INFO, __file__, 1, "calling %s", (Url(),), None)
    SecretMaskFilter().filter(record)
    assert "KOBJ" not in logging.Formatter("%(message)s").format(record)


def test_filter_is_idempotent():
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "u %s", ("?serviceKey=S1",), None)
    flt = SecretMaskFilter()
    flt.filter(record)
    first = record.getMessage()
    flt.filter(record)
    assert record.getMessage() == first and "S1" not in first


def test_dsn_password_masked():
    from app.core.logging import mask_secrets

    out = mask_secrets("connect failed: postgresql://neonuser:p4ss-W0rd@ep-x.neon.tech/db?sslmode=require")
    assert "p4ss-W0rd" not in out
    assert "postgresql://neonuser:***@ep-x.neon.tech/db" in out
