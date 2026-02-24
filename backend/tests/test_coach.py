"""Tests for Coaching Engine."""
import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient
from coach.main import app, _rule_based_feedback

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200


# ── Rule-based Fallback Tests ─────────────────────────────────────────────────

def test_rule_based_grammar_error():
    result = _rule_based_feedback("I is going to school.")
    assert result["correction"] is not None
    assert "grammar" in result["tags"]
    assert 1 <= result["score"] <= 10


def test_rule_based_encouragement_present():
    result = _rule_based_feedback("She play tennis every day.")
    assert len(result["encouragement"]) > 0


def test_rule_based_short_text():
    result = _rule_based_feedback("Yes.")
    assert "fluency" in result["tags"]
    assert result["score"] >= 1


# ── Integration Tests with mocked LLM ────────────────────────────────────────

MOCK_FEEDBACK = {
    "correction": "She plays tennis every day.",
    "explanation": "Use 's' with third-person singular subjects.",
    "vocabulary": ["participates in"],
    "encouragement": "Almost perfect — great effort!",
    "score": 7,
    "tags": ["grammar"],
}


@patch("coach.main.call_llama", new_callable=AsyncMock, return_value=MOCK_FEEDBACK)
@patch("coach.main.get_user_level", new_callable=AsyncMock, return_value="beginner")
@patch("coach.main.save_session", new_callable=AsyncMock)
def test_coach_endpoint(mock_save, mock_level, mock_llm):
    resp = client.post("/coach", json={
        "user_id": "test-user-123",
        "transcript": "She play tennis every day.",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["score"] == 7
    assert "grammar" in data["tags"]
    assert data["correction"] == "She plays tennis every day."


def test_coach_empty_transcript():
    resp = client.post("/coach", json={
        "user_id": "test-user-123",
        "transcript": "   ",
    })
    assert resp.status_code == 400


# ── Correctness Checklist (manual evaluation) ─────────────────────────────────
# For 20 sample transcripts, verify:
# [ ] Corrections are grammatically accurate
# [ ] Explanations are beginner-friendly
# [ ] Score correlates with visible error density
# [ ] Encouragement tone is consistently positive
# [ ] Tags correctly categorise the error type
