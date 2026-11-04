from pathlib import Path

import pytest


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture
def fixture_text():
    base = Path(__file__).resolve().parent / "fixtures"

    def _read(relpath: str) -> str:
        return (base / relpath).read_text(encoding="utf-8")

    return _read


@pytest.fixture
def fixture_json():
    import json

    base = Path(__file__).resolve().parent / "fixtures"

    def _read(relpath: str):
        return json.loads((base / relpath).read_text(encoding="utf-8"))

    return _read


@pytest.fixture
def ctx_factory(tmp_path):
    from datetime import date, datetime

    import httpx

    from jinju_pipeline.http import QuotaLedger
    from jinju_pipeline.raw_store import KST, RawStore, new_run_id
    from jinju_pipeline.region import load_region
    from jinju_pipeline.settings import Settings
    from jinju_pipeline.sources.base import make_context

    repo = Path(__file__).resolve().parents[2]

    def _make(transport, **settings_overrides):
        overrides = {"city_min_interval": 0.0, "raw_dir": tmp_path / "raw"}
        overrides.update(settings_overrides)
        settings = Settings(_env_file=None, **overrides)
        now = datetime.now(KST)
        return make_context(
            client=httpx.AsyncClient(transport=transport, follow_redirects=True),
            store=RawStore(settings.raw_dir, new_run_id(now)),
            ledger=QuotaLedger(None, 10**9, today=date.today()),
            settings=settings,
            region=load_region(repo / "config" / "region.yaml"),
        )

    return _make


@pytest.fixture
def previous_snapshot():
    """Factory: previous_snapshot(raw_by_source=..., pending=..., generated_at=...)."""
    from datetime import datetime

    from jinju_pipeline.models import PreviousSnapshot
    from jinju_pipeline.raw_store import KST

    def _make(raw_by_source=None, pending=(), generated_at=None):
        raw = raw_by_source or {}
        return PreviousSnapshot(
            generated_at=generated_at or datetime(2026, 11, 1, 3, 0, tzinfo=KST),
            place_count=sum(len(v) for v in raw.values()),
            source_index={},
            id_order={},
            aliases={},
            raw_by_source=raw,
            modified_by_key={
                r.key: r.payload["list"]["modifiedtime"]
                for v in raw.values() for r in v if "list" in r.payload
            },
            detail_pending_keys=set(pending),
        )

    return _make


@pytest.fixture
def region(repo_root):
    from jinju_pipeline.region import load_region

    return load_region(repo_root / "config" / "region.yaml")


@pytest.fixture
def city_raws():
    from helpers import city_raws_from_fixture

    return city_raws_from_fixture("tourinfo")


@pytest.fixture
def tour_raw_126833():
    from helpers import make_tour_raw_126833

    return make_tour_raw_126833()


@pytest.fixture
def tour_raw_hidden():
    from helpers import make_tour_raw_hidden

    return make_tour_raw_hidden()


@pytest.fixture
def places_fixture():
    import json

    from jinju_pipeline.models import Place

    path = Path(__file__).resolve().parent / "fixtures" / "places_small.json"
    return [Place(**d) for d in json.loads(path.read_text(encoding="utf-8"))]


@pytest.fixture
def cur():
    from jinju_pipeline.curation import load_curation

    return load_curation(Path(__file__).resolve().parent / "fixtures" / "curation")


# ---- A12 end-to-end fixtures ----

def _recorded_handler(city_kinds=None, tour=True):
    """MockTransport handler serving the recorded A4/A5 fixtures by URL pattern.

    Unrecorded requests get an empty result (city: ``results: []``; TourAPI: ``items: ""``,
    ``totalCount: 0``). ``city_kinds`` limits which city endpoints return their page-1 fixture.
    """
    import json

    import httpx

    base = Path(__file__).resolve().parent / "fixtures"
    endpoint_kind = {"tourinfo.do": "tourinfo", "restaurant.do": "restaurant", "festival.do": "festival",
                     "asset.do": "heritage", "lodging.do": "lodging"}
    tour_empty = {"response": {"header": {"resultCode": "0000", "resultMsg": "OK"},
                               "body": {"items": "", "numOfRows": 0, "pageNo": 1, "totalCount": 0}}}

    def load(rel):
        return json.loads((base / rel).read_text(encoding="utf-8"))

    def handler(request: httpx.Request) -> httpx.Response:
        host, path, p = request.url.host, request.url.path, request.url.params
        if host == "www.jinju.go.kr":
            kind = endpoint_kind.get(path.rsplit("/", 1)[-1])
            if kind is None:
                return httpx.Response(404)
            if p.get("page") == "1" and (city_kinds is None or kind in city_kinds):
                return httpx.Response(200, json=load(f"jinju_city/{kind}_p1.json"))
            return httpx.Response(200, json={"record_count": 0, "results": [], "status": "OK"})
        if host == "apis.data.go.kr" and tour:
            op = path.rsplit("/", 1)[-1]
            cid = p.get("contentId")
            if op == "areaBasedList2" and p.get("contentTypeId") == "12":
                return httpx.Response(200, json=load("tourapi/area_12_p1.json"))
            if op == "searchFestival2":
                return httpx.Response(200, json=load("tourapi/festival_p1.json"))
            if op == "ldongCode2":
                return httpx.Response(200, json=load("tourapi/ldong_48.json"))
            if cid == "126833" and op == "detailCommon2":
                return httpx.Response(200, json=load("tourapi/detail_common_126833.json"))
            if cid == "126833" and op == "detailIntro2":
                return httpx.Response(200, json=load("tourapi/detail_intro_126833_12.json"))
            if cid == "126833" and op == "detailImage2":
                return httpx.Response(200, json=load("tourapi/detail_image_126833.json"))
            return httpx.Response(200, json=tour_empty)
        return httpx.Response(404)

    return handler


@pytest.fixture
def recorded_transport():
    import httpx

    return httpx.MockTransport(_recorded_handler())


@pytest.fixture
def transport_returning_few():
    """Only the festival endpoint returns data: a run far below 80% of a normal one."""
    import httpx

    return httpx.MockTransport(_recorded_handler(city_kinds={"festival"}, tour=False))


@pytest.fixture
def tmp_settings(tmp_path):
    from jinju_pipeline.settings import Settings

    return Settings(
        _env_file=None,
        data_go_kr_key=None,
        raw_dir=tmp_path / "raw",
        work_dir=tmp_path / "work",
        state_dir=tmp_path / "state",
        output_db=tmp_path / "out" / "places.db",
        output_report=tmp_path / "out" / "report.json",
        curation_dir=Path(__file__).resolve().parent / "fixtures" / "curation",
        gate_min_first_run=5,
        city_min_interval=0.0,
    )
