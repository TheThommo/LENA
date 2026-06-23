'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import {
  clearAuthSession,
  isTokenStillValid,
  persistAuthSession,
  SESSION_STORAGE_KEYS,
} from '@/lib/authSession';

export interface User {
  id: string;
  email: string;
  name: string;
  role: string;
  persona_type?: string;
  tenant_id: string;
  created_at: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, sessionId?: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

function readStoredUser(): User | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(SESSION_STORAGE_KEYS.user);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function readStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(SESSION_STORAGE_KEYS.token);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(() => readStoredUser());
  const [token, setToken] = useState<string | null>(() => readStoredToken());
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    clearAuthSession();
  }, []);

  // Drop expired tokens on load so stale sessions don't linger past 7 days.
  useEffect(() => {
    const stored = readStoredToken();
    if (stored && !isTokenStillValid(stored)) {
      clearSession();
    }
  }, [clearSession]);

  useEffect(() => {
    if (token) {
      localStorage.setItem(SESSION_STORAGE_KEYS.token, token);
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEYS.token);
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      localStorage.setItem(SESSION_STORAGE_KEYS.user, JSON.stringify(user));
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEYS.user);
    }
  }, [user]);

  const refreshUser = useCallback(async () => {
    const activeToken = token || readStoredToken();
    if (!activeToken) {
      setIsLoading(false);
      return;
    }

    if (!isTokenStillValid(activeToken)) {
      clearSession();
      setIsLoading(false);
      return;
    }

    if (!token) {
      setToken(activeToken);
    }
    if (!user) {
      const cached = readStoredUser();
      if (cached) setUser(cached);
    }

    try {
      const response = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${activeToken}` },
      });

      if (response.status === 401 || response.status === 403) {
        // Only clear if the JWT is actually expired — avoids logout on transient misconfig.
        if (!isTokenStillValid(activeToken)) {
          clearSession();
        }
      } else if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        persistAuthSession(activeToken, userData);
      }
      // Non-auth failures (5xx, network): keep cached session alive
    } catch (error) {
      console.error('Error refreshing user:', error);
      const cached = readStoredUser();
      if (cached && isTokenStillValid(activeToken)) {
        setUser(cached);
        setToken(activeToken);
      }
    } finally {
      setIsLoading(false);
    }
  }, [token, user, clearSession]);

  useEffect(() => {
    refreshUser();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const login = async (email: string, password: string) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || 'Invalid email or password');
      }

      const data = await response.json();
      setToken(data.access_token);
      setUser(data.user);
      persistAuthSession(data.access_token, data.user);
    } catch (error) {
      console.error('Error logging in:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email: string, password: string, name: string, sessionId?: string) => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, name, session_id: sessionId }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || 'Registration failed. Please try again.');
      }

      const data = await response.json();
      setToken(data.access_token);
      setUser(data.user);
      persistAuthSession(data.access_token, data.user);
    } catch (error) {
      console.error('Error registering:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    clearSession();
  };

  const hasValidSession = !!user && !!token && isTokenStillValid(token);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: hasValidSession,
        isLoading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
