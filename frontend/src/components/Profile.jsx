import React from 'react';
import { Mail, FileText } from 'lucide-react';

function Profile({ user, history }) {
  const getInitials = (name) =>
    name ? name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2) : 'U';

  const getScoreColor = (score) => {
    if (score >= 75) return 'var(--success)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--error)';
  };

  const avgScore =
    history.length > 0
      ? Math.round(history.reduce((sum, h) => sum + h.match_score, 0) / history.length)
      : 0;

  const bestScore = history.length > 0 ? Math.max(...history.map((h) => h.match_score)) : 0;

  return (
    <div className="profile-page">
      {/* Profile Card */}
      <div className="glass-panel profile-card">
        <div className="profile-avatar-lg">{user ? getInitials(user.name) : 'U'}</div>
        <h2 className="profile-name-lg">{user?.name || 'Loading…'}</h2>
        <p className="profile-email-lg">
          <Mail size={13} /> {user?.email || ''}
        </p>

        <div className="profile-stats">
          <div className="profile-stat">
            <div className="stat-value">{history.length}</div>
            <div className="stat-label">Parsed</div>
          </div>
          <div className="profile-stat">
            <div className="stat-value" style={{ color: getScoreColor(avgScore) }}>
              {avgScore}%
            </div>
            <div className="stat-label">Avg Score</div>
          </div>
          <div className="profile-stat">
            <div className="stat-value" style={{ color: getScoreColor(bestScore) }}>
              {bestScore}%
            </div>
            <div className="stat-label">Best Score</div>
          </div>
        </div>
      </div>

      {/* Parsed Resumes List */}
      <div className="glass-panel parsed-list-card">
        <div className="panel-header">
          <FileText size={18} style={{ color: 'var(--accent)' }} />
          <h3>Your Parsed Resumes</h3>
        </div>

        {history.length === 0 ? (
          <div className="empty-state-small">
            No resumes parsed yet. Head to{' '}
            <strong>Resume Parser</strong> to get started!
          </div>
        ) : (
          <div className="parsed-resume-list">
            {history.map((item) => (
              <div key={item.id} className="parsed-resume-item">
                <div className="parsed-resume-info">
                  <div className="parsed-resume-name">{item.name || item.filename}</div>
                  <div className="parsed-resume-meta">
                    {item.filename} • {item.experience}
                  </div>
                </div>
                <div
                  className="parsed-resume-score"
                  style={{
                    color: getScoreColor(item.match_score),
                    background: `${getScoreColor(item.match_score)}18`,
                  }}
                >
                  {item.match_score}%
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Profile;
