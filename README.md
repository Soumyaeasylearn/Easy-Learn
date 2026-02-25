# 🎙 SpeakUp — Open-Source Spoken English Coach

> AI-powered spoken English coaching at **zero cost**.  
> Whisper · Kokoro · LLaMA-3 · FAISS · Supabase · Render · Vercel

[![CI/CD](https://github.com/YOUR_ORG/spoken-english-app/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/YOUR_ORG/spoken-english-app/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Architecture

```
Browser/App
    │
    ├─ WebSocket ──► /asr   Whisper tiny (→ Vosk fallback)
    ├─ POST ───────► /tts   Kokoro TTS   (→ pyttsx3 fallback)
    ├─ POST ───────► /coach LLaMA-3 via HF Inference API
    └─ GET/POST ───► /recommend  FAISS + Supabase personalization
                                    │
                              Supabase (Postgres + Auth)
```

All models are **open-source**. The entire stack runs on free tiers.

---

## Free-Tier Cost Breakdown

| Service      | Free Tier Limits              | Used For             |
|-------------|-------------------------------|----------------------|
| Render       | 512 MB RAM, 0.1 vCPU, 750 h/mo | Backend API          |
| Vercel       | 100 GB bandwidth/mo           | Next.js frontend     |
| Supabase     | 500 MB DB, 2 GB bandwidth     | Database + Auth      |
| HF Inference | ~30k tokens/day free          | LLaMA-3 coaching     |
| GitHub Actions | 2000 min/month              | CI/CD                |
| Grafana Cloud | 10k metrics free             | Monitoring           |

**Total: $0/month for up to ~100 daily active users.**

---

## Quick Start

### 1. Clone
```bash
git clone https://github.com/YOUR_ORG/spoken-english-app.git
cd spoken-english-app
```

### 2. Environment Variables
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env`:
```ini
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_KEY=your_supabase_anon_key
HF_TOKEN=hf_your_huggingface_token
WHISPER_MODEL=tiny          # tiny|base|small
KOKORO_LANG=a               # a=American, b=British
```

### 3. Run Backend Locally
```bash
cd backend
pip install -r asr/requirements.txt -r tts/requirements.txt -r coach/requirements.txt
pip install faiss-cpu sentence-transformers pydantic-settings supabase prometheus-fastapi-instrumentator
uvicorn gateway:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 4. Run Frontend Locally
```bash
cd frontend/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```
Open: http://localhost:3000

### 5. Run Tests
```bash
cd backend
pytest tests/ -v
```

---

## Deployment

### Backend → Render (free)

1. Push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your repo, select `backend/` as root
4. Settings:
   - **Build Command:** `pip install -r asr/requirements.txt -r tts/requirements.txt -r coach/requirements.txt && pip install faiss-cpu sentence-transformers pydantic-settings supabase prometheus-fastapi-instrumentator`
   - **Start Command:** `uvicorn gateway:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Instance Type:** Free
5. Add environment variables (SUPABASE_URL, SUPABASE_KEY, HF_TOKEN)
6. Copy the deploy hook URL → add to GitHub Secrets as `RENDER_DEPLOY_HOOK`

> ⚠️ Free Render instances spin down after 15 min of inactivity (cold start ~30 s). Use UptimeRobot (free) to ping `/health` every 14 min.

### Frontend → Vercel (free)

```bash
cd frontend/web
npm i -g vercel
vercel --prod
```
Set environment variable `NEXT_PUBLIC_API_URL` to your Render URL in Vercel dashboard.

### Database → Supabase (free)

1. Create project at [supabase.com](https://supabase.com)
2. Open SQL editor, paste contents of `infra/supabase_schema.sql`, run
3. Copy Project URL + anon key → set in `.env`

### CI/CD → GitHub Actions

Add these GitHub Secrets (Settings → Secrets → Actions):

| Secret               | Value                             |
|---------------------|-----------------------------------|
| `SUPABASE_URL`      | Your Supabase project URL         |
| `SUPABASE_KEY`      | Supabase anon key                 |
| `HF_TOKEN`          | Hugging Face access token         |
| `RENDER_DEPLOY_HOOK`| Render deploy hook URL            |
| `RENDER_APP_URL`    | e.g. https://myapp.onrender.com   |
| `VERCEL_TOKEN`      | Vercel API token                  |
| `VERCEL_ORG_ID`     | From `vercel whoami`              |
| `VERCEL_PROJECT_ID` | From `.vercel/project.json`       |
| `VERCEL_APP_URL`    | e.g. https://myapp.vercel.app     |

Copy `infra/ci-cd.yml` → `.github/workflows/ci-cd.yml` in your repo.

### Monitoring → Grafana Cloud (free)

1. Sign up at [grafana.com/products/cloud](https://grafana.com/products/cloud) (free tier: 10k metrics)
2. Add Prometheus data source, point to your Render app `/metrics`
3. Import `infra/monitoring/grafana-dashboard.json` → paste in Grafana → Import

---

## API Reference

### `POST /asr/transcribe`
```
Body: raw audio bytes (WAV, 16 kHz mono)
Response: { text, language, segments }
```

### `WS /asr`
```
Send: binary PCM frames → receive { type: "partial"|"final", text }
Send: "DONE" text → receive final transcript
```

### `POST /tts`
```json
{ "text": "Hello!", "ssml": false, "voice": "af_heart", "speed": 1.0, "format": "mp3" }
→ audio/mpeg stream
```

### `POST /coach`
```json
{ "user_id": "uuid", "transcript": "She play tennis." }
→ { correction, explanation, vocabulary, encouragement, score, tags }
```

### `GET /recommend/{user_id}`
```
→ { recommendations: [{ id, title, area, level }] }
```

### `POST /recommend/mistake`
```json
{ "user_id": "uuid", "mistake_text": "...", "tags": ["grammar"], "score": 6 }
```

---

## Testing Checklist

### ASR Accuracy
- [ ] Record 20 utterances at various difficulty levels
- [ ] Measure Word Error Rate (WER) — target < 15% for Whisper tiny
- [ ] Test with background noise (coffee shop recording)
- [ ] Verify WebSocket partial transcripts arrive within 1 s

### TTS Naturalness  
- [ ] Listen to 5 voices — rate naturalness 1–5
- [ ] Verify SSML `<break>` produces audible pause
- [ ] Check `<emphasis>` sounds louder/clearer
- [ ] Confirm MP3 file is valid and plays in all browsers

### Coaching Correctness
- [ ] Test 20 sentences with known errors — verify corrections
- [ ] Confirm grammar tags on grammar errors
- [ ] Confirm vocabulary suggestions are contextually appropriate
- [ ] Verify scores correlate with error density (few errors = high score)
- [ ] Confirm encouragement is always present and positive

### Personalization
- [ ] Add 10 grammar mistakes, call `/recommend` — verify grammar lessons appear
- [ ] Complete lesson, re-call `/recommend` — verify it's excluded
- [ ] Verify FAISS similarity search returns related past mistakes

### End-to-End Flow
- [ ] Open web app in Chrome + Safari
- [ ] Record 5 s of speech → transcript appears < 3 s
- [ ] Feedback panel renders with score, correction, encouragement
- [ ] TTS correction plays back automatically
- [ ] Profile page shows session history and streak
- [ ] Badges unlock correctly

### Load Test (100 users)
```bash
# Install: pip install locust
# Run: locust -f locustfile.py --headless -u 100 -r 10 --run-time 60s
```

---

## Project Structure

```
spoken-english-app/
├── backend/
│   ├── gateway.py              ← Single Uvicorn entry point
│   ├── asr/main.py             ← Whisper + Vosk ASR
│   ├── tts/main.py             ← Kokoro + pyttsx3 TTS
│   ├── coach/main.py           ← LLaMA-3 coaching engine
│   ├── personalization/
│   │   ├── model.py            ← FAISS user mistake index
│   │   └── recommender.py      ← Adaptive lesson recommender
│   ├── common/{config,db,logger}.py
│   ├── tests/                  ← pytest test suite
│   └── Dockerfile
├── frontend/
│   ├── web/                    ← Next.js (Vercel)
│   │   ├── pages/{index,lesson,profile}.js
│   │   └── components/{AudioRecorder,TranscriptDisplay,FeedbackPanel}.js
│   └── mobile/                 ← React Native (Expo)
│       ├── App.js
│       └── screens/{LessonScreen}.js
├── infra/
│   ├── supabase_schema.sql     ← Full DB schema + RLS policies
│   ├── ci-cd.yml               ← GitHub Actions pipeline
│   └── monitoring/             ← Prometheus + Grafana
└── README.md
```

---

## Contributing

1. Fork the repo
2. Create feature branch: `git checkout -b feat/your-feature`
3. Run tests: `pytest backend/tests/ -v`
4. Submit a PR — CI runs automatically
5. 

---

## License

MIT — use it, fork it, ship it. 🚀
