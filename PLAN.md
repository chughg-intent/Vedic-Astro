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
| Sensitive topics | Excluded: no longevity/death timing, no medical diagnoses, no other fear-inducing predictions; health is phrased as general tendencies |
| Language | English only for MVP |
| Reference books | 2 PDFs (~20 MB each). PDFs stay out of the public repo; only the extracted, paraphrased rule base (with book/page citations) is committed |

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
- [x] Get the books into the project (`knowledge/books/`, git-ignored); re-OCR'd in English
      because the scans' text layer is unusable (`knowledge/tools/`)
- [x] Rule library: 917 paraphrased `condition → effect` rules with book/chapter/verse/page
      (`knowledge/rules/`, see its README for coverage, format and condition language)
      — house effects (ch. 13–25), house lords, functional nature, yogas (ch. 36–44, 77),
      mahadasha and all 81 antardasha results; Phaladeepika (planets in houses, rising signs,
      profession, conjunctions, transits, house-lord dashas, marriage, children)
- [x] Report tab shows matched readings per life area and for the current dasha period, with citations
- [x] Rule matcher (`interpret/rules.py`), evaluated directly on the chart; `/api/chart` returns
      `interpretation.natal`, `interpretation.current_period` and `interpretation.transits`
- [ ] Extend the library: planets/signs (ch. 3–4), Nabhasa yogas (ch. 37),
      avasthas (ch. 47), house-lord dashas (ch. 50); Jaimini chapters once the engine computes karakas/arudhas
- [ ] Replace the dignity-based `strong`/`weak` approximation with validated Shadbala
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
1. Repo visibility — currently public. Keep it public (books never committed) or make it private.
