"""Gochara (current transits) relative to the natal Moon and Lagna."""
from __future__ import annotations

from datetime import datetime, timezone

from . import ephemeris
from .chart import Chart
from .constants import PLANETS, SIGNS
from .dignity import house_from


def transits(chart: Chart, when: datetime | None = None) -> dict:
    when = when or datetime.now(timezone.utc)
    jd = ephemeris.julian_day(when)
    bodies = ephemeris.planet_positions(jd, chart.ayanamsa)
    moon_sign = chart.signs["Moon"]
    rows = []
    for p in PLANETS:
        sign = int(bodies[p].longitude // 30)
        rows.append({
            "name": p, "longitude": bodies[p].longitude, "sign": SIGNS[sign],
            "retrograde": bodies[p].retrograde if p not in ("Rahu", "Ketu") else True,
            "house_from_lagna": house_from(chart.lagna_sign, sign),
            "house_from_moon": house_from(moon_sign, sign),
        })
    sat_from_moon = house_from(moon_sign, int(bodies["Saturn"].longitude // 30))
    sade_sati = {
        "active": sat_from_moon in (12, 1, 2),
        "phase": {12: "rising (1st phase)", 1: "peak (2nd phase)", 2: "setting (3rd phase)"}.get(sat_from_moon),
    }
    dhaiya = {"active": sat_from_moon in (4, 8),
              "type": {4: "Kantaka (4th)", 8: "Ashtama (8th)"}.get(sat_from_moon)}
    return {"as_of": when.isoformat(), "planets": rows, "sade_sati": sade_sati, "shani_dhaiya": dhaiya}
