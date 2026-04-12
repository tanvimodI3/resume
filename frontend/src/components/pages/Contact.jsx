import React from 'react';
import Navbar from '../Navbar';
import { FileText, Target, BarChart3, Lock, Hand, Mail } from 'lucide-react';

const TEAM = [
  { name: 'Manthan Patel', role: 'Founder & Lead Engineer', email: 'manthan@resumeai.dev', initial: 'MP' },
  { name: 'Arjun Shah', role: 'AI / ML Engineer', email: 'arjun@resumeai.dev', initial: 'AS' },
  { name: 'Priya Desai', role: 'Backend Developer', email: 'priya@resumeai.dev', initial: 'PD' },
  { name: 'Neha Verma', role: 'Frontend Developer', email: 'neha@resumeai.dev', initial: 'NV' },
  { name: 'Rohan Mehta', role: 'Product & QA', email: 'rohan@resumeai.dev', initial: 'RM' },
];

const SERVICES = [
  { icon: FileText, title: 'Resume Parsing', desc: 'AI-powered extraction of candidate data from any resume format.' },
  { icon: Target, title: 'JD Matching', desc: 'Embedding + LLM dual-evaluation to score resume-to-job-description fit.' },
  { icon: BarChart3, title: 'Skill Gap Analysis', desc: 'Identify exactly which skills a candidate has and what is missing.' },
  { icon: Lock, title: 'Secure Data Handling', desc: 'Files are processed and immediately deleted — never stored.' },
];

function Contact({ isLoggedIn }) {
  return (
    <>
      <Navbar isLoggedIn={isLoggedIn} />
      <div className="public-page">
        <div className="public-page-content">
          <div className="page-hero">
            <div className="page-hero-badge"><Hand size={16} /> Get in Touch</div>
            <h1>Meet the Team</h1>
            <p>
              We're a passionate team of engineers building smarter hiring tools. Reach out to us
              anytime — we'd love to hear from you.
            </p>
          </div>

          <h2 className="section-title">Our Team</h2>
          <div className="contact-grid" style={{ marginBottom: '3rem' }}>
            {TEAM.map((member) => (
              <div key={member.name} className="contact-card">
                <div className="contact-avatar">{member.initial}</div>
                <div className="contact-info">
                  <h4>{member.name}</h4>
                  <div className="contact-role">{member.role}</div>
                  <div className="contact-email"><Mail size={14} /> {member.email}</div>
                </div>
              </div>
            ))}
          </div>

          <h2 className="section-title">What We Provide</h2>
          <div className="service-list">
            {SERVICES.map((s) => (
              <div key={s.title} className="service-item">
                <div className="service-icon"><s.icon size={20} /></div>
                <div>
                  <h4>{s.title}</h4>
                  <p>{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

export default Contact;
