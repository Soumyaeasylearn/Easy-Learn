from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io, os, re, textwrap, asyncio, logging

logger = logging.getLogger("tts")
app = FastAPI(title="TTS Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def parse_ssml(text):
    text = re.sub(r'<break[^/]*/>', ' ', text)
    text = re.sub(r'<[^>]+>', '', text)
    return text.strip()

class TTSRequest(BaseModel):
    text: str
    ssml: bool = False
    voice: str = "af_heart"
    speed: float = 1.0
    format: str = "mp3"

@app.get("/health")
async def health():
    return {"status": "ok", "kokoro": False}

@app.get("/voices")
async def voices():
    return {"voices": [
        {"id": "af_heart", "name": "Heart (Female, American)"},
        {"id": "am_adam", "name": "Adam (Male, American)"},
    ]}

@app.post("/")
async def synthesize(req: TTSRequest):
    text = parse_ssml(req.text) if req.ssml else req.text
    try:
        import pyttsx3, tempfile
        def _run():
            engine = pyttsx3.init()
            engine.setProperty("rate", 150)
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
            engine.save_to_file(text, path)
            engine.runAndWait()
            with open(path, "rb") as f:
                data = f.read()
            os.unlink(path)
            return data
        audio = await asyncio.get_event_loop().run_in_executor(None, _run)
        media_type = "audio/wav"
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        audio = b""
        media_type = "audio/wav"
    return StreamingResponse(io.BytesIO(audio), media_type=media_type)
```

Scroll down → click **"Commit new file"** ✅

---

## Create `backend/coach` folder with files

### Step 6 — Create `coach/__init__.py`
Click **"Add file"** → **"Create new file"**

Type in filename box:
```
coach/__init__.py
```
Leave content **empty** → click **"Commit new file"** ✅

---

### Step 7 — Create `coach/main.py`
Click **"Add file"** → **"Create new file"**

Type in filename box:
```
coach/main.py
