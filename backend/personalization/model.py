"""
Personalization — FAISS semantic search over a user's past mistakes.
Embeddings: sentence-transformers/all-MiniLM-L6-v2 (22 MB, CPU fast)
"""

import json
import os
from pathlib import Path
from typing import Optional

import numpy as np

# Lazy imports to save startup time
_embed_model = None
_faiss = None


def _get_encoder():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        _embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _embed_model


def _get_faiss():
    global _faiss
    if _faiss is None:
        import faiss as f
        _faiss = f
    return _faiss


INDEX_DIR = Path(os.getenv("FAISS_INDEX_DIR", "/tmp/faiss_indexes"))
INDEX_DIR.mkdir(parents=True, exist_ok=True)


class UserMistakeIndex:
    """Per-user FAISS index of past mistake embeddings."""

    DIM = 384   # all-MiniLM-L6-v2 output dim

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.index_path = INDEX_DIR / f"{user_id}.index"
        self.meta_path  = INDEX_DIR / f"{user_id}.json"
        self._index  = None
        self._meta: list[dict] = []
        self._load()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _load(self):
        faiss = _get_faiss()
        if self.index_path.exists():
            self._index = faiss.read_index(str(self.index_path))
            self._meta  = json.loads(self.meta_path.read_text())
        else:
            self._index = faiss.IndexFlatIP(self.DIM)  # inner product = cosine on normalized

    def _save(self):
        _get_faiss().write_index(self._index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self._meta))

    # ── Public API ───────────────────────────────────────────────────────────

    def add(self, mistake_text: str, tags: list[str], score: int):
        """Add a new mistake to the user's index."""
        enc = _get_encoder()
        vec = enc.encode([mistake_text], normalize_embeddings=True).astype("float32")
        self._index.add(vec)
        self._meta.append({"text": mistake_text, "tags": tags, "score": score})
        self._save()

    def search(self, query: str, k: int = 5) -> list[dict]:
        """Return top-k similar past mistakes."""
        if self._index.ntotal == 0:
            return []
        enc = _get_encoder()
        vec = enc.encode([query], normalize_embeddings=True).astype("float32")
        k = min(k, self._index.ntotal)
        scores, indices = self._index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                item = self._meta[idx].copy()
                item["similarity"] = float(score)
                results.append(item)
        return results

    def frequent_errors(self, top_n: int = 3) -> list[str]:
        """Return top-n most common error tag categories."""
        from collections import Counter
        all_tags = [tag for m in self._meta for tag in m.get("tags", [])]
        return [t for t, _ in Counter(all_tags).most_common(top_n)]

    def __len__(self):
        return self._index.ntotal
