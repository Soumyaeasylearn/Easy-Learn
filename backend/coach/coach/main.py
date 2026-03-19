"""
Coaching Engine — LLaMA-3 via Groq API (free tier, fast)
Endpoint: POST /coach
"""

import logging
import os
import re
import json
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.db import get_supabase

logger = logging.getLogger("coach")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Coaching Engine", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama3-8b-8192"

SYSTEM_PROMPT = """You are an encouraging English speaking coach for non-native speakers.
Analyze the student's spoken transcript and respond with a JSON object containing:
{
  "correction": "Corrected version of their sentence (if needed, else null)",
  "explanation": "Brief, friendly grammar/pronunciation note (1 sentence)",
  "vocabulary": ["up to 2 better word suggestions if applicable"],
  "encouragement": "A short motivating sentence",
  "score": <integer 1-10 fluency estimate>,
  "tags": ["error_type tags like: grammar, pronunciation, vocabulary, fluency"]
}
Rules: be positive, keep total output under 120 words, use simple English. Respond with JSON only."""


async def call_groq(transcript: str, level: str = "beginner") -> dict:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": f'Student level: {level}\nTranscript: "{transcript}"'},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group())
            raise ValueError(f"No JSON in response: {content[:200]}")
    except Exception as e:
        logger.warning(f"Groq failed: {e}. Using rule-based fallback.")
        return _rule_based_feedback(transcript)


def _rule_based_feedback(transcript: str) -> dict:
    tags = []
    word_count = len(transcript.split())
    correction = None
    if re.search(r'\b(i is|he are|she are|they is)\b', transcript, re.I):
        tags.append("grammar")
        correction = re.sub(r'\bi is\b', 'I am', transcript, flags=re.I)
    if word_count < 5:
        tags.append("fluency")
    return {
        "correction": correction,
        "explanation": "Keep practicing — every sentence makes you better!",
        "vocabulary": [],
        "encouragement": "Great effort! You're improving every day. 🎉",
        "score": min(10, max(1, word_count // 2)),
        "tags": tags or ["fluency"],
    }


async def save_session(user_id: str, transcript: str, feedback: dict):
    try:
        supabase = get_supabase()
        supabase.table("coaching_sessions").insert({
            "user_id": user_id,
            "transcript": transcript,
            "correction": feedback.get("correction"),
            "score": feedback.get("score"),
            "tags": feedback.get("tags", []),
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        logger.error(f"Supabase insert failed: {e}")


async def get_user_level(user_id: str) -> str:
    try:
        supabase = get_supabase()
        result = supabase.table("profiles").select("level").eq("id", user_id).single().execute()
        return result.data.get("level", "beginner") if result.data else "beginner"
    except Exception:
        return "beginner"


class CoachRequest(BaseModel):
    user_id: str
    transcript: str
    lesson_context: Optional[str] = None


class CoachResponse(BaseModel):
    correction: Optional[str]
    explanation: str
    vocabulary: list[str]
    encouragement: str
    score: int
    tags: list[str]


@app.get("/health")
async def health():
    return {"status": "ok", "groq_key_set": bool(GROQ_API_KEY)}


@app.post("/", response_model=CoachResponse)
async def coach(req: CoachRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty.")
    level = await get_user_level(req.user_id)
    feedback = await call_groq(req.transcript, level)
    import asyncio
    asyncio.create_task(save_session(req.user_id, req.transcript, feedback))
    return CoachResponse(**feedback)


@app.get("/history/{user_id}")
async def get_history(user_id: str, limit: int = 20):
    try:
        supabase = get_supabase()
        result = (
            supabase.table("coaching_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"sessions": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
