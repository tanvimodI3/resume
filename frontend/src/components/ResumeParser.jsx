import React, { useState, useRef, useEffect } from 'react';
import {
  UploadCloud, FileText, CheckCircle, XCircle,
  User, Briefcase, Mail, Phone, Link as LinkIcon, TrendingUp, Search, Zap
} from 'lucide-react';

const STEPS = [
  { id: 0, label: 'Loading document' },
  { id: 1, label: 'Extracting text content' },
  { id: 2, label: 'Parsing candidate information' },
  { id: 3, label: 'Matching with job description' },
];

const STEP_DELAYS = [0, 4000, 9000, 14000];

function ResumeParser({ token, onScanComplete }) {
  const [file, setFile] = useState(null);
  const [jobDescription, setJobDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [loadingStep, setLoadingStep] = useState(-1);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);

  const fileInputRef = useRef(null);
  const timersRef = useRef([]);

  const clearTimers = () => {
    timersRef.current.forEach((t) => clearTimeout(t));
    timersRef.current = [];
  };

  useEffect(() => () => clearTimers(), []);

  const handleFileChange = (e) => {
    if (e.target.files?.[0]) {
      setFile(e.target.files[0]);
      setResult(null);
      setError('');
    }
  };

  const handleDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) {
      setFile(e.dataTransfer.files[0]);
      setResult(null);
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file || !jobDescription.trim()) {
      setError('Please provide both a resume file and a job description.');
      return;
    }

    clearTimers();
    setLoading(true);
    setError('');
    setResult(null);
    setLoadingStep(0);

    // Schedule each step advance
    STEP_DELAYS.slice(1).forEach((delay, idx) => {
      const t = setTimeout(() => setLoadingStep(idx + 1), delay);
      timersRef.current.push(t);
    });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('job_description', jobDescription);

    try {
      const response = await fetch('http://localhost:8000/api/parse', {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to parse resume. Please try again.');
      const data = await response.json();

      clearTimers();
      setLoadingStep(STEPS.length); // mark all done

      // Short pause so user sees the "all complete" state
      setTimeout(() => {
        setLoading(false);
        setResult(data);
        if (onScanComplete) onScanComplete();
      }, 700);
    } catch (err) {
      clearTimers();
      setError(err.message);
      setLoading(false);
      setLoadingStep(-1);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 75) return 'var(--success)';
    if (score >= 50) return 'var(--warning)';
    return 'var(--error)';
  };

  const getScoreLabel = (score) => {
    if (score >= 75) return 'Strong Match';
    if (score >= 50) return 'Moderate Match';
    return 'Low Match';
  };

  return (
    <div className="parser-layout">
      {/* ── Left: Upload Form ── */}
      <div className="glass-panel parser-input-panel">
        <div className="panel-header">
          <FileText size={19} style={{ color: 'var(--accent)' }} />
          <h2>New Analysis</h2>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Drag & Drop Upload */}
          <div
            id="resume-drop-zone"
            className={`file-drop-area${isDragging ? ' dragging' : ''}${file ? ' has-file' : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              id="resume-file-input"
              onChange={handleFileChange}
              style={{ display: 'none' }}
              accept=".pdf,.docx,.txt"
            />
            <UploadCloud className="drop-icon" size={38} />
            {file ? (
              <div>
                <p className="drop-filename"><FileText size={16} /> {file.name}</p>
                <p className="drop-sub">Click or drag to replace</p>
              </div>
            ) : (
              <div>
                <p className="drop-title">Drop your resume here</p>
                <p className="drop-sub">PDF, DOCX, or TXT</p>
              </div>
            )}
          </div>

          {/* Job Description */}
          <div className="form-group">
            <label htmlFor="job-description-input">
              <Search size={13} /> Job Description
            </label>
            <textarea
              id="job-description-input"
              rows={9}
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here..."
            />
          </div>

          {error && <div className="error-message">{error}</div>}

          <button id="analyze-btn" type="submit" className="btn-primary" disabled={loading}>
            {loading ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                <div className="spinner" /> Analyzing...
              </span>
            ) : (
              <><Zap size={16} /> Analyze Resume</>
            )}
          </button>
        </form>
      </div>

      {/* ── Right: Results / Loading / Empty ── */}
      <div className="parser-results-panel">
        {/* Loading with step animation */}
        {loading && (
          <div className="glass-panel loading-panel">
            <h3 className="loading-title">AI is working…</h3>
            <p className="loading-sub">This usually takes 15–30 seconds</p>

            <div className="steps-list">
              {STEPS.map((step, idx) => {
                const status =
                  loadingStep > idx ? 'done' : loadingStep === idx ? 'active' : 'pending';
                return (
                  <div key={step.id} className={`step-item ${status}`}>
                    <div className="step-icon-wrap">
                      {status === 'done' ? (
                        <CheckCircle size={18} style={{ color: 'var(--success)' }} />
                      ) : status === 'active' ? (
                        <div className="step-spinner" />
                      ) : (
                        <div className="step-dot" />
                      )}
                    </div>
                    <span className="step-label">{step.label}</span>
                    {status === 'active' && (
                      <span className="step-running-badge">Running</span>
                    )}
                    {status === 'done' && (
                      <span className="step-done-badge">Done</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Results */}
        {!loading && result && (
          <div className="result-card glass-panel">
            {/* Score */}
            <div className="score-section">
              <div
                className="score-circle"
                style={{
                  '--score': result.match_score,
                  '--score-color': getScoreColor(result.match_score),
                }}
              >
                <span
                  className="score-text"
                  style={{ color: getScoreColor(result.match_score) }}
                >
                  {result.match_score}%
                </span>
              </div>
              <div>
                <div className="score-label" style={{ color: getScoreColor(result.match_score) }}>
                  {getScoreLabel(result.match_score)}
                </div>
                <div className="score-sub">ATS Match Score</div>
              </div>
            </div>

            <hr className="divider" />

            {/* Candidate Info */}
            <div className="info-grid">
              <div className="result-field">
                <span className="field-label"><User size={12} /> Name</span>
                <span className="field-value">{result.name}</span>
              </div>
              <div className="result-field">
                <span className="field-label"><Briefcase size={12} /> Experience</span>
                <span className="field-value">{result.experience}</span>
              </div>
              <div className="result-field">
                <span className="field-label"><Mail size={12} /> Email</span>
                <span className="field-value">{result.email || 'N/A'}</span>
              </div>
              <div className="result-field">
                <span className="field-label"><Phone size={12} /> Phone</span>
                <span className="field-value">{result.phone || 'N/A'}</span>
              </div>
            </div>

            {result.profiles?.length > 0 && (
              <div className="result-field full-width" style={{ marginTop: '1rem' }}>
                <span className="field-label"><LinkIcon size={12} /> Profiles</span>
                <div className="tag-list">
                  {result.profiles.map((p, i) => (
                    <a
                      key={i}
                      href={p.startsWith('http') ? p : `https://${p}`}
                      target="_blank"
                      rel="noreferrer"
                      className="tag profile-tag"
                    >
                      {p}
                    </a>
                  ))}
                </div>
              </div>
            )}

            <hr className="divider" />

            <div className="result-field full-width">
              <span className="field-label success"><CheckCircle size={13} /> Key Strengths</span>
              <div className="tag-list">
                {result.strengths?.length > 0
                  ? result.strengths.map((s, i) => <span key={i} className="tag strength">{s}</span>)
                  : <span className="empty-label">None identified</span>}
              </div>
            </div>

            <div className="result-field full-width" style={{ marginTop: '1.25rem' }}>
              <span className="field-label error"><XCircle size={13} /> Missing Skills</span>
              <div className="tag-list">
                {result.missing_skills?.length > 0
                  ? result.missing_skills.map((s, i) => <span key={i} className="tag missing">{s}</span>)
                  : <span className="empty-label">No essential skills missing!</span>}
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!loading && !result && (
          <div className="glass-panel empty-state">
            <div className="empty-icon"><TrendingUp size={44} /></div>
            <h3>Ready to Analyze</h3>
            <p>Upload a resume and paste the job description, then click Analyze to see the full AI evaluation.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ResumeParser;
