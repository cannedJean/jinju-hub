from app.services.kma_grid import latlng_to_grid


def test_grid_seoul():
    assert latlng_to_grid(37.5729, 126.9794) == (60, 127)


def test_grid_daejeon():
    assert latlng_to_grid(36.3504, 127.3845) == (67, 100)


def test_grid_jinju():
    assert latlng_to_grid(35.18, 128.108) == (81, 75)
