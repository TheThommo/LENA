'use client';

import React, { createContext, useContext, useState } from 'react';

export type FunnelStage = 'landing' | 'name_captured' | 'disclaimer_accepted' | 'searching' | 'email_captured' | 'registered';

export type PersonaId = 'medical_student' | 'clinician' | 'pharmacist' | 'researcher' | 'lecturer' | 'physiotherapist' | 'patient' | 'general';

export const PERSONAS: { id: PersonaId; label: string; icon: string }[] = [
  { id: 'medical_student', label: 'Medical Student', icon: '🎓' },
  { id: 'clinician', label: 'Clinician', icon: '🩺' },
  { id: 'pharmacist', label: 'Pharmacist', icon: '💊' },
  { id: 'researcher', label: 'Researcher', icon: '🔬' },
  { id: 'lecturer', label: 'Lecturer', icon: '📚' },
  { id: 'physiotherapist', label: 'Physiotherapist', icon: '🏃' },
  { id: 'patient', label: 'Patient', icon: '❤️' },
  { id: 'general', label: 'General', icon: '🌐' },
];

export interface SessionState {
  sessionId: string | null;
  sessionToken: string | null;
  name: string | null;
  email: string | null;
  persona: PersonaId;
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
  setPersona: (persona: PersonaId) => void;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionState>({
    sessionId: null,
    sessionToken: null,
    name: null,
    email: null,
    persona: 'general',
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
    // Always update local state first so the funnel progresses
    setSession(prev => ({
      ...prev,
      name,
      funnelStage: 'name_captured',
    }));

    try {
      // Auto-start session if we don't have one yet
      let sid = session.sessionId;
      if (!sid) {
        const startRes = await fetch(`${API_BASE}/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (startRes.ok) {
          const data = await startRes.json();
          sid = data.session_id;
          setSession(prev => ({
            ...prev,
            sessionId: data.session_id,
            sessionToken: data.session_token,
          }));
        }
      }

      // Send name to backend if we have a session
      if (sid) {
        await fetch(`${API_BASE}/session/${sid}/name`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name }),
        });
      }
    } catch (error) {
      console.error('Error capturing name:', error);
    }
  };

  const acceptDisclaimer = async () => {
    // Always update local state first so the funnel progresses
    setSession(prev => ({
      ...prev,
      disclaimerAccepted: true,
      funnelStage: 'disclaimer_accepted',
    }));

    try {
      if (session.sessionId) {
        const response = await fetch(`${API_BASE}/session/${session.sessionId}/disclaimer`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ accepted: true }),
        });
        if (response.ok) {
          const data = await response.json();
          // Store the authorized session token for search requests
          if (data.session_token) {
            setSession(prev => ({
              ...prev,
              sessionToken: data.session_token,
            }));
          }
        }
      }
    } catch (error) {
      console.error('Error accepting disclaimer:', error);
    }
  };

  const captureEmail = async (email: string) => {
    // Always update local state first so the funnel progresses
    setSession(prev => ({
      ...prev,
      email,
      funnelStage: 'email_captured',
    }));

    try {
      if (session.sessionId) {
        await fetch(`${API_BASE}/session/${session.sessionId}/email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email }),
        });
      }
    } catch (error) {
      console.error('Error capturing email:', error);
    }
  };

  const setPersona = (persona: PersonaId) => {
    setSession(prev => ({ ...prev, persona }));
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
        setPersona,
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
