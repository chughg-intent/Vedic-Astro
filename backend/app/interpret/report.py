"""Writes the readable report from matched rules with the Claude API.

The model never sees the birth data (name, date, time, place) - only the chart factors and the
readings the rule library matched. It must ground every paragraph in those readings and cite their
ids; ids it did not receive are dropped, so a citation always points at a real rule and page.
"""
from __future__ import annotations

import json
import re

import anthropic

MODEL = "claude-opus-5-5"
NAME_TOKEN = "{NAME}"

# Section titles and what each house governs, in report order. The 8th house is framed without
# longevity, which the sensitive-topics policy excludes.
HOUSES = {
    1: ("Personality and Physical Self", "your body, appearance, temperament and the overall direction of life"),
    2: ("Wealth, Family and Speech", "money and savings, family, food and the way you speak"),
    3: ("Siblings", "siblings, courage, initiative and communication"),
    4: ("Property, Education etc.", "property, education, mother, vehicles and general happiness"),
    5: ("Children, Mind and Intelligence", "children, mind, intelligence and creativity"),
    6: ("Health, Service and Opponents", "health tendencies, work and service, competition and debts"),
    7: ("Marriage and Partnerships", "marriage, the spouse and business partnerships"),
    8: ("Hidden Matters and Inheritance", "research, hidden matters, sudden changes and inheritance"),
    9: ("Fortune, Father and Dharma", "fortune, the father, religion, higher learning and long journeys"),
    10: ("Career and Status", "career, profession, status and reputation"),
    11: ("Gains and Friends", "income, gains, elder siblings, friends and the fulfilment of wishes"),
    12: ("Expenses, Travel and Liberation", "expenses, foreign lands, solitude and spiritual liberation"),
}

SYSTEM_PROMPT = """You write horoscope reports for a Vedic (Jyotish) astrology app. You are given the chart's key \
factors and a list of readings. Each reading is a paraphrase of a classical rule (from Brihat Parasara Hora Sastra or \
Phaladeepika) that the app has already matched against this chart, with the chart factors that triggered it.

Your job is to turn those readings into a clear, readable report written house by house, in the manner of a \
traditional astrologer's written reading.

Grounding
- Use only the readings provided. Do not add predictions, chart facts or classical rules that are not in the input.
- Every paragraph must cite the ids of the readings it draws on, in rule_ids. Never cite an id you were not given.
- You may explain what a chart factor means in plain words (e.g. what the 10th house governs) to make a reading clear.

Weighing readings
- Classical rules often disagree. Where they do, say so plainly and weigh them the way the texts do: a planet's dignity \
and strength, benefic versus malefic influence, and how many independent readings point the same way. Do not hide a \
challenging reading or average everything into vagueness; give a balanced picture.
- Several readings saying the same thing are a stronger indication than one; say when a theme recurs.
- Readings with tone "neutral" are descriptive or timing indications, not good or bad omens.

Sensitive topics (strict)
- Never predict death, life span, serious illness, accidents or harm to anyone. The readings have been filtered for \
this; do not reintroduce it.
- Health appears only as general tendencies ("health needs care"), never as a diagnosis.
- Do not frighten. Present challenges as tendencies to be aware of, not certainties, and avoid fatalistic language.
- Use gender-neutral language for the person and their partner ("spouse", "partner", "children").

Structure
- One section per house that has readings, using the house numbers and titles given in "houses". Assign each reading \
to the house its chart factor is about (e.g. "3rd lord in the 7th" belongs to the 3rd house; "Mars in the 5th house" \
to the 5th). A reading may be used in only one section.
- Each section starts with "intro": one sentence saying what the house refers to, e.g. "The third house of the \
horoscope mainly refers to siblings, courage and cleverness."
- Then 1-4 paragraphs. Open each paragraph with the chart factor behind it, in plain words, then say what it means \
for the reader - e.g. "Since the lord of your 3rd house is in the 7th, you are better suited to steady employment \
than to business." or "Mars is placed in your 5th house. You ..." Keep related readings together in one paragraph.
- "opening": one short paragraph introducing the reading as a whole, drawing out the two or three strongest themes.
- "current_period": what the running dasha and sub-period suggest. "transits": what the current planetary movements \
suggest; slow planets (Saturn, Rahu, Ketu, Jupiter) matter more than fast ones.
- Leave out a house, or leave a part empty, rather than padding it when there is nothing to say.

Style
- Address the reader as "you", directly and confidently, as an astrologer would ("You will prove a good worker"). \
Challenges are still framed as tendencies, never as certainties of harm.
- Where you would address the reader by name, write the placeholder {NAME} followed by a comma at the start of the \
sentence - e.g. "{NAME}, since the 5th lord is in the 2nd, ...". Use it at most once per section. Never guess a name.
- Plain English for someone who knows little astrology; introduce Sanskrit terms only with a short gloss.
- Do not mention books, chapters, verses or rule ids in the text - sources are tracked separately in rule_ids.
- Be specific, not generic; avoid filler and flattery."""

_PARAGRAPHS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "rule_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["text", "rule_ids"],
        "additionalProperties": False,
    },
}
REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "opening": _PARAGRAPHS,
        "houses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "house": {"type": "integer", "enum": list(HOUSES)},
                    "intro": {"type": "string"},
                    "paragraphs": _PARAGRAPHS,
                },
                "required": ["house", "intro", "paragraphs"],
                "additionalProperties": False,
            },
        },
        "current_period": _PARAGRAPHS,
        "transits": _PARAGRAPHS,
    },
    "required": ["opening", "houses", "current_period", "transits"],
    "additionalProperties": False,
}


class ReportError(RuntimeError):
    """The report could not be written; ``status`` is the HTTP status the API should return."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


def _reading(m: dict) -> dict:
    src = m["source"]
    out = {"id": m["id"], "tone": m["tone"], "areas": m["areas"], "text": m["text"], "because": m["factors"],
           "source": f"{src['book']} ch. {src['chapter']} v. {src['verse']}"}
    if m.get("period"):
        out["period"] = m["period"]
    return out


def build_input(chart: dict) -> dict:
    """The payload sent to the model: chart factors and matched readings, no birth data."""
    interp = chart["interpretation"]
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    return {
        "chart": {
            "ascendant": chart["lagna"]["sign"],
            "moon": {"sign": moon["sign"]["name"], "nakshatra": moon["nakshatra"]["name"]},
            "planets": [{"name": p["name"], "sign": p["sign"]["name"], "house": p["house"], "dignity": p["dignity"],
                         "retrograde": p["retrograde"], "combust": p["combust"]}
                        for p in chart["planets"] if p["name"] != "Ascendant"],
            "current_dasha": chart["dasha"]["current"][:2],
            "transits_as_of": chart["transits"]["as_of"][:10],
        },
        "houses": [{"house": h, "title": t, "refers_to": what} for h, (t, what) in HOUSES.items()],
        # Rules without chart factors are reading principles, not statements about this chart.
        "natal_readings": [_reading(m) for m in interp["natal"] if m["factors"]],
        "current_period_readings": [_reading(m) for m in interp["current_period"]],
        "transit_readings": [_reading(m) for m in interp["transits"]],
    }


def personalise(text: str, name: str | None) -> str:
    """Put the person's name in place of the placeholder - the name itself is never sent to the model."""
    name = (name or "").strip()
    if name:
        return text.replace(NAME_TOKEN, name.split()[0])
    # No name: drop "{NAME}, " and capitalise what follows.
    text = re.sub(r"\{NAME\},?\s*(\w)", lambda m: m.group(1).upper(), text)
    return text.replace(NAME_TOKEN, "you")


def _clean(report: dict, known: set[str], name: str | None) -> dict:
    """Drop citations of ids the model was not given, empty parts, and fill in the name."""
    def paragraphs(ps):
        return [{"text": personalise(p["text"].strip(), name), "rule_ids": [i for i in p["rule_ids"] if i in known]}
                for p in ps if p["text"].strip()]

    houses = []
    for h in sorted(report["houses"], key=lambda h: h["house"]):
        ps = paragraphs(h["paragraphs"])
        if ps and h["house"] in HOUSES and h["house"] not in {x["house"] for x in houses}:
            houses.append({"house": h["house"], "title": HOUSES[h["house"]][0],
                           "intro": personalise(h["intro"].strip(), name), "paragraphs": ps})
    return {"opening": paragraphs(report["opening"]), "houses": houses,
            "current_period": paragraphs(report["current_period"]), "transits": paragraphs(report["transits"])}


def complete_json(system: str, user_text: str, schema: dict, *, effort: str, what: str = "report",
                  max_tokens: int = 64000, client: anthropic.Anthropic | None = None):
    """One Claude call returning JSON that matches ``schema``. Returns (parsed dict, message)."""
    try:
        client = client or anthropic.Anthropic()
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=max_tokens,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # a safety-classifier false positive retries on another model instead of failing
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_text}],
        ) as stream:
            message = stream.get_final_message()
    except anthropic.AuthenticationError:
        raise ReportError("The Claude API rejected the credentials. Check ANTHROPIC_API_KEY.", 503)
    except anthropic.RateLimitError:
        raise ReportError("The Claude API is rate-limiting requests; try again in a minute.", 503)
    except anthropic.APIStatusError as e:
        raise ReportError(f"The Claude API returned an error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise ReportError("Could not reach the Claude API. Check the network connection.", 503)
    except TypeError as e:  # raised by the SDK when no credentials are configured
        if "api_key" in str(e) or "auth" in str(e).lower():
            raise ReportError("No Claude API credentials. Set ANTHROPIC_API_KEY before starting the backend.", 503)
        raise

    if message.stop_reason == "refusal":
        raise ReportError(f"The model declined to write this {what}.")
    if message.stop_reason == "max_tokens":
        raise ReportError(f"The {what} was cut off before it finished.")
    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        return json.loads(text), message
    except json.JSONDecodeError:
        raise ReportError(f"The model returned a {what} that could not be read.")


def usage_of(message) -> dict:
    u = message.usage
    return {"input_tokens": u.input_tokens, "output_tokens": u.output_tokens,
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", None)}


def write_report(chart: dict, client: anthropic.Anthropic | None = None) -> dict:
    payload = build_input(chart)
    known = {r["id"] for key in ("natal_readings", "current_period_readings", "transit_readings") for r in payload[key]}
    report, message = complete_json(
        SYSTEM_PROMPT, "Write the report for this chart.\n\n" + json.dumps(payload, ensure_ascii=False, sort_keys=True),
        REPORT_SCHEMA, effort="high", client=client)
    return {"report": _clean(report, known, chart["input"].get("name")), "model": message.model,
            "usage": usage_of(message)}
