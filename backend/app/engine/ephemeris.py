"""Thin wrapper around Swiss Ephemeris for sidereal positions."""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import swisseph as swe

AYANAMSAS = {
    "lahiri": swe.SIDM_LAHIRI,
    "raman": swe.SIDM_RAMAN,
    "krishnamurti": swe.SIDM_KRISHNAMURTI,
    "true_chitra": swe.SIDM_TRUE_CITRA,
}

_SWE_IDS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY,
    "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN,
}

_EPHE_PATH = os.environ.get("SE_EPHE_PATH")
if _EPHE_PATH:
    swe.set_ephe_path(_EPHE_PATH)
# Without .se1 data files, fall back to the built-in Moshier ephemeris (~1" accuracy).
_EPH_FLAG = swe.FLG_SWIEPH if _EPHE_PATH else swe.FLG_MOSEPH


@dataclass
class Body:
    name: str
    longitude: float  # sidereal, 0-360
    latitude: float
    speed: float  # deg/day
    retrograde: bool


def julian_day(dt_utc: datetime) -> float:
    dt = dt_utc.astimezone(timezone.utc)
    hour = dt.hour + dt.minute / 60 + dt.second / 3600 + dt.microsecond / 3.6e9
    return swe.julday(dt.year, dt.month, dt.day, hour, swe.GREG_CAL)


def _set_ayanamsa(ayanamsa: str) -> None:
    swe.set_sid_mode(AYANAMSAS[ayanamsa], 0, 0)


def ayanamsa_value(jd: float, ayanamsa: str = "lahiri") -> float:
    _set_ayanamsa(ayanamsa)
    return swe.get_ayanamsa_ut(jd)


def planet_positions(jd: float, ayanamsa: str = "lahiri", node: str = "mean") -> dict[str, Body]:
    _set_ayanamsa(ayanamsa)
    flags = _EPH_FLAG | swe.FLG_SIDEREAL | swe.FLG_SPEED
    bodies: dict[str, Body] = {}
    for name, pid in _SWE_IDS.items():
        (lon, lat, _dist, speed, *_), _ = swe.calc_ut(jd, pid, flags)
        bodies[name] = Body(name, lon % 360, lat, speed, speed < 0)
    node_id = swe.TRUE_NODE if node == "true" else swe.MEAN_NODE
    (lon, lat, _d, speed, *_), _ = swe.calc_ut(jd, node_id, flags)
    bodies["Rahu"] = Body("Rahu", lon % 360, lat, speed, True)
    bodies["Ketu"] = Body("Ketu", (lon + 180) % 360, -lat, speed, True)
    return bodies


def ascendant(jd: float, lat: float, lon: float, ayanamsa: str = "lahiri") -> float:
    _set_ayanamsa(ayanamsa)
    _cusps, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    return ascmc[0] % 360


def tropical_declinations(jd: float) -> dict[str, float]:
    """Declination of the seven planets (used by Shadbala ayana bala)."""
    out = {}
    for name, pid in _SWE_IDS.items():
        (_ra, decl, *_), _ = swe.calc_ut(jd, pid, _EPH_FLAG | swe.FLG_EQUATORIAL)
        out[name] = decl
    return out


def _next_event(jd: float, rsmi: int, geopos) -> float:
    _res, tret = swe.rise_trans(jd, swe.SUN, rsmi, geopos, 0, 0, _EPH_FLAG)
    return tret[0]


def sunrise_sunset(jd: float, lat: float, lon: float) -> tuple[float, float, float]:
    """(sunrise, sunset, next sunrise) bracketing ``jd``: the latest sunrise at or before it."""
    geopos = (lon, lat, 0.0)
    rise = _next_event(jd - 1.0, swe.CALC_RISE, geopos)
    nxt = _next_event(rise + 0.01, swe.CALC_RISE, geopos)
    while nxt <= jd:
        rise, nxt = nxt, _next_event(nxt + 0.01, swe.CALC_RISE, geopos)
    sset = _next_event(rise, swe.CALC_SET, geopos)
    return rise, sset, nxt


def midheaven(jd: float, lat: float, lon: float, ayanamsa: str = "lahiri") -> float:
    _set_ayanamsa(ayanamsa)
    _cusps, ascmc = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)
    return ascmc[1] % 360


def heliocentric_longitudes(jd: float) -> dict[str, float]:
    """Tropical heliocentric longitudes of Mars..Saturn (used for cheshta bala)."""
    out = {}
    for name in ("Mars", "Mercury", "Jupiter", "Venus", "Saturn"):
        (lon, *_), _ = swe.calc_ut(jd, _SWE_IDS[name], _EPH_FLAG | swe.FLG_HELCTR)
        out[name] = lon % 360
    return out


def tropical_longitudes(jd: float) -> dict[str, float]:
    out = {}
    for name, pid in _SWE_IDS.items():
        (lon, *_), _ = swe.calc_ut(jd, pid, _EPH_FLAG)
        out[name] = lon % 360
    return out
