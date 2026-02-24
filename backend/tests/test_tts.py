"""Tests for TTS microservice."""
import pytest
from fastapi.testclient import TestClient
from tts.main import app, parse_ssml

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200


def test_list_voices():
    resp = client.get("/tts/voices")
    assert resp.status_code == 200
    data = resp.json()
    assert "voices" in data
    assert len(data["voices"]) >= 1


def test_tts_returns_audio():
    resp = client.post("/tts", json={"text": "Hello, let's practise English today!", "format": "wav"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("audio/")
    assert len(resp.content) > 1000   # some actual audio data


def test_tts_empty_text_rejected():
    resp = client.post("/tts", json={"text": "", "format": "wav"})
    assert resp.status_code in (400, 422)


def test_tts_long_text():
    long_text = "This is a test sentence. " * 50
    resp = client.post("/tts", json={"text": long_text, "format": "wav"})
    assert resp.status_code == 200


# ── SSML Parser Tests ────────────────────────────────────────────────────────

def test_parse_ssml_break():
    ssml = 'Hello <break time="500ms"/> world'
    result = parse_ssml(ssml)
    assert "Hello" in result
    assert "world" in result
    assert "<break" not in result


def test_parse_ssml_emphasis():
    ssml = "This is <emphasis level='strong'>very important</emphasis>."
    result = parse_ssml(ssml)
    assert "very important" in result
    assert "<emphasis" not in result


def test_parse_ssml_prosody():
    ssml = '<prosody rate="slow">Speak slowly.</prosody>'
    result = parse_ssml(ssml)
    assert "Speak slowly" in result
    assert "<prosody" not in result


# ── TTS Naturalness Checklist (manual) ──────────────────────────────────────
# Run: python -m pytest backend/tests/test_tts.py -v
# Then listen to output WAVs and rate:
# [ ] Intonation sounds natural
# [ ] Pauses at punctuation
# [ ] No artifacts / clicks
# [ ] Speed is comfortable
