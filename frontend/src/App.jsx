import React, { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './components/Login';
import Signup from './components/Signup';
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
        <Route path="/" element={token ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} />
        <Route path="/login" element={<Login setToken={saveToken} />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/about" element={token ? withAuth(About) : <Navigate to="/login" />} />
        <Route path="/contact" element={token ? withAuth(Contact) : <Navigate to="/login" />} />
        <Route path="/policy" element={token ? withAuth(Policy) : <Navigate to="/login" />} />
        <Route path="/docs" element={token ? withAuth(Docs) : <Navigate to="/login" />} />
        <Route
          path="/dashboard/*"
          element={token ? <AppShell token={token} logout={logout} /> : <Navigate to="/login" />}
        />
      </Routes>
    </Router>
  );
}

export default App;
