"""Extracts the chart factors that classical texts use to judge each area of life.

These structured "facts" are the bridge between the calculation engine and the
interpretation layer: the report generator looks up rules from the knowledge base
(built from the reference books) that match these facts, so every statement in the
report can be traced back to a concrete chart factor.
"""
from __future__ import annotations

from ..engine.chart import Chart
from ..engine.constants import HOUSE_SIGNIFICATIONS, SIGN_LORDS, SIGNS
from ..engine.dignity import dignity, house_from, is_combust
from ..engine.vargas import varga_sign

LIFE_AREAS: dict[str, dict] = {
    "physical": {"title": "Physical Structure & Appearance", "houses": [1], "karakas": ["Sun", "Moon"],
                 "vargas": [1, 9], "extra": "lagna"},
    "health": {"title": "Health & Vitality", "houses": [1, 6, 8], "karakas": ["Sun", "Moon"],
               "vargas": [1, 30]},
    "mind": {"title": "Mind, Temperament & Character", "houses": [1, 4, 5], "karakas": ["Moon", "Mercury"],
             "vargas": [1, 9]},
    "education": {"title": "Education & Learning", "houses": [2, 4, 5, 9], "karakas": ["Mercury", "Jupiter"],
                  "vargas": [24]},
    "career": {"title": "Career & Profession", "houses": [10, 6, 2, 11], "karakas": ["Sun", "Saturn", "Mercury"],
               "vargas": [10]},
    "wealth": {"title": "Money & Wealth", "houses": [2, 11, 5, 9], "karakas": ["Jupiter", "Venus"],
               "vargas": [2], "sav": True},
    "marriage": {"title": "Marriage & Relationships", "houses": [7, 2, 8, 12], "karakas": ["Venus", "Jupiter"],
                 "vargas": [9], "dosha": "Mangal Dosha"},
    "children": {"title": "Children & Progeny", "houses": [5], "karakas": ["Jupiter"], "vargas": [7]},
    "family": {"title": "Parents & Family", "houses": [4, 9, 2, 3], "karakas": ["Moon", "Sun", "Mars"],
               "vargas": [12]},
    "property": {"title": "Home, Property & Vehicles", "houses": [4], "karakas": ["Mars", "Venus"],
                 "vargas": [4, 16]},
    "travel": {"title": "Travel & Foreign Lands", "houses": [3, 9, 12], "karakas": ["Rahu"], "vargas": [1]},
    "spirituality": {"title": "Spirituality & Dharma", "houses": [9, 12, 5], "karakas": ["Jupiter", "Ketu"],
                     "vargas": [20]},
}


def planet_fact(chart: Chart, p: str) -> dict:
    b = chart.bodies[p]
    return {
        "planet": p, "house": chart.house_of(p), "sign": SIGNS[chart.signs[p]],
        "dignity": dignity(p, b.longitude, chart.signs),
        "retrograde": b.retrograde if p not in ("Rahu", "Ketu") else True,
        "combust": is_combust(p, b.longitude, chart.longitudes["Sun"], b.retrograde),
        "conjunctions": [q for q in chart.signs if q != p and chart.signs[q] == chart.signs[p]],
        "aspected_by": [q for q in chart.signs if q != p and chart.aspects(q, p)],
        "rules": chart.houses_ruled(p),
        "navamsa_sign": SIGNS[varga_sign(b.longitude, 9)],
    }


def house_fact(chart: Chart, h: int) -> dict:
    lord = chart.lord_of(h)
    return {
        "house": h, "signifies": HOUSE_SIGNIFICATIONS[h], "sign": SIGNS[chart.sign_of_house(h)],
        "occupants": chart.occupants(h), "aspected_by": chart.aspects_on_house(h),
        "lord": planet_fact(chart, lord),
    }


def varga_fact(chart: Chart, division: int, focus_house: int | None) -> dict:
    lagna = varga_sign(chart.lagna, division)
    placements = {p: varga_sign(l, division) for p, l in chart.longitudes.items()}
    fact = {"division": division, "lagna": SIGNS[lagna],
            "placements": {p: {"sign": SIGNS[s], "house": house_from(lagna, s)} for p, s in placements.items()}}
    if focus_house:
        sign = (lagna + focus_house - 1) % 12
        lord = SIGN_LORDS[sign]
        fact["focus_house"] = {"house": focus_house, "sign": SIGNS[sign], "lord": lord,
                               "lord_house": house_from(lagna, placements[lord]),
                               "occupants": [p for p, s in placements.items() if s == sign]}
    return fact


def extract(chart: Chart, yogas: dict, dashas: list[dict], av: dict) -> dict:
    out = {}
    for key, spec in LIFE_AREAS.items():
        primary = spec["houses"][0]
        lords = {chart.lord_of(h) for h in spec["houses"]}
        involved = lords | set(spec["karakas"])
        area = {
            "title": spec["title"],
            "houses": [house_fact(chart, h) for h in spec["houses"]],
            "karakas": [planet_fact(chart, p) for p in spec["karakas"]],
            "vargas": [varga_fact(chart, d, primary if d != 1 else None) for d in spec["vargas"]],
            "yogas": [y for y in yogas["yogas"] if involved & set(y["planets"])],
            "dasha_periods": [
                {"lord": d["lord"], "start": d["start"].date().isoformat(), "end": d["end"].date().isoformat()}
                for d in dashas if d["lord"] in involved
            ],
        }
        if spec.get("sav"):
            area["sav"] = {h: av["sav_by_house"][h - 1] for h in spec["houses"]}
        if spec.get("dosha"):
            area["doshas"] = [d for d in yogas["doshas"] if d["name"] == spec["dosha"]]
        if spec.get("extra") == "lagna":
            area["lagna"] = {"sign": SIGNS[chart.lagna_sign], "degree": chart.lagna % 30,
                             "moon_sign": SIGNS[chart.signs["Moon"]]}
        out[key] = area
    return out
