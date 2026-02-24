# ── Spoken English App — Backend Dockerfile ─────────────────────────────────
# Optimised for Render free tier: 512 MB RAM, shared CPU
# Build: docker build -t spoken-english-backend .
# Run:   docker run -p 8000:8000 --env-file .env spoken-english-backend

FROM python:3.11-slim AS base

# System deps (ffmpeg for audio conversion, libsndfile for soundfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Install all service requirements ─────────────────────────────────────────
COPY asr/requirements.txt     /tmp/req_asr.txt
COPY tts/requirements.txt     /tmp/req_tts.txt
COPY coach/requirements.txt   /tmp/req_coach.txt

RUN pip install --no-cache-dir \
    -r /tmp/req_asr.txt \
    -r /tmp/req_tts.txt \
    -r /tmp/req_coach.txt \
    faiss-cpu==1.8.0 \
    sentence-transformers==3.0.1 \
    pydantic-settings==2.2.1 \
    prometheus-fastapi-instrumentator==6.1.0

# ── Copy source ───────────────────────────────────────────────────────────────
COPY . /app/

# Pre-download Whisper tiny model into image layer (saves cold-start time)
RUN python -c "import whisper; whisper.load_model('tiny')" || true

# ── Entrypoint via unified gateway ───────────────────────────────────────────
# Uses a single Uvicorn process with sub-mounted apps to stay within free tier
EXPOSE 8000

CMD ["uvicorn", "gateway:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
