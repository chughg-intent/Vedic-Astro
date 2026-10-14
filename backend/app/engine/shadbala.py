"""Shadbala (six-fold planetary strength) after BPHS, in virupas (60 virupas = 1 rupa).

Implementation notes / deliberate simplifications:
* Dig bala uses the actual ascendant and midheaven longitudes.
* Abda and masa lords use the classical 360/30-day cycles counted from the Kali Yuga epoch.
* Cheshta bala for Mars..Saturn uses the angle between the planet's geocentric longitude and
  its seeghrochcha (Sun for outer planets, heliocentric planet for Mercury/Venus).
* Yuddha (planetary war) is applied for Mars..Saturn within 1 degree.
Results can differ by a few percent from other software; they are meant for relative ranking.
"""
from __future__ import annotations

from . import ephemeris
from .chart import Chart
from .constants import DEBILITATION, MOOLATRIKONA, OWN_SIGNS, SEVEN_PLANETS, SIGN_LORDS
from .dignity import angular_distance, compound_relation
from .vargas import varga_sign

NAISARGIKA = {"Sun": 60.0, "Moon": 51.43, "Venus": 42.86, "Jupiter": 34.29,
              "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57}
REQUIRED_RUPAS = {"Sun": 6.5, "Moon": 6.0, "Mars": 5.0, "Mercury": 7.0,
                  "Jupiter": 6.5, "Venus": 5.5, "Saturn": 5.0}
WEEKDAY_LORDS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
CHALDEAN = ["Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter", "Mars"]
KALI_EPOCH_JD = 588465.5  # 18 Feb 3102 BCE (Julian), start of Kali Yuga

_SAPTAVARGA = (1, 2, 3, 7, 9, 12, 30)
_REL_POINTS = {"great friend": 22.5, "friend": 15.0, "neutral": 7.5,
               "enemy": 3.75, "great enemy": 1.875}


def _weekday(jd: float) -> int:
    """0 = Sunday."""
    return int(jd + 1.5) % 7


# --- Sthana bala --------------------------------------------------------------------------
def uchcha(p: str, lon: float) -> float:
    s, d = DEBILITATION[p]
    return angular_distance(lon, s * 30 + d) / 3


def saptavargaja(p: str, chart: Chart) -> float:
    total = 0.0
    lon = chart.longitudes[p]
    for div in _SAPTAVARGA:
        sign = varga_sign(lon, div)
        if div == 1:
            mt = MOOLATRIKONA[p]
            if mt[0] == sign and mt[1] <= lon % 30 < mt[2]:
                total += 45
                continue
        if sign in OWN_SIGNS[p]:
            total += 30
            continue
        lord = SIGN_LORDS[sign]
        total += _REL_POINTS[compound_relation(p, lord, chart.signs)]
    return total


def ojayugma(p: str, chart: Chart) -> float:
    female = p in ("Moon", "Venus")
    total = 0.0
    for sign in (chart.signs[p], varga_sign(chart.longitudes[p], 9)):
        odd = sign % 2 == 0
        total += 15 if odd != female else 0
    return total


def kendradi(p: str, chart: Chart) -> float:
    h = chart.house_of(p)
    return 60.0 if h in (1, 4, 7, 10) else 30.0 if h in (2, 5, 8, 11) else 15.0


def drekkana(p: str, chart: Chart) -> float:
    dec = int((chart.longitudes[p] % 30) // 10)
    wanted = {"Sun": 0, "Mars": 0, "Jupiter": 0, "Mercury": 1, "Saturn": 1, "Moon": 2, "Venus": 2}[p]
    return 15.0 if dec == wanted else 0.0


# --- Dig bala -----------------------------------------------------------------------------
def dig(p: str, lon: float, asc: float, mc: float) -> float:
    strongest = {"Jupiter": asc, "Mercury": asc, "Sun": mc, "Mars": mc,
                 "Saturn": asc + 180, "Moon": mc + 180, "Venus": mc + 180}[p]
    return (180 - angular_distance(lon, strongest)) / 3


# --- Kala bala ----------------------------------------------------------------------------
def kala(chart: Chart) -> dict[str, dict[str, float]]:
    jd = chart.jd
    rise, sset, next_rise = ephemeris.sunrise_sunset(jd, chart.lat, chart.lon)
    is_day = rise <= jd < sset
    out = {p: {} for p in SEVEN_PLANETS}

    # Nathonnatha: distance from local apparent midnight approximated with local mean time.
    lmt_hours = ((jd + 0.5) % 1 * 24 + chart.lon / 15) % 24
    from_midnight = min(lmt_hours, 24 - lmt_hours)  # 0..12
    for p in SEVEN_PLANETS:
        if p == "Mercury":
            v = 60.0
        elif p in ("Sun", "Jupiter", "Venus"):
            v = from_midnight * 5
        else:
            v = 60 - from_midnight * 5
        out[p]["nathonnatha"] = v

    # Paksha
    elong = angular_distance(chart.longitudes["Moon"], chart.longitudes["Sun"])
    benefic_val = elong / 3
    for p in SEVEN_PLANETS:
        v = benefic_val if chart.is_benefic(p) else 60 - benefic_val
        out[p]["paksha"] = v * 2 if p == "Moon" else v

    # Tribhaga
    if is_day:
        third = int((jd - rise) / ((sset - rise) / 3))
        lord = ["Mercury", "Sun", "Saturn"][min(third, 2)]
    else:
        third = int((jd - sset) / ((next_rise - sset) / 3))
        lord = ["Moon", "Venus", "Mars"][min(third, 2)]
    for p in SEVEN_PLANETS:
        out[p]["tribhaga"] = 60.0 if p in (lord, "Jupiter") else 0.0

    # Abda / Masa / Vara / Hora
    vedic_day_jd = rise  # the Vedic day begins at sunrise
    ahargana = int(vedic_day_jd - KALI_EPOCH_JD)
    abda_lord = WEEKDAY_LORDS[_weekday(KALI_EPOCH_JD + (ahargana // 360) * 360)]
    masa_lord = WEEKDAY_LORDS[_weekday(KALI_EPOCH_JD + (ahargana // 30) * 30)]
    vara_lord = WEEKDAY_LORDS[_weekday(rise + 0.25)]  # sunrise is early in the civil day
    hora_idx = int((jd - rise) * 24)
    hora_lord = CHALDEAN[(CHALDEAN.index(vara_lord) + hora_idx) % 7]
    for p in SEVEN_PLANETS:
        out[p]["abda"] = 15.0 if p == abda_lord else 0.0
        out[p]["masa"] = 30.0 if p == masa_lord else 0.0
        out[p]["vara"] = 45.0 if p == vara_lord else 0.0
        out[p]["hora"] = 60.0 if p == hora_lord else 0.0

    # Ayana (declination-based)
    decl = ephemeris.tropical_declinations(jd)
    eps = 23.44
    for p in SEVEN_PLANETS:
        d = decl[p]
        if p in ("Moon", "Saturn"):
            v = (eps - d) / (2 * eps) * 60
        elif p == "Mercury":
            v = (eps + abs(d)) / (2 * eps) * 60
        else:
            v = (eps + d) / (2 * eps) * 60
        v = max(0.0, min(60.0, v))
        out[p]["ayana"] = v * 2 if p == "Sun" else v
    return out


# --- Cheshta bala -------------------------------------------------------------------------
def cheshta(chart: Chart, kala_parts: dict) -> dict[str, float]:
    trop = ephemeris.tropical_longitudes(chart.jd)
    helio = ephemeris.heliocentric_longitudes(chart.jd)
    out = {"Sun": kala_parts["Sun"]["ayana"] / 2, "Moon": kala_parts["Moon"]["paksha"] / 2}
    for p in ("Mars", "Jupiter", "Saturn"):
        out[p] = angular_distance(trop[p], trop["Sun"]) / 3
    for p in ("Mercury", "Venus"):
        out[p] = angular_distance(trop[p], helio[p]) / 3
    return out


# --- Drik bala ----------------------------------------------------------------------------
def drishti_value(aspecting: str, d: float) -> float:
    """Aspect strength (virupas) cast by ``aspecting`` on a point ``d`` degrees ahead."""
    d %= 360
    special = {"Saturn": ((60, 90), (270, 300)), "Jupiter": ((120, 150), (240, 270)),
               "Mars": ((90, 120), (210, 240))}
    for lo, hi in special.get(aspecting, ()):
        if lo <= d < hi:
            return 60.0
    if d < 30 or d >= 300:
        return 0.0
    if d < 60:
        return (d - 30) / 2
    if d < 90:
        return d - 60 + 15
    if d < 120:
        return (120 - d) / 2 + 30
    if d < 150:
        return 150 - d
    if d < 180:
        return (d - 150) * 2
    return (300 - d) / 2


def drik(chart: Chart) -> dict[str, float]:
    out = {}
    for target in SEVEN_PLANETS:
        total = 0.0
        for src in SEVEN_PLANETS:
            if src == target:
                continue
            v = drishti_value(src, chart.longitudes[target] - chart.longitudes[src])
            total += v if chart.is_benefic(src) else -v
        out[target] = total / 4
    return out


# --- Assembly -----------------------------------------------------------------------------
def shadbala(chart: Chart) -> dict:
    asc = chart.lagna
    mc = ephemeris.midheaven(chart.jd, chart.lat, chart.lon, chart.ayanamsa)
    kparts = kala(chart)
    chesh = cheshta(chart, kparts)
    drk = drik(chart)
    rows = {}
    for p in SEVEN_PLANETS:
        sthana = {"uchcha": uchcha(p, chart.longitudes[p]), "saptavargaja": saptavargaja(p, chart),
                  "ojayugma": ojayugma(p, chart), "kendradi": kendradi(p, chart),
                  "drekkana": drekkana(p, chart)}
        rows[p] = {
            "sthana": sum(sthana.values()), "sthana_parts": sthana,
            "dig": dig(p, chart.longitudes[p], asc, mc),
            "kala": sum(kparts[p].values()), "kala_parts": kparts[p],
            "cheshta": chesh[p], "naisargika": NAISARGIKA[p], "drik": drk[p],
        }
    _apply_yuddha(chart, rows)
    for p, r in rows.items():
        total = r["sthana"] + r["dig"] + r["kala"] + r["cheshta"] + r["naisargika"] + r["drik"]
        r["total_virupas"] = total
        r["total_rupas"] = total / 60
        r["required_rupas"] = REQUIRED_RUPAS[p]
        r["ratio"] = r["total_rupas"] / REQUIRED_RUPAS[p]
    ranking = sorted(rows, key=lambda p: rows[p]["ratio"], reverse=True)
    return {"planets": rows, "ranking": ranking}


def _apply_yuddha(chart: Chart, rows: dict) -> None:
    warriors = ("Mars", "Mercury", "Jupiter", "Venus", "Saturn")
    for i, a in enumerate(warriors):
        for b in warriors[i + 1:]:
            if angular_distance(chart.longitudes[a], chart.longitudes[b]) >= 1:
                continue
            score = {p: rows[p]["sthana"] + rows[p]["dig"] + rows[p]["kala"] for p in (a, b)}
            winner, loser = (a, b) if score[a] >= score[b] else (b, a)
            diff = score[winner] - score[loser]
            rows[winner]["kala"] += diff
            rows[loser]["kala"] -= diff
            rows[winner]["kala_parts"]["yuddha"] = diff
            rows[loser]["kala_parts"]["yuddha"] = -diff
