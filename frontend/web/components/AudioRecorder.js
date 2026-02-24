// components/AudioRecorder.js
// Records audio from mic, streams via WebSocket for partials,
// sends final blob to onComplete. Falls back to MediaRecorder-only.

import { useState, useRef, useEffect } from "react";

const SAMPLE_RATE = 16000;

export default function AudioRecorder({ onComplete, onPartial, wsUrl }) {
  const [state, setState] = useState("idle"); // idle | recording | processing
  const mediaRecorderRef = useRef(null);
  const chunksRef        = useRef([]);
  const wsRef            = useRef(null);
  const streamRef        = useRef(null);
  const animRef          = useRef(null);
  const [level, setLevel]    = useState(0);  // 0-1 mic level for visualiser

  const analyserRef = useRef(null);

  // ── Mic level visualiser ────────────────────────────────────────────────
  function startVisualiser(stream) {
    const ctx      = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
    const source   = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    analyserRef.current = analyser;

    const buf = new Uint8Array(analyser.frequencyBinCount);
    function tick() {
      analyser.getByteFrequencyData(buf);
      const avg = buf.reduce((a, b) => a + b, 0) / buf.length;
      setLevel(Math.min(1, avg / 80));
      animRef.current = requestAnimationFrame(tick);
    }
    tick();
  }

  function stopVisualiser() {
    if (animRef.current) cancelAnimationFrame(animRef.current);
    setLevel(0);
  }

  // ── Start recording ─────────────────────────────────────────────────────
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true },
      });
      streamRef.current = stream;
      chunksRef.current = [];
      setState("recording");
      startVisualiser(stream);

      // Try WebSocket streaming for partials
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        ws.onmessage = (e) => {
          const msg = JSON.parse(e.data);
          if (msg.type === "partial" && onPartial) onPartial(msg.text);
        };
        ws.onerror = () => { wsRef.current = null; };
      } catch (_) {
        wsRef.current = null;
      }

      const mr = new MediaRecorder(stream, { mimeType: getSupportedMime() });
      mediaRecorderRef.current = mr;

      mr.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
          // Stream chunk to WebSocket if open
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            e.data.arrayBuffer().then((buf) => wsRef.current.send(buf));
          }
        }
      };

      mr.start(500);  // collect chunks every 500 ms
    } catch (err) {
      console.error("Mic access denied:", err);
      alert("Microphone access is required. Please allow microphone permissions.");
    }
  }

  // ── Stop recording ──────────────────────────────────────────────────────
  async function stopRecording() {
    setState("processing");
    stopVisualiser();

    const mr = mediaRecorderRef.current;
    if (!mr) return;

    await new Promise((resolve) => {
      mr.onstop = resolve;
      mr.stop();
    });

    // Tell WS we're done
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send("DONE");
    }

    // Combine chunks → WAV blob
    const blob = new Blob(chunksRef.current, { type: "audio/webm" });
    const wavBlob = await convertToWav(blob);

    // Stop mic tracks
    streamRef.current?.getTracks().forEach((t) => t.stop());

    onComplete(wavBlob);
    setState("idle");
  }

  // ── Toggle ──────────────────────────────────────────────────────────────
  function toggle() {
    if (state === "idle")      startRecording();
    else if (state === "recording") stopRecording();
  }

  // ── Render ──────────────────────────────────────────────────────────────
  const isRecording = state === "recording";
  const isProcessing = state === "processing";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "1.5rem" }}>
      {/* Mic button */}
      <button
        onClick={toggle}
        disabled={isProcessing}
        style={{
          width: 100, height: 100,
          borderRadius: "50%",
          border: "none",
          background: isRecording
            ? `radial-gradient(circle, #ff6e6e ${20 + level * 60}%, #c62828 100%)`
            : "var(--accent)",
          cursor: isProcessing ? "wait" : "pointer",
          fontSize: "2rem",
          transition: "transform .1s",
          transform: isRecording ? `scale(${1 + level * 0.12})` : "scale(1)",
          boxShadow: isRecording
            ? `0 0 ${20 + level * 40}px rgba(255,110,110,0.6)`
            : "0 0 0px transparent",
        }}
        aria-label={isRecording ? "Stop recording" : "Start recording"}
      >
        {isProcessing ? "⏳" : isRecording ? "⏹" : "🎙"}
      </button>

      <span style={{ fontFamily: "var(--mono)", fontSize: ".85rem", color: "var(--muted)" }}>
        {isProcessing ? "Transcribing…" : isRecording ? "Tap to stop" : "Tap to speak"}
      </span>

      {/* Level bar */}
      {isRecording && (
        <div style={{
          width: 200, height: 6, background: "var(--border)", borderRadius: 999, overflow: "hidden"
        }}>
          <div style={{
            width: `${level * 100}%`, height: "100%", background: "#ff6e6e",
            transition: "width .05s", borderRadius: 999,
          }} />
        </div>
      )}
    </div>
  );
}

// ── Helpers ─────────────────────────────────────────────────────────────────

function getSupportedMime() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => MediaRecorder.isTypeSupported(t)) || "";
}

async function convertToWav(blob) {
  // Decode via AudioContext and re-encode as WAV
  const arrayBuffer = await blob.arrayBuffer();
  const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
  const decoded = await ctx.decodeAudioData(arrayBuffer);
  const pcm = decoded.getChannelData(0);  // mono
  return pcmToWavBlob(pcm, 16000);
}

function pcmToWavBlob(float32Array, sampleRate) {
  const int16 = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i++) {
    int16[i] = Math.max(-32768, Math.min(32767, float32Array[i] * 32767));
  }
  const wavBuffer = encodeWav(int16, sampleRate);
  return new Blob([wavBuffer], { type: "audio/wav" });
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view   = new DataView(buffer);
  function write(offset, str) { for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i)); }
  write(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  write(8, "WAVE"); write(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true);
  view.setUint16(22, 1, true); view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true); view.setUint16(32, 2, true);
  view.setUint16(34, 16, true); write(36, "data");
  view.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) view.setInt16(44 + i * 2, samples[i], true);
  return buffer;
}
