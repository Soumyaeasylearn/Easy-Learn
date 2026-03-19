// pages/lesson.js — Uses Chrome built-in speech recognition (no backend ASR needed)
import { useState, useRef, useCallback } from "react";
import Link from "next/link";
import Head from "next/head";
import FeedbackPanel from "../components/FeedbackPanel";

const API = process.env.NEXT_PUBLIC_API_URL || "https://your-render-app.onrender.com";

export default function LessonPage() {
  const [transcript, setTranscript] = useState("");
  const [partial,    setPartial]    = useState("");
  const [feedback,   setFeedback]   = useState(null);
  const [loading,    setLoading]    = useState(false);
  const [ttsUrl,     setTtsUrl]     = useState(null);
  const [state,      setState]      = useState("idle");
  const recognitionRef = useRef(null);

  const userId = typeof window !== "undefined"
    ? localStorage.getItem("user_id") || "00000000-0000-0000-0000-000000000000"
    : "00000000-0000-0000-0000-000000000000";

  async function getCoachFeedback(text) {
    setLoading(true);
    setFeedback(null);
    setTtsUrl(null);
    try {
      const coachRes = await fetch(`${API}/coach/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, transcript: text }),
      });
      const coachData = await coachRes.json();
      setFeedback(coachData);

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
  }

  function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Please use Google Chrome for speech recognition.");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.continuous = false;
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setState("recording");
      setPartial("");
      setTranscript("");
      setFeedback(null);
    };

    recognition.onresult = (event) => {
      let interimTranscript = "";
      let finalTranscript = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const t = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalTranscript += t;
        else interimTranscript += t;
      }
      if (interimTranscript) setPartial(interimTranscript);
      if (finalTranscript) {
        setTranscript(finalTranscript);
        setPartial("");
        setState("processing");
        getCoachFeedback(finalTranscript);
      }
    };

    recognition.onerror = (e) => {
      console.error("Speech error:", e.error);
      setState("idle");
      if (e.error === "not-allowed") {
        alert("Microphone access denied. Please allow microphone in Chrome settings.");
      }
    };

    recognition.onend = () => {
      if (state === "recording") setState("idle");
    };

    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setState("idle");
  }

  function toggle() {
    if (state === "idle") startListening();
    else if (state === "recording") stopListening();
  }

  const btnColor = { idle: "#7fff6e", recording: "#ff6e6e", processing: "#6b6b82" };
  const btnLabel = { idle: "🎙 Tap to Speak", recording: "⏹ Stop", processing: "⏳ Processing…" };

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

          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1rem" }}>
            <button
              onClick={toggle}
              disabled={state === "processing"}
              style={{
                width: 180, height: 60, borderRadius: 999,
                backgroundColor: btnColor[state],
                border: "none", cursor: state === "processing" ? "wait" : "pointer",
                fontWeight: 700, fontSize: 16, color: "#000",
              }}
            >
              {btnLabel[state]}
            </button>
            <p style={{ color: "var(--muted)", fontSize: ".85rem", fontFamily: "var(--mono)" }}>
              {state === "recording" ? "Listening… speak now" : "Powered by Chrome Speech API"}
            </p>
          </div>

          {(transcript || partial) && (
            <div style={{ background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: "1rem", padding: "1.5rem" }}>
              <p style={{ fontFamily: "var(--mono)", fontSize: ".85rem", color: "var(--muted)",
                marginBottom: ".5rem", textTransform: "uppercase", letterSpacing: ".06em" }}>
                Transcript
              </p>
              <p style={{ fontSize: "1.1rem", lineHeight: 1.7,
                color: partial && !transcript ? "var(--muted)" : "var(--text)",
                fontStyle: partial && !transcript ? "italic" : "normal" }}>
                {transcript || partial}
              </p>
            </div>
          )}

          {loading && (
            <p style={{ color: "var(--muted)", textAlign: "center", fontFamily: "var(--mono)" }}>
              Getting feedback…
            </p>
          )}

          {feedback && <FeedbackPanel feedback={feedback} ttsUrl={ttsUrl} />}
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
        .back-link { color: var(--muted); text-decoration: none; font-size: .9rem; transition: color .2s; }
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
