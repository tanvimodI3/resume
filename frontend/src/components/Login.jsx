import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import Navbar from './Navbar';
import ThemeToggle from './ThemeToggle';

function Login({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get('token');
    if (token) {
      setToken(token);
      navigate('/dashboard');
    }
  }, [location, setToken, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await fetch('http://localhost:8000/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: formData
      });

      if (!response.ok) throw new Error('Invalid credentials');

      const data = await response.json();
      setToken(data.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = "http://localhost:8000/auth/google";
  };

  return (
    <>
      <Navbar />
      <div className="auth-container">
        <div className="glass-panel auth-box">
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2.5rem', alignItems: 'flex-start' }}>
            <div>
              <h1 style={{ fontFamily: 'var(--font-serif)', fontStyle: 'normal !important', color: '#fff', margin: 0 }}>Welcome Back</h1>
              <p className="auth-subtitle" style={{ color: '#aaa', marginTop: '0.5rem' }}>Sign in to continue</p>
            </div>
            <ThemeToggle />
          </div>

          {error && <div className="error-message" style={{ marginBottom: '1rem' }}>{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading} style={{ width: '100%', marginTop: '1rem' }}>
              {loading ? "Signing in..." : "Sign In →"}
            </button>
          </form>

          {/* Divider */}
          <div style={{ margin: "1.5rem 0", textAlign: "center", position: 'relative' }}>
             <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)' }} />
             <span style={{ color: "#888", position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', background: 'var(--glass-bg)', padding: '0 10px' }}>OR</span>
          </div>

          {/* Google Button */}
          <button
            onClick={handleGoogleLogin}
            className="google-btn"
            style={{
              width: "100%",
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid rgba(255,255,255,0.1)",
              background: "rgba(255,255,255,0.05)",
              color: "#fff",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "10px",
              cursor: "pointer",
              transition: "all 0.3s ease"
            }}
          >
            <img
              src="https://developers.google.com/identity/images/g-logo.png"
              width="20"
              alt="google"
            />
            Continue with Google
          </button>

          <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.9rem' }}>
            No account? <Link to="/signup">Create one</Link>
          </div>
        </div>
      </div>
    </>
  );
}

export default Login;