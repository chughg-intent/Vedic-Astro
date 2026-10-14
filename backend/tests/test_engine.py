from datetime import date, datetime, time, timezone

import pytest

from app import geo
from app.engine import dasha
from app.engine.ashtakavarga import BAV_TOTALS, ashtakavarga
from app.engine.chart import build_chart
from app.engine.dignity import dignity
from app.engine.shadbala import drishti_value, shadbala
from app.engine.vargas import varga_sign
from app.engine.yogas import all_yogas

J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def chart():
    return build_chart(datetime(1990, 5, 15, 9, 0, tzinfo=timezone.utc), 28.65195, 77.23149)


def test_lahiri_ayanamsa_at_j2000():
    from app.engine.ephemeris import ayanamsa_value, julian_day
    assert ayanamsa_value(julian_day(J2000)) == pytest.approx(23.857, abs=0.01)


def test_sun_sidereal_at_j2000():
    from app.engine.ephemeris import julian_day, planet_positions
    sun = planet_positions(julian_day(J2000))["Sun"]
    assert sun.longitude == pytest.approx(256.52, abs=0.05)  # 16°31' Sagittarius


def test_rahu_ketu_opposite(chart):
    assert (chart.longitudes["Rahu"] - chart.longitudes["Ketu"]) % 360 == pytest.approx(180)


@pytest.mark.parametrize("lon,div,expected", [
    (0.0, 9, 0),        # 0° Aries -> Aries navamsa
    (29.9, 9, 8),       # end of Aries -> Sagittarius
    (30.0, 9, 9),       # 0° Taurus -> Capricorn
    (95.0, 9, 4),       # 5° Cancer -> 2nd pada Leo
    (35.0, 10, 10),     # 5° Taurus (even): counted from the 9th (Capricorn), 2nd part -> Aquarius
    (10.0, 2, 4),       # first half of odd sign -> Leo
    (40.0, 2, 3),       # first half of even sign -> Cancer
    (12.0, 3, 4),       # second decanate of Aries -> Leo
    (2.0, 30, 0),       # 2° Aries -> Mars trimsamsa (Aries)
    (33.0, 30, 1),      # 3° Taurus -> Venus trimsamsa (Taurus)
])
def test_varga_signs(lon, div, expected):
    assert varga_sign(lon, div) == expected


def test_dignity_labels():
    assert dignity("Sun", 10.0) == "exalted"
    assert dignity("Sun", 190.0) == "debilitated"
    assert dignity("Sun", 125.0) == "moolatrikona"
    assert dignity("Sun", 145.0) == "own sign"
    assert dignity("Moon", 31.0) == "exalted"


def test_nakshatra_boundaries():
    assert dasha.nakshatra(0)["name"] == "Ashwini"
    assert dasha.nakshatra(13.34)["name"] == "Bharani"
    assert dasha.nakshatra(359.9)["name"] == "Revati"
    assert dasha.nakshatra(359.9)["pada"] == 4


def test_vimshottari_spans_120_years(chart):
    periods = dasha.vimshottari(chart.longitudes["Moon"], chart.birth_utc, depth=2)
    total_days = (periods[-1]["end"] - periods[0]["start"]).days
    assert total_days == pytest.approx(120 * 365.2425, abs=1)
    for p in periods:
        assert p["sub"][0]["start"] == p["start"]
        assert p["sub"][-1]["end"] == p["end"]
    assert periods[0]["lord"] == dasha.nakshatra(chart.longitudes["Moon"])["lord"]


def test_ashtakavarga_totals(chart):
    av = ashtakavarga(chart)
    for p, total in BAV_TOTALS.items():
        assert sum(av["bav"][p]) == total
    assert av["total"] == 337


def test_shadbala_reasonable(chart):
    sb = shadbala(chart)["planets"]
    for p, row in sb.items():
        assert 2 < row["total_rupas"] < 15, p


def test_drishti_full_on_seventh():
    assert drishti_value("Sun", 180) == 60
    assert drishti_value("Saturn", 75) == 60
    assert drishti_value("Sun", 10) == 0


def test_yogas_detect_malavya(chart):
    names = [y["name"] for y in all_yogas(chart)["yogas"]]
    assert "Malavya Yoga" in names  # Venus exalted in the 7th for this chart


def test_local_to_utc_ist():
    utc, info = geo.local_to_utc(date(1990, 5, 15), time(14, 30), "Asia/Kolkata")
    assert utc == datetime(1990, 5, 15, 9, 0, tzinfo=timezone.utc)
    assert info["utc_offset_hours"] == 5.5


def test_local_to_utc_us_dst():
    utc, info = geo.local_to_utc(date(2020, 7, 1), time(12, 0), "America/New_York")
    assert info["dst"] and utc.hour == 16


def test_offline_place_search():
    hits = geo.search_places("Pune", "Maharashtra", "India", online=False)
    assert hits and hits[0].timezone == "Asia/Kolkata"
    hits = geo.search_places("Springfield", "Illinois", "USA", online=False)
    assert hits and hits[0].timezone == "America/Chicago"
