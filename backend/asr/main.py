import os
import httpx
import logging
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("asr")
app = FastAPI(title="ASR Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_ASR_URL = "https://router.huggingface.co/hf-inference/models/openai/whisper-tiny.en"

@app.get("/health")
async def health():
    return {"status": "ok", "model": "whisper-tiny.en (HF API)"}

@app.post("/transcribe")
async def transcribe_file(audio: UploadFile = File(...)):
    audio_data = await audio.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio")
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                HF_ASR_URL,
                headers={
                    "Authorization": f"Bearer {HF_TOKEN}",
                    "Content-Type": "audio/wav",
                },
                content=audio_data,
            )
        logger.info(f"HF response: {response.status_code} - {response.text}")
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"HF API error: {response.text}")
        result = response.json()
        text = result.get("text", "").strip()
        return {"success": True, "text": text}
    except Exception as e:
        logger.error(f"Transcribe error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_asr(ws):
    await ws.accept()
    await ws.send_json({"type": "partial", "text": ""})
    await ws.close()
