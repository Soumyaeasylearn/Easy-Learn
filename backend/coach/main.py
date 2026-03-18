"""
Coaching Engine — LLaMA-3-8B-Instruct via Hugging Face Inference API (free tier)
Endpoint: POST /coach
Input:  { user_id, transcript, lesson_context? }
Output: { correction, vocabulary, encouragement, score, tags }
Progress stored in Supabase.

FIX: Updated HF Inference API URL to the v2 serverless endpoint format.
     Added Mistral-7B as fallback if LLaMA-3 is unavailable.
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from common.db import get_supabase
from common.config import settings

logger = logging.getLogger("coach")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Coaching Engine", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

HF_API_URL = (
    "https://api-inference.huggingface.co/models/"
    "meta-llama/Meta-Llama-3-8B-Instruct"
)
HF_FALLBACK_URL = (
    "https://api-inference.huggingface.co/models/"
    "mistralai/Mistral-7B-Instruct-v0.3"
)
HF_TOKEN = os.getenv("HF_TOKEN", "")

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
Rules: be positive, keep total output under 120 words, use simple English."""


async def _call_hf(url: str, prompt: str) -> dict:
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {HF_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 220,
                    "temperature": 0.3,
                    "return_full_text": False,
                    "stop": ["<|eot_id|>", "</s>", "[/INST]"],
                },
            },
        )
        if resp.status_code == 503:
            raise RuntimeError("Model loading (503) — retry later.")
        resp.raise_for_status()
        raw = resp.json()
        generated = raw[0]["generated_text"] if isinstance(raw, list) else raw.get("generated_text", "")
        match = re.search(r'\{.*?\}', generated, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON in LLM response: {generated[:200]}")
        import json
        return json.loads(match.group())


async def call_llama(transcript: str, level: str = "beginner") -> dict:
    prompt = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n"
        f"{SYSTEM_PROMPT}\nStudent level: {level}<|eot_id|>\n"
        f"<|start_header_id|>user<|end_header_id|>\n"
        f'Transcript: "{transcript}"<|eot_id|>\n'
        f"<|start_header_id|>assistant<|end_header_id|>\n"
    )

    for url, label in [(HF_API_URL, "LLaMA-3"), (HF_FALLBACK_URL, "Mistral-7B")]:
        try:
            result = await _call_hf(url, prompt)
            logger.info(f"Coach response via {label}")
            return result
        except Exception as e:
            logger.warning(f"{label} failed: {e}. Trying next…")

    logger.warning("All LLM endpoints failed — using rule-based fallback.")
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
    return {"status": "ok", "hf_token_set": bool(HF_TOKEN)}


@app.post("/coach", response_model=CoachResponse)
async def coach(req: CoachRequest):
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Transcript is empty.")

    level = await get_user_level(req.user_id)
    feedback = await call_llama(req.transcript, level)

    import asyncio
    asyncio.create_task(save_session(req.user_id, req.transcript, feedback))

    return CoachResponse(**feedback)


@app.get("/coach/history/{user_id}")
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
