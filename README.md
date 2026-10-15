# Vedic Astro

A web app that takes date, time and place of birth, computes the sidereal (Vedic) birth chart,
and produces a detailed horoscope analysis covering physical constitution, health, career,
marriage, children, wealth and other areas of life.

* **backend/** — Python 3.11+ / FastAPI. Swiss Ephemeris (`pyswisseph`) for positions.
* **frontend/** — React + TypeScript (Vite). North Indian and South Indian chart styles.

See [PLAN.md](PLAN.md) for scope, architecture and roadmap.

## Run locally

```bash
# backend
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # only needed for the written report (/api/report)
.venv/bin/uvicorn app.main:app --reload --port 8000
.venv/bin/python -m pytest          # tests

# frontend (in another terminal; proxies /api to :8000)
cd frontend
npm install
npm run dev                         # http://localhost:5173
```

Optional: set `SE_EPHE_PATH` to a folder of Swiss Ephemeris `.se1` files for maximum precision;
otherwise the built-in Moshier ephemeris (~1 arc-second) is used.

## API

* `GET /api/places?city=&state=&country=` — candidate places with lat/long/time zone
* `POST /api/chart` — full chart (planets, houses, 16 vargas, Vimshottari dasha, yogas, doshas,
  Ashtakavarga, Shadbala, transits, per-life-area facts) and `interpretation`: the readings from the
  rule library (`knowledge/rules/`) that match the chart, the current dasha period and current transits
* `POST /api/report` — same input; Claude (`claude-opus-5-5`) writes a house-by-house report from
  those readings, tracking the rule ids behind each paragraph. Needs `ANTHROPIC_API_KEY` in the backend's
  environment. Only chart factors and readings are sent to the API — not the name, birth date,
  time or place. Takes about a minute.

## License note

Swiss Ephemeris is dual-licensed (AGPL or commercial). While this project is open source the AGPL
applies; a closed-source or commercial release needs the Swiss Ephemeris professional license.
