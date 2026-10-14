# Project plan

## Scope decisions (agreed)

| Topic | Decision |
|---|---|
| Inputs | Date, time, place (city, state, country); optional name and gender |
| Chart style | User chooses **North Indian** or **South Indian**; switchable on the results page |
| Calculation | Swiss Ephemeris, sidereal, Lahiri ayanamsa by default (Raman, KP, True Chitra selectable), whole-sign houses, mean node |
| MVP calculations | D1 + all 16 Shodasavarga charts, nakshatras, Vimshottari dasha (MD/AD/PD), yogas, doshas, Ashtakavarga, Shadbala, transits |
| Interpretation | Built from the owner's reference books (`documents/claude/horobuilder`) |
| Stack | Python/FastAPI + React/TypeScript |
| Audience | Undecided — build as MVP, keep the engine isolated so licensing can change later |

## Architecture

```
Birth form ─► /api/places (Nominatim → offline GeoNames fallback) ─► lat/long + IANA time zone
          └─► /api/chart
                 geo.local_to_utc  (historical offsets + DST, flags ambiguous times)
                 engine/            pure calculation, no interpretation
                   ephemeris  chart  vargas  dignity  dasha  yogas
                   ashtakavarga  shadbala  transits
                 interpret/facts    per-life-area chart factors
                 interpret/report   (next) rules from the books + LLM write-up
```

The interpretation layer never invents chart facts. It receives the structured facts
(e.g. "7th lord Jupiter in 10th, aspected by Saturn; Venus exalted in 7th; Mangal dosha mild")
and matches them against rules extracted from the reference books. Each report statement
cites the chart factor and the source rule.

## Status

### Done (phase 1 — calculation engine + UI)
- [x] Geocoding with offline fallback, historical time-zone/DST handling
- [x] Planet positions, lagna, retrograde, combustion, dignity (compound relationships)
- [x] Whole-sign houses, lordships, graha drishti (incl. special aspects)
- [x] Shodasavarga: D1 D2 D3 D4 D7 D9 D10 D12 D16 D20 D24 D27 D30 D40 D45 D60, vargottama
- [x] Nakshatra/pada, Vimshottari dasha 3 levels, current period
- [x] Yogas: Pancha Mahapurusha, Raja, Yogakaraka, Dhana, Viparita Raja, Parivartana,
      Neecha Bhanga, Gajakesari, Chandra-Mangala, Sunapha/Anapha/Durudhara/Kemadruma, Adhi,
      Shakata, Budhaditya, Vesi/Vasi/Ubhayachari, Amala, Lakshmi, Saraswati, Guru Chandala, Grahan
- [x] Doshas: Mangal (from Lagna/Moon/Venus with mitigations), Kaal Sarp, Sade Sati, Shani Dhaiya
- [x] Ashtakavarga (BAV + SAV), Shadbala (six components, yuddha)
- [x] React UI: form, North/South charts (D1, D9, any varga), planets/houses, dasha tree,
      yogas & doshas, strength, transits, life-area factor view

### Next (phase 2 — interpretation from the reference books)
- [ ] Get the books into the project (see "Open questions")
- [ ] Extract a structured rule base: `condition → effect`, tagged by life area, with source + page
- [ ] Rule matcher over `interpret/facts` output
- [ ] Report writer: matched rules + chart facts → readable sections (Claude API), with citations;
      timing section from dasha/antardasha of relevant lords
- [ ] PDF export of the report

### Later (phase 3)
- [ ] Validate calculations against Jagannatha Hora on a set of reference charts
      (Shadbala in particular — see notes in `engine/shadbala.py`)
- [ ] Accounts, saved charts; payments if it becomes commercial
- [ ] Deployment (container for API, static hosting for UI)
- [ ] Pre-1950 India / LMT birth times: manual UTC-offset override

## Open questions
1. **Reference books** — this cloud workspace cannot read files on your laptop. Options:
   commit them to a private repo folder (e.g. `knowledge/books/`), or connect your computer to
   this session. Text PDFs/EPUBs are best; scanned PDFs need OCR. Keep the repo private if the
   books are copyrighted.
2. **Sensitive predictions** — suggested policy: no death/longevity timing, no medical
   diagnoses; health is phrased as tendencies with a "consult a doctor" note.
3. **Report language(s)** — English only for MVP?
