"""Rule library: loads the paraphrased rules in ``knowledge/rules`` and matches them to a chart.

A rule is ``condition -> effect``. Conditions are small JSON expressions evaluated against
the calculated chart, so a rule can only fire on a factor the engine actually computed, and
every match carries the chart factors that triggered it plus the book/chapter/verse/page it
was paraphrased from. The condition language is documented in ``knowledge/rules/README.md``.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from ..engine.chart import Chart
from ..engine.constants import KENDRAS, MOVABLE, PLANETS, SIGNS, TRIKONAS
from ..engine.dignity import dignity, house_from, is_combust
from .facts import LIFE_AREAS

RULES_DIR = Path(__file__).resolve().parents[3] / "knowledge" / "rules"

AREAS = set(LIFE_AREAS) | {"general"}
TONES = {"favourable", "challenging", "mixed", "neutral"}
DIGNITIES = {"exalted", "moolatrikona", "own", "friend", "neutral", "enemy", "debilitated"}
GROUPS = {"benefic", "malefic", "any"}
_REF = re.compile(r"^(L([1-9]|1[0-2])|MD|AD)$")


class RuleError(ValueError):
    pass


def ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def _as_list(x) -> list:
    return x if isinstance(x, list) else [x]


class Context:
    """A chart plus (for dasha rules) the running period lords."""

    def __init__(self, chart: Chart, yogas: dict | None = None, md: str | None = None, ad: str | None = None):
        self.chart, self.md, self.ad = chart, md, ad
        self.yogas = {y["name"].lower() for y in (yogas or {}).get("yogas", [])}
        self.doshas = {d["name"].lower() for d in (yogas or {}).get("doshas", []) if d.get("present")}

    # --- references -----------------------------------------------------------------------
    def planet(self, ref: str) -> str:
        if ref in PLANETS:
            return ref
        if ref == "MD" and self.md:
            return self.md
        if ref == "AD" and self.ad:
            return self.ad
        if ref.startswith("L"):
            return self.chart.lord_of(int(ref[1:]))
        raise RuleError(f"cannot resolve planet reference {ref!r}")

    def label(self, ref: str) -> str:
        p = self.planet(ref)
        if ref.startswith("L"):
            return f"{ordinal(int(ref[1:]))} lord {p}"
        return {"MD": f"dasha lord {p}", "AD": f"sub-period lord {p}"}.get(ref, p)

    def group(self, who: str, exclude: str | None = None) -> list[str]:
        if who in GROUPS:
            c = self.chart
            return [p for p in PLANETS if p != exclude
                    and (who == "any" or c.is_benefic(p) == (who == "benefic"))]
        return [self.planet(who)]

    def house(self, spec) -> int:
        """A house number, or ``[ref, n]`` for the n-th house counted from a planet."""
        if isinstance(spec, int):
            return spec
        base, n = spec
        return (self.chart.house_of(self.planet(base)) + n - 2) % 12 + 1

    def house_label(self, spec) -> str:
        if isinstance(spec, int):
            return f"the {ordinal(spec)} house"
        return f"the {ordinal(spec[1])} from {self.label(spec[0])}"

    def dignity(self, p: str) -> str:
        d = dignity(p, self.chart.longitudes[p], self.chart.signs)
        if d == "own sign":
            return "own"
        if "friend" in d:
            return "friend"
        if "enemy" in d:
            return "enemy"
        return "neutral" if d.startswith("neutral") else d

    def combust(self, p: str) -> bool:
        b = self.chart.bodies[p]
        return is_combust(p, b.longitude, self.chart.longitudes["Sun"], b.retrograde)

    def strong(self, p: str) -> bool:
        """Approximation of the texts' "endowed with strength" from dignity and placement."""
        d = self.dignity(p)
        well_placed = self.chart.house_of(p) in set(KENDRAS) | set(TRIKONAS)
        return not self.combust(p) and (d in ("exalted", "moolatrikona", "own") or (d == "friend" and well_placed))

    def weak(self, p: str) -> bool:
        return self.combust(p) or self.dignity(p) in ("debilitated", "enemy")


# --- predicates: each returns (matched, human-readable chart factor) ---------------------------
def _in_house(c: Context, a):
    p = c.planet(a[0])
    h = c.chart.house_of(p)
    return h in _as_list(a[1]), f"{c.label(a[0])} in the {ordinal(h)} house"


def _in_house_from(c: Context, a):
    p, base = c.planet(a[0]), a[1]
    start = c.chart.lagna_sign if base == "lagna" else c.chart.signs[c.planet(base)]
    h = house_from(start, c.chart.signs[p])
    origin = "the ascendant" if base == "lagna" else c.label(base)
    return h in _as_list(a[2]), f"{c.label(a[0])} in the {ordinal(h)} from {origin}"


def _in_sign(c: Context, a):
    s = SIGNS[c.chart.signs[c.planet(a[0])]]
    return s in _as_list(a[1]), f"{c.label(a[0])} in {s}"


def _lagna(c: Context, a):
    s = SIGNS[c.chart.lagna_sign]
    return s in _as_list(a), f"{s} ascendant"


def _lagna_movable(c: Context, a):
    return (c.chart.lagna_sign in MOVABLE) == bool(a), f"{SIGNS[c.chart.lagna_sign]} ascendant"


def _dignity(c: Context, a):
    d = c.dignity(c.planet(a[0]))
    return d in _as_list(a[1]), f"{c.label(a[0])} {_DIGNITY_TEXT[d]}"


_DIGNITY_TEXT = {"exalted": "exalted", "moolatrikona": "in moolatrikona", "own": "in own sign",
                 "friend": "in a friend's sign", "neutral": "in a neutral sign",
                 "enemy": "in an enemy's sign", "debilitated": "debilitated"}


def _strong(c: Context, a):
    return c.strong(c.planet(a)), f"{c.label(a)} strong"


def _weak(c: Context, a):
    return c.weak(c.planet(a)), f"{c.label(a)} weak"


def _nature(c: Context, a):
    p = c.planet(a[0])
    kind = "benefic" if c.chart.is_benefic(p) else "malefic"
    return kind == a[1], f"{c.label(a[0])} is a natural {kind}"


def _rules(c: Context, a):
    p = c.planet(a[0])
    hits = [h for h in c.chart.houses_ruled(p) if h in _as_list(a[1])]
    return bool(hits), f"{c.label(a[0])} rules the {' and '.join(ordinal(h) for h in hits)}"


def _others(c: Context, a, test) -> list[str]:
    p = c.planet(a[0])
    return [q for q in c.group(a[1], exclude=p) if q != p and test(q, p)]


def _conjunct(c: Context, a):
    hits = _others(c, a, c.chart.conjunct)
    return bool(hits), f"{c.label(a[0])} conjunct {', '.join(hits)}"


def _aspected_by(c: Context, a):
    hits = _others(c, a, c.chart.aspects)
    return bool(hits), f"{c.label(a[0])} aspected by {', '.join(hits)}"


def _influenced_by(c: Context, a):
    hits = _others(c, a, lambda q, p: c.chart.conjunct(q, p) or c.chart.aspects(q, p))
    return bool(hits), f"{c.label(a[0])} joined or aspected by {', '.join(hits)}"


def _house_has(c: Context, a):
    occ = c.chart.occupants(c.house(a[0]))
    hits = [p for p in c.group(a[1]) if p in occ]
    return bool(hits), f"{', '.join(hits)} in {c.house_label(a[0])}"


def _house_only(c: Context, a):
    occ = c.chart.occupants(c.house(a[0]))
    ok = bool(occ) and all(p in c.group(a[1]) for p in occ)
    return ok, f"only {a[1]}s ({', '.join(occ)}) in {c.house_label(a[0])}"


def _house_aspected_by(c: Context, a):
    asp = c.chart.aspects_on_house(c.house(a[0]))
    hits = [p for p in c.group(a[1]) if p in asp]
    return bool(hits), f"{c.house_label(a[0])} aspected by {', '.join(hits)}"


def _exchange(c: Context, a):
    x, y = c.planet(a[0]), c.planet(a[1])
    return "exchange" in c.chart.related(x, y), f"{c.label(a[0])} and {c.label(a[1])} exchange signs"


def _related(c: Context, a):
    kinds = c.chart.related(c.planet(a[0]), c.planet(a[1]))
    return bool(kinds), f"{c.label(a[0])} and {c.label(a[1])} related by {', '.join(kinds)}"


def _mutual_kendra(c: Context, a):
    x, y = c.planet(a[0]), c.planet(a[1])
    ok = x != y and house_from(c.chart.signs[x], c.chart.signs[y]) in KENDRAS
    return ok, f"{c.label(a[0])} and {c.label(a[1])} in mutual angles"


def _combust(c: Context, a):
    return c.combust(c.planet(a)), f"{c.label(a)} combust"


def _retrograde(c: Context, a):
    p = c.planet(a)
    return p not in ("Rahu", "Ketu") and c.chart.bodies[p].retrograde, f"{c.label(a)} retrograde"


def _count_dignity(c: Context, a):
    labels, lo = _as_list(a[0]), a[1]
    hi = a[2] if len(a) > 2 else 9
    hits = [p for p in PLANETS[:7] if c.dignity(p) in labels]
    return lo <= len(hits) <= hi, f"{', '.join(hits)} {' / '.join(_DIGNITY_TEXT[x] for x in labels)}"


def _count_in_houses(c: Context, a):
    """[group, houses, min, max?] — how many planets of a group occupy the given houses."""
    houses = [c.house(h) for h in a[1]]
    hits = [p for p in c.group(a[0]) if c.chart.house_of(p) in houses]
    hi = a[3] if len(a) > 3 else 9
    return a[2] <= len(hits) <= hi, f"{', '.join(hits)} in houses {', '.join(map(str, sorted(set(houses))))}"


def _all_in_houses(c: Context, a):
    """[group, houses] — every planet of the group (nodes excluded) occupies one of the houses."""
    members = [p for p in c.group(a[0]) if p not in ("Rahu", "Ketu")]
    ok = bool(members) and all(c.chart.house_of(p) in a[1] for p in members)
    return ok, f"all {a[0]}s ({', '.join(members)}) in houses {', '.join(map(str, a[1]))}"


def _waxing_moon(c: Context, a):
    w = c.chart.moon_waxing
    return w == bool(a), f"Moon {'waxing' if w else 'waning'}"


def _yoga(c: Context, a):
    return any(n.startswith(a.lower()) for n in c.yogas), a


def _dosha(c: Context, a):
    return any(n.startswith(a.lower()) for n in c.doshas), a


PREDICATES = {
    "in_house": _in_house, "in_house_from": _in_house_from, "in_sign": _in_sign,
    "lagna": _lagna, "lagna_movable": _lagna_movable, "dignity": _dignity,
    "strong": _strong, "weak": _weak, "nature": _nature, "rules": _rules,
    "conjunct": _conjunct, "aspected_by": _aspected_by, "influenced_by": _influenced_by,
    "house_has": _house_has, "house_only": _house_only, "house_aspected_by": _house_aspected_by,
    "exchange": _exchange, "related": _related, "mutual_kendra": _mutual_kendra,
    "combust": _combust, "retrograde": _retrograde, "count_dignity": _count_dignity,
    "count_in_houses": _count_in_houses, "all_in_houses": _all_in_houses,
    "waxing_moon": _waxing_moon, "yoga": _yoga, "dosha": _dosha,
}


def evaluate(cond: dict | None, ctx: Context) -> tuple[bool, list[str]]:
    """Evaluate a condition; returns whether it holds and the chart factors that made it hold."""
    if not cond:
        return True, []
    (op, arg), = cond.items()
    if op == "all":
        factors = []
        for sub in arg:
            ok, f = evaluate(sub, ctx)
            if not ok:
                return False, []
            factors += f
        return True, factors
    if op == "any":
        for sub in arg:
            ok, f = evaluate(sub, ctx)
            if ok:
                return True, f
        return False, []
    if op == "not":
        return not evaluate(arg, ctx)[0], []
    ok, factor = PREDICATES[op](ctx, arg)
    return ok, [factor] if ok else []


# --- loading and validation ------------------------------------------------------------------
def _check_ref(ref, where: str, dasha: bool) -> None:
    ok = isinstance(ref, str) and (ref in PLANETS or _REF.match(ref))
    if not ok or (ref in ("MD", "AD") and not dasha):
        raise RuleError(f"{where}: bad planet reference {ref!r}")


def _check_house(spec, where: str, dasha: bool) -> None:
    if isinstance(spec, int) and 1 <= spec <= 12:
        return
    if isinstance(spec, list) and len(spec) == 2 and isinstance(spec[1], int):
        return _check_ref(spec[0], where, dasha)
    raise RuleError(f"{where}: bad house {spec!r}")


def check_condition(cond, where: str, dasha: bool = False) -> None:
    """Static validation, so a malformed rule fails at load time rather than on some chart."""
    if not isinstance(cond, dict) or len(cond) != 1:
        raise RuleError(f"{where}: a condition is an object with exactly one key, got {cond!r}")
    (op, a), = cond.items()
    if op in ("all", "any"):
        for sub in a:
            check_condition(sub, where, dasha)
    elif op == "not":
        check_condition(a, where, dasha)
    elif op not in PREDICATES:
        raise RuleError(f"{where}: unknown predicate {op!r}")
    elif op in ("strong", "weak", "combust", "retrograde"):
        _check_ref(a, where, dasha)
    elif op in ("in_house", "in_house_from", "rules"):
        _check_ref(a[0], where, dasha)
        if op == "in_house_from" and a[1] != "lagna":
            _check_ref(a[1], where, dasha)
        if not all(isinstance(h, int) and 1 <= h <= 12 for h in _as_list(a[-1])):
            raise RuleError(f"{where}: bad houses {a[-1]!r}")
    elif op in ("in_sign", "lagna"):
        if op == "in_sign":
            _check_ref(a[0], where, dasha)
        bad = [s for s in _as_list(a[1] if op == "in_sign" else a) if s not in SIGNS]
        if bad:
            raise RuleError(f"{where}: unknown sign {bad}")
    elif op == "dignity":
        _check_ref(a[0], where, dasha)
        if not set(_as_list(a[1])) <= DIGNITIES:
            raise RuleError(f"{where}: unknown dignity in {a[1]!r}")
    elif op == "count_dignity":
        if not set(_as_list(a[0])) <= DIGNITIES:
            raise RuleError(f"{where}: unknown dignity in {a[0]!r}")
    elif op == "nature":
        _check_ref(a[0], where, dasha)
        if a[1] not in ("benefic", "malefic"):
            raise RuleError(f"{where}: nature must be benefic or malefic")
    elif op in ("conjunct", "aspected_by", "influenced_by"):
        _check_ref(a[0], where, dasha)
        if a[1] not in GROUPS:
            _check_ref(a[1], where, dasha)
    elif op in ("house_has", "house_only", "house_aspected_by"):
        _check_house(a[0], where, dasha)
        if a[1] not in GROUPS:
            _check_ref(a[1], where, dasha)
    elif op in ("exchange", "related", "mutual_kendra"):
        _check_ref(a[0], where, dasha)
        _check_ref(a[1], where, dasha)
    elif op == "count_in_houses":
        if a[0] not in GROUPS:
            raise RuleError(f"{where}: unknown group {a[0]!r}")
        for h in a[1]:
            _check_house(h, where, dasha)
    elif op == "all_in_houses":
        if a[0] not in GROUPS:
            raise RuleError(f"{where}: unknown group {a[0]!r}")


def _load_file(path: Path) -> list[dict]:
    doc = json.loads(path.read_text())
    src, kind = doc["source"], doc.get("kind", "natal")
    if kind not in ("natal", "dasha"):
        raise RuleError(f"{path.name}: kind must be natal or dasha")
    rules = []
    for raw in doc["rules"]:
        rid = raw.get("id") or f"{src['book']}.{src['chapter']}.{raw['verse']}"
        where = f"{path.name}:{rid}"
        missing = {"verse", "page", "areas", "tone", "text"} - set(raw)
        if missing:
            raise RuleError(f"{where}: missing {sorted(missing)}")
        if not set(raw["areas"]) <= AREAS or not raw["areas"]:
            raise RuleError(f"{where}: unknown life area in {raw['areas']}")
        if raw["tone"] not in TONES:
            raise RuleError(f"{where}: unknown tone {raw['tone']!r}")
        if kind == "dasha" and "md" not in raw.get("period", {}):
            raise RuleError(f"{where}: dasha rules need a period with at least 'md'")
        if raw.get("when"):
            check_condition(raw["when"], where, kind == "dasha")
        for v in raw.get("variants", []):
            check_condition(v["when"], where, kind == "dasha")
            if not v.get("text") or v.get("tone", "mixed") not in TONES:
                raise RuleError(f"{where}: bad variant")
        if not raw["text"] and not raw.get("variants"):
            raise RuleError(f"{where}: rule has no text")
        rules.append({**raw, "id": rid, "kind": kind,
                      "source": {**src, "verse": raw["verse"], "page": raw["page"]}})
    return rules


@lru_cache(maxsize=None)
def load_rules(directory: Path = RULES_DIR) -> tuple[dict, ...]:
    rules = [r for path in sorted(directory.glob("*.json")) for r in _load_file(path)]
    seen: set[str] = set()
    for r in rules:
        if r["id"] in seen:
            raise RuleError(f"duplicate rule id {r['id']}")
        seen.add(r["id"])
    return tuple(rules)


# --- matching --------------------------------------------------------------------------------
def _apply(rule: dict, ctx: Context) -> dict | None:
    ok, factors = evaluate(rule.get("when"), ctx)
    if not ok:
        return None
    texts = [rule["text"]] if rule["text"] else []
    tones = [rule["tone"]] if rule["text"] else []
    for v in rule.get("variants", []):
        v_ok, v_factors = evaluate(v["when"], ctx)
        if v_ok:
            texts.append(v["text"])
            tones.append(v.get("tone", rule["tone"]))
            factors = factors + v_factors
    if not texts:
        return None
    return {"id": rule["id"], "areas": rule["areas"], "tone": _combine(tones), "text": " ".join(texts),
            "factors": list(dict.fromkeys(factors)), "source": rule["source"]}


def _combine(tones: list[str]) -> str:
    """One label for a rule whose base text and matched variants may differ in tone."""
    found = set(tones)
    if "mixed" in found or {"favourable", "challenging"} <= found:
        return "mixed"
    for tone in ("challenging", "favourable"):
        if tone in found:
            return tone
    return "neutral"


def match(chart: Chart, yogas: dict | None = None, rules: tuple[dict, ...] | None = None) -> list[dict]:
    """Natal rules that apply to the chart, in library order."""
    ctx = Context(chart, yogas)
    hits = (_apply(r, ctx) for r in (rules if rules is not None else load_rules()) if r["kind"] == "natal")
    return [h for h in hits if h]


def match_period(chart: Chart, md: str, ad: str | None = None, yogas: dict | None = None,
                 rules: tuple[dict, ...] | None = None) -> list[dict]:
    """Dasha rules for a mahadasha (``ad`` is None) or for one antardasha within it."""
    ctx = Context(chart, yogas, md, ad)
    out = []
    for r in (rules if rules is not None else load_rules()):
        if r["kind"] != "dasha" or r["period"]["md"] not in (md, "any") or r["period"].get("ad") != ad:
            continue
        hit = _apply(r, ctx)
        if hit:
            out.append({**hit, "period": {"md": md, "ad": ad}})
    return out
