import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { apiGet } from '../lib/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!token) {
      setLoading(false);
      return;
    }

    apiGet('/auth/me')
      .then(setUser)
      .catch(() => {
        localStorage.removeItem('token');
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(() => {
    apiGet('/auth/login').then((data) => {
      window.location.href = data.url;
    });
  }, []);

  const handleCallback = useCallback(async (code) => {
    const data = await apiGet(`/auth/callback?code=${code}`);
    localStorage.setItem('token', data.token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, handleCallback }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
