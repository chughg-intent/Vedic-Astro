from app import geo


def test_offline_place_search_from_sqlite():
    (jaipur,) = geo.search_places("Jaipur", None, "India", online=False)[:1]
    assert jaipur.country_code == "IN" and jaipur.timezone == "Asia/Kolkata" and abs(jaipur.latitude - 26.92) < 0.1
    assert geo.search_places("Hapur", None, "India", online=False)[0].display_name.startswith("H")  # accent-insensitive
    springfield = geo.search_places("Springfield", "Illinois", "USA", online=False)
    assert springfield and springfield[0].timezone == "America/Chicago"
    assert geo.search_places("Nowhereville", None, "India", online=False) == []


def test_offline_search_used_when_nominatim_fails(monkeypatch):
    def down(*a, **k):
        raise OSError("blocked")
    monkeypatch.setattr(geo, "_nominatim_search", down)
    assert geo.search_places("Jaipur", None, "India")[0].source == "geonames"
