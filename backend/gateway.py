"""
API Gateway — mounts ASR, TTS, Coach, Personalization under one process.
Free-tier friendly: single worker, lazy model loading.

Routes:
  /asr/*          → ASR service
  /tts/*          → TTS service
  /coach/*        → Coaching engine
  /recommend/*    → Personalization
  /metrics        → Prometheus
  /health         → Overall health check
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

# Sub-apps
from asr.main   import app as asr_app
from tts.main   import app as tts_app
from coach.main import app as coach_app

# Personalization routes (lightweight — inline here)
from personalization.recommender import recommend_lessons, mark_lesson_complete
from personalization.model import UserMistakeIndex
from pydantic import BaseModel

gateway = FastAPI(
    title="Spoken English Coach API",
    version="1.0.0",
    description="Open-source spoken English coaching — ASR · TTS · AI Coach",
)

gateway.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Prometheus metrics ────────────────────────────────────────────────────────
Instrumentator().instrument(gateway).expose(gateway, endpoint="/metrics")

# ── Mount sub-applications ────────────────────────────────────────────────────
gateway.mount("/asr",   asr_app)
gateway.mount("/tts",   tts_app)
gateway.mount("/coach", coach_app)


# ── Personalization endpoints ─────────────────────────────────────────────────

class AddMistakeRequest(BaseModel):
    user_id: str
    mistake_text: str
    tags: list[str] = []
    score: int = 5


@gateway.get("/recommend/{user_id}")
async def get_recommendations(user_id: str, n: int = 3):
    lessons = await recommend_lessons(user_id, n=n)
    return {"user_id": user_id, "recommendations": lessons}


@gateway.post("/recommend/mistake")
async def add_mistake(req: AddMistakeRequest):
    idx = UserMistakeIndex(req.user_id)
    idx.add(req.mistake_text, req.tags, req.score)
    return {"added": True, "total_mistakes": len(idx)}


@gateway.post("/recommend/complete/{user_id}/{lesson_id}")
async def complete_lesson(user_id: str, lesson_id: str):
    await mark_lesson_complete(user_id, lesson_id)
    return {"marked_complete": lesson_id}


# ── Root health ───────────────────────────────────────────────────────────────

@gateway.get("/health")
async def health():
    return {
        "status": "ok",
        "services": ["asr", "tts", "coach", "personalization"],
    }


# Alias for Render's health check path
@gateway.get("/")
async def root():
    return {"service": "Spoken English Coach API", "docs": "/docs"}


# ── Dev run ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("gateway:gateway", host="0.0.0.0", port=8000, reload=True)

app = gateway   # Uvicorn entrypoint
