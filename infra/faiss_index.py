"""
infra/faiss_index.py
One-time setup: pre-populate FAISS index with example English errors
so new users get meaningful recommendations immediately.
Run: python infra/faiss_index.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from personalization.model import UserMistakeIndex

SEED_USER = "seed-example-user"

EXAMPLE_MISTAKES = [
    ("I go to school yesterday.", ["grammar"], 5),
    ("She don't like coffee.", ["grammar"], 4),
    ("He is more taller than me.", ["grammar"], 4),
    ("They was at home last night.", ["grammar"], 3),
    ("I am very exciting about the trip.", ["vocabulary"], 5),
    ("The weather is very heat today.", ["vocabulary"], 4),
    ("I need to make my homework.", ["vocabulary"], 5),
    ("Um, I, uh, want to say that, you know, it is good.", ["fluency"], 4),
    ("I speak English since five years.", ["grammar"], 5),
    ("The pronunciation of 'world' is dificult.", ["pronunciation"], 5),
]


def main():
    print(f"Building seed FAISS index for user [{SEED_USER}]…")
    idx = UserMistakeIndex(SEED_USER)
    for text, tags, score in EXAMPLE_MISTAKES:
        idx.add(text, tags, score)
        print(f"  ✓ Added: {text[:50]}")
    print(f"\nDone. Index contains {len(idx)} entries.")
    print(f"Stored at: {idx.index_path}")

    # Test search
    print("\nTest search: 'I goed to the store'")
    results = idx.search("I goed to the store", k=3)
    for r in results:
        print(f"  similarity={r['similarity']:.3f} | {r['text']}")

    print("\nMost common error areas:", idx.frequent_errors())


if __name__ == "__main__":
    main()
