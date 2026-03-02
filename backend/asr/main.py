import os
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ASR Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_ASR_URL = "https://api-inference.huggingface.co/models/openai/whisper-tiny.en"

@app.get("/health")
async def health():
    return {"status": "ok", "model": "whisper-tiny.en (HF API)"}

@app.post("/transcribe")
async def transcribe_file(audio: UploadFile = File(...)):
    audio_data = await audio.read()
    if not audio_data:
        raise HTTPException(status_code=400, detail="Empty audio")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            HF_ASR_URL,
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            content=audio_data,
        )
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="ASR service error")
    result = response.json()
    text = result.get("text", "").strip()
    return {"success": True, "text": text}
