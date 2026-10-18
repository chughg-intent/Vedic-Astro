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
    assert [h["house"] for h in payload["houses"]] == list(range(1, 13))


def test_report_is_house_by_house_with_known_citations_and_the_name_filled_in(chart):
    real = next(m["id"] for m in chart["interpretation"]["natal"] if m["factors"])
    fake_report = {
        "opening": [{"text": "{NAME}, yours is a chart of steady effort.", "rule_ids": [real, "made.up.id"]}],
        "houses": [
            {"house": 5, "intro": "The fifth house refers to children.", "paragraphs": [{"text": "Mars is in your 5th.", "rule_ids": [real]}]},
            {"house": 3, "intro": "The third house refers to siblings.", "paragraphs": [{"text": "{NAME}, since the 3rd lord is in the 7th, you prefer employment.", "rule_ids": []}]},
            {"house": 8, "intro": "Empty.", "paragraphs": []},
            {"house": 3, "intro": "Duplicate.", "paragraphs": [{"text": "Again.", "rule_ids": []}]},
        ],
        "current_period": [{"text": "Now.", "rule_ids": []}],
        "transits": [{"text": " ", "rule_ids": []}],
    }
    client = FakeClient(json.dumps(fake_report))
    out = R.write_report(chart, client=client)["report"]
    assert out["opening"] == [{"text": "Test, yours is a chart of steady effort.", "rule_ids": [real]}]
    assert [h["house"] for h in out["houses"]] == [3, 5]  # house order; empty and duplicate dropped
    assert out["houses"][0]["title"] == "Siblings"
    assert out["houses"][0]["paragraphs"][0]["text"].startswith("Test, since the 3rd lord")
    assert out["transits"] == []
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5" and call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"]["format"]["schema"] == R.REPORT_SCHEMA
    assert "Test" not in json.dumps(call["messages"])


def test_name_placeholder_without_a_name():
    assert R.personalise("{NAME}, since the Sun is strong, you lead.", None) == "Since the Sun is strong, you lead."
    assert R.personalise("{NAME}, since x.", "  Gaurav Chugh ") == "Gaurav, since x."


def test_refusal_and_truncation_raise(chart):
    with pytest.raises(R.ReportError, match="declined"):
        R.write_report(chart, client=FakeClient(stop_reason="refusal"))
    with pytest.raises(R.ReportError, match="cut off"):
        R.write_report(chart, client=FakeClient(stop_reason="max_tokens"))


def test_access_code_and_daily_limit(chart, monkeypatch):
    import app.main as main
    client = TestClient(app)
    monkeypatch.setenv("ACCESS_CODE", "lotus")
    monkeypatch.setenv("REPORT_DAILY_LIMIT", "1")
    main._reports_today.update(day=None, count=0)
    calls = []
    monkeypatch.setattr(main.report_mod, "write_report", lambda c: calls.append(c) or {"report": {}})
    assert client.get("/api/config").json()["report_requires_code"] is True
    assert client.post("/api/report", json=BIRTH).status_code == 401
    assert client.post("/api/report", json=BIRTH, headers={"X-Access-Code": "wrong"}).status_code == 401
    assert client.post("/api/report", json=BIRTH, headers={"X-Access-Code": "lotus"}).status_code == 200
    assert client.post("/api/report", json=BIRTH, headers={"X-Access-Code": "lotus"}).status_code == 429
    assert len(calls) == 1
    monkeypatch.delenv("ACCESS_CODE")
    assert client.get("/api/config").json()["report_requires_code"] is False
