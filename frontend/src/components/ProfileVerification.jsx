import React, { useState } from 'react';
import {
  ShieldCheck, GitBranch, Code2, Link2, Globe, ExternalLink,
  Star, GitFork, Users, BookOpen, Trophy, Target, TrendingUp,
  Loader2, AlertCircle, CheckCircle2, Search, Sparkles, Zap
} from 'lucide-react';

const PLATFORM_ICONS = {
  github: GitBranch,
  leetcode: Code2,
  linkedin: Link2,
  twitter: Globe,
  kaggle: Globe,
  other: Globe,
};

const PLATFORM_LABELS = {
  github: 'GitHub',
  leetcode: 'LeetCode',
  linkedin: 'LinkedIn',
  twitter: 'Twitter / X',
  kaggle: 'Kaggle',
  other: 'Website',
};

const LANG_COLORS = {
  JavaScript: '#f1e05a', Python: '#3572A5', TypeScript: '#3178c6',
  Java: '#b07219', 'C++': '#f34b7d', C: '#555555',
  Go: '#00ADD8', Rust: '#dea584', Ruby: '#701516',
  PHP: '#4F5D95', Swift: '#F05138', Kotlin: '#A97BFF',
  Dart: '#00B4AB', HTML: '#e34c26', CSS: '#563d7c',
  Shell: '#89e051', Jupyter: '#DA5B0B', 'Jupyter Notebook': '#DA5B0B',
  R: '#198CE7', Scala: '#c22d40', Lua: '#000080',
  Vue: '#41b883', SCSS: '#c6538c',
};

function ProfileVerification({ token, lastScanProfiles }) {
  const [urlInput, setUrlInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');

  const handleAutoFill = () => {
    if (lastScanProfiles && lastScanProfiles.length > 0) {
      setUrlInput(lastScanProfiles.join('\n'));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const urls = urlInput
      .split(/[\n,]+/)
      .map((u) => u.trim())
      .filter(Boolean);

    if (urls.length === 0) {
      setError('Please enter at least one profile URL.');
      return;
    }

    setLoading(true);
    setError('');
    setResults(null);

    try {
      const resp = await fetch('http://localhost:8000/api/analyze-profiles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profiles: urls }),
      });

      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}));
        throw new Error(errData.detail || 'Failed to analyze profiles');
      }

      const data = await resp.json();
      setResults(data.results || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pv-layout">
      {/* ── Input Panel ── */}
      <div className="glass-panel pv-input-panel">
        <div className="panel-header">
          <ShieldCheck size={19} style={{ color: 'var(--accent)' }} />
          <h2>Profile Verification</h2>
        </div>

        <p className="pv-desc">
          Paste GitHub, LeetCode, LinkedIn or other profile URLs to get a deep analysis.
        </p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="pv-url-input">
              <Search size={13} /> Profile URLs
            </label>
            <textarea
              id="pv-url-input"
              rows={6}
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder={"https://github.com/username\nhttps://leetcode.com/u/username\nhttps://linkedin.com/in/username"}
            />
          </div>

          {lastScanProfiles && lastScanProfiles.length > 0 && (
            <button
              type="button"
              className="btn-secondary pv-autofill-btn"
              onClick={handleAutoFill}
            >
              <Sparkles size={14} /> Use profiles from last scan ({lastScanProfiles.length})
            </button>
          )}

          {error && <div className="error-message">{error}</div>}

          <button
            id="pv-analyze-btn"
            type="submit"
            className="btn-primary"
            disabled={loading}
          >
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <Loader2 size={16} className="pv-spin" /> Analyzing...
              </span>
            ) : (
              '⚡ Analyze Profiles'
            )}
          </button>
        </form>
      </div>

      {/* ── Results Panel ── */}
      <div className="pv-results-panel">
        {loading && (
          <div className="glass-panel pv-loading-panel">
            <Loader2 size={36} className="pv-spin" style={{ color: 'var(--accent)' }} />
            <h3>Fetching profile data…</h3>
            <p className="pv-loading-sub">Querying public APIs for your profiles</p>
          </div>
        )}

        {!loading && results && results.length > 0 && (
          <div className="pv-results-list">
            {results.map((r, i) => (
              <ProfileCard key={i} data={r} index={i} />
            ))}
          </div>
        )}

        {!loading && results && results.length === 0 && (
          <div className="glass-panel empty-state">
            <AlertCircle size={40} />
            <h3>No Results</h3>
            <p>No analyzable profiles were found in the provided URLs.</p>
          </div>
        )}

        {!loading && !results && (
          <div className="glass-panel empty-state">
            <div className="empty-icon"><ShieldCheck size={44} /></div>
            <h3>Ready to Verify</h3>
            <p>Enter profile URLs and click Analyze to see deep insights into GitHub & LeetCode profiles.</p>
          </div>
        )}
      </div>
    </div>
  );
}


/* ─────────────────────────────────────────────────────────
   PROFILE CARD (dispatches to platform-specific renderer)
   ───────────────────────────────────────────────────────── */

function ProfileCard({ data, index }) {
  const platform = data.platform || 'other';
  const delay = `${index * 0.08}s`;

  if (data.status === 'not_found') {
    return (
      <div className="glass-panel pv-card pv-card-error" style={{ animationDelay: delay }}>
        <div className="pv-card-header">
          <AlertCircle size={18} style={{ color: 'var(--error)' }} />
          <span className="pv-platform-label">{PLATFORM_LABELS[platform]} — Not Found</span>
        </div>
        <p className="pv-error-text">{data.error || `User "${data.username}" was not found.`}</p>
      </div>
    );
  }

  if (data.status === 'error' || data.status === 'rate_limited') {
    return (
      <div className="glass-panel pv-card pv-card-error" style={{ animationDelay: delay }}>
        <div className="pv-card-header">
          <AlertCircle size={18} style={{ color: 'var(--warning)' }} />
          <span className="pv-platform-label">{PLATFORM_LABELS[platform]} — Error</span>
        </div>
        <p className="pv-error-text">{data.error || 'An error occurred.'}</p>
      </div>
    );
  }

  if (platform === 'github' && data.status === 'success') {
    return <GitHubCard data={data} delay={delay} />;
  }

  if (platform === 'leetcode' && data.status === 'success') {
    return <LeetCodeCard data={data} delay={delay} />;
  }

  // link_only or other
  return <OtherLinkCard data={data} delay={delay} />;
}


/* ─────────────────────────────────────────────────────────
   GITHUB CARD
   ───────────────────────────────────────────────────────── */

function GitHubCard({ data, delay }) {
  const user = data.user || {};
  const repos = data.repos || [];
  const stats = data.stats || {};
  const langs = data.languages || [];
  const totalLangCount = langs.reduce((s, l) => s + l.count, 0) || 1;

  return (
    <div className="glass-panel pv-card pv-github-card" style={{ animationDelay: delay }}>
      {/* Header */}
      <div className="pv-card-header">
        <GitBranch size={20} />
        <span className="pv-platform-label">GitHub</span>
        <a href={user.html_url} target="_blank" rel="noreferrer" className="pv-ext-link">
          <ExternalLink size={13} />
        </a>
      </div>

      {/* User info */}
      <div className="pv-gh-user">
        {user.avatar_url && (
          <img src={user.avatar_url} alt={user.name} className="pv-gh-avatar" />
        )}
        <div>
          <div className="pv-gh-name">{user.name}</div>
          {user.bio && <div className="pv-gh-bio">{user.bio}</div>}
          {user.location && (
            <div className="pv-gh-meta">📍 {user.location}</div>
          )}
        </div>
      </div>

      {/* Stats row */}
      <div className="pv-stat-row">
        <div className="pv-stat">
          <BookOpen size={14} />
          <span className="pv-stat-val">{stats.total_repos || 0}</span>
          <span className="pv-stat-label">Repos</span>
        </div>
        <div className="pv-stat">
          <Star size={14} />
          <span className="pv-stat-val">{stats.total_stars || 0}</span>
          <span className="pv-stat-label">Stars</span>
        </div>
        <div className="pv-stat">
          <GitFork size={14} />
          <span className="pv-stat-val">{stats.total_forks || 0}</span>
          <span className="pv-stat-label">Forks</span>
        </div>
        <div className="pv-stat">
          <Users size={14} />
          <span className="pv-stat-val">{user.followers || 0}</span>
          <span className="pv-stat-label">Followers</span>
        </div>
      </div>

      {/* Language bar */}
      {langs.length > 0 && (
        <div className="pv-lang-section">
          <div className="pv-section-title">Languages</div>
          <div className="pv-lang-bar">
            {langs.slice(0, 8).map((lang) => (
              <div
                key={lang.name}
                className="pv-lang-segment"
                style={{
                  width: `${(lang.count / totalLangCount) * 100}%`,
                  backgroundColor: LANG_COLORS[lang.name] || '#888',
                }}
                title={`${lang.name}: ${lang.count} repos`}
              />
            ))}
          </div>
          <div className="pv-lang-legend">
            {langs.slice(0, 6).map((lang) => (
              <span key={lang.name} className="pv-lang-item">
                <span
                  className="pv-lang-dot"
                  style={{ backgroundColor: LANG_COLORS[lang.name] || '#888' }}
                />
                {lang.name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Top repos */}
      {repos.length > 0 && (
        <div className="pv-repos-section">
          <div className="pv-section-title">Top Repositories</div>
          <div className="pv-repos-grid">
            {repos.filter(r => !r.is_fork).slice(0, 4).map((repo) => (
              <a
                key={repo.name}
                href={repo.html_url}
                target="_blank"
                rel="noreferrer"
                className="pv-repo-card"
              >
                <div className="pv-repo-name">{repo.name}</div>
                {repo.description && (
                  <div className="pv-repo-desc">{repo.description}</div>
                )}
                <div className="pv-repo-meta">
                  {repo.language !== 'N/A' && (
                    <span className="pv-repo-lang">
                      <span
                        className="pv-lang-dot"
                        style={{ backgroundColor: LANG_COLORS[repo.language] || '#888' }}
                      />
                      {repo.language}
                    </span>
                  )}
                  <span className="pv-repo-stars">
                    <Star size={11} /> {repo.stars}
                  </span>
                  <span className="pv-repo-forks">
                    <GitFork size={11} /> {repo.forks}
                  </span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


/* ─────────────────────────────────────────────────────────
   LEETCODE CARD
   ───────────────────────────────────────────────────────── */

function LeetCodeCard({ data, delay }) {
  const user = data.user || {};
  const solved = data.solved || {};
  const contest = data.contest || {};
  const total = solved.total || 0;

  // Ring chart percentages (LeetCode has ~3300 total problems)
  const TOTAL_PROBLEMS = 3300;
  const pct = Math.min((total / TOTAL_PROBLEMS) * 100, 100);

  return (
    <div className="glass-panel pv-card pv-leetcode-card" style={{ animationDelay: delay }}>
      {/* Header */}
      <div className="pv-card-header">
        <Code2 size={20} />
        <span className="pv-platform-label">LeetCode</span>
        <a href={user.html_url} target="_blank" rel="noreferrer" className="pv-ext-link">
          <ExternalLink size={13} />
        </a>
      </div>

      {/* User info */}
      <div className="pv-lc-user">
        <div className="pv-lc-name">{user.name || data.username}</div>
        {user.ranking > 0 && (
          <div className="pv-lc-rank">
            <Trophy size={13} /> Rank #{user.ranking.toLocaleString()}
          </div>
        )}
      </div>

      {/* Solved stats */}
      <div className="pv-lc-solved-section">
        <div className="pv-lc-ring-wrap">
          <svg viewBox="0 0 100 100" className="pv-lc-ring">
            <circle cx="50" cy="50" r="42" className="pv-lc-ring-bg" />
            <circle
              cx="50" cy="50" r="42"
              className="pv-lc-ring-fill"
              style={{
                strokeDasharray: `${pct * 2.64} ${264 - pct * 2.64}`,
              }}
            />
          </svg>
          <div className="pv-lc-ring-text">
            <span className="pv-lc-ring-num">{total}</span>
            <span className="pv-lc-ring-label">Solved</span>
          </div>
        </div>

        <div className="pv-lc-difficulty-col">
          <div className="pv-lc-diff-row">
            <span className="pv-lc-diff-dot easy" />
            <span className="pv-lc-diff-label">Easy</span>
            <span className="pv-lc-diff-val">{solved.easy || 0}</span>
          </div>
          <div className="pv-lc-diff-row">
            <span className="pv-lc-diff-dot medium" />
            <span className="pv-lc-diff-label">Medium</span>
            <span className="pv-lc-diff-val">{solved.medium || 0}</span>
          </div>
          <div className="pv-lc-diff-row">
            <span className="pv-lc-diff-dot hard" />
            <span className="pv-lc-diff-label">Hard</span>
            <span className="pv-lc-diff-val">{solved.hard || 0}</span>
          </div>
        </div>
      </div>

      {/* Contest info */}
      {contest.attended > 0 && (
        <div className="pv-lc-contest">
          <div className="pv-section-title">Contest Performance</div>
          <div className="pv-stat-row">
            <div className="pv-stat">
              <Target size={14} />
              <span className="pv-stat-val">{contest.attended}</span>
              <span className="pv-stat-label">Contests</span>
            </div>
            <div className="pv-stat">
              <TrendingUp size={14} />
              <span className="pv-stat-val">{contest.rating || '—'}</span>
              <span className="pv-stat-label">Rating</span>
            </div>
            {contest.top_percentage > 0 && (
              <div className="pv-stat">
                <Zap size={14} />
                <span className="pv-stat-val">Top {contest.top_percentage}%</span>
                <span className="pv-stat-label">Global</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Badges */}
      {data.badges && data.badges.length > 0 && (
        <div className="pv-lc-badges">
          <div className="pv-section-title">Badges</div>
          <div className="tag-list">
            {data.badges.slice(0, 6).map((b, i) => (
              <span key={i} className="tag strength">{b}</span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


/* ─────────────────────────────────────────────────────────
   OTHER LINK CARD (LinkedIn, Portfolio, etc.)
   ───────────────────────────────────────────────────────── */

function OtherLinkCard({ data, delay }) {
  const platform = data.platform || 'other';
  const Icon = PLATFORM_ICONS[platform] || Globe;
  const label = PLATFORM_LABELS[platform] || 'Website';
  const url = data.url || '';

  return (
    <div className="glass-panel pv-card pv-other-card" style={{ animationDelay: delay }}>
      <div className="pv-card-header">
        <Icon size={18} />
        <span className="pv-platform-label">{label}</span>
        <a href={url} target="_blank" rel="noreferrer" className="pv-ext-link">
          <ExternalLink size={13} />
        </a>
      </div>
      <div className="pv-other-body">
        <a href={url} target="_blank" rel="noreferrer" className="pv-other-url">
          {url}
        </a>
        {data.username && (
          <div className="pv-other-username">@{data.username}</div>
        )}
        <div className="pv-other-note">
          <CheckCircle2 size={13} style={{ color: 'var(--success)' }} />
          Link detected — deep analysis not available for this platform
        </div>
      </div>
    </div>
  );
}

export default ProfileVerification;
