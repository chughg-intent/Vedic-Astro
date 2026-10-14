"""Planetary dignity, relationships and combustion."""
from __future__ import annotations

from .constants import (COMBUSTION_ORB, DEBILITATION, EXALTATION, MOOLATRIKONA,
                        NATURAL_FRIENDS, OWN_SIGNS, SIGN_LORDS)


def angular_distance(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def house_from(from_sign: int, to_sign: int) -> int:
    """1-based house count from one sign to another (same sign = 1)."""
    return (to_sign - from_sign) % 12 + 1


def natural_relation(planet: str, other: str) -> str:
    rel = NATURAL_FRIENDS.get(planet)
    if rel is None or other not in NATURAL_FRIENDS:
        return "neutral"
    for key, label in (("friends", "friend"), ("enemies", "enemy")):
        if other in rel[key]:
            return label
    return "neutral"


def temporary_relation(planet_sign: int, other_sign: int) -> str:
    return "friend" if house_from(planet_sign, other_sign) in (2, 3, 4, 10, 11, 12) else "enemy"


_COMPOUND = {
    ("friend", "friend"): "great friend", ("friend", "enemy"): "neutral",
    ("neutral", "friend"): "friend", ("neutral", "enemy"): "enemy",
    ("enemy", "friend"): "neutral", ("enemy", "enemy"): "great enemy",
}


def compound_relation(planet: str, other: str, signs: dict[str, int]) -> str:
    return _COMPOUND[(natural_relation(planet, other), temporary_relation(signs[planet], signs[other]))]


def dignity(planet: str, longitude: float, signs: dict[str, int] | None = None) -> str:
    """Dignity label for a planet at a sidereal longitude.

    ``signs`` (planet -> D1 sign) enables compound-relationship labels for the dispositor.
    """
    sign = int(longitude // 30) % 12
    deg = longitude % 30
    if EXALTATION.get(planet, (None,))[0] == sign:
        return "exalted"
    if DEBILITATION.get(planet, (None,))[0] == sign:
        return "debilitated"
    mt = MOOLATRIKONA.get(planet)
    if mt and mt[0] == sign and mt[1] <= deg < mt[2]:
        return "moolatrikona"
    if sign in OWN_SIGNS.get(planet, ()):
        return "own sign"
    lord = SIGN_LORDS[sign]
    if planet in ("Rahu", "Ketu"):
        return "neutral"
    if signs and lord in signs and planet in signs:
        return f"{compound_relation(planet, lord, signs)}'s sign"
    return f"{natural_relation(planet, lord)}'s sign"


def is_combust(planet: str, longitude: float, sun_longitude: float, retrograde: bool) -> bool:
    orb = COMBUSTION_ORB.get(planet)
    if not orb:
        return False
    return angular_distance(longitude, sun_longitude) <= (orb[1] if retrograde else orb[0])
