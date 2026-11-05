import shutil
import sqlite3

import pytest

from app.schemas.places import PlaceQuery
from app.services.places_repo import CATEGORY_LABELS, PlacesRepo


@pytest.fixture
def repo(fixture_db_path):
    r = PlacesRepo(fixture_db_path)
    yield r
    r.close()


@pytest.fixture
def some_id(repo):
    return repo.search(PlaceQuery(q="촉석루")).items[0].id


@pytest.fixture
def alias_db(tmp_path, fixture_db_path):
    p = tmp_path / "p.db"
    shutil.copy(fixture_db_path, p)
    return p


def _add_alias(p, old, new):
    con = sqlite3.connect(p)
    con.execute("INSERT INTO place_aliases(old_id,new_id) VALUES(?,?)", (old, new))
    con.commit()
    con.close()


@pytest.fixture
def repo_with_alias(alias_db, some_id):
    _add_alias(alias_db, "jh-old", some_id)
    r = PlacesRepo(alias_db)
    yield r
    r.close()


def test_search_category_and_paging(repo):
    page = repo.search(PlaceQuery(category=["food"], size=5))
    assert page.size == 5 and page.items and all(i.category == "food" for i in page.items)
    assert page.totalPages == -(-page.total // 5)


def test_search_two_char_korean_uses_like(repo):
    assert any("냉면" in (i.title + (i.summary or "")) for i in repo.search(PlaceQuery(q="냉면")).items)


def test_search_three_char_fts(repo):
    assert "촉석루" in repo.search(PlaceQuery(q="촉석루")).items[0].title


def test_search_punctuation_no_error(repo):
    repo.search(PlaceQuery(q='진주성(촉석루) "AND" -*'))
    repo.search(PlaceQuery(q="100%_\\"))


def test_search_multiword_short_tokens(repo):
    assert repo.search(PlaceQuery(q="진주 냉면")).total >= 1


def test_near_radius_sorted_by_distance(repo):
    items = repo.search(PlaceQuery(near=(35.1925, 128.0845), radius=1000, sort="distance")).items
    d = [i.distance_m for i in items]
    assert d and d == sorted(d) and all(x <= 1000 for x in d)


def test_bbox_filter(repo):
    items = repo.search(PlaceQuery(bbox=(128.07, 35.18, 128.10, 35.20))).items
    assert items and all(35.18 <= i.lat <= 35.20 for i in items)


def test_tags_filter_indoor(repo):
    items = repo.search(PlaceQuery(tags=["indoor"])).items
    assert items and all("indoor" in i.tags for i in items)


def test_sort_collection_and_name(repo):
    items = repo.search(PlaceQuery(sort="collection", size=8)).items
    assert [i.jinju8_rank for i in items] == list(range(1, 9))
    names = [i.title for i in repo.search(PlaceQuery(sort="name", size=50)).items]
    assert names == sorted(names)


def test_markers_have_coords(repo):
    ms = repo.markers(None)
    assert ms and all(m.lat and m.lng for m in ms)
    assert {m.category for m in repo.markers(["food"])} == {"food"}


def test_get_detail_with_nearby(repo, some_id):
    d = repo.get(some_id)
    assert d.canonical_id == some_id and len(d.nearby) <= 6 and some_id not in [n.id for n in d.nearby]


def test_get_by_alias_returns_canonical(repo_with_alias, some_id):
    d = repo_with_alias.get("jh-old")
    assert d is not None and d.canonical_id == some_id != "jh-old"


def test_alias_chain_and_dangling(alias_db, some_id):
    _add_alias(alias_db, "jh-a", "jh-b")
    _add_alias(alias_db, "jh-b", some_id)
    _add_alias(alias_db, "jh-gone", "jh-deleted")
    _add_alias(alias_db, "jh-loop1", "jh-loop2")
    _add_alias(alias_db, "jh-loop2", "jh-loop1")
    r = PlacesRepo(alias_db)
    try:
        assert r.get("jh-a").canonical_id == some_id
        assert r.get("jh-gone") is None
        assert r.get("jh-loop1") is None
    finally:
        r.close()


def test_get_unknown_returns_none(repo):
    assert repo.get("jh-nope") is None


def test_readonly_connection(repo):
    with pytest.raises(sqlite3.OperationalError):
        repo._con.execute("DELETE FROM places")


def test_collection_shape(repo):
    c = repo.collection()
    assert len(c.badges) == 6 and len(c.jinju8) == 8
    assert [j.rank for j in c.jinju8] == list(range(1, 9))


def test_meta(repo):
    m = repo.meta()
    assert m.attribution == "한국관광공사 TourAPI · 진주시 공공데이터" and m.data_version
    assert [c.code for c in m.categories] == list(CATEGORY_LABELS) and m.region


def test_festival_rows(repo):
    rows = repo.festival_rows()
    lantern = next(r for r in rows if r["id"] == "jh-0994890048")
    assert str(lantern["start_date"]) == "2026-10-03" and str(lantern["end_date"]) == "2026-10-18"
    assert len(lantern["programs"]) == 4 and len(lantern["venue_place_ids"]) == 3
    assert set(lantern) == {"id", "title", "summary", "hero_image", "addr", "lat", "lng", "start_date", "end_date",
                            "date_undecided", "venue_place_ids", "programs"}
    assert any(r["start_date"] is None for r in rows)


def test_report(fixture_db_path, tmp_path):
    f = tmp_path / "r.json"
    f.write_text('{"a": 1}', encoding="utf-8")
    r = PlacesRepo(fixture_db_path, f)
    assert r.report() == {"a": 1}
    r.close()
    r2 = PlacesRepo(fixture_db_path, tmp_path / "missing.json")
    assert r2.report() is None
    r2.close()


def test_fixture_uses_trigram_fts(repo):
    assert repo.fts_mode == "trigram"


@pytest.mark.parametrize("q", ['진주성(촉석루) "AND" NOT', '"""', "촉석루* 진주성)", "촉석루 AND 진주성", "촉석루 NOT 진주성"])
def test_fts_path_operators_are_literals(repo, q):
    repo.search(PlaceQuery(q=q))  # all tokens >= 3 chars -> quoted MATCH path; must not raise
    assert repo.last_search_mode == "fts"


def test_fts_operator_words_are_and_of_literals(repo):
    for q in ("촉석루 AND 존재안함", "촉석루 NOT 존재안함"):
        assert repo.search(PlaceQuery(q=q)).total == 0  # operator semantics would return >= 1 for NOT
        assert repo.last_search_mode == "fts"
    assert repo.search(PlaceQuery(q="촉석루 촉석루")).total >= 1
    assert repo.last_search_mode == "fts"


@pytest.mark.parametrize("q", ['진주성(촉석루) "AND" OR NOT', "촉석루 OR NOT 진주성", "촉석루 OR 존재안함", "진주성(촉석루) \"AND\" -*"])
def test_like_path_with_short_tokens(repo, q):
    repo.search(PlaceQuery(q=q))
    assert repo.last_search_mode == "like"
    assert repo.search(PlaceQuery(q="촉석루 OR 존재안함")).total == 0


def test_query_input_caps():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        PlaceQuery(q="가" * 201)
    with pytest.raises(ValidationError):
        PlaceQuery(near=(35.1, 128.1), radius=0)


def test_like_search_matches_menu(repo):
    # "육전" (2 chars -> LIKE path) appears only in 하연옥's menu column.
    page = repo.search(PlaceQuery(q="육전"))
    assert repo.last_search_mode == "like"
    assert [i.title for i in page.items] == ["하연옥 하대점"]
