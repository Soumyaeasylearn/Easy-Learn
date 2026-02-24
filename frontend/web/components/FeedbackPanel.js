// components/FeedbackPanel.js
import { useEffect, useRef } from "react";

export default function FeedbackPanel({ feedback, ttsUrl }) {
  const audioRef = useRef(null);

  useEffect(() => {
    if (ttsUrl && audioRef.current) {
      audioRef.current.src = ttsUrl;
      audioRef.current.play().catch(() => {});
    }
  }, [ttsUrl]);

  if (!feedback) return null;

  const scoreColor = (s) => {
    if (!s) return "var(--muted)";
    if (s >= 8)  return "#7fff6e";
    if (s >= 5)  return "#ffe066";
    return "#ff6e6e";
  };

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "1rem",
      padding: "1.5rem",
      display: "flex",
      flexDirection: "column",
      gap: "1.2rem",
      animation: "fadeUp .3s ease",
    }}>
      <style>{`@keyframes fadeUp { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }`}</style>

      {/* Score badge */}
      {feedback.score != null && (
        <div style={{ display: "flex", alignItems: "center", gap: ".8rem" }}>
          <span style={{
            fontSize: "2.5rem", fontWeight: 800,
            color: scoreColor(feedback.score),
          }}>{feedback.score}<span style={{ fontSize: "1rem", color: "var(--muted)" }}>/10</span></span>
          <div>
            <div style={{ fontWeight: 700, fontSize: ".95rem" }}>Fluency Score</div>
            <div style={{ color: "var(--muted)", fontSize: ".8rem", fontFamily: "var(--mono)" }}>
              {feedback.tags?.join(" · ") || ""}
            </div>
          </div>
        </div>
      )}

      {/* Correction */}
      {feedback.correction && (
        <section>
          <Label>✏️ Correction</Label>
          <div style={{
            background: "#0f1f0f", border: "1px solid #2a4a2a", borderRadius: ".6rem",
            padding: "1rem", fontFamily: "var(--mono)", fontSize: ".95rem",
            color: "#7fff6e", lineHeight: 1.6,
          }}>
            {feedback.correction}
            {ttsUrl && (
              <button onClick={() => audioRef.current?.play()}
                style={{ marginLeft: ".8rem", background: "none", border: "none",
                  cursor: "pointer", fontSize: "1rem" }} title="Play audio">
                🔊
              </button>
            )}
          </div>
        </section>
      )}

      {/* Explanation */}
      {feedback.explanation && (
        <section>
          <Label>💡 Explanation</Label>
          <p style={{ color: "var(--text)", lineHeight: 1.6, fontSize: ".95rem" }}>
            {feedback.explanation}
          </p>
        </section>
      )}

      {/* Vocabulary */}
      {feedback.vocabulary?.length > 0 && (
        <section>
          <Label>📚 Better alternatives</Label>
          <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap", marginTop: ".4rem" }}>
            {feedback.vocabulary.map((w) => (
              <span key={w} style={{
                background: "#1a1a2e", border: "1px solid #3a3a5e",
                borderRadius: "999px", padding: ".25rem .85rem",
                fontFamily: "var(--mono)", fontSize: ".85rem", color: "#a8a8ff",
              }}>{w}</span>
            ))}
          </div>
        </section>
      )}

      {/* Encouragement */}
      {feedback.encouragement && (
        <div style={{
          background: "#1a1a0a", border: "1px solid #3a3a20",
          borderRadius: ".6rem", padding: "1rem",
          color: "#ffe066", fontSize: ".95rem", lineHeight: 1.6,
        }}>
          🌟 {feedback.encouragement}
        </div>
      )}

      <audio ref={audioRef} hidden preload="auto" />
    </div>
  );
}

function Label({ children }) {
  return (
    <p style={{
      fontFamily: "var(--mono)", fontSize: ".75rem", color: "var(--muted)",
      textTransform: "uppercase", letterSpacing: ".06em", marginBottom: ".4rem",
    }}>{children}</p>
  );
}
