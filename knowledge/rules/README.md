# Rule library

Paraphrased interpretive rules extracted from the reference books, as `condition → effect`
statements that the backend can evaluate against a calculated chart
(`backend/app/interpret/rules.py`). Each rule carries the book, chapter, verse and printed
page it came from, so every sentence in a report can be traced to a chart factor and a source.

The books themselves (`knowledge/books/`) and their OCR text (`knowledge/ocr/`) are **not**
committed. Only these paraphrases are.

## Source

| Key | Book |
|---|---|
| `bphs-sharma` | *Brihat Parasara Hora Sastra*, with English translation and commentary by Girish Chand Sharma, Sagar Publications. Vol. 1 (chapters 1–47, 1994), Vol. 2 (chapters 48–100, 1995). |
| `phaladeepika-sastri` | Mantreswara's *Phaladeepika* (Adhyayas I–XXVIII), with English translation by V. Subrahmanya Sastri, Bangalore, 1937. Single volume (`volume` is 1); `chapter` is the Adhyaya number, `verse` the sloka. |

`page` is the page number printed in the book, not the PDF page.

## Coverage

756 rules (532 from BPHS, 224 from Phaladeepika). "Encoded" counts rules, not verses; one verse can yield several rules and several
verses can merge into one.

| Ch. | Subject | File | Rules | Status |
|---|---|---|---|---|
| 13 | Whether each house prospers or suffers (general test) | `bphs_13_judging_houses.json` | 22 | All houses except the 8th |
| 14–20, 22–25 | Effects of the 1st–7th and 9th–12th houses | `bphs_14…25_*_house.json` | 88 | Encodable verses; see exclusions below |
| 26 | Lord of each house in each house | `bphs_26_house_lords.json` | 143 | Complete (143 of 144; v.75 withheld by policy) |
| 36 | Functional benefics/malefics per ascendant | `bphs_36_functional_nature.json` | 14 | Complete except Rahu/Ketu dispositor rule |
| 38 | Named yogas (Gajakesari, Amala, Parvata, Kahala …) | `bphs_38_yogas.json` | 20 | 4 yogas not encodable yet |
| 39 | Lunar yogas | `bphs_39_lunar_yogas.json` | 7 | Complete except day/night navamsa rule |
| 40 | Solar yogas | `bphs_40_solar_yogas.json` | 3 | Complete |
| 41 | Raja yogas | `bphs_41_raja_yogas.json` | 15 | Birth-chart yogas only; Jaimini-based ones skipped |
| 42 | Yogas for royal association | `bphs_42_royal_association.json` | 2 | Most verses need Jaimini karakas |
| 43 | Wealth yogas | `bphs_43_wealth_yogas.json` | 15 | Complete except divisional-dignity verses |
| 44 | Combinations for penury | `bphs_44_penury.json` | 8 | Partial |
| 49 | Mahadasha results, all nine planets | `bphs_49_mahadasha.json` | 21 | Complete |
| 54–62 | Antardasha results within each mahadasha | `bphs_5x/6x_antardasha_*.json` | 169 | 78 of 81 pairs (see below) |
| 77 | Pancha Mahapurusha yogas | `bphs_77_mahapurusha.json` | 5 | Complete |

**Phaladeepika** (files `phaladeepika_*.json`):

| Adh. | Subject | Rules | Status |
|---|---|---|---|
| V | Profession from the 10th lord's navamsa; source of wealth from the 10th house | 15 | Complete (from the ascendant only) |
| VIII | Each planet in each of the twelve houses | 108 | Complete (all 9 × 12) |
| IX | Each rising sign (also applied to the Moon's sign); dasha of a planet by its sign | 16 | Complete except combust-planet dasha (policy) |
| XVIII | Two-planet conjunctions; the Moon's sign aspected by each planet | 85 | Moon's-navamsa verses (12–17) not yet encoded |

Not yet encoded from Phaladeepika: yogas (VI–VII, much overlaps BPHS), the 7th house and
children (X, XII), general effects of houses (XV–XVI), dashas of house lords (XX–XXI),
Ashtakavarga (XXIII–XXIV) and transits (XXVI).

Every file has a `skipped` list naming the verses left out and why.

**Not started** (in rough priority order): planets and signs described (ch. 3–4), divisional charts and their use (ch. 6–8), Nabhasa yogas
(ch. 37), avasthas (ch. 47), dasha results of house lords (ch. 50), Ashtakavarga
interpretation (ch. 66–72), female horoscopy (ch. 80–81). Jaimini material (ch. 31–35, karakas,
arudhas, chara dasha) needs engine support first.

**Deliberately excluded** by the project's sensitive-topics policy: evils at birth and their
remedies (ch. 11–12), the 8th house (ch. 21, entirely longevity), diseases (most of ch. 19),
deaths of children, spouse, siblings and father (parts of ch. 16, 18, 20, 22), childhood
marriage ages (ch. 20 v. 22–34), longevity (ch. 45), maraka planets (ch. 46), and every individual clause about life span, death,
named diseases or 'maraka' lordship. A rule that lost such a clause lists what was removed in
`dropped`. Remedial rituals are also left out.

### Defects in the scan of Volume 2

Roughly 27 PDF pages of Volume 2 are the wrong page (a different page of the book scanned in
their place), so the corresponding printed pages are missing. In the dasha chapters this loses
printed pages 219, 353 and 395, and with them three antardasha sections that could not be
encoded: **Mercury–Mercury**, **Mercury–Saturn** and **Venus–Saturn**. Moon–Mars has only its
unfavourable half, and Jupiter–Rahu likewise. A complete copy of those pages would fill the gaps.

## File format

```json
{
  "source": {"book": "bphs-sharma", "volume": 1, "chapter": 26, "chapter_title": "..."},
  "kind": "natal",
  "notes": "chapter-level reading guidance",
  "skipped": [{"verse": "75", "reason": "..."}],
  "rules": [
    {"verse": "94", "page": 321,
     "when": {"in_house": ["L8", 10]},
     "areas": ["career", "family"], "tone": "challenging",
     "text": "Little happiness from the father, ...",
     "variants": [{"when": {"aspected_by": ["L8", "benefic"]},
                   "text": "A benefic aspects the 8th lord, so ...", "tone": "mixed"}],
     "dropped": ["longevity"]}
  ]
}
```

- `id` defaults to `<book>.<chapter>.<verse>`; set it explicitly when one verse yields several rules.
- `when` may be omitted (the rule always applies). `text` may be empty when every outcome is a variant.
- `variants` add their text (and may override `tone`) when their own condition also holds.
- `areas` are the life-area keys from `backend/app/interpret/facts.py`, plus `general`.
- `tone` is `favourable`, `challenging`, `mixed` or `neutral`.
- `kind: "dasha"` rules need `"period": {"md": "Sun"}` (mahadasha; `"any"` matches all nine) or
  `{"md": "Sun", "ad": "Moon"}` (antardasha), and may use the references `MD` and `AD`.
- `note` records an approximation or a doubt about the printed text. Unknown keys are ignored.

The loader validates every file on first use and rejects unknown predicates, planets, signs,
dignities, life areas or duplicate ids, so a typo fails the tests rather than silently never matching.

## Condition language

A condition is an object with exactly one key.

**References** — a planet name (`"Jupiter"`), a house lord (`"L1"` … `"L12"`), or in dasha rules
`"MD"` / `"AD"`. **Groups** — `"benefic"`, `"malefic"` (natural: waxing Moon and unafflicted
Mercury count as benefic) or `"any"`. **Houses** — a number, or `[ref, n]` for the n-th house
counted from that planet.

| Predicate | Argument | True when |
|---|---|---|
| `in_house` | `[ref, house or list]` | planet occupies one of the houses |
| `in_house_from` | `[ref, base, houses]` | planet's house counted from `base` (a ref or `"lagna"`) |
| `in_sign` | `[ref, sign or list]` | planet is in one of the signs |
| `lagna` / `lagna_movable` | `sign or list` / `true` | ascendant sign test |
| `rules` | `[ref, house or list]` | planet is lord of one of the houses |
| `in_navamsa_of` | `[ref, planet or list]` | the navamsa sign the planet occupies is ruled by one of these |
| `dignity` | `[ref, label or list]` | `exalted` `moolatrikona` `own` `friend` `neutral` `enemy` `debilitated` |
| `strong` / `weak` | `ref` | see below |
| `nature` | `[ref, "benefic"\|"malefic"]` | natural nature of the planet |
| `conjunct` / `aspected_by` / `influenced_by` | `[ref, ref or group]` | same sign / full graha drishti / either |
| `house_has` / `house_only` / `house_aspected_by` | `[house, ref or group]` | occupants / all occupants are of the group / aspects |
| `exchange` / `related` / `mutual_kendra` | `[ref, ref]` | sign exchange / any Parashari relation / in angles from each other |
| `combust` / `retrograde` | `ref` | |
| `count_dignity` | `[labels, min, max?]` | number of the seven planets with that dignity |
| `count_in_houses` | `[group, houses, min, max?]` | number of the group in those houses |
| `all_in_houses` | `[group, houses]` | every member of the group (nodes excluded) is in those houses |
| `waxing_moon` | `true/false` | |
| `yoga` / `dosha` | `"name"` | the engine detected a yoga/dosha whose name starts with this |
| `all` / `any` / `not` | list / list / condition | combinators |

### Approximations to be aware of

- **Strength.** The text's "strong" means Shadbala. Here `strong` = exalted, moolatrikona or own
  sign, or a friend's sign in an angle or trine, and not combust; `weak` = debilitated, in an
  enemy's sign, or combust. Replace with Shadbala once it is validated (see PLAN.md).
- **Aspects** are whole-sign full aspects only.
- **Language.** "King" is rendered as government, authority or employer (following the
  translator's own glosses); "sons" as children; "wife" as spouse. Moral judgements in the verses
  are kept but softened into tendencies.
- Some verses' "and/or" lists are ambiguous in translation; where an encoding choice was made
  the rule has a `note`.

## Regenerating the OCR text

The BPHS PDFs' embedded text layer is unusable for English (it was produced with a Devanagari
OCR model), and the Phaladeepika scan has no text layer at all. On macOS:

```bash
pip install pymupdf
swiftc -O knowledge/tools/ocr.swift -o knowledge/tools/ocr
python knowledge/tools/ocr_books.py      # ~5 minutes, writes knowledge/ocr/{vol1,vol2,phaladeepika}/pNNNN.txt
```
