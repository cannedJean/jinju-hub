from datetime import datetime

from jinju_pipeline.models import RawRecord


def test_raw_record_key():
    rec = RawRecord(source="tourapi.area", source_id="126508", payload={}, fetched_at=datetime(2026, 11, 4))
    assert rec.key == "tourapi.area:126508"
