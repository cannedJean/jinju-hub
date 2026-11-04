from jinju_pipeline.region import load_region


def test_region_loads_and_contains(repo_root):
    r = load_region(repo_root / "config/region.yaml")
    assert (r.regn_cd, r.signgu_cd) == ("48", "170")
    assert r.contains(35.1925, 128.0845)  # 진주성
    assert r.contains(35.04, 128.0)  # margin 0.02 이내
    assert not r.contains(36.35, 127.38)  # 대전
