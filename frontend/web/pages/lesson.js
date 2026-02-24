// pages/lesson.js — Core practice screen: record → transcript → feedback
import { useState, useRef, useCallback } from "react";
import Link from "next/link";
import Head from "next/head";
import AudioRecorder from "../components/AudioRecorder";
import TranscriptDisplay from "../components/TranscriptDisplay";
import FeedbackPanel from "../components/FeedbackPanel";

const API = process.env.NEXT_PUBLIC_API_URL || "https://your-render-app.onrender.com";

export default function LessonPage() {
  const [transcript, setTranscript] = useState("");
  const [partial,    setPartial]    = useState("");
  const [feedback,   setFeedback]   = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [ttsUrl,     setTtsUrl]     = useState(null);

  const userId = typeof window !== "undefined"
    ? localStorage.getItem("user_id") || "demo-user" : "demo-user";

  // Called when recording finishes with final audio blob
  const handleRecordingComplete = useCallback(async (audioBlob) => {
    setLoading(true);
    setFeedback(null);
    setTtsUrl(null);
    setTranscript("");

    try {
      // 1. Transcribe
      const arrayBuffer = await audioBlob.arrayBuffer();
      const asr = await fetch(`${API}/asr/transcribe`, {
        method: "POST",
        body: arrayBuffer,
        headers: { "Content-Type": "audio/wav" },
      });
      const asrData = await asr.json();
      const text = asrData.text || "";
      setTranscript(text);

      if (!text.trim()) {
        setFeedback({ encouragement: "We couldn't hear you clearly — try again!", score: null });
        return;
      }

      // 2. Get coaching feedback
      const coachRes = await fetch(`${API}/coach`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, transcript: text }),
      });
      const coachData = await coachRes.json();
      setFeedback(coachData);

      // 3. Store mistake in personalization index (fire-and-forget)
      if (coachData.tags?.length) {
        fetch(`${API}/recommend/mistake`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: userId,
            mistake_text: coachData.correction || text,
            tags: coachData.tags,
            score: coachData.score,
          }),
        }).catch(() => {});
      }

      // 4. TTS — read out the correction
      if (coachData.correction) {
        const ttsRes = await fetch(`${API}/tts`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: coachData.correction, format: "mp3" }),
        });
        const blob = await ttsRes.blob();
        setTtsUrl(URL.createObjectURL(blob));
      }
    } catch (e) {
      console.error(e);
      setFeedback({ encouragement: "Something went wrong — please try again.", score: null });
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // WebSocket partial transcript handler
  const handlePartial = useCallback((text) => setPartial(text), []);

  return (
    <>
      <Head>
        <title>Practice — SpeakUp</title>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:ital,wght@0,400;1,400&display=swap" rel="stylesheet" />
      </Head>

      <div className="shell">
        <header className="top-bar">
          <Link href="/" className="back-link">← Home</Link>
          <span className="lesson-badge">Speaking Practice</span>
        </header>

        <main className="main">
          <h1 className="title">Say anything in English</h1>
          <p className="subtitle">Hit record and speak naturally — we'll coach you instantly.</p>

          <AudioRecorder
            onComplete={handleRecordingComplete}
            onPartial={handlePartial}
            wsUrl={`${API.replace("https", "wss").replace("http", "ws")}/asr`}
          />

          <TranscriptDisplay
            transcript={transcript}
            partial={partial}
            loading={loading}
          />

          {feedback && (
            <FeedbackPanel
              feedback={feedback}
              ttsUrl={ttsUrl}
            />
          )}
        </main>
      </div>

      <style jsx global>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --bg: #0a0a0f; --surface: #13131a; --border: #1e1e2e;
          --accent: #7fff6e; --text: #e8e8f0; --muted: #6b6b82;
          --font: 'Syne', sans-serif; --mono: 'DM Mono', monospace;
        }
        html, body { background: var(--bg); color: var(--text); font-family: var(--font); }
        .shell { max-width: 700px; margin: 0 auto; padding: 0 1.5rem; min-height: 100vh; }
        .top-bar { display: flex; align-items: center; justify-content: space-between;
          padding: 1.5rem 0; border-bottom: 1px solid var(--border); }
        .back-link { color: var(--muted); text-decoration: none; font-size: .9rem;
          transition: color .2s; }
        .back-link:hover { color: var(--accent); }
        .lesson-badge { background: var(--surface); border: 1px solid var(--border);
          border-radius: 999px; padding: .25rem .9rem; font-size: .8rem;
          font-family: var(--mono); color: var(--accent); }
        .main { padding: 3rem 0; display: flex; flex-direction: column; gap: 2rem; }
        .title { font-size: clamp(1.8rem, 4vw, 2.8rem); font-weight: 800; letter-spacing: -.02em; }
        .subtitle { color: var(--muted); font-size: 1rem; }
      `}</style>
    </>
  );
}
