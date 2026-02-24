import os
import re
import logging
import httpx

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger("coach")

app = FastAPI(title="Coach Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"


def rule_based(transcript):
    words = len(transcript.split())
    correction = None
    tags = []
    if re.search(r'\bi is\b', transcript, re.I):
        correction = re.sub(r'\bi is\b', 'I am', transcript, flags=re.I)
        tags.append("grammar")
    if words < 5:
        tags.append("fluency")
    return {
        "correction": correction,
        "explanation": "Keep practising every day!",
        "vocabulary": [],
        "encouragement": "Great effort! You are improving!",
        "score": min(10, max(1, words // 2)),
        "tags": tags or ["fluency"],
    }


class CoachRequest(BaseModel):
    user_id: str
    transcript: str
    lesson_context: Optional[str] = None


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/")
async def coach(req: CoachRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")
    feedback = rule_based(req.transcript)
    try:
        from common.db import get_supabase
        from datetime import datetime
        sb = get_supabase()
        sb.table("coaching_sessions").insert({
            "user_id": req.user_id,
            "transcript": req.transcript,
            "correction": feedback.get("correction"),
            "score": feedback.get("score"),
            "tags": feedback.get("tags", []),
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"DB error: {e}")
    return feedback


@app.get("/history/{user_id}")
async def history(user_id: str, limit: int = 20):
    try:
        from common.db import get_supabase
        sb = get_supabase()
        r = sb.table("coaching_sessions").select("*").eq(
            "user_id", user_id
        ).order("created_at", desc=True).limit(limit).execute()
        return {"sessions": r.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
