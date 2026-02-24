// pages/index.js — Home screen with streak + lesson entry
import Head from "next/head";
import Link from "next/link";
import { useEffect, useState } from "react";
import styles from "../public/styles.css";

const API = process.env.NEXT_PUBLIC_API_URL || "https://your-render-app.onrender.com";

export default function Home() {
  const [profile, setProfile] = useState(null);
  const [lessons, setLessons] = useState([]);
  const [loading, setLoading] = useState(true);

  const userId =
    typeof window !== "undefined"
      ? localStorage.getItem("user_id") || "demo-user"
      : "demo-user";

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    try {
      const [profileRes, lessonRes] = await Promise.all([
        fetch(`${API}/coach/history/${userId}?limit=1`),
        fetch(`${API}/recommend/${userId}?n=3`),
      ]);
      const lessonData = await lessonRes.json();
      setLessons(lessonData.recommendations || []);
    } catch (e) {
      console.error("API unavailable — using demo data");
      setLessons(DEMO_LESSONS);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>SpeakUp — English Coaching</title>
        <meta name="description" content="AI-powered spoken English coach" />
        <link rel="icon" href="/favicon.ico" />
        <link
          href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:ital,wght@0,400;1,400&display=swap"
          rel="stylesheet"
        />
      </Head>

      <div className="shell">
        {/* ── Header ── */}
        <header className="header">
          <div className="logo">
            <span className="logo-mark">◉</span>
            <span className="logo-text">SpeakUp</span>
          </div>
          <nav className="nav">
            <Link href="/lesson" className="nav-link">Practice</Link>
            <Link href="/profile" className="nav-link">Profile</Link>
          </nav>
        </header>

        {/* ── Hero ── */}
        <section className="hero">
          <div className="hero-badge">AI-Powered · Free · Open Source</div>
          <h1 className="hero-title">
            Your personal<br />
            <em>English coach</em><br />
            is ready.
          </h1>
          <p className="hero-sub">
            Speak. Get instant feedback. Improve every day.
          </p>
          <Link href="/lesson" className="cta-btn">
            Start Speaking →
          </Link>
        </section>

        {/* ── Streak Card ── */}
        <StreakCard streak={profile?.streak || 0} />

        {/* ── Recommended Lessons ── */}
        <section className="lessons-section">
          <h2 className="section-title">Recommended for you</h2>
          {loading ? (
            <div className="skeleton-grid">
              {[1, 2, 3].map((i) => <div key={i} className="skeleton-card" />)}
            </div>
          ) : (
            <div className="lesson-grid">
              {lessons.map((l) => (
                <LessonCard key={l.id} lesson={l} />
              ))}
            </div>
          )}
        </section>

        {/* ── Stats Row ── */}
        <section className="stats-row">
          {STATS.map((s) => (
            <div key={s.label} className="stat-card">
              <span className="stat-value">{s.value}</span>
              <span className="stat-label">{s.label}</span>
            </div>
          ))}
        </section>

        <footer className="footer">
          Built with ♥ using Whisper · Kokoro · LLaMA-3 · FAISS
        </footer>
      </div>

      <style jsx global>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
          --bg: #0a0a0f;
          --surface: #13131a;
          --border: #1e1e2e;
          --accent: #7fff6e;
          --accent2: #ff6e6e;
          --text: #e8e8f0;
          --muted: #6b6b82;
          --font: 'Syne', sans-serif;
          --mono: 'DM Mono', monospace;
        }
        html, body { background: var(--bg); color: var(--text); font-family: var(--font); min-height: 100vh; }

        .shell { max-width: 960px; margin: 0 auto; padding: 0 1.5rem; }

        .header { display: flex; align-items: center; justify-content: space-between;
          padding: 1.5rem 0; border-bottom: 1px solid var(--border); }
        .logo { display: flex; align-items: center; gap: .6rem; font-size: 1.25rem; font-weight: 800; }
        .logo-mark { color: var(--accent); font-size: 1.5rem; }
        .nav { display: flex; gap: 2rem; }
        .nav-link { color: var(--muted); text-decoration: none; font-size: .95rem;
          transition: color .2s; }
        .nav-link:hover { color: var(--accent); }

        .hero { padding: 5rem 0 3rem; }
        .hero-badge { display: inline-block; background: var(--surface);
          border: 1px solid var(--border); border-radius: 999px;
          padding: .3rem 1rem; font-size: .8rem; color: var(--muted);
          font-family: var(--mono); margin-bottom: 1.5rem; }
        .hero-title { font-size: clamp(2.5rem, 6vw, 4.5rem); font-weight: 800;
          line-height: 1.1; letter-spacing: -.03em; margin-bottom: 1.2rem; }
        .hero-title em { color: var(--accent); font-style: normal; }
        .hero-sub { font-size: 1.15rem; color: var(--muted); margin-bottom: 2.5rem; }
        .cta-btn { display: inline-block; background: var(--accent); color: #000;
          font-weight: 700; padding: 1rem 2.5rem; border-radius: 999px;
          text-decoration: none; font-size: 1rem; transition: transform .15s, box-shadow .15s; }
        .cta-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(127,255,110,.3); }

        .streak-card { background: var(--surface); border: 1px solid var(--border);
          border-radius: 1rem; padding: 1.5rem 2rem; display: flex; align-items: center;
          gap: 1.5rem; margin: 2rem 0; }
        .streak-flame { font-size: 3rem; }
        .streak-count { font-size: 2.5rem; font-weight: 800; color: var(--accent); }
        .streak-label { color: var(--muted); font-size: .9rem; }

        .section-title { font-size: 1.3rem; font-weight: 700; margin-bottom: 1.2rem; }
        .lessons-section { margin: 2rem 0; }
        .lesson-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
        .lesson-card { background: var(--surface); border: 1px solid var(--border);
          border-radius: 1rem; padding: 1.5rem; cursor: pointer;
          transition: border-color .2s, transform .2s; text-decoration: none; color: inherit; }
        .lesson-card:hover { border-color: var(--accent); transform: translateY(-2px); }
        .lesson-area { font-size: .75rem; font-family: var(--mono); color: var(--accent);
          text-transform: uppercase; letter-spacing: .08em; margin-bottom: .6rem; }
        .lesson-title { font-weight: 700; font-size: 1rem; margin-bottom: .4rem; }
        .lesson-level { font-size: .8rem; color: var(--muted); }

        .skeleton-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 1rem; }
        .skeleton-card { background: var(--surface); border-radius: 1rem; height: 120px;
          animation: pulse 1.5s ease-in-out infinite; }
        @keyframes pulse { 0%,100% { opacity: .5; } 50% { opacity: 1; } }

        .stats-row { display: flex; gap: 1rem; margin: 2rem 0; flex-wrap: wrap; }
        .stat-card { flex: 1; min-width: 120px; background: var(--surface);
          border: 1px solid var(--border); border-radius: 1rem;
          padding: 1.2rem; text-align: center; }
        .stat-value { display: block; font-size: 2rem; font-weight: 800; color: var(--accent); }
        .stat-label { display: block; font-size: .8rem; color: var(--muted); margin-top: .3rem; }

        .footer { text-align: center; color: var(--muted); font-size: .8rem;
          font-family: var(--mono); padding: 3rem 0; border-top: 1px solid var(--border);
          margin-top: 2rem; }
      `}</style>
    </>
  );
}

function StreakCard({ streak }) {
  return (
    <div className="streak-card">
      <span className="streak-flame">🔥</span>
      <div>
        <div className="streak-count">{streak} day{streak !== 1 ? "s" : ""}</div>
        <div className="streak-label">current streak — keep it going!</div>
      </div>
    </div>
  );
}

function LessonCard({ lesson }) {
  return (
    <Link href={`/lesson?id=${lesson.id}`} className="lesson-card">
      <div className="lesson-area">{lesson.area}</div>
      <div className="lesson-title">{lesson.title}</div>
      <div className="lesson-level">{lesson.level}</div>
    </Link>
  );
}

const DEMO_LESSONS = [
  { id: "g1", title: "Subject-Verb Agreement", area: "grammar",       level: "beginner" },
  { id: "p1", title: "Vowel Sounds Practice",  area: "pronunciation", level: "beginner" },
  { id: "f1", title: "Filler Words & Hesitations", area: "fluency",  level: "beginner" },
];

const STATS = [
  { value: "100%", label: "Free forever" },
  { value: "< 2s",  label: "ASR latency"  },
  { value: "Open",  label: "Source"       },
  { value: "8",     label: "Voices"       },
];
