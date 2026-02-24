"""Tests for ASR microservice."""
import asyncio
import io
import wave
import struct
import pytest
from fastapi.testclient import TestClient
from asr.main import app, transcribe_whisper

client = TestClient(app)


def _make_silence_wav(duration_s: float = 1.0, rate: int = 16000) -> bytes:
    """Generate a silent WAV file for testing."""
    buf = io.BytesIO()
    n_frames = int(rate * duration_s)
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{n_frames}h", *([0] * n_frames)))
    buf.seek(0)
    return buf.read()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_transcribe_silence():
    """Silence should return empty or near-empty transcript without crashing."""
    wav = _make_silence_wav(2.0)
    resp = client.post("/asr/transcribe", content=wav)
    assert resp.status_code == 200
    data = resp.json()
    assert "text" in data
    assert isinstance(data["text"], str)


@pytest.mark.asyncio
async def test_whisper_returns_string():
    wav = _make_silence_wav(1.0)
    result = await transcribe_whisper(wav)
    assert isinstance(result["text"], str)
    assert "language" in result


def test_transcribe_invalid_audio():
    """Garbage bytes should not crash the service."""
    resp = client.post("/asr/transcribe", content=b"not_audio_data")
    # Expect either a 200 (with empty text) or a handled 500
    assert resp.status_code in (200, 500)


# ── ASR Accuracy Benchmark ───────────────────────────────────────────────────
# Run separately with: pytest -k benchmark --benchmark
BENCHMARK_PAIRS = [
    # (label, expected_keywords)
    # Add real .wav fixtures here for CI accuracy tests
]


@pytest.mark.parametrize("label,keywords", BENCHMARK_PAIRS)
def test_asr_accuracy(label, keywords):
    pass  # placeholder for real benchmark fixtures
