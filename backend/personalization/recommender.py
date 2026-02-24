"""
Adaptive Lesson Recommender
Combines FAISS mistake history + Supabase user profile
to generate personalised lesson plans.
"""

from __future__ import annotations
import logging
from typing import Optional

from common.db import get_supabase
from personalization.model import UserMistakeIndex

logger = logging.getLogger("recommender")

# ── Lesson Catalogue (static for prototype) ──────────────────────────────────

LESSONS = {
    "grammar": [
        {"id": "g1", "title": "Subject-Verb Agreement", "level": "beginner"},
        {"id": "g2", "title": "Past Simple vs Present Perfect", "level": "intermediate"},
        {"id": "g3", "title": "Conditional Sentences", "level": "advanced"},
    ],
    "vocabulary": [
        {"id": "v1", "title": "Common Phrasal Verbs", "level": "beginner"},
        {"id": "v2", "title": "Business English Vocabulary", "level": "intermediate"},
        {"id": "v3", "title": "Idiomatic Expressions", "level": "advanced"},
    ],
    "pronunciation": [
        {"id": "p1", "title": "Vowel Sounds Practice", "level": "beginner"},
        {"id": "p2", "title": "Stress and Rhythm", "level": "intermediate"},
        {"id": "p3", "title": "Connected Speech", "level": "advanced"},
    ],
    "fluency": [
        {"id": "f1", "title": "Filler Words & Hesitations", "level": "beginner"},
        {"id": "f2", "title": "Storytelling Techniques", "level": "intermediate"},
        {"id": "f3", "title": "Debate & Persuasion", "level": "advanced"},
    ],
}


async def get_user_profile(user_id: str) -> dict:
    try:
        sb = get_supabase()
        r = sb.table("profiles").select("*").eq("id", user_id).single().execute()
        return r.data or {}
    except Exception as e:
        logger.warning(f"Profile fetch failed: {e}")
        return {}


async def recommend_lessons(user_id: str, n: int = 3) -> list[dict]:
    """
    Recommend top-N lessons based on:
    1. User's frequent error tags (from FAISS index)
    2. User's level (from Supabase profile)
    3. Lessons not yet completed
    """
    profile = await get_user_profile(user_id)
    level    = profile.get("level", "beginner")
    done_ids = set(profile.get("completed_lessons", []))

    idx = UserMistakeIndex(user_id)
    weak_areas = idx.frequent_errors(top_n=4) if len(idx) > 0 else list(LESSONS.keys())

    recommendations = []
    for area in weak_areas:
        for lesson in LESSONS.get(area, []):
            if lesson["id"] not in done_ids and lesson["level"] == level:
                lesson_copy = lesson.copy()
                lesson_copy["area"] = area
                recommendations.append(lesson_copy)
                if len(recommendations) >= n:
                    return recommendations

    # Fill remaining slots with any unfinished lessons at the right level
    for area, lessons in LESSONS.items():
        for lesson in lessons:
            if lesson["id"] not in done_ids and lesson["level"] == level:
                lesson_copy = lesson.copy()
                lesson_copy["area"] = area
                if lesson_copy not in recommendations:
                    recommendations.append(lesson_copy)
                if len(recommendations) >= n:
                    return recommendations

    return recommendations[:n]


async def mark_lesson_complete(user_id: str, lesson_id: str):
    """Mark a lesson as complete in the user's Supabase profile."""
    try:
        sb = get_supabase()
        profile = (await get_user_profile(user_id))
        done = profile.get("completed_lessons", [])
        if lesson_id not in done:
            done.append(lesson_id)
        sb.table("profiles").update({"completed_lessons": done}).eq("id", user_id).execute()
    except Exception as e:
        logger.error(f"Failed to mark lesson complete: {e}")
