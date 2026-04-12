import React from 'react';
import Navbar from '../Navbar';

function Docs({ isLoggedIn }) {
  return (
    <>
      <Navbar isLoggedIn={isLoggedIn} />
      <div className="public-page">
        <div className="public-page-content">
          <div className="page-hero">
            <div className="page-hero-badge">📖 Developer Docs</div>
            <h1>API Documentation</h1>
            <p>
              ResumeAI exposes a RESTful FastAPI backend. All authenticated endpoints require
              a Bearer token obtained via the login endpoint.
            </p>
          </div>

          {/* TOC */}
          <div className="docs-toc">
            <h4>Contents</h4>
            <a href="#auth">Authentication</a>
            <a href="#parse">Resume Parsing</a>
            <a href="#history">History</a>
            <a href="#me">User Profile</a>
            <a href="#errors">Error Handling</a>
          </div>

          {/* Auth */}
          <div className="docs-section" id="auth">
            <h3>Authentication</h3>

            <div className="endpoint-block">
              <div className="endpoint-header">
                <span className="method-badge post">POST</span>
                <span className="endpoint-path">/auth/signup</span>
                <span className="endpoint-desc">Register new account</span>
              </div>
              <div className="endpoint-body">
                <p>Create a new user account. Passwords are hashed with bcrypt.</p>
                <div className="code-block">{`// Request body (JSON)
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword"
}

// Response 200
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}`}</div>
              </div>
            </div>

            <div className="endpoint-block">
              <div className="endpoint-header">
                <span className="method-badge post">POST</span>
                <span className="endpoint-path">/auth/token</span>
                <span className="endpoint-desc">Login & get JWT</span>
              </div>
              <div className="endpoint-body">
                <p>Submit credentials as <code>application/x-www-form-urlencoded</code>. Returns a Bearer JWT token.</p>
                <div className="code-block">{`// Request (form-encoded)
username=john@example.com&password=securepassword

// Response 200
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer"
}

// Use in subsequent requests:
Authorization: Bearer eyJhbGciOi...`}</div>
              </div>
            </div>
          </div>

          {/* Parse */}
          <div className="docs-section" id="parse">
            <h3>Resume Parsing</h3>
            <div className="endpoint-block">
              <div className="endpoint-header">
                <span className="method-badge post">POST</span>
                <span className="endpoint-path">/api/parse</span>
                <span className="endpoint-desc">Analyze a resume · Auth required</span>
              </div>
              <div className="endpoint-body">
                <p>
                  Submit a resume file (PDF, DOCX, or TXT) and a job description as{' '}
                  <code>multipart/form-data</code>. The pipeline extracts text, chunks it,
                  computes embedding similarity, and runs LLM evaluation.
                  Takes ~15–30s depending on file size.
                </p>
                <div className="code-block">{`// Request (multipart/form-data)
file: <binary PDF/DOCX/TXT>
job_description: "We are looking for a Python engineer..."

// Response 200
{
  "id": 12,
  "user_id": 1,
  "filename": "resume.pdf",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+91-9876543210",
  "experience": "3 years",
  "profiles": ["github.com/johndoe"],
  "match_score": 78.5,
  "missing_skills": ["Kubernetes", "GraphQL"],
  "strengths": ["Python", "FastAPI", "Docker"],
  "job_description": "We are looking for...",
  "created_at": "2026-04-11T10:00:00Z"
}`}</div>
              </div>
            </div>
          </div>

          {/* History */}
          <div className="docs-section" id="history">
            <h3>History</h3>
            <div className="endpoint-block">
              <div className="endpoint-header">
                <span className="method-badge get">GET</span>
                <span className="endpoint-path">/api/history</span>
                <span className="endpoint-desc">Get all parsed resumes · Auth required</span>
              </div>
              <div className="endpoint-body">
                <p>Returns all past scan results for the authenticated user, ordered newest first.</p>
                <div className="code-block">{`// Response 200 — array of ScanResult objects
[
  { "id": 12, "name": "John Doe", "match_score": 78.5, ... },
  { "id": 11, "name": "Jane Smith", "match_score": 62.0, ... }
]`}</div>
              </div>
            </div>
          </div>

          {/* Me */}
          <div className="docs-section" id="me">
            <h3>User Profile</h3>
            <div className="endpoint-block">
              <div className="endpoint-header">
                <span className="method-badge get">GET</span>
                <span className="endpoint-path">/api/me</span>
                <span className="endpoint-desc">Get current user info · Auth required</span>
              </div>
              <div className="endpoint-body">
                <p>Returns the authenticated user's basic information.</p>
                <div className="code-block">{`// Response 200
{
  "id": 1,
  "name": "John Doe",
  "email": "john@example.com"
}`}</div>
              </div>
            </div>
          </div>

          {/* Errors */}
          <div className="docs-section" id="errors">
            <h3>Error Handling</h3>
            <div className="glass-panel" style={{ padding: '1.5rem' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '0.5rem 1rem 0.75rem 0', textAlign: 'left', color: 'var(--text-secondary)' }}>Status</th>
                    <th style={{ padding: '0.5rem 1rem 0.75rem', textAlign: 'left', color: 'var(--text-secondary)' }}>Meaning</th>
                    <th style={{ padding: '0.5rem 0 0.75rem 1rem', textAlign: 'left', color: 'var(--text-secondary)' }}>Common Cause</th>
                  </tr>
                </thead>
                <tbody>
                  {[
                    ['400', 'Bad Request', 'Email already registered, or missing required fields'],
                    ['401', 'Unauthorized', 'Missing, expired or invalid Bearer token'],
                    ['422', 'Validation Error', 'Request body/form data does not match expected schema'],
                    ['500', 'Server Error', 'AI parsing pipeline failure (usually transient)'],
                  ].map(([code, meaning, cause]) => (
                    <tr key={code} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: '0.75rem 1rem 0.75rem 0', fontFamily: 'monospace', color: 'var(--error)' }}>{code}</td>
                      <td style={{ padding: '0.75rem 1rem', color: 'var(--text-primary)' }}>{meaning}</td>
                      <td style={{ padding: '0.75rem 0 0.75rem 1rem', color: 'var(--text-secondary)' }}>{cause}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default Docs;
