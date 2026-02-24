from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import httpx, os, re, logging

logger = logging.getLogger("coach")

app = FastAPI(title="Coach Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3-8B-Instruct"
HF_TOKEN = os.getenv("HF_TOKEN", "")


def _rule_based_feedback(transcript):
    tags = []
    correction = None
    if re.search(r'\b(i is|he are|she are|they is)\b', transcript, re.I):
        tags.append("grammar")
        correction = re.sub(r'\bi is\b', 'I am', transcript, flags=re.I)
    words = len(transcript.split())
    if words < 5:
        tags.append("fluency")
    return {
        "correction": correction,
        "explanation": "Keep practising — every sentence makes you better!",
        "vocabulary": [],
        "encouragement": "Great effort! You are improving every day!",
        "score": min(10, max(1, words // 2)),
        "tags": tags or ["fluency"],
    }


async def call_llama(transcript, level="beginner"):
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                HF_API_URL,
                headers={"Authorization": f"Bearer {HF_TOKEN}"},
                json={
                    "inputs": transcript,
                    "parameters": {
                        "max_new_tokens": 200,
                        "temperature": 0.3,
                        "return_full_text": False
                    }
                },
            )
            resp.raise_for_status()
            raw = resp.json()[0]["generated_text"]
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                import json
                return json.loads(match.group())
    except Exception as e:
        logger.warning(f"LLaMA failed: {e}")
    return _rule_based_feedback(transcript)


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
        raise HTTPException(status_code=400, detail="Transcript is empty.")
    feedback = await call_llama(req.transcript)
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
        logger.error(f"DB save failed: {e}")
    return feedback


@app.get("/history/{user_id}")
async def history(user_id: str, limit: int = 20):
    try:
        from common.db import get_supabase
        sb = get_supabase()
        r = (
            sb.table("coaching_sessions")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"sessions": r.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---
