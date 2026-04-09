'use client';

import React, { createContext, useContext, useState } from 'react';

export type FunnelStage = 'landing' | 'name_captured' | 'disclaimer_accepted' | 'searching' | 'email_captured' | 'registered';

export interface SessionState {
  sessionId: string | null;
  sessionToken: string | null;
  name: string | null;
  email: string | null;
  disclaimerAccepted: boolean;
  searchCount: number;
  funnelStage: FunnelStage;
}

interface SessionContextType {
  session: SessionState;
  startSession: () => Promise<void>;
  captureName: (name: string) => Promise<void>;
  acceptDisclaimer: () => Promise<void>;
  captureEmail: (email: string) => Promise<void>;
  incrementSearch: () => Promise<void>;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionState>({
    sessionId: null,
    sessionToken: null,
    name: null,
    email: null,
    disclaimerAccepted: false,
    searchCount: 0,
    funnelStage: 'landing',
  });

  const startSession = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) throw new Error('Failed to start session');

      const data = await response.json();
      setSession(prev => ({
        ...prev,
        sessionId: data.session_id,
        sessionToken: data.session_token,
      }));
    } catch (error) {
      console.error('Error starting session:', error);
    }
  };

  const captureName = async (name: string) => {
    try {
      const response = await fetch(`${API_BASE}/session/capture-name`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.sessionId, name }),
      });
      if (!response.ok) throw new Error('Failed to capture name');

      setSession(prev => ({
        ...prev,
        name,
        funnelStage: 'name_captured',
      }));
    } catch (error) {
      console.error('Error capturing name:', error);
    }
  };

  const acceptDisclaimer = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/accept-disclaimer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.sessionId }),
      });
      if (!response.ok) throw new Error('Failed to accept disclaimer');

      setSession(prev => ({
        ...prev,
        disclaimerAccepted: true,
        funnelStage: 'disclaimer_accepted',
      }));
    } catch (error) {
      console.error('Error accepting disclaimer:', error);
    }
  };

  const captureEmail = async (email: string) => {
    try {
      const response = await fetch(`${API_BASE}/session/capture-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.sessionId, email }),
      });
      if (!response.ok) throw new Error('Failed to capture email');

      setSession(prev => ({
        ...prev,
        email,
        funnelStage: 'email_captured',
      }));
    } catch (error) {
      console.error('Error capturing email:', error);
    }
  };

  const incrementSearch = async () => {
    try {
      const response = await fetch(`${API_BASE}/session/increment-search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.sessionId }),
      });
      if (!response.ok) throw new Error('Failed to increment search count');

      setSession(prev => ({
        ...prev,
        searchCount: prev.searchCount + 1,
        funnelStage: prev.searchCount >= 1 ? 'searching' : prev.funnelStage,
      }));
    } catch (error) {
      console.error('Error incrementing search:', error);
    }
  };

  return (
    <SessionContext.Provider
      value={{
        session,
        startSession,
        captureName,
        acceptDisclaimer,
        captureEmail,
        incrementSearch,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession(): SessionContextType {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
