"""FastAPI application: birth data in, full Vedic chart out."""
from __future__ import annotations

import hmac
import os
import threading
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
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
from .interpret import ask as ask_mod
from .interpret import report as report_mod
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
    return _build(inp)[0]


def _build(inp: BirthInput):
    """The chart response, plus the objects the question endpoint needs to look ahead in time."""
    place = _resolve_place(inp)
    birth_utc, tzinfo = geo.local_to_utc(inp.date, inp.time, place["timezone"])
    c = build_chart(birth_utc, place["latitude"], place["longitude"], inp.ayanamsa, inp.node)

    dashas = dasha_mod.vimshottari(c.longitudes["Moon"], birth_utc, depth=3)
    yogas = all_yogas(c)
    av = ashtakavarga(c)
    now = datetime.now(timezone.utc)
    current = dasha_mod.current_periods(dashas, now)
    gochara = transits(c, now)

    response = {
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
        "transits": gochara,
        "life_areas": extract(c, yogas, dashas, av),
        "interpretation": {
            "natal": rules.match(c, yogas),
            "current_period": [m for ad in (None, *current[1:2]) if current
                               for m in rules.match_period(c, current[0], ad, yogas)],
            "transits": rules.match_transits(c, {t["name"]: t["longitude"] for t in gochara["planets"]},
                                             av["bav"], yogas),
        },
    }
    return response, c, yogas, dashas, now


# --- Written report: optional access code and daily cap, both set through the environment ----------
# ACCESS_CODE: when set, /api/report requires it in the X-Access-Code header.
# REPORT_DAILY_LIMIT: when set, at most this many reports per UTC day (counted in memory, so a
# restart resets it). Both guard the Claude API spend when the site is shared.
# ASK_DAILY_LIMIT does the same for questions (default 50 when unset).
_reports_lock = threading.Lock()
_reports_today = {"day": None, "count": 0}
_asks_today = {"day": None, "count": 0}


def _access_code() -> str:
    return os.environ.get("ACCESS_CODE", "").strip()


def _daily_limit(var: str = "REPORT_DAILY_LIMIT", default: int = 0) -> int:
    try:
        return int(os.environ.get(var, str(default)))
    except ValueError:
        return default


def _take_slot(counter: dict, limit: int, what: str) -> None:
    with _reports_lock:
        today = datetime.now(timezone.utc).date()
        if counter["day"] != today:
            counter.update(day=today, count=0)
        if limit and counter["count"] >= limit:
            raise HTTPException(429, f"Today's limit of {what} has been reached. Please try again tomorrow.")
        counter["count"] += 1


def _give_back_slot(counter: dict) -> None:
    with _reports_lock:
        counter["count"] = max(0, counter["count"] - 1)


def _take_report_slot() -> None:
    _take_slot(_reports_today, _daily_limit(), "written reports")


def _give_back_report_slot() -> None:
    _give_back_slot(_reports_today)


def _check_access_code(x_access_code: Optional[str]) -> None:
    code = _access_code()
    if code and not hmac.compare_digest((x_access_code or "").strip().encode(), code.encode()):
        raise HTTPException(401, "Enter the access code to continue." if not x_access_code
                            else "That access code is not right.")


@app.get("/api/config")
def config():
    return {"report_requires_code": bool(_access_code()),
            "topics": [{"house": h, "title": t} for h, (t, _) in report_mod.HOUSES.items()]}


@app.post("/api/report")
def report(inp: BirthInput, x_access_code: Optional[str] = Header(default=None)):
    """Readable report written by Claude from the matched readings (takes about a minute)."""
    _check_access_code(x_access_code)
    _take_report_slot()
    try:
        return report_mod.write_report(chart(inp))
    except report_mod.ReportError as e:
        _give_back_report_slot()  # failed attempts don't use up the day's allowance
        raise HTTPException(e.status, str(e))


class AskInput(BaseModel):
    birth: BirthInput
    house: int = Field(ge=1, le=12)
    question: str = Field(min_length=1, max_length=ask_mod.MAX_QUESTION)


def _coming_periods(c, dashas, yogas, now, count: int = 4) -> list[dict]:
    """The running sub-period and the next few, each with the readings that apply to it."""
    out, seen_md = [], set()
    for md in dashas:
        for ad in md.get("sub", []):
            if ad["end"] <= now:
                continue
            readings = rules.match_period(c, md["lord"], ad["lord"], yogas)
            if md["lord"] not in seen_md:  # the mahadasha's own readings, once
                readings = rules.match_period(c, md["lord"], None, yogas) + readings
                seen_md.add(md["lord"])
            out.append({"md": md["lord"], "ad": ad["lord"], "start": ad["start"].date().isoformat(),
                        "end": ad["end"].date().isoformat(), "readings": readings})
            if len(out) == count:
                return out
    return out


@app.post("/api/ask")
def ask(body: AskInput, x_access_code: Optional[str] = Header(default=None)):
    """Answer a question about one house, from the readings and the running and coming periods."""
    _check_access_code(x_access_code)
    _take_slot(_asks_today, _daily_limit("ASK_DAILY_LIMIT", 50), "questions")
    try:
        chart_resp, c, yogas, dashas, now = _build(body.birth)
        return ask_mod.answer_question(chart_resp, body.house, body.question, _coming_periods(c, dashas, yogas, now))
    except ask_mod.AskError as e:
        _give_back_slot(_asks_today)
        raise HTTPException(422, str(e))
    except report_mod.ReportError as e:
        _give_back_slot(_asks_today)
        raise HTTPException(e.status, str(e))


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


# --- Built frontend ----------------------------------------------------------------------------------
# In production one server serves both the API and the React app (FRONTEND_DIST is set in the Docker
# image). Mounted last, so every /api route above takes precedence.
_dist = Path(os.environ.get("FRONTEND_DIST", Path(__file__).resolve().parents[2] / "frontend" / "dist"))
if (_dist / "index.html").exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
