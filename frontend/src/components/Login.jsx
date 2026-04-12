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

  const handleGoogleLogin = () => {
    window.location.href = "http://localhost:8000/auth/google";
  };

  return (
    <>
      <Navbar />
      <div className="auth-container">
        <motion.div
          className="auth-box"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
        >

          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2.5rem' }}>
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

            <button type="submit" className="btn-primary" disabled={loading}>
              {loading ? "Signing in..." : "Sign In →"}
            </button>
          </form>

          {/* Divider */}
          <div style={{ margin: "1.5rem 0", textAlign: "center" }}>
            <span style={{ color: "#888" }}>OR</span>
          </div>

          {/* Google Button */}
          <button
            onClick={handleGoogleLogin}
            style={{
              width: "100%",
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid #ddd",
              background: "white",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              gap: "10px",
              cursor: "pointer"
            }}
          >
            <img
              src="https://developers.google.com/identity/images/g-logo.png"
              width="20"
              alt="google"
            />
            Continue with Google
          </button>

          <div style={{ marginTop: '2rem', textAlign: 'center' }}>
            No account? <Link to="/signup">Create one</Link>
          </div>

        </motion.div>
      </div>
    </>
  );
}

export default Login;