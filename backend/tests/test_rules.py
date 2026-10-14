import json
from datetime import datetime, timezone

import pytest

from app.engine.chart import build_chart
from app.engine.constants import PLANETS
from app.engine.yogas import all_yogas
from app.interpret import rules as R


@pytest.fixture(scope="module")
def chart():
    return build_chart(datetime(1990, 5, 15, 9, 0, tzinfo=timezone.utc), 28.65195, 77.23149)


@pytest.fixture(scope="module")
def library():
    return R.load_rules()


def test_library_loads_and_every_rule_is_cited(library):
    assert len(library) > 250
    assert len({r["id"] for r in library}) == len(library)
    for r in library:
        src = r["source"]
        assert src["book"] and src["chapter"] and src["verse"] and isinstance(src["page"], int), r["id"]


def test_house_lord_chapter_is_complete(library):
    """Chapter 26 has one verse per (lord, house); only verse 75 is withheld by policy."""
    seen = set()
    for r in library:
        if r["source"]["book"] != "bphs-sharma" or r["source"]["chapter"] != 26:
            continue
        cond = r["when"]["all"][0] if "all" in r["when"] else r["when"]
        ref, house = cond["in_house"]
        assert int(r["verse"]) == (int(ref[1:]) - 1) * 12 + house, r["id"]
        seen.add((int(ref[1:]), house))
    assert {(l, h) for l in range(1, 13) for h in range(1, 13)} - seen == {(7, 3)}


def test_each_house_lord_matches_at_most_one_placement(chart, library):
    hits = [m for m in R.match(chart, all_yogas(chart)) if m["source"]["book"] == "bphs-sharma" and m["source"]["chapter"] == 26]
    lords = [m["factors"][0].split(" lord")[0] for m in hits]
    assert len(lords) == len(set(lords)) and 10 <= len(hits) <= 12
    for m in hits:
        assert m["text"] and m["tone"] in R.TONES and m["factors"]


def test_matches_are_traceable_to_chart_factors(chart):
    # Virgo rising with Mercury (1st lord) in the 8th house.
    by_id = {m["id"]: m for m in R.match(chart, all_yogas(chart))}
    assert by_id["bphs-sharma.26.8"]["factors"] == ["1st lord Mercury in the 8th house"]
    assert by_id["bphs-sharma.36.31-32"]["factors"] == ["Virgo ascendant"]
    assert "bphs-sharma.77.malavya" in by_id  # engine detects Malavya Yoga for this chart


def test_variants_add_text_only_when_their_condition_holds(chart):
    rule = {"id": "t", "kind": "natal", "areas": ["general"], "tone": "neutral", "text": "base.",
            "source": {}, "when": {"lagna": "Virgo"},
            "variants": [{"when": {"in_house": ["L1", 8]}, "text": "yes.", "tone": "mixed"},
                         {"when": {"in_house": ["L1", 9]}, "text": "no."}]}
    (hit,) = R.match(chart, rules=(rule,))
    assert hit["text"] == "base. yes." and hit["tone"] == "mixed"
    assert hit["factors"] == ["Virgo ascendant", "1st lord Mercury in the 8th house"]


def test_condition_operators(chart):
    ctx = R.Context(chart)
    t = lambda cond: R.evaluate(cond, ctx)[0]
    assert t({"all": [{"lagna": "Virgo"}, {"in_house": ["Mercury", [8]]}]})
    assert not t({"all": [{"lagna": "Virgo"}, {"in_house": ["Mercury", 1]}]})
    assert t({"any": [{"lagna": "Aries"}, {"dignity": ["Venus", "exalted"]}]})
    assert t({"not": {"lagna": "Aries"}})
    assert t({"rules": ["Mercury", [1, 10]]}) and not t({"rules": ["Mercury", 5]})
    assert t({"in_house_from": ["Moon", "Sun", [9]]})
    assert t({"house_has": [["Sun", 1], "Sun"]})
    # every atomic predicate evaluates on a real chart
    for p in PLANETS:
        for cond in ({"strong": p}, {"weak": p}, {"combust": p}, {"retrograde": p},
                     {"conjunct": [p, "malefic"]}, {"aspected_by": [p, "benefic"]}):
            assert isinstance(t(cond), bool)


@pytest.mark.parametrize("bad", [
    {"in_house": ["L13", 1]},
    {"in_house": ["Pluto", 1]},
    {"in_house": ["L1", 13]},
    {"dignity": ["Sun", "happy"]},
    {"lagna": "Ophiuchus"},
    {"sideways": "Sun"},
    {"in_house": ["MD", 1]},            # dasha reference in a natal rule
    {"all": [{"lagna": "Aries"}], "any": []},
])
def test_malformed_conditions_are_rejected_at_load(bad):
    with pytest.raises(R.RuleError):
        R.check_condition(bad, "test")


def test_duplicate_ids_and_unknown_areas_are_rejected(tmp_path):
    doc = {"source": {"book": "b", "volume": 1, "chapter": 1}, "rules": [
        {"verse": "1", "page": 1, "areas": ["wealth"], "tone": "neutral", "text": "x"},
        {"verse": "1", "page": 1, "areas": ["wealth"], "tone": "neutral", "text": "y"}]}
    (tmp_path / "a.json").write_text(json.dumps(doc))
    with pytest.raises(R.RuleError, match="duplicate"):
        R.load_rules(tmp_path)
    doc["rules"] = [{"verse": "1", "page": 1, "areas": ["fame"], "tone": "neutral", "text": "x"}]
    (tmp_path / "a.json").write_text(json.dumps(doc))
    R.load_rules.cache_clear()
    with pytest.raises(R.RuleError, match="life area"):
        R.load_rules(tmp_path)


def test_dasha_rules_match_only_their_period(chart, library):
    yogas = all_yogas(chart)
    md_only = R.match_period(chart, "Jupiter", yogas=yogas)
    assert md_only and all(m["period"] == {"md": "Jupiter", "ad": None} for m in md_only)
    assert any(m["id"] == "bphs-sharma.49.45-48" for m in md_only)  # Jupiter in the 10th
    sub = R.match_period(chart, "Sun", "Jupiter", yogas)
    assert sub and all(m["source"]["chapter"] == 54 for m in sub)
    assert R.match(chart, yogas) and not any(m["id"].startswith("bphs-sharma.49") for m in R.match(chart, yogas))


def test_policy_no_longevity_or_death_predictions_in_rule_text(library):
    banned = ("long lived", "long-lived", "short lived", "short-lived", "longevity", "will die",
              "death", "killer", "maraka", "widow", "tubercul", "leprosy")
    for r in library:
        texts = [r["text"]] + [v["text"] for v in r.get("variants", [])]
        for text in texts:
            assert not any(b in text.lower() for b in banned), (r["id"], text)
            assert "cancer" not in text, (r["id"], text)  # the disease; the sign is capitalised


def test_conflicting_variant_tones_are_reported_as_mixed(chart):
    rule = {"id": "t", "kind": "natal", "areas": ["general"], "tone": "neutral", "text": "", "source": {},
            "variants": [{"when": {"lagna": "Virgo"}, "text": "good.", "tone": "favourable"},
                         {"when": {"in_house": ["L1", 8]}, "text": "bad.", "tone": "challenging"}]}
    (hit,) = R.match(chart, rules=(rule,))
    assert hit["tone"] == "mixed"
    rule["variants"].pop()
    (hit,) = R.match(chart, rules=(rule,))
    assert hit["tone"] == "favourable"


def test_every_house_has_a_judgement_rule_except_the_eighth(library):
    houses = {int(r["id"].split(".h")[1].split(".")[0]) for r in library
              if r["source"]["book"] == "bphs-sharma" and r["source"]["chapter"] == 13}
    assert houses == set(range(1, 13)) - {8}


def test_phaladeepika_covers_every_planet_in_every_house(library):
    pairs = {tuple(r["when"]["in_house"]) for r in library
             if r["source"]["book"] == "phaladeepika-sastri" and r["source"]["chapter"] == 8}
    assert pairs == {(p, h) for p in PLANETS for h in range(1, 13)}


def test_navamsa_lord_predicate(chart):
    from app.engine.constants import SIGN_LORDS
    from app.engine.vargas import varga_sign
    lord = SIGN_LORDS[varga_sign(chart.longitudes["Sun"], 9)]
    ctx = R.Context(chart)
    assert R.evaluate({"in_navamsa_of": ["Sun", lord]}, ctx)[0]
    assert not R.evaluate({"in_navamsa_of": ["Sun", [q for q in PLANETS[:7] if q != lord]]}, ctx)[0]
    with pytest.raises(R.RuleError):
        R.check_condition({"in_navamsa_of": ["Sun", "Rahu"]}, "test")
