"""
download_models.py
------------------
Run this ONCE during the Render build step (before uvicorn starts).
Downloads the Whisper model into a fixed path so the first real
request never has to wait for a network download.
"""

import os
import sys

MODEL_SIZE = os.getenv("WHISPER_MODEL", "tiny")
CACHE_DIR  = os.path.join(os.path.dirname(__file__), ".whisper_cache")

def main():
    print(f"[download_models] Downloading Whisper '{MODEL_SIZE}' → {CACHE_DIR}")
    try:
        import whisper
        model = whisper.load_model(MODEL_SIZE, download_root=CACHE_DIR)
        print(f"[download_models] ✓ Whisper '{MODEL_SIZE}' ready "
              f"({sum(p.numel() for p in model.parameters()):,} params)")
    except Exception as e:
        print(f"[download_models] ✗ Whisper download failed: {e}", file=sys.stderr)
        print("[download_models]   ASR will use Vosk fallback at runtime.")

if __name__ == "__main__":
    main()
