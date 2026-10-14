"""Writes the readable report from matched rules with the Claude API.

The model never sees the birth data (name, date, time, place) - only the chart factors and the
readings the rule library matched. It must ground every paragraph in those readings and cite their
ids; ids it did not receive are dropped, so a citation always points at a real rule and page.
"""
from __future__ import annotations

import json

import anthropic

from .facts import LIFE_AREAS

MODEL = "claude-opus-5-5"
AREAS = list(LIFE_AREAS)

SYSTEM_PROMPT = """You write horoscope reports for a Vedic (Jyotish) astrology app. You are given the chart's key \
factors and a list of readings. Each reading is a paraphrase of a classical rule (from Brihat Parasara Hora Sastra or \
Phaladeepika) that the app has already matched against this chart, with the chart factors that triggered it.

Your job is to turn those readings into a clear, warm, readable report.

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

Style
- Plain English for someone who knows little astrology; introduce Sanskrit terms only with a short gloss.
- Address the reader as "you". Be specific, not generic; avoid filler and flattery.
- The overview: 2-3 short paragraphs drawing out the strongest themes across the whole chart.
- One section per life area that has readings, in the order given. Each: a one-sentence summary, then 1-4 paragraphs.
- Current period: what the running dasha and sub-period suggest. Transits: what the current planetary movements \
suggest, noting that slow planets (Saturn, Rahu, Ketu, Jupiter) matter more than fast ones.
- Leave a section's paragraphs empty rather than padding it when there is nothing to say."""

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
        "overview": _PARAGRAPHS,
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "area": {"type": "string", "enum": AREAS},
                    "summary": {"type": "string"},
                    "paragraphs": _PARAGRAPHS,
                },
                "required": ["area", "summary", "paragraphs"],
                "additionalProperties": False,
            },
        },
        "current_period": _PARAGRAPHS,
        "transits": _PARAGRAPHS,
    },
    "required": ["overview", "sections", "current_period", "transits"],
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
        "life_areas": [{"key": k, "title": a["title"]} for k, a in chart["life_areas"].items()],
        # Rules without chart factors are reading principles, not statements about this chart.
        "natal_readings": [_reading(m) for m in interp["natal"] if m["factors"]],
        "current_period_readings": [_reading(m) for m in interp["current_period"]],
        "transit_readings": [_reading(m) for m in interp["transits"]],
    }


def _clean(report: dict, known: set[str]) -> dict:
    """Drop citations of ids the model was not given, and empty sections."""
    def paragraphs(ps):
        out = []
        for p in ps:
            ids = [i for i in p["rule_ids"] if i in known]
            if p["text"].strip():
                out.append({"text": p["text"].strip(), "rule_ids": ids})
        return out

    order = {a: i for i, a in enumerate(AREAS)}
    sections = [{**s, "paragraphs": paragraphs(s["paragraphs"])} for s in report["sections"]]
    sections = [s for s in sections if s["paragraphs"]]
    sections.sort(key=lambda s: order.get(s["area"], len(order)))
    return {"overview": paragraphs(report["overview"]), "sections": sections,
            "current_period": paragraphs(report["current_period"]), "transits": paragraphs(report["transits"])}


def write_report(chart: dict, client: anthropic.Anthropic | None = None) -> dict:
    payload = build_input(chart)
    known = {r["id"] for key in ("natal_readings", "current_period_readings", "transit_readings") for r in payload[key]}
    try:
        client = client or anthropic.Anthropic()
        with client.beta.messages.stream(
            model=MODEL,
            max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # a safety-classifier false positive retries on another model instead of failing
            output_config={"effort": "high", "format": {"type": "json_schema", "schema": REPORT_SCHEMA}},
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": "Write the report for this chart.\n\n"
                                                  + json.dumps(payload, ensure_ascii=False, sort_keys=True)}],
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
        raise ReportError("The model declined to write this report.")
    if message.stop_reason == "max_tokens":
        raise ReportError("The report was cut off before it finished.")
    text = next((b.text for b in message.content if b.type == "text"), "")
    try:
        report = json.loads(text)
    except json.JSONDecodeError:
        raise ReportError("The model returned a report that could not be read.")
    usage = message.usage
    return {"report": _clean(report, known), "model": message.model,
            "usage": {"input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens,
                      "cache_read_input_tokens": getattr(usage, "cache_read_input_tokens", None)}}
