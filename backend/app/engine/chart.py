"""Assembles a full natal chart from birth data."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from . import ephemeris
from .constants import (ABBR, KENDRAS, NATURAL_BENEFICS, PLANETS, SIGN_LORDS, SIGNS,
                        SIGNS_SANSKRIT, SPECIAL_ASPECTS)
from .dasha import nakshatra
from .dignity import dignity, house_from, is_combust
from .vargas import VARGA_NAMES, fmt_dms, varga_sign


@dataclass
class Chart:
    birth_utc: datetime
    jd: float
    lat: float
    lon: float
    ayanamsa: str
    ayanamsa_value: float
    lagna: float
    bodies: dict[str, ephemeris.Body]
    longitudes: dict[str, float] = field(init=False)
    signs: dict[str, int] = field(init=False)

    def __post_init__(self):
        self.longitudes = {n: b.longitude for n, b in self.bodies.items()}
        self.signs = {n: int(l // 30) for n, l in self.longitudes.items()}

    # --- house helpers (whole-sign houses) --------------------------------------------
    @property
    def lagna_sign(self) -> int:
        return int(self.lagna // 30)

    def house_of(self, planet: str) -> int:
        return house_from(self.lagna_sign, self.signs[planet])

    def sign_of_house(self, house: int) -> int:
        return (self.lagna_sign + house - 1) % 12

    def lord_of(self, house: int) -> str:
        return SIGN_LORDS[self.sign_of_house(house)]

    def occupants(self, house: int) -> list[str]:
        return [p for p in PLANETS if self.house_of(p) == house]

    def houses_ruled(self, planet: str) -> list[int]:
        return [h for h in range(1, 13) if self.lord_of(h) == planet]

    def aspected_houses(self, planet: str) -> list[int]:
        """Houses receiving a full graha drishti from ``planet`` (whole-sign)."""
        h = self.house_of(planet)
        offsets = (7,) + SPECIAL_ASPECTS.get(planet, ())
        return sorted({(h + o - 2) % 12 + 1 for o in offsets})

    def aspects_on_house(self, house: int) -> list[str]:
        return [p for p in PLANETS if house in self.aspected_houses(p)]

    def is_benefic(self, planet: str) -> bool:
        """Functional nature by natural rules: waxing Moon and unafflicted Mercury are benefic."""
        if planet in NATURAL_BENEFICS:
            return True
        if planet == "Moon":
            return self.moon_waxing
        if planet == "Mercury":
            mates = [p for p in PLANETS if p != "Mercury" and self.signs[p] == self.signs["Mercury"]]
            return not any(p in ("Sun", "Mars", "Saturn", "Rahu", "Ketu") for p in mates)
        return False

    @property
    def moon_waxing(self) -> bool:
        return (self.longitudes["Moon"] - self.longitudes["Sun"]) % 360 < 180

    def in_kendra(self, planet: str, from_sign: int | None = None) -> bool:
        base = self.lagna_sign if from_sign is None else from_sign
        return house_from(base, self.signs[planet]) in KENDRAS

    def conjunct(self, a: str, b: str) -> bool:
        return self.signs[a] == self.signs[b]

    def aspects(self, a: str, b: str) -> bool:
        """Planet ``a`` casts a full aspect on planet ``b``."""
        return self.house_of(b) in self.aspected_houses(a)

    def related(self, a: str, b: str) -> list[str]:
        """Kinds of Parashari relationship between two planets."""
        kinds = []
        if a == b:
            return kinds
        if self.conjunct(a, b):
            kinds.append("conjunction")
        if self.aspects(a, b) and self.aspects(b, a):
            kinds.append("mutual aspect")
        if self.signs[a] in _owned(b) and self.signs[b] in _owned(a):
            kinds.append("exchange")
        return kinds


def _owned(planet: str) -> list[int]:
    return [s for s in range(12) if SIGN_LORDS[s] == planet]


def build_chart(birth_utc: datetime, lat: float, lon: float,
                ayanamsa: str = "lahiri", node: str = "mean") -> Chart:
    jd = ephemeris.julian_day(birth_utc)
    return Chart(
        birth_utc=birth_utc, jd=jd, lat=lat, lon=lon, ayanamsa=ayanamsa,
        ayanamsa_value=ephemeris.ayanamsa_value(jd, ayanamsa),
        lagna=ephemeris.ascendant(jd, lat, lon, ayanamsa),
        bodies=ephemeris.planet_positions(jd, ayanamsa, node),
    )


def sign_label(sign: int) -> dict:
    return {"index": sign, "name": SIGNS[sign], "sanskrit": SIGNS_SANSKRIT[sign], "lord": SIGN_LORDS[sign]}


def planet_table(chart: Chart) -> list[dict]:
    rows = []
    lagna_nk = nakshatra(chart.lagna)
    rows.append({
        "name": "Ascendant", "abbr": ABBR["Ascendant"], "longitude": chart.lagna,
        "sign": sign_label(chart.lagna_sign), "degree": fmt_dms(chart.lagna % 30),
        "house": 1, "nakshatra": _nk(lagna_nk), "retrograde": False, "combust": False,
        "dignity": None, "rules": [], "navamsa_sign": varga_sign(chart.lagna, 9),
    })
    sun = chart.longitudes["Sun"]
    for p in PLANETS:
        b = chart.bodies[p]
        rows.append({
            "name": p, "abbr": ABBR[p], "longitude": b.longitude,
            "sign": sign_label(chart.signs[p]), "degree": fmt_dms(b.longitude % 30),
            "house": chart.house_of(p), "nakshatra": _nk(nakshatra(b.longitude)),
            "retrograde": b.retrograde if p not in ("Rahu", "Ketu") else True,
            "combust": is_combust(p, b.longitude, sun, b.retrograde),
            "dignity": dignity(p, b.longitude, chart.signs),
            "rules": chart.houses_ruled(p), "speed": b.speed,
            "navamsa_sign": varga_sign(b.longitude, 9),
            "aspects_houses": chart.aspected_houses(p),
        })
    return rows


def _nk(nk: dict) -> dict:
    return {k: nk[k] for k in ("index", "name", "pada", "lord")}


def house_table(chart: Chart) -> list[dict]:
    return [{
        "house": h, "sign": sign_label(chart.sign_of_house(h)), "lord": chart.lord_of(h),
        "lord_in_house": chart.house_of(chart.lord_of(h)),
        "occupants": chart.occupants(h), "aspected_by": chart.aspects_on_house(h),
    } for h in range(1, 13)]


def divisional(chart: Chart, division: int) -> dict:
    lagna = varga_sign(chart.lagna, division)
    placements = {p: varga_sign(l, division) for p, l in chart.longitudes.items()}
    return {
        "division": division, "name": VARGA_NAMES[division],
        "lagna_sign": lagna,
        "placements": placements,
        "houses": {p: house_from(lagna, s) for p, s in placements.items()},
    }


def vargottama(chart: Chart) -> list[str]:
    return [p for p in PLANETS if varga_sign(chart.longitudes[p], 9) == chart.signs[p]]

