import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LandingPage from './components/LandingPage';
import AppShell from './components/AppShell';
import About from './components/pages/About';
import Contact from './components/pages/Contact';
import Policy from './components/pages/Policy';
import Docs from './components/pages/Docs';

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));

  const saveToken = (userToken) => {
    localStorage.setItem('token', userToken);
    setToken(userToken);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
  };

  const isLoggedIn = !!token;

  // Wrap public pages to pass isLoggedIn to their internal Navbar
  const withAuth = (Component) => <Component isLoggedIn={isLoggedIn} />;

  return (
    <Router>
      <Routes>
        {/* Landing page with scroll-to-auth — redirects to dashboard if logged in */}
        <Route
          path="/"
          element={token ? <Navigate to="/dashboard" /> : <LandingPage setToken={saveToken} />}
        />
        {/* Keep legacy routes so direct URLs still work */}
        <Route path="/login" element={token ? <Navigate to="/dashboard" /> : <LandingPage setToken={saveToken} />} />
        <Route path="/signup" element={token ? <Navigate to="/dashboard" /> : <LandingPage setToken={saveToken} />} />
        <Route path="/about" element={token ? withAuth(About) : <Navigate to="/" />} />
        <Route path="/contact" element={token ? withAuth(Contact) : <Navigate to="/" />} />
        <Route path="/policy" element={token ? withAuth(Policy) : <Navigate to="/" />} />
        <Route path="/docs" element={token ? withAuth(Docs) : <Navigate to="/" />} />
        <Route
          path="/dashboard/*"
          element={token ? <AppShell token={token} logout={logout} /> : <Navigate to="/" />}
        />
      </Routes>
    </Router>
  );
}

export default App;
