import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap, FileText, Brain, BarChart3 } from 'lucide-react';

/* ── Typing animation hook ────────────────────────────────────── */
function useTyping(words, { typeSpeed = 120, deleteSpeed = 80, pause = 2400 } = {}) {
  const [text, setText] = useState('');
  const wordIdx = useRef(0);
  const charIdx = useRef(0);
  const deleting = useRef(false);

  useEffect(() => {
    let raf;
    let last = 0;

    function tick(ts) {
      const word = words[wordIdx.current];
      const delay = deleting.current
        ? deleteSpeed
        : charIdx.current === word.length
        ? pause
        : typeSpeed;

      if (ts - last >= delay) {
        last = ts;
        if (!deleting.current) {
          if (charIdx.current < word.length) {
            charIdx.current++;
            setText(word.slice(0, charIdx.current));
          } else {
            deleting.current = true;
          }
        } else {
          if (charIdx.current > 0) {
            charIdx.current--;
            setText(word.slice(0, charIdx.current));
          } else {
            deleting.current = false;
            wordIdx.current = (wordIdx.current + 1) % words.length;
          }
        }
      }
      raf = requestAnimationFrame(tick);
    }

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  return text;
}

/* ── Scroll trigger hook ──────────────────────────────────────── */
function useScrollTrigger(threshold = 60) {
  const [triggered, setTriggered] = useState(false);

  useEffect(() => {
    if (triggered) return;

    const onWheel = (e) => { if (e.deltaY > 30) setTriggered(true); };
    const onScroll = () => { if (window.scrollY > threshold) setTriggered(true); };
    let startY = 0;
    const onTouchStart = (e) => { startY = e.touches[0].clientY; };
    const onTouchEnd = (e) => {
      if (startY - e.changedTouches[0].clientY > 40) setTriggered(true);
    };

    window.addEventListener('wheel', onWheel, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('touchstart', onTouchStart, { passive: true });
    window.addEventListener('touchend', onTouchEnd, { passive: true });

    return () => {
      window.removeEventListener('wheel', onWheel);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('touchstart', onTouchStart);
      window.removeEventListener('touchend', onTouchEnd);
    };
  }, [triggered, threshold]);

  return triggered;
}

/* ── Landing Hero ─────────────────────────────────────────────── */
function LandingHero({ exiting, theme, toggleTheme }) {
  const typed = useTyping(['forreal.', 'for real.', 'no filters.', 'just you.']);

  return (
    <motion.section
      className="lp-landing"
      animate={{
        opacity: exiting ? 0 : 1,
        scale: exiting ? 1.06 : 1,
        filter: exiting ? 'blur(8px)' : 'blur(0px)',
      }}
      transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Nav */}
      <header className="lp-nav" id="landing-nav">
        <div className="lp-logo">
          <span className="lp-logo-icon"><Zap size={20} /></span>
          Resume<span className="lp-logo-accent">AI</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span className="lp-hint">scroll to enter</span>
          <button className="lp-theme-btn" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === 'dark' ? '○' : '●'}
          </button>
        </div>
      </header>

      {/* Center hero */}
      <div className="lp-center">
        <motion.p
          className="lp-eyebrow"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        >
          AI-Powered Hiring
        </motion.p>

<motion.h1
          className="lp-hero"
          id="landing-hero-title"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="lp-typed">{typed}</span>
          <span className="lp-cursor" />
        </motion.h1>

        <motion.p
          className="lp-sub"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.8 }}
        >
          Real connections only.
        </motion.p>

        <motion.div
          className="lp-features"
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 1.1 }}
        >
          <div className="lp-feature-pill">
            <span className="lp-pill-icon"><FileText size={14} /></span>
            PDF Parsing
          </div>
          <div className="lp-feature-pill">
            <span className="lp-pill-icon"><Brain size={14} /></span>
            AI Matching
          </div>
          <div className="lp-feature-pill">
            <span className="lp-pill-icon"><BarChart3 size={14} /></span>
            Smart Scoring
          </div>
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="lp-foot">
        <span className="lp-foot-left">Est. 2025</span>
        <div className="lp-scroll-pulse">
          <span className="lp-scroll-line" />
          <span className="lp-scroll-text">scroll</span>
        </div>
      </footer>
    </motion.section>
  );
}

/* ── Auth Panel ───────────────────────────────────────────────── */
function AuthPanel({ visible, setToken, theme, toggleTheme }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (mode === 'login') {
        const body = new URLSearchParams();
        body.append('username', email);
        body.append('password', password);
        const res = await fetch('http://localhost:8000/auth/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body,
        });
        if (!res.ok) throw new Error('Invalid credentials');
        const data = await res.json();
        setToken(data.access_token);
        navigate('/dashboard');
      } else {
        const res = await fetch('http://localhost:8000/auth/signup', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password }),
        });
        if (!res.ok) {
          const data = await res.json();
          throw new Error(data.detail || 'Could not create account');
        }
        setMode('login');
        setError('');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="lp-auth"
      id="auth-screen"
      initial={{ opacity: 0, y: 40 }}
      animate={{
        opacity: visible ? 1 : 0,
        y: visible ? 0 : 40,
        pointerEvents: visible ? 'all' : 'none',
      }}
      transition={{ duration: 0.7, delay: 0.15, ease: [0.22, 1, 0.36, 1] }}
    >
      {/* Top bar */}
      <header className="lp-auth-nav">
        <div className="lp-logo">
          <span className="lp-logo-icon"><Zap size={20} /></span>
          Resume<span className="lp-logo-accent">AI</span>
        </div>
        <button className="lp-theme-btn" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === 'dark' ? '○' : '●'}
        </button>
      </header>

      {/* Glass panel */}
      <AnimatePresence mode="wait">
        <motion.div
          key={mode}
          className="lp-auth-panel"
          id="auth-panel"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -15 }}
          transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="corner c-tl" />
          <span className="corner c-tr" />
          <span className="corner c-bl" />
          <span className="corner c-br" />

          <p className="lp-auth-eyebrow">
            0{mode === 'login' ? '1' : '2'} / {mode === 'login' ? 'Login' : 'Sign Up'}
          </p>
<h1 className="lp-auth-title" id="auth-title">
            {mode === 'login' ? 'Welcome back.' : 'Join us.'}
          </h1>
          <p className="lp-auth-sub">
            {mode === 'login' ? 'Sign in to continue' : 'Create your account'}
          </p>

          {error && <p className="lp-auth-error">{error}</p>}

          <form onSubmit={handleSubmit} className="lp-auth-form">
            {mode === 'signup' && (
              <motion.div
                className="lp-field"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                transition={{ duration: 0.35 }}
              >
                <label className="lp-label">Full Name</label>
                <input
                  className="lp-input"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  autoComplete="name"
                  placeholder="Your name"
                  id="auth-name-input"
                />
                <span className="lp-underline" />
              </motion.div>
            )}

            <div className="lp-field">
              <label className="lp-label">Email</label>
              <input
                className="lp-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="you@example.com"
                id="auth-email-input"
              />
              <span className="lp-underline" />
            </div>

            <div className="lp-field">
              <label className="lp-label">Password</label>
              <input
                className="lp-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                placeholder="••••••••"
                id="auth-password-input"
              />
              <span className="lp-underline" />
            </div>

            <button className="lp-cta" type="submit" disabled={loading} id="auth-submit-btn">
              {loading ? (
                <span className="lp-spinner" />
              ) : (
                <>
                  <span>{mode === 'login' ? 'Sign In' : 'Create Account'}</span>
                  <span className="lp-arrow">→</span>
                </>
              )}
            </button>
          </form>

          <p className="lp-switch">
            {mode === 'login' ? "No account? " : 'Already have one? '}
            <button
              className="lp-switch-btn"
              onClick={() => {
                setMode(mode === 'login' ? 'signup' : 'login');
                setError('');
              }}
              id="auth-mode-toggle"
            >
              {mode === 'login' ? 'Create one →' : 'Sign in →'}
            </button>
          </p>
        </motion.div>
      </AnimatePresence>

      <p className="lp-tagline">Real connections only.</p>
    </motion.div>
  );
}

/* ── Main LandingPage Export ──────────────────────────────────── */
export default function LandingPage({ setToken }) {
  const scrolled = useScrollTrigger(60);
  const [showAuth, setShowAuth] = useState(false);
  const [theme, setTheme] = useState(() => {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  });

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  };

  useEffect(() => {
    if (scrolled) {
      const t = setTimeout(() => setShowAuth(true), 250);
      return () => clearTimeout(t);
    }
  }, [scrolled]);

  return (
    <>
      <LandingHero exiting={scrolled} theme={theme} toggleTheme={toggleTheme} />
      <AuthPanel visible={showAuth} setToken={setToken} theme={theme} toggleTheme={toggleTheme} />
    </>
  );
}
