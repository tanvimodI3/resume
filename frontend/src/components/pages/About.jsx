import React from 'react';
import Navbar from '../Navbar';
import { FileText, Brain, BarChart3, Mic, CheckCircle, Lock, Rocket } from 'lucide-react';

const FEATURES = [
  {
    icon: FileText,
    title: 'Resume Parser',
    desc: 'Upload any PDF, DOCX, or TXT resume. Our AI extracts structured data—name, contact, experience, profiles—in seconds.',
  },
  {
    icon: Brain,
    title: 'AI Matching Engine',
    desc: 'Dual-layer scoring using embedding similarity + LLM-based qualitative evaluation gives you an accurate match percentage.',
  },
  {
    icon: BarChart3,
    title: 'Gap Analysis',
    desc: 'Instantly see which skills the candidate has, which are missing, and their key strengths compared to the job requirements.',
  },
  {
    icon: Mic,
    title: 'AI Interviewer',
    desc: 'Coming soon — an AI-powered interview simulator that adapts questions based on parsed resume and role requirements.',
  },
  {
    icon: CheckCircle,
    title: 'Credential Verification',
    desc: 'Coming soon — automated verification of claimed experience, certifications, and portfolio links.',
  },
  {
    icon: Lock,
    title: 'Secure & Private',
    desc: 'Your data is processed securely. Resume files are never stored permanently — they are deleted after analysis.',
  },
];

function About({ isLoggedIn }) {
  return (
    <>
      <Navbar isLoggedIn={isLoggedIn} />
      <div className="public-page">
        <div className="public-page-content">
          <div className="page-hero">
            <div className="page-hero-badge"><Rocket size={16} /> AI-Powered ATS Platform</div>
            <h1>Smarter Hiring, Faster Decisions</h1>
            <p>
              ResumeAI is an intelligent Applicant Tracking System that combines embedding-based
              similarity search with LLM-powered evaluation to give you the most accurate
              candidate-to-job match score available.
            </p>
          </div>

          <div className="cards-grid">
            {FEATURES.map((f) => (
              <div key={f.title} className="feature-card">
                <div className="feature-card-icon"><f.icon size={24} /></div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            ))}
          </div>

          <div className="glass-panel" style={{ textAlign: 'center', padding: '2.5rem' }}>
            <h2 style={{ marginBottom: '0.75rem', fontSize: '1.4rem' }}>
              How It Works
            </h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem', maxWidth: '500px', margin: '0 auto 2rem' }}>
              Three steps from resume to insight.
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
              {[
                { step: '01', title: 'Upload', desc: 'Drag & drop a resume and paste the job description.' },
                { step: '02', title: 'Analyze', desc: 'Our AI extracts text, chunks it and runs dual-layer evaluation.' },
                { step: '03', title: 'Decide', desc: 'Get a match score, strengths list, and missing skills — instantly.' },
              ].map((s) => (
                <div key={s.step} style={{ padding: '1rem' }}>
                  <div style={{
                    fontSize: '2rem', fontWeight: '800', background: 'var(--accent-gradient)',
                    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', marginBottom: '0.5rem'
                  }}>
                    {s.step}
                  </div>
                  <h4 style={{ marginBottom: '0.4rem' }}>{s.title}</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default About;
