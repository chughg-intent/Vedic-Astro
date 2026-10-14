"""Nakshatras and Vimshottari dasha."""
from __future__ import annotations

from datetime import datetime, timedelta

from .constants import (DASHA_ORDER, DASHA_TOTAL_YEARS, DASHA_YEARS, NAKSHATRA_SPAN,
                        NAKSHATRAS, PADA_SPAN)

YEAR_DAYS = 365.2425


def nakshatra(longitude: float) -> dict:
    lon = longitude % 360
    idx = int(lon // NAKSHATRA_SPAN)
    within = lon - idx * NAKSHATRA_SPAN
    return {
        "index": idx,
        "name": NAKSHATRAS[idx],
        "pada": int(within // PADA_SPAN) + 1,
        "lord": DASHA_ORDER[idx % 9],
        "fraction_elapsed": within / NAKSHATRA_SPAN,
    }


def _sub_periods(lord: str, start: datetime, total_years: float, depth: int) -> list[dict]:
    """Split a period of ``lord`` into its nine sub-periods, starting with ``lord`` itself."""
    i = DASHA_ORDER.index(lord)
    out, cursor = [], start
    for k in range(9):
        sub = DASHA_ORDER[(i + k) % 9]
        years = total_years * DASHA_YEARS[sub] / DASHA_TOTAL_YEARS
        end = cursor + timedelta(days=years * YEAR_DAYS)
        node = {"lord": sub, "start": cursor, "end": end}
        if depth > 1:
            node["sub"] = _sub_periods(sub, cursor, years, depth - 1)
        out.append(node)
        cursor = end
    return out


def vimshottari(moon_longitude: float, birth: datetime, depth: int = 3) -> list[dict]:
    """Mahadashas from birth for 120 years, each with ``depth - 1`` levels of sub-periods.

    The first mahadasha is truncated by the portion of the birth nakshatra already traversed;
    sub-periods are computed over the *full* mahadasha so that they line up with
    standard software, then periods ending before birth are dropped.
    """
    nk = nakshatra(moon_longitude)
    first = nk["lord"]
    elapsed_years = nk["fraction_elapsed"] * DASHA_YEARS[first]
    cursor = birth - timedelta(days=elapsed_years * YEAR_DAYS)
    i = DASHA_ORDER.index(first)
    periods = []
    for k in range(10):  # one extra cycle entry to cover 120 years after birth
        lord = DASHA_ORDER[(i + k) % 9]
        years = DASHA_YEARS[lord]
        end = cursor + timedelta(days=years * YEAR_DAYS)
        node = {"lord": lord, "start": cursor, "end": end}
        if depth > 1:
            node["sub"] = _sub_periods(lord, cursor, years, depth - 1)
        periods.append(node)
        cursor = end
    return _trim(periods, birth, birth + timedelta(days=DASHA_TOTAL_YEARS * YEAR_DAYS))


def _trim(periods: list[dict], start: datetime, stop: datetime) -> list[dict]:
    kept = []
    for p in periods:
        if p["end"] <= start or p["start"] >= stop:
            continue
        q = dict(p)
        if "sub" in q:
            q["sub"] = _trim(q["sub"], start, stop)
        q["start"] = max(q["start"], start)
        q["end"] = min(q["end"], stop)
        kept.append(q)
    return kept


def current_periods(periods: list[dict], when: datetime) -> list[str]:
    """Chain of running lords at ``when``, e.g. ['Saturn', 'Mercury', 'Ketu']."""
    chain, level = [], periods
    while level:
        hit = next((p for p in level if p["start"] <= when < p["end"]), None)
        if hit is None:
            break
        chain.append(hit["lord"])
        level = hit.get("sub", [])
    return chain


def serialize(periods: list[dict]) -> list[dict]:
    out = []
    for p in periods:
        q = {"lord": p["lord"], "start": p["start"].isoformat(), "end": p["end"].isoformat()}
        if "sub" in p:
            q["sub"] = serialize(p["sub"])
        out.append(q)
    return out
