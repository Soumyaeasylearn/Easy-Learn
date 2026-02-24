// pages/profile.js — User profile, badges, progress history
import { useEffect, useState } from "react";
import Link from "next/link";
import Head from "next/head";

const API = process.env.NEXT_PUBLIC_API_URL || "https://your-render-app.onrender.com";

const BADGES = [
  { id: "first_session", icon: "🎙", label: "First Word",    desc: "Complete your first session" },
  { id: "streak_3",      icon: "🔥", label: "On Fire",       desc: "3-day streak" },
  { id: "streak_7",      icon: "⚡", label: "Lightning",     desc: "7-day streak" },
  { id: "score_9",       icon: "🏆", label: "Top Speaker",   desc: "Score 9+ in a session" },
  { id: "sessions_10",   icon: "💎", label: "Diamond",       desc: "Complete 10 sessions" },
  { id: "sessions_50",   icon: "👑", label: "Crown",         desc: "Complete 50 sessions" },
];

export default function ProfilePage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const userId = typeof window !== "undefined"
    ? localStorage.getItem("user_id") || "demo-user" : "demo-user";

  useEffect(() => { fetchHistory(); }, []);

  async function fetchHistory() {
    try {
      const res  = await fetch(`${API}/coach/history/${userId}?limit=20`);
      const data = await res.json();
      setHistory(data.sessions || []);
    } catch { setHistory(DEMO_HISTORY); }
    finally  { setLoading(false); }
  }

  const avgScore = history.length
    ? Math.round(history.reduce((s, h) => s + (h.score || 0), 0) / history.length)
    : 0;

  const earnedBadges = computeBadges(history);

  return (
    <>
      <Head>
        <title>Profile — SpeakUp</title>
        <link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:ital,wght@0,400;1,400&display=swap" rel="stylesheet" />
      </Head>

      <div className="shell">
        <header className="top-bar">
          <Link href="/" className="back">← Home</Link>
          <span className="badge-label">Your Profile</span>
        </header>

        {/* Stats */}
        <section className="stats">
          <StatCard value={history.length} label="Sessions" />
          <StatCard value={avgScore || "—"} label="Avg Score" />
          <StatCard value={earnedBadges.length} label="Badges" />
          <StatCard value={computeStreak(history)} label="Day Streak 🔥" />
        </section>

        {/* Badges */}
        <section className="section">
          <h2 className="heading">Achievements</h2>
          <div className="badge-grid">
            {BADGES.map((b) => {
              const earned = earnedBadges.includes(b.id);
              return (
                <div key={b.id} className={`badge-card ${earned ? "earned" : "locked"}`}>
                  <span className="badge-icon">{earned ? b.icon : "🔒"}</span>
                  <span className="badge-name">{b.label}</span>
                  <span className="badge-desc">{b.desc}</span>
                </div>
              );
            })}
          </div>
        </section>

        {/* History */}
        <section className="section">
          <h2 className="heading">Session History</h2>
          {loading ? <p style={{ color: "var(--muted)" }}>Loading…</p> : (
            <div className="history-list">
              {history.map((s, i) => (
                <div key={i} className="history-item">
                  <div className="history-score" style={{ color: scoreColor(s.score) }}>
                    {s.score ?? "—"}
                  </div>
                  <div className="history-body">
                    <p className="history-text">{s.transcript}</p>
                    {s.correction && (
                      <p className="history-correction">→ {s.correction}</p>
                    )}
                    <p className="history-meta">
                      {s.tags?.join(" · ")}
                      {s.created_at && ` · ${new Date(s.created_at).toLocaleDateString()}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      <style jsx global>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --bg:#0a0a0f; --surface:#13131a; --border:#1e1e2e;
          --accent:#7fff6e; --text:#e8e8f0; --muted:#6b6b82;
          --font:'Syne',sans-serif; --mono:'DM Mono',monospace;
        }
        html,body { background:var(--bg); color:var(--text); font-family:var(--font); }
        .shell { max-width:800px; margin:0 auto; padding:0 1.5rem 4rem; }
        .top-bar { display:flex; align-items:center; justify-content:space-between;
          padding:1.5rem 0; border-bottom:1px solid var(--border); }
        .back { color:var(--muted); text-decoration:none; font-size:.9rem; transition:color .2s; }
        .back:hover { color:var(--accent); }
        .badge-label { background:var(--surface); border:1px solid var(--border); border-radius:999px;
          padding:.25rem .9rem; font-size:.8rem; font-family:var(--mono); color:var(--accent); }
        .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:1rem; margin:2rem 0; }
        .stat-card { background:var(--surface); border:1px solid var(--border); border-radius:.8rem;
          padding:1.2rem; text-align:center; }
        .stat-value { display:block; font-size:2rem; font-weight:800; color:var(--accent); }
        .stat-label { display:block; font-size:.75rem; color:var(--muted); margin-top:.3rem;
          font-family:var(--mono); }
        .section { margin:2rem 0; }
        .heading { font-size:1.2rem; font-weight:700; margin-bottom:1rem; }
        .badge-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(130px,1fr)); gap:.8rem; }
        .badge-card { background:var(--surface); border:1px solid var(--border);
          border-radius:.8rem; padding:1rem; text-align:center;
          display:flex; flex-direction:column; gap:.4rem; }
        .badge-card.earned { border-color: var(--accent); }
        .badge-card.locked { opacity:.45; }
        .badge-icon { font-size:1.8rem; }
        .badge-name { font-weight:700; font-size:.85rem; }
        .badge-desc { font-size:.73rem; color:var(--muted); font-family:var(--mono); }
        .history-list { display:flex; flex-direction:column; gap:.8rem; }
        .history-item { background:var(--surface); border:1px solid var(--border); border-radius:.8rem;
          padding:1rem; display:flex; gap:1rem; align-items:flex-start; }
        .history-score { font-size:1.8rem; font-weight:800; min-width:44px; text-align:center; }
        .history-body { flex:1; }
        .history-text { font-size:.95rem; line-height:1.5; margin-bottom:.3rem; }
        .history-correction { font-size:.9rem; color:#7fff6e; font-family:var(--mono);
          margin-bottom:.3rem; }
        .history-meta { font-size:.75rem; color:var(--muted); font-family:var(--mono); }
        @media(max-width:480px) { .stats { grid-template-columns:repeat(2,1fr); } }
      `}</style>
    </>
  );
}

function StatCard({ value, label }) {
  return (
    <div className="stat-card">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  );
}

function scoreColor(s) {
  if (!s) return "var(--muted)";
  if (s >= 8) return "#7fff6e";
  if (s >= 5) return "#ffe066";
  return "#ff6e6e";
}

function computeBadges(history) {
  const badges = [];
  if (history.length >= 1)  badges.push("first_session");
  if (history.length >= 10) badges.push("sessions_10");
  if (history.length >= 50) badges.push("sessions_50");
  if (history.some((h) => h.score >= 9)) badges.push("score_9");
  const streak = computeStreak(history);
  if (streak >= 3) badges.push("streak_3");
  if (streak >= 7) badges.push("streak_7");
  return badges;
}

function computeStreak(history) {
  if (!history.length) return 0;
  const dates = [...new Set(history.map((h) =>
    new Date(h.created_at || Date.now()).toDateString()
  ))].reverse();
  let streak = 0;
  let current = new Date();
  for (const d of dates) {
    const day = new Date(d);
    const diff = Math.round((current - day) / 86400000);
    if (diff <= 1) { streak++; current = day; }
    else break;
  }
  return streak;
}

const DEMO_HISTORY = [
  { score: 7, transcript: "I go to school yesterday.", correction: "I went to school yesterday.", tags: ["grammar"], created_at: new Date().toISOString() },
  { score: 9, transcript: "She is very beautiful and kind.", correction: null, tags: ["fluency"], created_at: new Date(Date.now() - 86400000).toISOString() },
];
