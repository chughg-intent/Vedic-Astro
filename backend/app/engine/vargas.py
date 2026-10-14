"""Divisional charts (Shodasavarga) per Brihat Parashara Hora Shastra."""
from __future__ import annotations

from .constants import FIXED, MOVABLE

_EPS = 1e-9  # guards exact division boundaries against float rounding

VARGA_NAMES = {
    1: "Rashi", 2: "Hora", 3: "Drekkana", 4: "Chaturthamsa", 7: "Saptamsa",
    9: "Navamsa", 10: "Dasamsa", 12: "Dwadasamsa", 16: "Shodasamsa",
    20: "Vimsamsa", 24: "Chaturvimsamsa", 27: "Saptavimsamsa", 30: "Trimsamsa",
    40: "Khavedamsa", 45: "Akshavedamsa", 60: "Shashtiamsa",
}
VARGA_THEMES = {
    1: "body and overall life", 2: "wealth", 3: "siblings, courage", 4: "property, fortune",
    7: "children, progeny", 9: "spouse, dharma, inner strength", 10: "career, profession",
    12: "parents", 16: "vehicles, comforts", 20: "spiritual progress", 24: "education, learning",
    27: "strengths and weaknesses", 30: "misfortunes, evils", 40: "maternal legacy",
    45: "paternal legacy, character", 60: "past karma, overall",
}


def _is_odd(sign: int) -> bool:
    """Odd sign in the 1-based sense (Aries, Gemini, ...)."""
    return sign % 2 == 0


def _start_by_modality(sign: int, movable: int, fixed: int, dual: int) -> int:
    if sign in MOVABLE:
        return movable
    if sign in FIXED:
        return fixed
    return dual


def varga_sign(longitude: float, division: int) -> int:
    """Sign index (0 = Aries) of a sidereal longitude in the given divisional chart."""
    lon = longitude % 360
    sign = int(lon // 30)
    deg = lon - sign * 30
    part = min(int(deg * division / 30 + _EPS), division - 1)
    odd = _is_odd(sign)

    if division == 1:
        return sign
    if division == 2:  # Parashari hora: Leo (Sun) / Cancer (Moon)
        first_half = deg < 15
        return 4 if first_half == odd else 3
    if division == 3:
        return (sign + 4 * part) % 12
    if division == 4:
        return (sign + 3 * part) % 12
    if division == 7:
        return (sign + part + (0 if odd else 6)) % 12
    if division == 9:
        return int(lon * 9 / 30 + _EPS) % 12
    if division == 10:
        return (sign + part + (0 if odd else 8)) % 12
    if division == 12:
        return (sign + part) % 12
    if division == 16:
        return (_start_by_modality(sign, 0, 4, 8) + part) % 12
    if division == 20:
        return (_start_by_modality(sign, 0, 8, 4) + part) % 12
    if division == 24:
        return ((4 if odd else 3) + part) % 12
    if division == 27:
        return int(lon * 27 / 30 + _EPS) % 12
    if division == 30:
        return _trimsamsa(deg, odd)
    if division == 40:
        return ((0 if odd else 6) + part) % 12
    if division == 45:
        return (_start_by_modality(sign, 0, 4, 8) + part) % 12
    if division == 60:
        return (sign + part) % 12
    raise ValueError(f"Unsupported division D{division}")


def _trimsamsa(deg: float, odd: bool) -> int:
    if odd:  # Mars, Saturn, Jupiter, Mercury, Venus
        bounds = [(5, 0), (10, 10), (18, 8), (25, 2), (30, 6)]
    else:  # Venus, Mercury, Jupiter, Saturn, Mars
        bounds = [(5, 1), (12, 5), (20, 11), (25, 9), (30, 7)]
    for limit, sign in bounds:
        if deg < limit:
            return sign
    return bounds[-1][1]


def varga_chart(longitudes: dict[str, float], division: int) -> dict[str, int]:
    return {name: varga_sign(lon, division) for name, lon in longitudes.items()}


def degree_in_sign(longitude: float) -> float:
    return longitude % 30


def fmt_dms(deg: float) -> str:
    d = int(deg)
    m_full = (deg - d) * 60
    m = int(m_full)
    s = int(round((m_full - m) * 60))
    if s == 60:
        s, m = 0, m + 1
    if m == 60:
        m, d = 0, d + 1
    return f"{d:02d}°{m:02d}'{s:02d}\""


__all__ = ["VARGA_NAMES", "VARGA_THEMES", "varga_sign", "varga_chart", "fmt_dms"]
