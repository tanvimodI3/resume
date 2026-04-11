import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertCircle, User, Briefcase, Mail, Phone, Link as LinkIcon, TrendingUp } from 'lucide-react';

function Dashboard({ token, logout }) {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setFile(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !jobDescription) {
      setError('Please provide both a resume file and a job description.');
      return;
    }

    if (!token) {
      setError('Authentication token missing. Please log in again.');
      logout();
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDescription);

    try {
      const response = await fetch('http://localhost:8000/api/parse', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        },
        body: formData
      });

      if (response.status === 401) {
        setError('Session expired. Please log in again.');
        logout();
        return;
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || 'Failed to parse resume');
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <nav className="dashboard-nav">
        <div className="nav-brand">ATS AI</div>
        <div className="nav-links">
          <button onClick={logout}>Sign Out</button>
        </div>
      </nav>

      <div className="dashboard-container">
        <div className="upload-section glass-panel">
          <h2 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <UploadCloud size={24} color="var(--accent-primary)" /> New Scan
          </h2>

          <form onSubmit={handleSubmit}>
            <div
              className={`file-drop-area ${file ? 'active' : ''}`}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current.click()}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileChange}
                style={{ display: 'none' }}
                accept=".pdf,.docx,.txt"
              />
              <UploadCloud className="drop-icon" />
              {file ? (
                <div>
                  <p style={{ fontWeight: 600 }}>{file.name}</p>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Click or drag to change</p>
                </div>
              ) : (
                <div>
                  <p>Drag and drop resume here</p>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>Supports PDF, DOCX, TXT</p>
                </div>
              )}
            </div>

            <div className="form-group">
              <label>Job Description</label>
              <textarea
                rows="6"
                value={jobDescription}
                onChange={e => setJobDescription(e.target.value)}
                placeholder="Paste the target job description here..."
              ></textarea>
            </div>

            {error && <div style={{ color: 'var(--error)', marginBottom: '1rem' }}>{error}</div>}

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? <div className="spinner"></div> : 'Analyze Candidate'}
            </button>
          </form>
        </div>

        <div className="results-section">
          {loading && (
            <div className="glass-panel" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
              <div style={{ textAlign: 'center' }}>
                <div className="spinner" style={{ width: '48px', height: '48px', borderWidth: '4px', marginBottom: '1rem', borderColor: 'rgba(59, 130, 246, 0.3)', borderTopColor: 'var(--accent-primary)' }}></div>
                <p>AI is analyzing the candidate...</p>
                <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>This usually takes 10-20 seconds</p>
              </div>
            </div>
          )}

          {!loading && result && (
            <div className="result-card glass-panel" style={{ '--score': result.match_score }}>
              <div className="score-circle">
                <span className="score-text">{result.match_score}%</span>
              </div>
              <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>Candidate Evaluation</h2>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                <div className="result-field">
                  <span className="label"><User size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Name</span>
                  <span className="value">{result.name}</span>
                </div>
                <div className="result-field">
                  <span className="label"><Briefcase size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Experience</span>
                  <span className="value">{result.experience}</span>
                </div>
                <div className="result-field">
                  <span className="label"><Mail size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Email</span>
                  <span className="value">{result.email || 'N/A'}</span>
                </div>
                <div className="result-field">
                  <span className="label"><Phone size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Phone</span>
                  <span className="value">{result.phone || 'N/A'}</span>
                </div>
              </div>

              {result.profiles && result.profiles.length > 0 && (
                <div className="result-field" style={{ marginTop: '1rem' }}>
                  <span className="label"><LinkIcon size={14} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '4px' }} /> Profiles</span>
                  <div className="tag-list">
                    {result.profiles.map((p, i) => (
                      <a key={i} href={p.startsWith('http') ? p : `https://${p}`} target="_blank" rel="noreferrer" className="tag">{p}</a>
                    ))}
                  </div>
                </div>
              )}

              <hr style={{ border: 0, borderTop: '1px solid var(--border)', margin: '1.5rem 0' }} />

              <div className="result-field">
                <span className="label" style={{ color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <CheckCircle size={16} /> Key Strengths
                </span>
                <div className="tag-list">
                  {result.strengths && result.strengths.length > 0 ? (
                    result.strengths.map((s, i) => <span key={i} className="tag strength">{s}</span>)
                  ) : (
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>None identified</span>
                  )}
                </div>
              </div>

              <div className="result-field" style={{ marginTop: '1.5rem' }}>
                <span className="label" style={{ color: 'var(--error)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <AlertCircle size={16} /> Missing Skills
                </span>
                <div className="tag-list">
                  {result.missing_skills && result.missing_skills.length > 0 ? (
                    result.missing_skills.map((s, i) => <span key={i} className="tag missing">{s}</span>)
                  ) : (
                    <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>No essential skills missing!</span>
                  )}
                </div>
              </div>

            </div>
          )}

          {!loading && !result && (
            <div className="glass-panel" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px', flexDirection: 'column', color: 'var(--text-secondary)' }}>
              <div style={{ padding: '2rem', background: 'rgba(30, 41, 59, 0.4)', borderRadius: '50%', marginBottom: '1rem' }}>
                <TrendingUp size={48} color="var(--border)" />
              </div>
              <p>Upload a resume and job description</p>
              <p>to see the analysis results here.</p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

export default Dashboard;
