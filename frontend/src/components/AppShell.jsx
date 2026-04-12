import React, { useState, useEffect } from 'react';
import { FileText, Mic, ShieldCheck, LogOut, ChevronRight, Clock, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import ResumeParser from './ResumeParser';
import Profile from './Profile';
import ProfileVerification from './ProfileVerification';
import AIInterviewer from './AIInterviewer';

const NAV_ITEMS = [
  { id: 'resume-parser', icon: FileText, label: 'Resume Parser', available: true },
  { id: 'ai-interviewer', icon: Mic, label: 'AI Interviewer', available: true },
  { id: 'verification', icon: ShieldCheck, label: 'Verification', available: true },
];

function AppShell({ token, logout }) {
  const [activeTool, setActiveTool] = useState('resume-parser');
  const [history, setHistory] = useState([]);
  const [lastScanProfiles, setLastScanProfiles] = useState([]);
  const [user, setUser] = useState(null);
  const [theme, setTheme] = useState(() => {
    return document.documentElement.getAttribute('data-theme') || 'dark';
  });

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    document.documentElement.setAttribute('data-theme', next);
  };

  useEffect(() => {
    fetchUser();
    fetchHistory();
  }, []);

  const fetchUser = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/me', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setUser(await res.json());
    } catch (e) { console.error(e); }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/history', {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.slice(0, 15));
        // Extract profiles from most recent scan for auto-fill
        if (data.length > 0 && data[0].profiles) {
          setLastScanProfiles(data[0].profiles);
        }
      }
    } catch (e) { console.error(e); }
  };

  const getInitials = (name) =>
    name ? name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2) : 'U';

  const getScoreColor = (score) => {
    if (score >= 75) return 'var(--success)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--error)';
  };

  const renderContent = () => {
    if (activeTool === 'profile') {
      return <Profile user={user} history={history} />;
    }
    if (activeTool === 'resume-parser') {
      return <ResumeParser token={token} onScanComplete={fetchHistory} />;
    }
    if (activeTool === 'ai-interviewer') {
      return <AIInterviewer token={token} />;
    }
    if (activeTool === 'verification') {
      return <ProfileVerification token={token} lastScanProfiles={lastScanProfiles} lastScan={history[0]} />;
    }
    return (
      <div className="coming-soon-page">
        <div className="coming-soon-icon">✅</div>
        <h2>Verification</h2>
        <p>This powerful feature is under active development.</p>
        <p className="coming-soon-sub">Stay tuned — it's coming very soon!</p>
      </div>
    );
  };

  const titleMap = {
    'resume-parser': 'Resume Parser',
    'ai-interviewer': 'AI Interviewer',
    'verification': 'Verification',
    profile: 'My Profile',
  };

  return (
    <div className="app-shell">
      {/* ── Sidebar ── */}
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-logo">
          <div className="logo-icon">⚡</div>
          <span className="logo-text">Resume<span>AI</span></span>
        </div>

        {/* Navigation */}
        <nav className="sidebar-nav">
          <div className="nav-section-label">TOOLS</div>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              className={`nav-item${activeTool === item.id ? ' active' : ''}${!item.available ? ' disabled' : ''}`}
              onClick={() => item.available && setActiveTool(item.id)}
              title={!item.available ? 'Coming Soon' : item.label}
            >
              <item.icon size={17} className="nav-item-icon" />
              <span className="nav-item-label">{item.label}</span>
              {!item.available && <span className="soon-badge">Soon</span>}
              {item.available && activeTool === item.id && (
                <ChevronRight size={13} className="nav-item-arrow" />
              )}
            </button>
          ))}
        </nav>

        {/* Recent Scans History */}
        {history.length > 0 && (
          <div className="sidebar-history">
            <div className="nav-section-label">
              <Clock size={10} /> RECENT SCANS
            </div>
            <div className="history-list">
              {history.map((item) => (
                <div key={item.id} className="history-item" title={item.filename}>
                  <div className="history-item-name">{item.name || item.filename}</div>
                  <div
                    className="history-item-score"
                    style={{ color: getScoreColor(item.match_score) }}
                  >
                    {item.match_score}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bottom: User profile + logout */}
        <div className="sidebar-bottom">
          <button className="profile-btn" onClick={() => setActiveTool('profile')}>
            <div className="avatar-circle">
              {user ? getInitials(user.name) : 'U'}
            </div>
            <div className="profile-info">
              <div className="profile-name">{user?.name || 'Loading...'}</div>
              <div className="profile-email">{user?.email || ''}</div>
            </div>
          </button>
          <button className="logout-btn" onClick={logout} title="Sign Out">
            <LogOut size={15} />
          </button>
        </div>
      </aside>

      {/* ── Main Area ── */}
      <div className="main-area">
        {/* Top Bar */}
        <header className="top-bar">
          <div className="top-bar-title">
            <Zap size={17} />
            <span>{titleMap[activeTool]}</span>
          </div>
          <div className="top-bar-center">
            {[
              { path: '/about', label: 'About' },
              { path: '/contact', label: 'Contact' },
              { path: '/policy', label: 'Policy' },
              { path: '/docs', label: 'Docs' },
            ].map(({ path, label }) => (
              <Link key={path} to={path} className="topbar-nav-link">
                {label}
              </Link>
            ))}
          </div>
          <div className="top-bar-right">
            <button
              className="lp-theme-btn"
              onClick={toggleTheme}
              aria-label="Toggle theme"
              style={{ marginRight: '0.5rem' }}
            >
              {theme === 'dark' ? '○' : '●'}
            </button>
            <button className="top-profile-btn" onClick={() => setActiveTool('profile')}>
              <div className="avatar-circle small">
                {user ? getInitials(user.name) : 'U'}
              </div>
              <span>{user?.name || 'Profile'}</span>
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="content-area">{renderContent()}</main>
      </div>
    </div>
  );
}

export default AppShell;
