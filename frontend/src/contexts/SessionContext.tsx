'use client';

import React, { createContext, useContext, useState, useRef, useCallback, useEffect } from 'react';

const STORAGE_KEY = 'lena_session_v1';

interface PersistedSession {
  name?: string | null;
  email?: string | null;
  disclaimerAccepted?: boolean;
  persona?: string;
}

function loadPersistedSession(): PersistedSession {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function savePersistedSession(s: PersistedSession) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {}
}

export type FunnelStage = 'landing' | 'name_captured' | 'disclaimer_accepted' | 'searching' | 'email_captured' | 'registered';

export type PersonaId =
  | 'medical_student'
  | 'clinician'
  | 'pharmacist'
  | 'researcher'
  | 'lecturer'
  | 'physiotherapist'
  | 'neuroscientist'
  | 'alternative_practitioner'
  | 'patient'
  | 'general';

export const PERSONAS: { id: PersonaId; label: string; icon: string }[] = [
  { id: 'medical_student', label: 'Medical Student', icon: '🎓' },
  { id: 'clinician', label: 'Clinician', icon: '🩺' },
  { id: 'pharmacist', label: 'Pharmacist', icon: '💊' },
  { id: 'researcher', label: 'Researcher', icon: '🔬' },
  { id: 'lecturer', label: 'Lecturer', icon: '📚' },
  { id: 'physiotherapist', label: 'Physiotherapist', icon: '🏃' },
  { id: 'neuroscientist', label: 'Neuroscientist', icon: '🧠' },
  { id: 'alternative_practitioner', label: 'Alternative Practitioner', icon: '🌿' },
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

export interface EmailCapturePayload {
  email: string;
  institution?: string;
  phone?: string;
  city?: string;
  country?: string;
  dataConsentAccepted: boolean;
}

export interface UnifiedCapturePayload {
  name: string;
  email: string;
  disclaimerAccepted: boolean;
  dataConsentAccepted: boolean;
  institution?: string;
}

interface SessionContextType {
  session: SessionState;
  startSession: () => Promise<void>;
  captureName: (name: string) => Promise<void>;
  acceptDisclaimer: () => Promise<void>;
  captureEmail: (data: EmailCapturePayload) => Promise<void>;
  captureAll: (data: UnifiedCapturePayload) => Promise<void>;
  skipEmail: () => void;
  incrementSearch: () => Promise<void>;
  setPersona: (persona: PersonaId) => void;
}

const SessionContext = createContext<SessionContextType | undefined>(undefined);

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<SessionState>(() => {
    const persisted = loadPersistedSession();
    return {
      sessionId: null,
      sessionToken: null,
      name: persisted.name ?? null,
      email: persisted.email ?? null,
      persona: (persisted.persona as PersonaId) || 'general',
      disclaimerAccepted: !!persisted.disclaimerAccepted,
      searchCount: 0,
      funnelStage: persisted.disclaimerAccepted ? 'disclaimer_accepted' : (persisted.name ? 'name_captured' : 'landing'),
    };
  });

  // Persist session state to localStorage whenever it changes
  useEffect(() => {
    savePersistedSession({
      name: session.name,
      email: session.email,
      disclaimerAccepted: session.disclaimerAccepted,
      persona: session.persona,
    });
  }, [session.name, session.email, session.disclaimerAccepted, session.persona]);

  // Ref to always hold the latest sessionId, avoiding stale closures
  const sessionIdRef = useRef<string | null>(null);

  // Shared promise so only ONE session creation happens, even if called concurrently
  const sessionPromiseRef = useRef<Promise<string | null> | null>(null);

  /**
   * Ensure a session exists. If one is already being created, await that same promise.
   * Returns the session ID or null on failure.
   */
  const ensureSession = useCallback(async (): Promise<string | null> => {
    // Already have a session
    if (sessionIdRef.current) return sessionIdRef.current;

    // Another call is already creating the session — wait for it
    if (sessionPromiseRef.current) return sessionPromiseRef.current;

    // Create the session (single shared promise)
    sessionPromiseRef.current = (async () => {
      try {
        const res = await fetch(`${API_BASE}/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });
        if (!res.ok) throw new Error('Failed to start session');

        const data = await res.json();
        sessionIdRef.current = data.session_id;
        setSession(prev => ({
          ...prev,
          sessionId: data.session_id,
          sessionToken: data.session_token,
        }));
        return data.session_id as string;
      } catch (error) {
        console.error('Error starting session:', error);
        return null;
      } finally {
        sessionPromiseRef.current = null;
      }
    })();

    return sessionPromiseRef.current;
  }, []);

  const startSession = async () => {
    await ensureSession();
  };

  const captureName = async (name: string) => {
    // Update UI immediately
    setSession(prev => ({ ...prev, name, funnelStage: 'name_captured' }));

    try {
      const sid = await ensureSession();
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
    // Update UI immediately
    setSession(prev => ({ ...prev, disclaimerAccepted: true, funnelStage: 'disclaimer_accepted' }));

    try {
      const sid = await ensureSession();
      if (!sid) return;

      const response = await fetch(`${API_BASE}/session/${sid}/disclaimer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accepted: true }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.session_token) {
          setSession(prev => ({ ...prev, sessionToken: data.session_token }));
        }
      }
    } catch (error) {
      console.error('Error accepting disclaimer:', error);
    }
  };

  const captureEmail = async (data: EmailCapturePayload) => {
    setSession(prev => ({ ...prev, email: data.email, funnelStage: 'email_captured' }));

    try {
      const sid = sessionIdRef.current;
      if (sid) {
        await fetch(`${API_BASE}/session/${sid}/email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            email: data.email,
            institution: data.institution,
            phone: data.phone,
            city: data.city,
            country: data.country,
            data_consent_accepted: data.dataConsentAccepted,
          }),
        });
      }
    } catch (error) {
      console.error('Error capturing email:', error);
    }
  };

  const captureAll = async (data: UnifiedCapturePayload) => {
    const sid = await ensureSession();
    if (!sid) throw new Error('Could not start session. Please try again.');

    const res = await fetch(`${API_BASE}/session/${sid}/capture`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: data.name,
        email: data.email,
        disclaimer_accepted: data.disclaimerAccepted,
        data_consent_accepted: data.dataConsentAccepted,
        institution: data.institution,
      }),
    });

    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.detail || 'Unable to complete sign-up.');
    }

    const payload = await res.json();
    setSession(prev => ({
      ...prev,
      name: data.name,
      email: data.email,
      disclaimerAccepted: true,
      sessionToken: payload.session_token || prev.sessionToken,
      funnelStage: 'email_captured',
    }));
  };

  const skipEmail = () => {
    setSession(prev => ({ ...prev, email: '_skipped', funnelStage: 'email_captured' }));
  };

  const setPersona = (persona: PersonaId) => {
    setSession(prev => ({ ...prev, persona }));
  };

  const incrementSearch = async () => {
    setSession(prev => ({
      ...prev,
      searchCount: prev.searchCount + 1,
      funnelStage: prev.searchCount >= 1 ? 'searching' : prev.funnelStage,
    }));
  };

  return (
    <SessionContext.Provider
      value={{
        session,
        startSession,
        captureName,
        acceptDisclaimer,
        captureEmail,
        captureAll,
        skipEmail,
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
