"""Place lookup and local-time -> UTC conversion.

Geocoding tries OpenStreetMap Nominatim first and falls back to the offline GeoNames city
database bundled with ``geonamescache`` (cities with population >= 500).
The time zone is resolved from coordinates, and the historical offset (including DST) for the
birth date comes from the IANA tz database.
"""
from __future__ import annotations

import logging
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "vedic-astro/0.1 (https://github.com/chughg-intent/Vedic-Astro)"


@dataclass
class Place:
    name: str
    display_name: str
    latitude: float
    longitude: float
    timezone: str
    country_code: str | None = None
    source: str = "geonames"

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=1)
def _tf():
    from timezonefinder import TimezoneFinder
    return TimezoneFinder()


def timezone_at(lat: float, lon: float) -> str:
    return _tf().timezone_at(lat=lat, lng=lon) or "UTC"


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return s.strip().lower()


@lru_cache(maxsize=1)
def _geonames():
    import geonamescache
    gc = geonamescache.GeonamesCache(min_city_population=500)
    countries = gc.get_countries()
    by_name = {_norm(c["name"]): code for code, c in countries.items()}
    by_name.update({code.lower(): code for code in countries})
    by_name.update({"usa": "US", "us": "US", "united states of america": "US", "uk": "GB",
                    "england": "GB", "uae": "AE"})
    us_states = {_norm(s["name"]): code for code, s in gc.get_us_states().items()}
    cities = gc.get_cities()
    index: dict[str, list[dict]] = {}
    for c in cities.values():
        for n in {c["name"], *c.get("alternatenames", [])}:
            if n:
                index.setdefault(_norm(n), []).append(c)
    return countries, by_name, us_states, index


def _offline_search(city: str, state: str | None, country: str | None, limit: int) -> list[Place]:
    countries, by_name, us_states, index = _geonames()
    hits = index.get(_norm(city), [])
    cc = by_name.get(_norm(country)) if country else None
    if cc:
        hits = [h for h in hits if h["countrycode"] == cc]
    if state and cc == "US":
        code = us_states.get(_norm(state)) or state.upper()
        filtered = [h for h in hits if h.get("admin1code") == code]
        hits = filtered or hits
    hits = sorted({h["geonameid"]: h for h in hits}.values(), key=lambda h: -h["population"])
    out = []
    for h in hits[:limit]:
        cname = countries.get(h["countrycode"], {}).get("name", h["countrycode"])
        out.append(Place(h["name"], f"{h['name']}, {cname}", h["latitude"], h["longitude"],
                         h["timezone"], h["countrycode"], "geonames"))
    return out


def _nominatim_search(query: str, limit: int) -> list[Place]:
    import httpx
    r = httpx.get(NOMINATIM_URL, params={"q": query, "format": "json", "limit": limit,
                                         "addressdetails": 1},
                  headers={"User-Agent": USER_AGENT}, timeout=8)
    r.raise_for_status()
    out = []
    for item in r.json():
        lat, lon = float(item["lat"]), float(item["lon"])
        cc = (item.get("address") or {}).get("country_code")
        out.append(Place(item.get("name") or item["display_name"].split(",")[0], item["display_name"],
                         lat, lon, timezone_at(lat, lon), cc.upper() if cc else None, "nominatim"))
    return out


def search_places(city: str, state: str | None = None, country: str | None = None,
                  limit: int = 5, online: bool = True) -> list[Place]:
    if online:
        query = ", ".join(x for x in (city, state, country) if x)
        try:
            results = _nominatim_search(query, limit)
            if results:
                return results
        except Exception as exc:  # network blocked, rate limited, etc.
            log.info("Nominatim unavailable (%s); using offline database", exc)
    return _offline_search(city, state, country, limit)


def local_to_utc(d: date, t: time, tz_name: str) -> tuple[datetime, dict]:
    """Convert a local civil birth time to UTC, flagging DST gaps and overlaps."""
    tz = ZoneInfo(tz_name)
    naive = datetime.combine(d, t)
    first = naive.replace(tzinfo=tz, fold=0)
    second = naive.replace(tzinfo=tz, fold=1)
    notes = []
    if first.utcoffset() != second.utcoffset():
        # Either an overlap (ambiguous) or a gap (non-existent); round-trip tells them apart.
        roundtrip = first.astimezone(ZoneInfo("UTC")).astimezone(tz).replace(tzinfo=None)
        notes.append("ambiguous local time (DST overlap); using the earlier offset"
                     if roundtrip == naive else
                     "local time falls in a DST gap; interpreted with the pre-transition offset")
    utc = first.astimezone(ZoneInfo("UTC"))
    offset: timedelta = first.utcoffset() or timedelta(0)
    info = {"timezone": tz_name, "utc_offset_hours": offset.total_seconds() / 3600,
            "dst": bool(first.dst()), "notes": notes}
    return utc, info
