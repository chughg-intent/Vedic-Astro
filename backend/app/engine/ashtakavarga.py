"""Ashtakavarga: Bhinnashtakavarga (BAV) for the seven planets and Sarvashtakavarga (SAV)."""
from __future__ import annotations

from .chart import Chart
from .constants import SEVEN_PLANETS

# BAV_TABLE[planet][contributor] = houses (counted from the contributor) that receive a bindu.
BAV_TABLE: dict[str, dict[str, tuple[int, ...]]] = {
    "Sun": {"Sun": (1, 2, 4, 7, 8, 9, 10, 11), "Moon": (3, 6, 10, 11), "Mars": (1, 2, 4, 7, 8, 9, 10, 11),
            "Mercury": (3, 5, 6, 9, 10, 11, 12), "Jupiter": (5, 6, 9, 11), "Venus": (6, 7, 12),
            "Saturn": (1, 2, 4, 7, 8, 9, 10, 11), "Lagna": (3, 4, 6, 10, 11, 12)},
    "Moon": {"Sun": (3, 6, 7, 8, 10, 11), "Moon": (1, 3, 6, 7, 10, 11), "Mars": (2, 3, 5, 6, 9, 10, 11),
             "Mercury": (1, 3, 4, 5, 7, 8, 10, 11), "Jupiter": (1, 4, 7, 8, 10, 11, 12),
             "Venus": (3, 4, 5, 7, 9, 10, 11), "Saturn": (3, 5, 6, 11), "Lagna": (3, 6, 10, 11)},
    "Mars": {"Sun": (3, 5, 6, 10, 11), "Moon": (3, 6, 11), "Mars": (1, 2, 4, 7, 8, 10, 11),
             "Mercury": (3, 5, 6, 11), "Jupiter": (6, 10, 11, 12), "Venus": (6, 8, 11, 12),
             "Saturn": (1, 4, 7, 8, 9, 10, 11), "Lagna": (1, 3, 6, 10, 11)},
    "Mercury": {"Sun": (5, 6, 9, 11, 12), "Moon": (2, 4, 6, 8, 10, 11), "Mars": (1, 2, 4, 7, 8, 9, 10, 11),
                "Mercury": (1, 3, 5, 6, 9, 10, 11, 12), "Jupiter": (6, 8, 11, 12),
                "Venus": (1, 2, 3, 4, 5, 8, 9, 11), "Saturn": (1, 2, 4, 7, 8, 9, 10, 11),
                "Lagna": (1, 2, 4, 6, 8, 10, 11)},
    "Jupiter": {"Sun": (1, 2, 3, 4, 7, 8, 9, 10, 11), "Moon": (2, 5, 7, 9, 11), "Mars": (1, 2, 4, 7, 8, 10, 11),
                "Mercury": (1, 2, 4, 5, 6, 9, 10, 11), "Jupiter": (1, 2, 3, 4, 7, 8, 10, 11),
                "Venus": (2, 5, 6, 9, 10, 11), "Saturn": (3, 5, 6, 12),
                "Lagna": (1, 2, 4, 5, 6, 7, 9, 10, 11)},
    "Venus": {"Sun": (8, 11, 12), "Moon": (1, 2, 3, 4, 5, 8, 9, 11, 12), "Mars": (3, 5, 6, 9, 11, 12),
              "Mercury": (3, 5, 6, 9, 11), "Jupiter": (5, 8, 9, 10, 11), "Venus": (1, 2, 3, 4, 5, 8, 9, 10, 11),
              "Saturn": (3, 4, 5, 8, 9, 10, 11), "Lagna": (1, 2, 3, 4, 5, 8, 9, 11)},
    "Saturn": {"Sun": (1, 2, 4, 7, 8, 10, 11), "Moon": (3, 6, 11), "Mars": (3, 5, 6, 10, 11, 12),
               "Mercury": (6, 8, 9, 10, 11, 12), "Jupiter": (5, 6, 11, 12), "Venus": (6, 11, 12),
               "Saturn": (3, 5, 6, 11), "Lagna": (1, 3, 4, 6, 10, 11)},
}
BAV_TOTALS = {"Sun": 48, "Moon": 49, "Mars": 39, "Mercury": 54, "Jupiter": 56, "Venus": 52, "Saturn": 39}


def bhinnashtakavarga(chart: Chart) -> dict[str, list[int]]:
    """For each planet, 12 bindu counts indexed by sign (0 = Aries)."""
    refs = {**{p: chart.signs[p] for p in SEVEN_PLANETS}, "Lagna": chart.lagna_sign}
    out = {}
    for planet, table in BAV_TABLE.items():
        bindus = [0] * 12
        for contributor, houses in table.items():
            for h in houses:
                bindus[(refs[contributor] + h - 1) % 12] += 1
        out[planet] = bindus
    return out


def ashtakavarga(chart: Chart) -> dict:
    bav = bhinnashtakavarga(chart)
    sav = [sum(bav[p][s] for p in bav) for s in range(12)]
    by_house = [sav[chart.sign_of_house(h)] for h in range(1, 13)]
    return {"bav": bav, "sav": sav, "sav_by_house": by_house, "total": sum(sav)}
