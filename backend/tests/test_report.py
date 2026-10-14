import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.interpret import report as R
from app.main import app

BIRTH = {"name": "Test Person", "date": "1990-05-15", "time": "14:30", "city": "Delhi", "country": "India",
         "latitude": 28.65195, "longitude": 77.23149, "timezone": "Asia/Kolkata"}


@pytest.fixture(scope="module")
def chart():
    return TestClient(app).post("/api/chart", json=BIRTH).json()


class FakeClient:
    """Stands in for anthropic.Anthropic: records the request and returns a canned message."""

    def __init__(self, text="", stop_reason="end_turn"):
        self.calls = []
        message = SimpleNamespace(stop_reason=stop_reason, model=R.MODEL,
                                  content=[SimpleNamespace(type="text", text=text)],
                                  usage=SimpleNamespace(input_tokens=1, output_tokens=2, cache_read_input_tokens=0))
        outer = self

        class Stream:
            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def get_final_message(self):
                return message

        def stream(**kwargs):
            outer.calls.append(kwargs)
            return Stream()

        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=stream))


def test_model_input_carries_readings_but_no_birth_data(chart):
    payload = R.build_input(chart)
    blob = json.dumps(payload)
    for private in ("Test Person", "1990-05-15", "14:30", "Delhi", "28.65"):
        assert private not in blob
    assert payload["natal_readings"] and all(r["because"] for r in payload["natal_readings"])
    assert {a["key"] for a in payload["life_areas"]} == set(R.AREAS)


def test_report_keeps_only_known_citations_and_orders_sections(chart):
    real = next(m["id"] for m in chart["interpretation"]["natal"] if m["factors"])
    fake_report = {
        "overview": [{"text": "Overview.", "rule_ids": [real, "made.up.id"]}],
        "sections": [
            {"area": "wealth", "summary": "W", "paragraphs": [{"text": "Money.", "rule_ids": [real]}]},
            {"area": "career", "summary": "C", "paragraphs": [{"text": "Work.", "rule_ids": []}]},
            {"area": "health", "summary": "H", "paragraphs": []},
        ],
        "current_period": [{"text": "Now.", "rule_ids": []}],
        "transits": [{"text": " ", "rule_ids": []}],
    }
    client = FakeClient(json.dumps(fake_report))
    out = R.write_report(chart, client=client)["report"]
    assert out["overview"] == [{"text": "Overview.", "rule_ids": [real]}]
    assert [s["area"] for s in out["sections"]] == ["career", "wealth"]  # LIFE_AREAS order; empty section dropped
    assert out["transits"] == []
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"]["format"]["schema"] == R.REPORT_SCHEMA


def test_refusal_and_truncation_raise(chart):
    with pytest.raises(R.ReportError, match="declined"):
        R.write_report(chart, client=FakeClient(stop_reason="refusal"))
    with pytest.raises(R.ReportError, match="cut off"):
        R.write_report(chart, client=FakeClient(stop_reason="max_tokens"))
