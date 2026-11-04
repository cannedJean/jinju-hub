import json
from datetime import datetime

from jinju_pipeline.raw_store import KST, RawStore, mask_params, new_run_id


def test_write_page_preserves_body_bytes(tmp_path):
    body = {"results": [{"idx": 1, "name": "진주성"}], "record_count": 1}
    store = RawStore(tmp_path, "20261104T090507+0900")

    path = store.write_page("jinju", 1, body, {"page": 1, "pageunit": 10})

    assert path == tmp_path / "jinju" / "20261104T090507+0900" / "page-001.json"
    assert json.loads(path.read_text(encoding="utf-8")) == body


def test_manifest_masks_service_key(tmp_path):
    store = RawStore(tmp_path, "20261104T090507+0900")
    store.write_page("tour", 1, {"ok": True}, {"serviceKey": "SECRET", "pageNo": 1})

    manifests = store.finalize()

    manifest_path = tmp_path / "tour" / "20261104T090507+0900" / "manifest.json"
    text = manifest_path.read_text(encoding="utf-8")
    assert "SECRET" not in text
    assert "***" in text
    assert manifests["tour"]["requests"][0] == {"serviceKey": "***", "pageNo": 1}


def test_run_id_format():
    assert KST == datetime(2026, 11, 4, 9, 5, 7, tzinfo=KST).tzinfo
    assert new_run_id(datetime(2026, 11, 4, 9, 5, 7, tzinfo=KST)) == "20261104T090507+0900"


def test_mask_params_masks_auth_keys_without_mutating_input():
    original = {"serviceKey": "A", "authKey": "B", "page": 2}

    masked = mask_params(original)

    assert masked == {"serviceKey": "***", "authKey": "***", "page": 2}
    assert original == {"serviceKey": "A", "authKey": "B", "page": 2}


def test_manifest_records_hint_and_sha256_per_page(tmp_path):
    store = RawStore(tmp_path, "20261104T090507+0900")
    store.write_page("jinju", 1, {"results": [{"idx": 1}, {"idx": 2}]}, {"page": 1})
    store.write_page("jinju", 2, {"results": [{"idx": 3}]}, {"page": 2})

    manifest = store.finalize()["jinju"]

    assert manifest["run_id"] == "20261104T090507+0900"
    assert manifest["source"] == "jinju"
    assert manifest["records_hint"] == 3
    assert [p["page"] for p in manifest["pages"]] == [1, 2]
    assert all(len(p["sha256"]) == 64 for p in manifest["pages"])
    assert "written_at" in manifest


def test_records_hint_null_for_text_bodies(tmp_path):
    store = RawStore(tmp_path, "20261104T090507+0900")
    store.write_page("raw", 1, "<xml>not json</xml>", {"page": 1})

    manifest = store.finalize()["raw"]

    assert manifest["records_hint"] is None
    assert (tmp_path / "raw" / "20261104T090507+0900" / "page-001.json").read_text(
        encoding="utf-8"
    ) == "<xml>not json</xml>"
