"""Detection of classical yogas and doshas.

Each detector returns a list of findings: ``{"name", "category", "present", "strength",
"planets", "description", "conditions"}``. ``description`` states only *what was detected*;
interpretation text comes from the knowledge base (see ``app.interpret``).
"""
from __future__ import annotations

from itertools import combinations

from .chart import Chart
from .constants import (DUSTHANAS, KENDRAS, OWN_SIGNS, PLANETS, SEVEN_PLANETS, SIGN_LORDS,
                        TRIKONAS)
from .dignity import dignity, house_from


def _finding(name, category, planets, description, conditions=None, strength="normal"):
    return {"name": name, "category": category, "planets": sorted(set(planets)),
            "description": description, "conditions": conditions or [], "strength": strength}


def _strong(chart: Chart, p: str) -> bool:
    return dignity(p, chart.longitudes[p]) in ("exalted", "moolatrikona", "own sign")


# --- Pancha Mahapurusha -------------------------------------------------------------------
_MAHAPURUSHA = {"Mars": "Ruchaka", "Mercury": "Bhadra", "Jupiter": "Hamsa",
                "Venus": "Malavya", "Saturn": "Sasa"}


def mahapurusha(chart: Chart) -> list[dict]:
    out = []
    for p, name in _MAHAPURUSHA.items():
        if chart.house_of(p) in KENDRAS and _strong(chart, p):
            out.append(_finding(f"{name} Yoga", "Pancha Mahapurusha", [p],
                                f"{p} is {dignity(p, chart.longitudes[p])} in house {chart.house_of(p)} (a kendra).",
                                ["kendra from lagna", "own/exalted/moolatrikona"]))
    return out


# --- Moon-based yogas ---------------------------------------------------------------------
def moon_yogas(chart: Chart) -> list[dict]:
    out = []
    moon = chart.signs["Moon"]
    if chart.in_kendra("Jupiter", moon):
        out.append(_finding("Gajakesari Yoga", "Lunar", ["Moon", "Jupiter"],
                            f"Jupiter is in house {house_from(moon, chart.signs['Jupiter'])} from the Moon.",
                            ["Jupiter in kendra from Moon"]))
    if chart.conjunct("Moon", "Mars"):
        out.append(_finding("Chandra-Mangala Yoga", "Lunar", ["Moon", "Mars"],
                            "Moon and Mars occupy the same sign.", ["Moon conjunct Mars"]))

    others = [p for p in SEVEN_PLANETS if p not in ("Sun", "Moon")]
    second = [p for p in others if house_from(moon, chart.signs[p]) == 2]
    twelfth = [p for p in others if house_from(moon, chart.signs[p]) == 12]
    if second and twelfth:
        out.append(_finding("Durudhara Yoga", "Lunar", ["Moon", *second, *twelfth],
                            f"Planets on both sides of the Moon: 2nd {second}, 12th {twelfth}."))
    elif second:
        out.append(_finding("Sunapha Yoga", "Lunar", ["Moon", *second], f"{second} in 2nd from Moon."))
    elif twelfth:
        out.append(_finding("Anapha Yoga", "Lunar", ["Moon", *twelfth], f"{twelfth} in 12th from Moon."))
    else:
        cancelled = [p for p in SEVEN_PLANETS if p != "Moon" and chart.in_kendra(p, moon)] or \
                    [p for p in SEVEN_PLANETS if p != "Moon" and chart.house_of(p) in KENDRAS]
        out.append(_finding("Kemadruma Yoga", "Dosha", ["Moon"],
                            "No planets (excluding Sun and nodes) in the 2nd or 12th from the Moon."
                            + (f" Cancelled (bhanga) by {cancelled} in kendra." if cancelled else ""),
                            strength="cancelled" if cancelled else "normal"))

    benefics_678 = [p for p in ("Mercury", "Jupiter", "Venus")
                    if house_from(moon, chart.signs[p]) in (6, 7, 8)]
    if len(benefics_678) >= 2:
        out.append(_finding("Adhi Yoga", "Lunar", ["Moon", *benefics_678],
                            f"Benefics {benefics_678} in the 6th/7th/8th from the Moon.",
                            strength="strong" if len(benefics_678) == 3 else "normal"))
    if house_from(chart.signs["Jupiter"], moon) in (6, 8, 12):
        out.append(_finding("Shakata Yoga", "Dosha", ["Moon", "Jupiter"],
                            f"Moon is in house {house_from(chart.signs['Jupiter'], moon)} from Jupiter.",
                            strength="cancelled" if chart.house_of("Moon") in KENDRAS else "normal"))
    return out


# --- Solar yogas --------------------------------------------------------------------------
def solar_yogas(chart: Chart) -> list[dict]:
    out = []
    sun = chart.signs["Sun"]
    if chart.conjunct("Sun", "Mercury"):
        out.append(_finding("Budhaditya Yoga", "Solar", ["Sun", "Mercury"],
                            "Sun and Mercury occupy the same sign."))
    others = [p for p in ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")]
    second = [p for p in others if house_from(sun, chart.signs[p]) == 2]
    twelfth = [p for p in others if house_from(sun, chart.signs[p]) == 12]
    if second and twelfth:
        out.append(_finding("Ubhayachari Yoga", "Solar", ["Sun", *second, *twelfth],
                            "Planets on both sides of the Sun."))
    elif second:
        out.append(_finding("Vesi Yoga", "Solar", ["Sun", *second], f"{second} in 2nd from Sun."))
    elif twelfth:
        out.append(_finding("Vasi Yoga", "Solar", ["Sun", *twelfth], f"{twelfth} in 12th from Sun."))
    return out


# --- Lordship yogas -----------------------------------------------------------------------
def _relation_text(chart: Chart, a: str, b: str) -> list[str]:
    return chart.related(a, b)


def raja_yogas(chart: Chart) -> list[dict]:
    """Kendra lord related to a trikona lord (conjunction, mutual aspect or exchange)."""
    out, seen = [], set()
    for k in KENDRAS:
        for t in TRIKONAS:
            a, b = chart.lord_of(k), chart.lord_of(t)
            if k == t == 1:
                continue
            if a == b:
                # yogakaraka: one planet owns both a kendra and a trikona (other than lagna)
                if k != 1 and t != 1 and a not in seen:
                    seen.add(a)
                    out.append(_finding("Yogakaraka", "Raja Yoga", [a],
                                        f"{a} rules both house {k} (kendra) and house {t} (trikona).",
                                        strength="strong"))
                continue
            kinds = _relation_text(chart, a, b)
            key = frozenset((a, b))
            if kinds and key not in seen:
                seen.add(key)
                out.append(_finding("Raja Yoga", "Raja Yoga", [a, b],
                                    f"Lord of {k} ({a}) and lord of {t} ({b}) are linked by {', '.join(kinds)}.",
                                    [f"{k}L-{t}L {kind}" for kind in kinds]))
    return out


def dhana_yogas(chart: Chart) -> list[dict]:
    wealth_houses = (1, 2, 5, 9, 11)
    out, seen = [], set()
    for h1, h2 in combinations(wealth_houses, 2):
        a, b = chart.lord_of(h1), chart.lord_of(h2)
        if a == b or frozenset((a, b)) in seen:
            continue
        kinds = chart.related(a, b)
        if kinds:
            seen.add(frozenset((a, b)))
            out.append(_finding("Dhana Yoga", "Dhana Yoga", [a, b],
                                f"Lord of {h1} ({a}) and lord of {h2} ({b}) are linked by {', '.join(kinds)}."))
    return out


def viparita_raja(chart: Chart) -> list[dict]:
    names = {6: "Harsha", 8: "Sarala", 12: "Vimala"}
    out = []
    for h, name in names.items():
        lord = chart.lord_of(h)
        if chart.house_of(lord) in DUSTHANAS:
            out.append(_finding(f"{name} Yoga (Viparita Raja)", "Viparita Raja Yoga", [lord],
                                f"Lord of {h} ({lord}) is placed in house {chart.house_of(lord)} (a dusthana)."))
    return out


def parivartana(chart: Chart) -> list[dict]:
    out = []
    for a, b in combinations(SEVEN_PLANETS, 2):
        if chart.signs[a] in OWN_SIGNS[b] and chart.signs[b] in OWN_SIGNS[a]:
            ha, hb = chart.house_of(a), chart.house_of(b)
            kind = "Dainya" if 6 in (ha, hb) or 8 in (ha, hb) or 12 in (ha, hb) else \
                   "Khala" if 3 in (ha, hb) else "Maha"
            out.append(_finding(f"{kind} Parivartana Yoga", "Exchange", [a, b],
                                f"{a} (in house {ha}) and {b} (in house {hb}) exchange signs."))
    return out


def neecha_bhanga(chart: Chart) -> list[dict]:
    from .constants import DEBILITATION, EXALTATION
    out = []
    moon = chart.signs["Moon"]
    for p in SEVEN_PLANETS:
        if DEBILITATION[p][0] != chart.signs[p]:
            continue
        deb_sign = chart.signs[p]
        dispositor = SIGN_LORDS[deb_sign]
        exalt_lord = next(q for q in SEVEN_PLANETS if EXALTATION[q][0] == deb_sign) \
            if any(EXALTATION[q][0] == deb_sign for q in SEVEN_PLANETS) else None
        reasons = []
        for who, label in ((dispositor, "dispositor"), (exalt_lord, "lord of exaltation in that sign")):
            if who and (chart.house_of(who) in KENDRAS or chart.in_kendra(who, moon)):
                reasons.append(f"{label} {who} in kendra from lagna/Moon")
        if chart.house_of(p) in KENDRAS:
            reasons.append("debilitated planet itself in a kendra")
        out.append(_finding(f"Debilitated {p}" + (" with Neecha Bhanga" if reasons else ""),
                            "Neecha Bhanga Raja Yoga" if reasons else "Debility", [p],
                            f"{p} is debilitated in house {chart.house_of(p)}."
                            + (f" Cancellation: {'; '.join(reasons)}." if reasons else ""),
                            reasons))
    return out


def misc_yogas(chart: Chart) -> list[dict]:
    out = []
    tenth = chart.occupants(10)
    tenth_moon = [p for p in PLANETS if house_from(chart.signs["Moon"], chart.signs[p]) == 10]
    amala = [p for p in set(tenth) | set(tenth_moon) if p in ("Jupiter", "Venus", "Mercury")]
    if amala:
        out.append(_finding("Amala Yoga", "Misc", amala, f"Benefic {amala} in the 10th from lagna or Moon."))
    l9 = chart.lord_of(9)
    if _strong(chart, l9) and chart.house_of(l9) in set(KENDRAS) | set(TRIKONAS):
        out.append(_finding("Lakshmi Yoga", "Dhana Yoga", [l9, chart.lord_of(1)],
                            f"9th lord {l9} is strong in house {chart.house_of(l9)}."))
    benefic_places = set(KENDRAS) | set(TRIKONAS) | {2}
    if all(chart.house_of(p) in benefic_places for p in ("Jupiter", "Venus", "Mercury")) and _strong(chart, "Jupiter"):
        out.append(_finding("Saraswati Yoga", "Misc", ["Jupiter", "Venus", "Mercury"],
                            "Jupiter, Venus and Mercury in kendra/trikona/2nd with Jupiter strong."))
    if chart.conjunct("Jupiter", "Rahu") or chart.conjunct("Jupiter", "Ketu"):
        node = "Rahu" if chart.conjunct("Jupiter", "Rahu") else "Ketu"
        out.append(_finding("Guru Chandala Yoga", "Dosha", ["Jupiter", node],
                            f"Jupiter conjunct {node}."))
    for lum in ("Sun", "Moon"):
        for node in ("Rahu", "Ketu"):
            if chart.conjunct(lum, node):
                out.append(_finding("Grahan Yoga", "Dosha", [lum, node], f"{lum} conjunct {node}."))
    return out


# --- Doshas -------------------------------------------------------------------------------
def mangal_dosha(chart: Chart) -> dict:
    houses = (1, 2, 4, 7, 8, 12)
    refs = {"Lagna": chart.lagna_sign, "Moon": chart.signs["Moon"], "Venus": chart.signs["Venus"]}
    hits = {ref: house_from(s, chart.signs["Mars"]) for ref, s in refs.items()
            if house_from(s, chart.signs["Mars"]) in houses}
    mitigations = []
    mars_dignity = dignity("Mars", chart.longitudes["Mars"])
    if mars_dignity in ("own sign", "exalted", "moolatrikona"):
        mitigations.append(f"Mars is {mars_dignity}")
    if chart.conjunct("Mars", "Jupiter") or chart.aspects("Jupiter", "Mars"):
        mitigations.append("Mars is conjunct or aspected by Jupiter")
    return {"name": "Mangal Dosha", "present": bool(hits), "from": hits,
            "mitigations": mitigations,
            "severity": "none" if not hits else ("mild" if mitigations or len(hits) == 1 else "strong")}


def kaal_sarp(chart: Chart) -> dict:
    rahu = chart.longitudes["Rahu"]
    arcs = [(chart.longitudes[p] - rahu) % 360 for p in SEVEN_PLANETS]
    one_side = all(a < 180 for a in arcs) or all(a > 180 for a in arcs)
    names = ["Anant", "Kulik", "Vasuki", "Shankhpal", "Padma", "Mahapadma",
             "Takshak", "Karkotak", "Shankhachur", "Ghatak", "Vishdhar", "Sheshnag"]
    return {"name": "Kaal Sarp Dosha", "present": one_side,
            "type": names[chart.house_of("Rahu") - 1] if one_side else None,
            "rahu_house": chart.house_of("Rahu")}


def all_yogas(chart: Chart) -> dict:
    yogas = (mahapurusha(chart) + raja_yogas(chart) + dhana_yogas(chart) + viparita_raja(chart)
             + parivartana(chart) + moon_yogas(chart) + solar_yogas(chart) + neecha_bhanga(chart)
             + misc_yogas(chart))
    return {"yogas": yogas, "doshas": [mangal_dosha(chart), kaal_sarp(chart)]}
