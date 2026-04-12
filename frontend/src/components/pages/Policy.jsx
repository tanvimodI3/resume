import React from 'react';
import Navbar from '../Navbar';
import { Lock } from 'lucide-react';

const POLICIES = [
  {
    title: '1. Data Collection',
    content: (
      <>
        <p>We collect only the minimum data required to operate the platform:</p>
        <ul>
          <li>Account information: name and email address (for authentication).</li>
          <li>Resume files: uploaded temporarily for analysis purposes only.</li>
          <li>Job descriptions: stored with parsed results for reference.</li>
          <li>Parsed results: match scores, extracted candidate information, and skill data.</li>
        </ul>
      </>
    ),
  },
  {
    title: '2. Data Usage',
    content: (
      <>
        <p>Your data is used exclusively for:</p>
        <ul>
          <li>Authenticating your account and providing access to the platform.</li>
          <li>Running AI analysis on uploaded resumes against provided job descriptions.</li>
          <li>Displaying historical analysis results within your personal dashboard.</li>
        </ul>
        <p style={{ marginTop: '0.75rem' }}>We do not sell, trade, or monetize your data in any form.</p>
      </>
    ),
  },
  {
    title: '3. File Storage & Deletion',
    content: (
      <p>
        Uploaded resume files are stored only temporarily in server memory during the analysis
        pipeline. They are automatically and permanently deleted after the analysis completes,
        regardless of success or failure. We do not retain a copy of your uploaded resume.
      </p>
    ),
  },
  {
    title: '4. Security',
    content: (
      <>
        <p>We implement the following security measures:</p>
        <ul>
          <li>Passwords are hashed using bcrypt before storage — never stored in plaintext.</li>
          <li>API endpoints are protected with JWT-based authentication.</li>
          <li>All API communication occurs over HTTPS in production.</li>
          <li>Sensitive credentials are managed via environment variables, never hardcoded.</li>
        </ul>
      </>
    ),
  },
  {
    title: '5. Cookies & Local Storage',
    content: (
      <p>
        We use browser local storage to store your authentication token so you remain logged in
        between sessions. No third-party tracking cookies are used on this platform.
      </p>
    ),
  },
  {
    title: '6. Third-Party Services',
    content: (
      <>
        <p>Our platform integrates with the following third-party APIs for AI functionality:</p>
        <ul>
          <li><strong>Cohere API</strong> — used for LLM-based text evaluation and embedding generation. Refer to Cohere's privacy policy for their data handling practices.</li>
        </ul>
        <p style={{ marginTop: '0.75rem' }}>Resume text excerpts are transmitted to Cohere for analysis and are subject to their terms of service.</p>
      </>
    ),
  },
  {
    title: '7. Policy Updates',
    content: (
      <p>
        We may update this policy periodically. Significant changes will be communicated via the
        platform dashboard. Continued use of the platform after an update implies acceptance of
        the revised policy.
      </p>
    ),
  },
];

function Policy({ isLoggedIn }) {
  return (
    <>
      <Navbar isLoggedIn={isLoggedIn} />
      <div className="public-page">
        <div className="public-page-content">
          <div className="page-hero">
            <div className="page-hero-badge"><Lock size={16} /> Legal</div>
            <h1>Privacy Policy</h1>
            <p>
              Last updated: April 2026. We are committed to transparency about how your data is
              handled.
            </p>
          </div>

          <div className="policy-sections">
            {POLICIES.map((p) => (
              <div key={p.title} className="policy-block">
                <h3>{p.title}</h3>
                {p.content}
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

export default Policy;
