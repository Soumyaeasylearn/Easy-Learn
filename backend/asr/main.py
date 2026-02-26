"""
ASR Microservice — Whisper (primary) + Vosk (fallback)
Endpoint: /asr  — WebSocket streaming, returns partial + final transcripts
Optimized for free-tier memory limits (~512 MB RAM on Render)
"""

import asyncio
import io
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
import whisper
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("asr")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ASR Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model Loading ────────────────────────────────────────────────────────────
# "tiny" model: ~39 MB, runs on CPU in ~1-2 s — perfect for free tier
_whisper_model: Optional[whisper.Whisper] = None
_vosk_model = None


def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        model_size = os.getenv("WHISPER_MODEL", "tiny")   # tiny / base / small
        logger.info(f"Loading Whisper [{model_size}]…")
        _whisper_model = whisper.load_model(model_size)
        logger.info("Whisper ready.")
    return _whisper_model


def get_vosk():
    global _vosk_model
    if _vosk_model is None:
        try:
            from vosk import Model
            model_path = os.getenv("VOSK_MODEL_PATH", "vosk-model-small-en-us-0.15")
            if Path(model_path).exists():
                _vosk_model = Model(model_path)
                logger.info("Vosk fallback ready.")
            else:
                logger.warning("Vosk model path not found — fallback disabled.")
        except ImportError:
            logger.warning("Vosk not installed — fallback disabled.")
    return _vosk_model


# ── Transcription Helpers ────────────────────────────────────────────────────

async def transcribe_whisper(audio_bytes: bytes) -> dict:
    """Transcribe using Whisper tiny. Returns {text, language, segments}."""
    model = get_whisper()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.transcribe(
                tmp_path,
                language="en",
                fp16=False,                 # CPU-safe
                temperature=0.0,
                best_of=1,
                beam_size=1,               # fast decode
                condition_on_previous_text=False,
            ),
        )
        return {
            "text": result["text"].strip(),
            "language": result.get("language", "en"),
            "segments": [
                {"start": s["start"], "end": s["end"], "text": s["text"]}
                for s in result.get("segments", [])
            ],
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def transcribe_vosk(audio_bytes: bytes) -> dict:
    """Fallback transcription with Vosk (offline, lightweight)."""
    vosk = get_vosk()
    if vosk is None:
        raise RuntimeError("Vosk model unavailable.")
    from vosk import KaldiRecognizer
    rec = KaldiRecognizer(vosk, 16000)
    rec.SetWords(True)
    data, _ = sf.read(io.BytesIO(audio_bytes), dtype="int16")
    chunk_size = 4000
    for i in range(0, len(data), chunk_size):
        rec.AcceptWaveform(data[i : i + chunk_size].tobytes())
    final = json.loads(rec.FinalResult())
    return {"text": final.get("text", ""), "language": "en", "segments": []}


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "model": os.getenv("WHISPER_MODEL", "tiny")}


@app.post("/asr/transcribe")
async def transcribe_file(audio: UploadFile = File(...)):
    audio_data = await audio.read()
    """Single-shot transcription for short clips (< 30 s)."""
    try:
        result = await transcribe_whisper(audio_data)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"Whisper failed: {e}. Trying Vosk…")
        try:
            result = transcribe_vosk(audio_data)
            return {"success": True, "fallback": "vosk", **result}
        except Exception as e2:
            raise HTTPException(status_code=500, detail=str(e2))


@app.websocket("/asr")
async def websocket_asr(ws: WebSocket):
    """
    WebSocket streaming ASR.
    Protocol:
      Client → binary frames (16-bit PCM 16 kHz mono)
      Client → text "DONE" to signal end of utterance
      Server → JSON partial transcript or final result
    """
    await ws.accept()
    logger.info("WebSocket ASR session opened.")
    buffer = bytearray()

    try:
        while True:
            msg = await ws.receive()

            if msg["type"] == "websocket.receive":
                if "bytes" in msg and msg["bytes"]:
                    chunk = msg["bytes"]
                    buffer.extend(chunk)
                    # Send interim partial every ~0.5 s of audio (8000 bytes @ 16 kHz 16-bit)
                    if len(buffer) >= 8000:
                        partial = await _partial_decode(bytes(buffer))
                        await ws.send_json({"type": "partial", "text": partial})

                elif "text" in msg and msg["text"] == "DONE":
                    if buffer:
                        try:
                            result = await transcribe_whisper(bytes(buffer))
                        except Exception:
                            result = transcribe_vosk(bytes(buffer))
                        await ws.send_json({"type": "final", **result})
                    buffer.clear()

    except WebSocketDisconnect:
        logger.info("WebSocket ASR session closed.")


async def _partial_decode(audio_bytes: bytes) -> str:
    """Quick partial decode — reuse last 2 s to stay fast."""
    # Only decode the last 2 s window for speed
    window = audio_bytes[-64000:] if len(audio_bytes) > 64000 else audio_bytes
    try:
        result = await transcribe_whisper(window)
        return result["text"]
    except Exception:
        return ""
