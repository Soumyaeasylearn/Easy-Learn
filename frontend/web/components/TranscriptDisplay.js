// components/TranscriptDisplay.js
export default function TranscriptDisplay({ transcript, partial, loading }) {
  const show = transcript || partial || loading;
  if (!show) return null;

  return (
    <div style={{
      background: "var(--surface)",
      border: "1px solid var(--border)",
      borderRadius: "1rem",
      padding: "1.5rem",
      minHeight: 80,
    }}>
      <p style={{
        fontFamily: "var(--mono)",
        fontSize: ".85rem",
        color: "var(--muted)",
        marginBottom: ".5rem",
        textTransform: "uppercase",
        letterSpacing: ".06em",
      }}>
        Transcript
      </p>

      {loading && !transcript && !partial ? (
        <div className="loading-dots">
          <span /><span /><span />
          <style jsx>{`
            .loading-dots { display: flex; gap: 6px; align-items: center; }
            .loading-dots span {
              width: 8px; height: 8px; border-radius: 50%; background: var(--muted);
              animation: bounce .8s ease-in-out infinite;
            }
            .loading-dots span:nth-child(2) { animation-delay: .15s; }
            .loading-dots span:nth-child(3) { animation-delay: .3s; }
            @keyframes bounce { 0%,80%,100%{transform:scale(0)} 40%{transform:scale(1)} }
          `}</style>
        </div>
      ) : (
        <p style={{
          fontSize: "1.1rem",
          lineHeight: 1.7,
          color: partial && !transcript ? "var(--muted)" : "var(--text)",
          fontStyle: partial && !transcript ? "italic" : "normal",
        }}>
          {transcript || partial || ""}
        </p>
      )}
    </div>
  );
}
