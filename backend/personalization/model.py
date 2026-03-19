"""
Personalization — simplified version without FAISS dependency.
Uses simple in-memory storage for mistake tracking.
"""

import json
import os
from pathlib import Path
from collections import Counter

INDEX_DIR = Path(os.getenv("FAISS_INDEX_DIR", "/tmp/faiss_indexes"))
INDEX_DIR.mkdir(parents=True, exist_ok=True)


class UserMistakeIndex:
    """Per-user mistake index stored as JSON (no FAISS needed)."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.meta_path = INDEX_DIR / f"{user_id}.json"
        self._meta: list[dict] = []
        self._load()

    def _load(self):
        if self.meta_path.exists():
            try:
                self._meta = json.loads(self.meta_path.read_text())
            except Exception:
                self._meta = []

    def _save(self):
        self.meta_path.write_text(json.dumps(self._meta))

    def add(self, mistake_text: str, tags: list[str], score: int):
        self._meta.append({"text": mistake_text, "tags": tags, "score": score})
        self._save()

    def search(self, query: str, k: int = 5) -> list[dict]:
        return self._meta[-k:] if self._meta else []

    def frequent_errors(self, top_n: int = 3) -> list[str]:
        all_tags = [tag for m in self._meta for tag in m.get("tags", [])]
        return [t for t, _ in Counter(all_tags).most_common(top_n)]

    def __len__(self):
        return len(self._meta)
