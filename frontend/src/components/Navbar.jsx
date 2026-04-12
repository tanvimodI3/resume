import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import ThemeToggle from './ThemeToggle';
import { Zap } from 'lucide-react';

const NAV_LINKS = [
  { to: '/about', label: 'About' },
  { to: '/contact', label: 'Contact' },
  { to: '/policy', label: 'Policy' },
  { to: '/docs', label: 'Docs' },
];

function Navbar({ isLoggedIn = false }) {
  const location = useLocation();

  return (
    <nav className="public-nav">
      <div className="public-nav-inner">
        <Link to={isLoggedIn ? '/dashboard' : '/about'} className="public-nav-logo">
          <span className="logo-icon-small"><Zap size={18} /></span>
          Resume<span className="logo-accent">AI</span>
        </Link>

        {isLoggedIn && (
          <div className="public-nav-links">
            {NAV_LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                className={`public-nav-link${location.pathname === link.to ? ' active' : ''}`}
              >
                {link.label}
              </Link>
            ))}
          </div>
        )}

        <div className="public-nav-actions">
          <ThemeToggle />
          {isLoggedIn ? (
            <Link to="/dashboard" className="nav-signup-btn">Dashboard →</Link>
          ) : (
            <>
              <Link to="/login" className="nav-login-btn">Login</Link>
              <Link to="/signup" className="nav-signup-btn">Get Started →</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}

export default Navbar;