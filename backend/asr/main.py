"""
ASR Microservice — Whisper via HuggingFace Inference API (free tier)
No local model loading — stays within 512MB RAM limit on Render free tier.
"""

import logging
import os
import asyncio

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
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

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_ASR_URL = "https://api-inference.huggingface.co/models/openai/whisper-tiny.en"


async def transcribe_hf(audio_bytes: bytes) -> dict:
    """Transcribe using HuggingFace Whisper API — no local model needed."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            HF_ASR_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            content=audio_bytes,
        )
        if resp.status_code == 503:
            await asyncio.sleep(10)
            resp = await client.post(
                HF_ASR_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                content=audio_bytes,
            )
        resp.raise_for_status()
        result = resp.json()
        text = result.get("text", "").strip()
        return {"text": text, "language": "en", "segments": []}


def _rule_based_transcribe() -> dict:
    return {"text": "", "language": "en", "segments": []}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mode": "huggingface-api",
        "hf_token_set": bool(HF_TOKEN),
    }


@app.post("/transcribe")
async def transcribe_file(request: Request):
    audio_data = await request.body()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio payload.")
    try:
        result = await transcribe_hf(audio_data)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"HF ASR failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ASR failed: {e}"
        )


@app.websocket("/ws")
async def websocket_asr(ws: WebSocket):
    await ws.accept()
    logger.info("WebSocket ASR session opened.")
    buffer = bytearray()

    try:
        while True:
            msg = await ws.receive()
            if msg["type"] == "websocket.disconnect":
                break
            if msg["type"] == "websocket.receive":
                if "bytes" in msg and msg["bytes"]:
                    buffer.extend(msg["bytes"])
                    if len(buffer) >= 8000:
                        await ws.send_json({"type": "partial", "text": "..."})
                elif "text" in msg and msg["text"] == "DONE":
                    if buffer:
                        try:
                            result = await transcribe_hf(bytes(buffer))
                        except Exception:
                            result = _rule_based_transcribe()
                        await ws.send_json({"type": "final", **result})
                    buffer.clear()
    except WebSocketDisconnect:
        logger.info("WebSocket ASR session closed.")
