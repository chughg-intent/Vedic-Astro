"""FastAPI application: birth data in, full Vedic chart out."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import geo
from .engine import dasha as dasha_mod
from .engine.ashtakavarga import ashtakavarga
from .engine.chart import build_chart, divisional, house_table, planet_table, vargottama
from .engine.constants import SIGNS
from .engine.shadbala import shadbala
from .engine.transits import transits
from .engine.vargas import VARGA_NAMES, VARGA_THEMES
from .engine.yogas import all_yogas
from .interpret import rules
from .interpret.facts import extract

app = FastAPI(title="Vedic Astro API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class BirthInput(BaseModel):
    name: str | None = None
    gender: Literal["male", "female", "other"] | None = None
    date: date
    time: time
    city: str = Field(min_length=1)
    state: str | None = None
    country: str = Field(min_length=1)
    # Optional overrides when the user picks a specific place from the search results.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    chart_style: Literal["north", "south"] = "north"
    ayanamsa: Literal["lahiri", "raman", "krishnamurti", "true_chitra"] = "lahiri"
    node: Literal["mean", "true"] = "mean"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/places")
def places(city: str = Query(min_length=1), state: str | None = None, country: str | None = None):
    return [p.to_dict() for p in geo.search_places(city, state, country)]


@app.post("/api/chart")
def chart(inp: BirthInput):
    place = _resolve_place(inp)
    birth_utc, tzinfo = geo.local_to_utc(inp.date, inp.time, place["timezone"])
    c = build_chart(birth_utc, place["latitude"], place["longitude"], inp.ayanamsa, inp.node)

    dashas = dasha_mod.vimshottari(c.longitudes["Moon"], birth_utc, depth=3)
    yogas = all_yogas(c)
    av = ashtakavarga(c)
    now = datetime.now(timezone.utc)
    current = dasha_mod.current_periods(dashas, now)

    return {
        "input": inp.model_dump(mode="json"),
        "place": place,
        "time": {"utc": birth_utc.isoformat(), "julian_day": c.jd, **tzinfo},
        "settings": {"ayanamsa": inp.ayanamsa, "ayanamsa_value": c.ayanamsa_value,
                     "node": inp.node, "house_system": "whole sign", "chart_style": inp.chart_style},
        "lagna": {"longitude": c.lagna, "sign": SIGNS[c.lagna_sign]},
        "planets": planet_table(c),
        "houses": house_table(c),
        "vargas": {d: {**divisional(c, d), "theme": VARGA_THEMES[d]} for d in VARGA_NAMES},
        "vargottama": vargottama(c),
        "dasha": {"system": "vimshottari", "periods": dasha_mod.serialize(dashas),
                  "current": current},
        **yogas,
        "ashtakavarga": av,
        "shadbala": shadbala(c),
        "transits": transits(c, now),
        "life_areas": extract(c, yogas, dashas, av),
        "interpretation": {
            "natal": rules.match(c, yogas),
            "current_period": [m for ad in (None, *current[1:2]) if current
                               for m in rules.match_period(c, current[0], ad, yogas)],
        },
    }


def _resolve_place(inp: BirthInput) -> dict:
    if inp.latitude is not None and inp.longitude is not None:
        tz = inp.timezone or geo.timezone_at(inp.latitude, inp.longitude)
        name = ", ".join(x for x in (inp.city, inp.state, inp.country) if x)
        return geo.Place(inp.city, name, inp.latitude, inp.longitude, tz, None, "user").to_dict()
    results = geo.search_places(inp.city, inp.state, inp.country, limit=1)
    if not results:
        raise HTTPException(404, f"Could not find '{inp.city}, {inp.state or ''} {inp.country}'. "
                                 "Check the spelling or choose a nearby larger city.")
    return results[0].to_dict()
