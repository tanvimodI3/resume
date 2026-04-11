import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import Navbar from './Navbar';
import ThemeToggle from './ThemeToggle';

function Login({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

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

  return (
    <>
      <Navbar />
      <div className="auth-container">
        <motion.div
          className="auth-box"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2.5rem' }}>
            <div>
              <h1>Welcome back.</h1>
              <p className="auth-subtitle">Sign in to continue</p>
            </div>
            <ThemeToggle />
          </div>

          {error && <div className="error-message">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
            </div>

            <button type="submit" className="btn-primary" disabled={loading} style={{ marginTop: '1rem' }}>
              {loading ? <><div className="spinner" /> Signing in…</> : 'Sign In →'}
            </button>
          </form>

          <div style={{ marginTop: '2rem', paddingTop: '1.75rem', borderTop: '1px solid var(--border-subtle)', textAlign: 'center', fontFamily: 'var(--font-body)', fontSize: '0.78rem', fontWeight: 300, color: 'var(--text-muted)' }}>
            No account?{' '}
            <Link to="/signup" style={{ color: 'var(--text-secondary)', textDecoration: 'underline', textUnderlineOffset: '3px' }}>
              Create one
            </Link>
          </div>
        </motion.div>
      </div>
    </>
  );
}

export default Login;