'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { product, branding } from '@/config/branding';
import WelcomeView from '@/components/chat/WelcomeView';
import ChatMessage from '@/components/chat/ChatMessage';
import ResearchPanel from '@/components/chat/ResearchPanel';
import ThinkingIndicator from '@/components/search/ThinkingIndicator';
import SearchLimitModal from '@/components/funnel/SearchLimitModal';
import DisclaimerCard from '@/components/chat/DisclaimerCard';
import UpgradeCTACard from '@/components/chat/UpgradeCTACard';
import ContactSupportCard from '@/components/chat/ContactSupportCard';
import PersonaSelector from '@/components/PersonaSelector';
import ComingSoon, { COMMUNITY_CONFIG, CONTRIBUTION_CONFIG } from '@/components/views/ComingSoon';
import HowItWorks from '@/components/views/HowItWorks';
import MyDocuments from '@/components/views/MyDocuments';
import ProfileSettings from '@/components/views/MyBrain';
import { useSession } from '@/contexts/SessionContext';
import { useProjects } from '@/contexts/ProjectsContext';
import { useAuth } from '@/contexts/AuthContext';
import { useTenant } from '@/contexts/TenantContext';
import { searchLiterature, SearchResponse, ResultMode, listProjectSearches, type ProjectSearch, getBillingStatus, createCheckoutSession, type BillingPlan, fetchSavedDocuments, upsertSavedDocumentApi, deleteSavedDocumentApi, LenaSystemError, LenaUpgradeRequiredError, ingestDocument } from '@/lib/api';
import {
  configureDocumentsSync,
  hydrateDocumentsFromCloud,
  type SavedDocument,
} from '@/lib/savedDocuments';
import { configureProfileSync, buildProfileContextForSearch } from '@/lib/userProfile';
import {
  type RecentSessionRecord,
  normalizeRecentSession,
  sessionNeedsTimestampMigration,
} from '@/lib/sessionTime';
import { resolvePulseConfidencePercent } from '@/lib/pulseLabels';
import { copyTextToClipboard } from '@/lib/clipboard';
import { SegmentedControl } from '@/components/ui/SegmentedControl';
import { BrandMark } from '@/components/brand/BrandMark';
import { useMediaQuery, useVisualViewportBottomInset } from '@/hooks/useMediaQuery';

const RESULT_MODE_OPTIONS = [
  { id: 'all' as ResultMode, label: 'All', shortLabel: 'All' },
  { id: 'supplements' as ResultMode, label: 'Supplements', shortLabel: 'Supp.' },
  { id: 'herbal' as ResultMode, label: 'Herbal', shortLabel: 'Herbal' },
  { id: 'alternatives' as ResultMode, label: 'Alt.', shortLabel: 'Alt.' },
  { id: 'outlier' as ResultMode, label: 'Outlier', shortLabel: 'Out.' },
];

interface MessageAttachment {
  name: string;
  kind: string;
  previewUrl?: string;
  charCount?: number;
}

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  attachment?: MessageAttachment;
  response?: SearchResponse;
  timestamp: Date;
}

function normalizeView(view: string): string {
  if (view === 'sources') return 'documents';
  if (view === 'brain') return 'profile';
  return view;
}

export default function Home() {
  const router = useRouter();
  const { session, incrementSearch, acceptDisclaimer } = useSession();
  const pendingQueryRef = useRef<string | null>(null);
  const { activeProject, activeProjectId, setActiveProjectId, refresh: refreshProjects, projects, assignSearch, createNew: createNewProject, rename: renameProject, archive: archiveProject } = useProjects();
  const { isAuthenticated, isLoading: authLoading, user, token: authToken, logout } = useAuth();
  const { tenant } = useTenant();

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [pendingAttachment, setPendingAttachment] = useState<{
    name: string;
    text: string;
    kind: string;
    previewUrl?: string;
  } | null>(null);
  const [attaching, setAttaching] = useState(false);
  const [loading, setLoading] = useState(false);
  type ClientNotice = { kind: 'support' } | { kind: 'upgrade'; message: string };
  const [clientNotice, setClientNotice] = useState<ClientNotice | null>(null);
  const [signupModalOpen, setSignupModalOpen] = useState(false);

  // UI state
  const [activeView, setActiveView] = useState('chat');
  const [panelOpen, setPanelOpen] = useState(false);
  const [sessionSearchOpen, setSessionSearchOpen] = useState(false);
  const [sessionSearch, setSessionSearch] = useState('');
  // Result-mode multi-select: 'all' (default), 'supplements', 'herbal', 'alternatives', 'outlier'. Multiple may be active.
  // Persisted per user so filters survive logout/reload (Lauren bug: "have to select every login").
  const resultModesKey = user?.id ? `lena_result_modes_${user.id}` : null;
  const [resultModes, setResultModes] = useState<ResultMode[]>(['all']);

  // Load saved result modes for this user on login
  useEffect(() => {
    if (!resultModesKey) return;
    try {
      const saved = JSON.parse(localStorage.getItem(resultModesKey) || '');
      if (Array.isArray(saved) && saved.length > 0) setResultModes(saved as ResultMode[]);
    } catch { /* no saved prefs → stay with default */ }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultModesKey]);

  const handleResultModesChange = useCallback((next: ResultMode[]) => {
    setResultModes(next);
    if (resultModesKey) {
      try { localStorage.setItem(resultModesKey, JSON.stringify(next)); } catch {}
    }
  }, [resultModesKey]);

  const [recentSessions, setRecentSessions] = useState<RecentSessionRecord[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [projectSearches, setProjectSearches] = useState<ProjectSearch[]>([]);
  const [projectLoading, setProjectLoading] = useState(false);
  const [projectSearchesRevision, setProjectSearchesRevision] = useState(0);
  const isDesktop = useMediaQuery('(min-width: 1024px)');
  const isTabletUp = useMediaQuery('(min-width: 768px)');
  const keyboardInset = useVisualViewportBottomInset();

  // Desktop: sidebar open by default; mobile: closed until user opens it
  useEffect(() => {
    setSidebarOpen(isDesktop);
  }, [isDesktop]);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const attachFile = useCallback(async (file: File) => {
    setAttaching(true);
    try {
      const ingested = await ingestDocument(file);
      if (!ingested.text?.trim()) {
        setClientNotice({
          kind: 'upgrade',
          message: 'LENA could not read text from that file. Try a clearer photo of the label, or paste the product URL in your question.',
        });
        return;
      }
      const previewUrl = file.type.startsWith('image/')
        ? URL.createObjectURL(file)
        : undefined;
      setPendingAttachment({
        name: ingested.filename || ingested.title || file.name,
        text: ingested.text,
        kind: ingested.kind || (file.type.startsWith('image/') ? 'image' : 'text'),
        previewUrl,
      });
    } catch {
      setClientNotice({
        kind: 'upgrade',
        message: 'Could not read that file. Try a JPG/PNG label photo, PDF, or paste the product link in your question.',
      });
    } finally {
      setAttaching(false);
    }
  }, []);

  // Revoke blob preview URLs when attachment is removed or replaced
  useEffect(() => {
    return () => {
      if (pendingAttachment?.previewUrl) {
        URL.revokeObjectURL(pendingAttachment.previewUrl);
      }
    };
  }, [pendingAttachment?.previewUrl]);
  const currentSessionIdRef = useRef<string>(Date.now().toString());

  // ── Recent sessions: per-user, auth-gated, zero-leak ──────────────
  //
  // Rules:
  //   1. NOT logged in → recentSessions is ALWAYS empty. No exceptions.
  //   2. Logged in → data keyed to `lena_recent_sessions_{userId}`.
  //      Different user = different key = different history.
  //   3. On first load, nuke the old global keys (pre-fix orphaned data)
  //      so they can never surface during auth transitions.

  const sessionsKey = user?.id ? `lena_recent_sessions_${user.id}` : null;
  const threadsKey = user?.id ? `lena_session_threads_${user.id}` : null;
  const activeSessionKey = user?.id ? `lena_active_session_${user.id}` : null;
  const restoringThreadRef = useRef(false);
  const hasAutoRestoredRef = useRef(false);

  // One-time cleanup: remove pre-fix un-namespaced keys so they can never
  // flash on screen during auth state transitions.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.removeItem('lena_recent_sessions');
      localStorage.removeItem('lena_session_threads');
    } catch {}
  }, []);

  const prevUserIdRef = useRef<string | null>(null);
  useEffect(() => {
    const uid = user?.id || null;
    // HARD RULE: not authenticated → empty. No stale data, no exceptions.
    if (!isAuthenticated || !uid || !sessionsKey) {
      // Only clear if we previously had a user (avoids infinite re-render
      // from setting new [] references on every render cycle).
      if (prevUserIdRef.current !== null) {
        setRecentSessions([]);
        setMessages([]);
        setClientNotice(null);
      }
      prevUserIdRef.current = null;
      return;
    }
    // User changed (login / switch account) — load their sessions
    if (prevUserIdRef.current !== uid) {
      prevUserIdRef.current = uid;
      try {
        const stored = localStorage.getItem(sessionsKey);
        const parsed: RecentSessionRecord[] = stored ? JSON.parse(stored) : [];
        const migrated = parsed.map(normalizeRecentSession);
        const needsSave = parsed.some(sessionNeedsTimestampMigration);
        if (needsSave) {
          localStorage.setItem(sessionsKey, JSON.stringify(migrated));
        }
        setRecentSessions(migrated);
      } catch {
        setRecentSessions([]);
      }
    }
  }, [isAuthenticated, user?.id, sessionsKey]);

  // Cloud sync for documents (profile sync is handled in ProfileSettings).
  useEffect(() => {
    if (!isAuthenticated || !user?.id || !authToken) {
      configureDocumentsSync(null, null);
      configureProfileSync(null, null);
      return;
    }
    configureProfileSync(user.id, authToken);
    configureDocumentsSync(user.id, authToken, {
      listRemote: async (token) => {
        const { documents } = await fetchSavedDocuments(token);
        return documents as unknown as SavedDocument[];
      },
      upsertRemote: async (token, doc) => {
        await upsertSavedDocumentApi(token, doc.id, doc as unknown as Record<string, unknown>);
      },
      deleteRemote: async (token, docKey) => {
        await deleteSavedDocumentApi(token, docKey);
      },
    });
    void hydrateDocumentsFromCloud();
  }, [isAuthenticated, user?.id, authToken]);

  // Persist the full message thread for a session so clicking a recent
  // session restores it locally instead of re-running the search (which
  // would double-bill the backend / API tokens).
  const persistSessionThread = useCallback((sessionId: string, thread: Message[]) => {
    if (!threadsKey) return;
    try {
      const raw = localStorage.getItem(threadsKey);
      const all: Record<string, Message[]> = raw ? JSON.parse(raw) : {};
      all[sessionId] = thread;
      localStorage.setItem(threadsKey, JSON.stringify(all));
    } catch {}
  }, [threadsKey]);

  const loadSessionThread = useCallback((sessionId: string): Message[] | null => {
    if (!threadsKey) return null;
    try {
      const raw = localStorage.getItem(threadsKey);
      if (!raw) return null;
      const all: Record<string, Message[]> = JSON.parse(raw);
      const thread = all[sessionId];
      if (!thread) return null;
      // Revive Date objects after JSON round-trip
      return thread.map(m => ({ ...m, timestamp: new Date(m.timestamp) }));
    } catch {
      return null;
    }
  }, [threadsKey]);

  // Restore the user's last active chat after reload (e.g. floaters search).
  useEffect(() => {
    if (!isAuthenticated || !threadsKey || hasAutoRestoredRef.current) return;
    if (recentSessions.length === 0 || messages.length > 0) return;

    const pickLatest = (sessions: RecentSessionRecord[]) =>
      [...sessions].sort(
        (a, b) => new Date(b.lastActivityAt).getTime() - new Date(a.lastActivityAt).getTime(),
      )[0];

    const savedActiveId = activeSessionKey ? localStorage.getItem(activeSessionKey) : null;
    const target =
      (savedActiveId ? recentSessions.find(s => s.id === savedActiveId) : undefined) ||
      pickLatest(recentSessions);

    const thread = loadSessionThread(target.id);
    if (!thread?.length) return;

    restoringThreadRef.current = true;
    currentSessionIdRef.current = target.id;
    if (target.projectId) setActiveProjectId(target.projectId);
    setMessages(thread);
    setActiveView('chat');
    hasAutoRestoredRef.current = true;
  }, [
    isAuthenticated,
    recentSessions,
    threadsKey,
    activeSessionKey,
    loadSessionThread,
    messages.length,
    setActiveProjectId,
  ]);

  // Flush chat thread to localStorage if the tab closes mid-session.
  useEffect(() => {
    if (!isAuthenticated || !threadsKey) return;
    const flush = () => {
      if (messages.length > 0) {
        persistSessionThread(currentSessionIdRef.current, messages);
      }
    };
    window.addEventListener('beforeunload', flush);
    return () => window.removeEventListener('beforeunload', flush);
  }, [isAuthenticated, threadsKey, messages, persistSessionThread]);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-resize textarea
  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 130) + 'px';
  }, []);

  // Save recent search — grouped by session. Only persisted for authenticated
  // users (anonymous visitors don't get a history trail).
  const addRecentSearch = useCallback((query: string) => {
    if (!isAuthenticated) return;
    const sid = currentSessionIdRef.current;
    const pid = activeProjectId || null;
    const now = new Date().toISOString();
    if (activeSessionKey) {
      try { localStorage.setItem(activeSessionKey, sid); } catch {}
    }
    setRecentSessions(prev => {
      const existing = prev.find(s => s.id === sid);
      let updated: RecentSessionRecord[];
      if (existing) {
        // Append query to existing session. Keep session's original
        // projectId - don't silently rehome it across projects mid-thread.
        updated = [
          {
            ...existing,
            queries: [...existing.queries, query],
            lastActivityAt: now,
          },
          ...prev.filter(s => s.id !== sid),
        ];
      } else {
        // New session - stamp with the project context it was born into
        updated = [
          {
            id: sid,
            firstQuery: query,
            queries: [query],
            createdAt: now,
            lastActivityAt: now,
            projectId: pid,
          },
          ...prev,
        ];
      }
      // Cap only the unfiled list so project-scoped history isn't evicted
      const unfiled = updated.filter(s => !s.projectId).slice(0, 8);
      const filed = updated.filter(s => s.projectId);
      updated = [...filed, ...unfiled];
      if (sessionsKey) {
        localStorage.setItem(sessionsKey, JSON.stringify(updated));
      }
      return updated;
    });
  }, [isAuthenticated, sessionsKey, activeProjectId, activeSessionKey]);

  const deleteRecentSession = useCallback((sessionId: string) => {
    if (!isAuthenticated || !sessionsKey || !threadsKey) return;
    setRecentSessions(prev => {
      const next = prev.filter(s => s.id !== sessionId);
      try {
        localStorage.setItem(sessionsKey, JSON.stringify(next));
      } catch {}
      return next;
    });
    try {
      const raw = localStorage.getItem(threadsKey);
      if (raw) {
        const all: Record<string, Message[]> = JSON.parse(raw);
        delete all[sessionId];
        localStorage.setItem(threadsKey, JSON.stringify(all));
      }
    } catch {}
    if (currentSessionIdRef.current === sessionId) {
      setMessages([]);
      setClientNotice(null);
      currentSessionIdRef.current = Date.now().toString();
    }
  }, [isAuthenticated, sessionsKey, threadsKey]);

  const renameRecentSession = useCallback((sessionId: string, title: string) => {
    if (!isAuthenticated || !sessionsKey) return;
    const trimmed = title.trim();
    setRecentSessions(prev => {
      const next = prev.map(s => {
        if (s.id !== sessionId) return s;
        if (!trimmed || trimmed === s.firstQuery) {
          const { title: _drop, ...rest } = s;
          return rest;
        }
        return { ...s, title: trimmed };
      });
      try { localStorage.setItem(sessionsKey, JSON.stringify(next)); } catch {}
      return next;
    });
  }, [isAuthenticated, sessionsKey]);

  // Update a recent session's projectId in-place (after user clicks
  // "Add to Project" on a result). Lets the sidebar move it from top-
  // level Recent Sessions into the project's nested list without a reload.
  const setSessionProject = useCallback((sessionId: string, projectId: string | null) => {
    if (!isAuthenticated || !sessionsKey) return;
    setRecentSessions(prev => {
      const next = prev.map(s => s.id === sessionId ? { ...s, projectId } : s);
      try { localStorage.setItem(sessionsKey, JSON.stringify(next)); } catch {}
      return next;
    });
  }, [isAuthenticated, sessionsKey]);

  // Handle search
  const handleSend = async (text?: string) => {
    const query = (text || input).trim();
    if (!query || loading) return;

    // Gate the 2nd anon attempt here so the signup modal only fires when
    // the visitor tries to SEARCH AGAIN - never right after the first
    // result lands. This lets them read the 1st result in peace.
    // Dev bypass: URL ?bypass=1 or localStorage.lena_bypass_gate === '1'.
    const bypass = (() => {
      if (typeof window === 'undefined') return false;
      try {
        if (new URLSearchParams(window.location.search).get('bypass') === '1') return true;
        return localStorage.getItem('lena_bypass_gate') === '1';
      } catch {
        return false;
      }
    })();
    if (!isAuthenticated && session.searchCount >= 1 && !bypass) {
      setSignupModalOpen(true);
      return;
    }

    setInput('');
    setClientNotice(null);
    const attachmentSnapshot: MessageAttachment | undefined = pendingAttachment
      ? {
          name: pendingAttachment.name,
          kind: pendingAttachment.kind,
          previewUrl: pendingAttachment.previewUrl,
          charCount: pendingAttachment.text.length,
        }
      : undefined;
    const attachmentText = pendingAttachment?.text;
    const attachmentMeta = pendingAttachment
      ? { filename: pendingAttachment.name, kind: pendingAttachment.kind }
      : undefined;
    setPendingAttachment(null);
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: query,
      attachment: attachmentSnapshot,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    addRecentSearch(query);

    try {
      const result = await searchLiterature(query, {
        sources: ['pubmed', 'clinical_trials', 'cochrane', 'who_iris', 'cdc', 'openalex', 'semantic_scholar', 'europe_pmc', 'dailymed', 'ods_dsld', 'openfda'],
        modes: resultModes,
        maxResults: 50,
        sessionId: session.sessionId || undefined,
        sessionToken: authToken || session.sessionToken || undefined,
        tenantId: tenant.id,
        persona: session.persona,
        profileContext: buildProfileContextForSearch(user?.id),
        attachedContext: attachmentText,
        attachmentMeta,
        projectId: isAuthenticated && activeProjectId ? activeProjectId : undefined,
      });

      // Guardrail responses (off-topic, profanity, self-harm) have no
      // pulse_report or llm_summary — show the guardrail message directly.
      const summary = result.guardrail_triggered && result.guardrail_message
        ? result.guardrail_message
        : (result.llm_summary || generateSummary(result));

      const isDisclaimerPrompt =
        result.guardrail_triggered && result.guardrail_type === 'disclaimer_required';

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: summary,
        response: result,
        timestamp: new Date(),
      };
      if (isDisclaimerPrompt) {
        pendingQueryRef.current = query;
      }
      setMessages(prev => {
        const next = [...prev, assistantMsg];
        // Persist so clicking this session in 'Recent Sessions' restores from
        // local state without re-calling the backend (which would re-bill).
        if (isAuthenticated) {
          persistSessionThread(currentSessionIdRef.current, next);
        }
        return next;
      });
      // Only count a search against the visitor's quota if it actually
      // returned papers. Guardrails never count, and 0-result searches
      // (source timeouts, no matches) don't count either - backend follows
      // the same rule on fingerprint/search_logs, so client + server stay
      // in sync.
      const chargeable =
        !result.guardrail_triggered && (result.total_results || 0) > 0;
      if (chargeable) {
        incrementSearch();
      }
      if (isAuthenticated && activeProjectId && result.search_id) {
        try {
          await assignSearch(result.search_id, activeProjectId);
        } catch {
          /* sidebar still updates via setSessionProject */
        }
      }
      // Update the project's search_count badge in the sidebar
      if (isAuthenticated && activeProjectId) {
        setSessionProject(currentSessionIdRef.current, activeProjectId);
        setProjectSearchesRevision(r => r + 1);
        refreshProjects();
      }
    } catch (err) {
      if (err instanceof LenaUpgradeRequiredError) {
        setClientNotice({ kind: 'upgrade', message: err.message });
      } else {
        setClientNotice({ kind: 'support' });
      }
    } finally {
      setLoading(false);
    }
  };

  // Route the upgrade CTA: if Stripe is live, create a checkout session
  // and redirect; otherwise fall back to a mailto so we never leave the
  // user stranded. Anon visitors hit the signup page first.
  const handleUpgrade = useCallback(async (plan: BillingPlan = 'pro_monthly') => {
    if (!isAuthenticated || !authToken) {
      router.push(`/register?session_id=${session.sessionId || ''}`);
      return;
    }
    try {
      const billingStatus = await getBillingStatus();
      if (billingStatus.enabled && billingStatus.plans[plan]) {
        const checkout = await createCheckoutSession(authToken, plan);
        window.location.href = checkout.url;
        return;
      }
    } catch (err) {
      console.warn('Stripe unavailable, falling back to mailto', err);
    }
    window.location.href =
      'mailto:hello@lena-app.com?subject=LENA%20Pro%20Upgrade&body=I%27d%20like%20to%20upgrade%20to%20LENA%20Pro.';
  }, [isAuthenticated, authToken, router, session.sessionId]);

  // Handle inline disclaimer acceptance: POST accept, drop the card
  // message, then replay the pending query.
  const handleAcceptDisclaimer = useCallback(async () => {
    await acceptDisclaimer();
    const pending = pendingQueryRef.current;
    pendingQueryRef.current = null;
    setMessages(prev => prev.filter(m => m.response?.guardrail_type !== 'disclaimer_required'));
    if (pending) {
      await handleSend(pending);
    }
  }, [acceptDisclaimer]);

  // Restore a prior session's thread from localStorage without re-hitting the
  // backend. Falls back to running a fresh search only if the thread is
  // missing (e.g. storage cleared, cross-device).
  const handleRecentSessionClick = useCallback((sessionId: string, fallbackQuery: string) => {
    const thread = loadSessionThread(sessionId);
    // Restore the project context this session was born into so the
    // pill and sidebar highlight match the thread being viewed.
    const saved = recentSessions.find(s => s.id === sessionId);
    if (saved) {
      restoringThreadRef.current = true;
      setActiveProjectId(saved.projectId || null);
    }
    if (thread && thread.length > 0) {
      currentSessionIdRef.current = sessionId;
      setMessages(thread);
      setClientNotice(null);
      setActiveView('chat');
      return;
    }
    // No persisted thread — run the query as a last resort
    setActiveView('chat');
    handleSend(fallbackQuery);
  }, [loadSessionThread, recentSessions, setActiveProjectId]);

  const handleProjectSearchOpen = useCallback((search: ProjectSearch) => {
    if (!activeProjectId) return;
    if (threadsKey) {
      try {
        const raw = localStorage.getItem(threadsKey);
        if (raw) {
          const all: Record<string, Message[]> = JSON.parse(raw);
          for (const [sid, msgs] of Object.entries(all)) {
            if (Array.isArray(msgs) && msgs.some(m => m.response?.search_id === search.id)) {
              handleRecentSessionClick(sid, search.query);
              return;
            }
          }
        }
      } catch {}
    }
    const sess = recentSessions.find(
      s => s.projectId === activeProjectId && s.queries.includes(search.query),
    );
    if (sess) {
      handleRecentSessionClick(sess.id, search.query);
      return;
    }
    setActiveView('chat');
    void handleSend(search.query);
  }, [activeProjectId, threadsKey, recentSessions, handleRecentSessionClick]);

  const handleShareReferral = useCallback(async (): Promise<boolean> => {
    if (typeof window === 'undefined') return false;
    const ref = user?.id ? `?ref=${user.id}` : '';
    return copyTextToClipboard(`${window.location.origin}${ref}`);
  }, [user?.id]);

  // Handle keyboard
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // When the user switches to a different project context (or creates a
  // new one), start a fresh conversation. Lauren's feedback: carrying the
  // thread across projects was confusing - a new folder should be blank.
  // restoringThreadRef guards the case where handleRecentSessionClick is
  // explicitly restoring a session; that path already sets its own
  // activeProjectId and shouldn't be wiped.
  const lastProjectIdRef = useRef<string | null>(null);

  /** Blank chat thread filed under a project — used by "Search in project" and new-project create. */
  const startFreshProjectChat = useCallback((projectId: string) => {
    restoringThreadRef.current = true;
    setActiveProjectId(projectId);
    setMessages([]);
    setClientNotice(null);
    setInput('');
    currentSessionIdRef.current = Date.now().toString();
    lastProjectIdRef.current = projectId;
    setActiveView('chat');
    inputRef.current?.focus();
  }, [setActiveProjectId]);

  useEffect(() => {
    if (restoringThreadRef.current) {
      restoringThreadRef.current = false;
      lastProjectIdRef.current = activeProjectId || null;
      return;
    }
    const prev = lastProjectIdRef.current;
    const curr = activeProjectId || null;
    if (prev !== curr) {
      setMessages([]);
      setClientNotice(null);
      currentSessionIdRef.current = Date.now().toString();
      lastProjectIdRef.current = curr;
    }
  }, [activeProjectId]);

  // New search — starts a fresh conversation session OUTSIDE any
  // project. The effect that wipes messages on project-switch will
  // also fire here (pid -> null), but we set restoringThreadRef so
  // we don't double-clear.
  const handleNewSearch = () => {
    restoringThreadRef.current = true;
    setActiveProjectId(null);
    setMessages([]);
    setClientNotice(null);
    setActiveView('chat');
    currentSessionIdRef.current = Date.now().toString();
    inputRef.current?.focus();
  };

  // Bind hardware/browser Back to view navigation so leaving "How It Works"
  // (or any non-chat view) returns to chat instead of exiting the page.
  const popInProgressRef = useRef(false);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    // Baseline history entry for the chat view
    if (!window.history.state || !window.history.state.lenaView) {
      window.history.replaceState({ lenaView: 'chat' }, '');
    }
    const onPop = (e: PopStateEvent) => {
      const v = normalizeView((e.state && e.state.lenaView) || 'chat');
      popInProgressRef.current = true;
      setActiveView(v);
    };
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (popInProgressRef.current) {
      // This view change came from a Back nav — don't push another entry.
      popInProgressRef.current = false;
      return;
    }
    const current = window.history.state && window.history.state.lenaView;
    if (current === activeView) return;
    window.history.pushState({ lenaView: activeView }, '');
  }, [activeView]);

  // Auto-open research panel on first REAL result (not guardrail responses)
  const realResponseCount = messages.filter(
    m => m.response && m.response.pulse_report && !m.response.guardrail_triggered
  ).length;
  const panelOpenRef = useRef(panelOpen);
  panelOpenRef.current = panelOpen;
  useEffect(() => {
    if (realResponseCount === 1 && !panelOpenRef.current && isTabletUp) {
      setPanelOpen(true);
    }
  }, [realResponseCount, isTabletUp]);

  // Funnel overlay: only renders when the user tries a SECOND search as
  // anon. Never fires automatically on searchCount>=1 (that was dismissing
  // the 1st result page). handleSend sets signupModalOpen when it catches
  // the second-attempt intent.
  const funnelOverlay = authLoading || isAuthenticated ? null : (
    <SearchLimitModal
      isOpen={signupModalOpen}
      onRegister={() => router.push(`/register?session_id=${session.sessionId || ''}`)}
      onLogin={() => router.push('/login')}
      onClose={() => setSignupModalOpen(false)}
    />
  );

  // Render active view content
  const renderContent = () => {
    switch (activeView) {
      case 'community':
        return <ComingSoon {...COMMUNITY_CONFIG} authToken={authToken} />;
      case 'contribution':
        return <ComingSoon {...CONTRIBUTION_CONFIG} authToken={authToken} />;
      case 'how-it-works':
        return <HowItWorks />;
      case 'documents':
        return <MyDocuments />;
      case 'profile':
      case 'brain':
        return <ProfileSettings />;
      case 'sources':
        return <MyDocuments />;
      case 'projects':
        return renderProjectView();
      default:
        return renderChat();
    }
  };

  useEffect(() => {
    if (activeView !== 'projects' || !activeProjectId || !authToken) {
      setProjectSearches([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setProjectLoading(true);
      try {
        const data = await listProjectSearches(authToken, activeProjectId);
        if (!cancelled) setProjectSearches(data.searches || []);
      } catch { /* logged by caller */ }
      if (!cancelled) setProjectLoading(false);
    })();
    return () => { cancelled = true; };
  }, [activeView, activeProjectId, authToken, projectSearchesRevision]);

  const renderProjectView = () => {
    if (!isAuthenticated) {
      return (
        <div className="flex-1 overflow-y-auto p-6 text-center py-20">
          <p className="text-slate-400">Sign in to manage research projects.</p>
        </div>
      );
    }

    if (!activeProject) {
      return (
        <div className="flex-1 overflow-y-auto p-6 text-center py-20">
          <p className="text-slate-500 mb-2">No project selected.</p>
          <p className="text-sm text-slate-400">Click a project in the sidebar to view its searches, or create a new one with the + button.</p>
        </div>
      );
    }

    const localFiledCount = recentSessions.filter(s => s.projectId === activeProject.id).length;
    const displaySearchCount = Math.max(
      activeProject.search_count,
      localFiledCount,
      projectSearches.length,
    );

    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          <div className="mb-6 rounded-xl border border-lena-200/70 bg-lena-50/50 px-4 py-3 text-sm text-lena-900 leading-relaxed">
            <strong>Projects group your research by topic.</strong> Select a project in the sidebar to open it here.
            Click <strong>Search in project</strong> to start researching — every query and follow-up in that thread saves under this project automatically.
            Use <strong>Add to Project</strong> on past results to file them retroactively.
          </div>
          {/* Project header */}
          <div className="flex flex-col sm:flex-row sm:items-start gap-4 mb-8">
            <div className="flex items-start gap-4 flex-1 min-w-0">
              <div className="text-3xl flex-shrink-0">{activeProject.emoji || '📁'}</div>
              <div className="flex-1 min-w-0">
                <h2 className="text-xl font-bold text-slate-900">{activeProject.name}</h2>
                {activeProject.description && (
                  <p className="text-sm text-slate-500 mt-1">{activeProject.description}</p>
                )}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-2 text-xs text-slate-400">
                  <span>{displaySearchCount} search{displaySearchCount !== 1 ? 'es' : ''}</span>
                  <span>Created {new Date(activeProject.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 flex-shrink-0">
              <button
                type="button"
                onClick={async () => {
                  const name = window.prompt('Rename project', activeProject.name);
                  if (name?.trim()) await renameProject(activeProject.id, name.trim());
                }}
                className="px-3 py-2.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-xl hover:bg-slate-50 min-h-[44px]"
              >
                Rename
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (window.confirm(`Archive "${activeProject.name}"?`)) {
                    await archiveProject(activeProject.id);
                    setActiveView('chat');
                  }
                }}
                className="px-3 py-2.5 text-xs font-medium text-slate-600 border border-slate-200 rounded-xl hover:bg-slate-50 min-h-[44px]"
              >
                Archive
              </button>
              <button
                onClick={() => startFreshProjectChat(activeProject.id)}
                className="px-4 py-2.5 bg-lena-500 text-white text-sm font-medium rounded-xl hover:bg-lena-600 transition-colors min-h-[44px] flex-1 sm:flex-none"
              >
                Search in this project
              </button>
            </div>
          </div>

          {/* Search threads */}
          {projectLoading && (
            <div className="text-center py-8 text-slate-400 text-sm">Loading searches...</div>
          )}
          {!projectLoading && projectSearches.length === 0 && (
            <div className="text-center py-12 text-slate-500">
              <p className="font-medium text-slate-700 mb-1">No searches in this project yet</p>
              <p className="text-sm text-slate-400">Click &quot;Search in this project&quot; above, or file a past result with Add to Project.</p>
            </div>
          )}
          {!projectLoading && projectSearches.length > 0 && (
            <div className="space-y-2">
              {projectSearches.map((s) => (
                <button
                  type="button"
                  key={s.id}
                  onClick={() => handleProjectSearchOpen(s)}
                  className="w-full text-left p-4 bg-white border border-slate-200 rounded-xl hover:border-lena-300 hover:bg-lena-50/30 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-lena-50 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4 h-4 text-lena-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                      </svg>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-800">{s.query}</p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                        <span>{new Date(s.created_at).toLocaleString()}</span>
                        {s.persona && <span className="bg-slate-100 px-1.5 py-0.5 rounded">{s.persona}</span>}
                        {s.total_results != null && <span>{s.total_results} results</span>}
                        {s.pulse_status && (
                          <span className={`uppercase tracking-wide ${
                            s.pulse_status === 'validated' ? 'text-emerald-500' :
                            s.pulse_status === 'edge_case' ? 'text-amber-500' : 'text-slate-400'
                          }`}>{s.pulse_status}</span>
                        )}
                      </div>
                      <p className="text-[11px] text-lena-600 mt-1">Click to reopen thread</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  };

  // Chat view
  const renderChat = () => {
    const showWelcome = messages.length === 0 && !loading;

    // Session-search: filter visible messages. Both user query and assistant
    // content are checked. When a match is found we also include the paired
    // adjacent message so context is never lost.
    const needle = sessionSearch.trim().toLowerCase();
    const visibleMessages = needle
      ? messages.filter((msg, i, arr) => {
          const hay = (msg.content + ' ' + (msg.response?.query || '')).toLowerCase();
          const match = hay.includes(needle);
          if (match) return true;
          // Include the sibling so user Q + LENA A stay paired
          const sibling = arr[i - 1] || arr[i + 1];
          if (!sibling) return false;
          const sibHay = (sibling.content + ' ' + (sibling.response?.query || '')).toLowerCase();
          return sibHay.includes(needle);
        })
      : messages;

    return (
      <div className="flex flex-col h-full">
        {/* Session search bar (shown when toggled in header) */}
        {sessionSearchOpen && messages.length > 0 && (
          <div className="border-b border-slate-200/80 bg-white/95 px-4 py-2 flex items-center gap-2">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              autoFocus
              value={sessionSearch}
              onChange={e => setSessionSearch(e.target.value)}
              placeholder="Search within this session…"
              className="flex-1 bg-transparent input-touch text-slate-700 placeholder-slate-400 outline-none"
            />
            {sessionSearch && (
              <span className="text-[11px] text-slate-400">
                {visibleMessages.length}/{messages.length}
              </span>
            )}
            <button
              onClick={() => { setSessionSearchOpen(false); setSessionSearch(''); }}
              className="text-slate-400 hover:text-slate-600 p-2 -mr-1 touch-target flex items-center justify-center"
              aria-label="Close session search"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto">
          {showWelcome ? (
            <WelcomeView
              persona={session.persona}
              projectName={activeProject?.name}
              onPromptClick={(q) => handleSend(q)}
            />
          ) : (
            <div className="max-w-3xl mx-auto px-3 sm:px-4 py-4 sm:py-6 space-y-1">
              {visibleMessages.map((msg) => {
                const gt = msg.response?.guardrail_type;
                if (gt === 'disclaimer_required') {
                  return <DisclaimerCard key={msg.id} onAccept={handleAcceptDisclaimer} />;
                }
                if (gt === 'registered_limit' || gt === 'signup_required') {
                  return (
                    <UpgradeCTACard
                      key={msg.id}
                      message={msg.response?.guardrail_message}
                      onUpgrade={() => handleUpgrade('pro_monthly')}
                      onContact={() => {
                        window.location.href = 'mailto:hello@lena-app.com?subject=LENA%20Enterprise%20enquiry';
                      }}
                    />
                  );
                }
                return (
                  <ChatMessage
                    key={msg.id}
                    type={msg.type}
                    content={msg.content}
                    attachment={msg.attachment}
                    response={msg.response}
                    activeModes={resultModes}
                    onFollowUp={(q) => handleSend(q)}
                    projects={isAuthenticated ? projects.filter(p => !p.archived_at).map(p => ({
                      id: p.id, name: p.name, emoji: p.emoji,
                    })) : undefined}
                    onAddToProject={isAuthenticated ? async (searchId, projectId) => {
                      await assignSearch(searchId, projectId);
                      setSessionProject(currentSessionIdRef.current, projectId);
                      restoringThreadRef.current = true;
                      setActiveProjectId(projectId);
                      setProjectSearchesRevision(r => r + 1);
                      await refreshProjects();
                    } : undefined}
                    onCreateProject={isAuthenticated ? async (name) => {
                      const p = await createNewProject({ name });
                      return { id: p.id, name: p.name, emoji: p.emoji };
                    } : undefined}
                    authToken={authToken}
                  />
                );
              })}
              {loading && (
                <div className="py-4">
                  <ThinkingIndicator />
                </div>
              )}
              {clientNotice?.kind === 'upgrade' && !loading && (
                <UpgradeCTACard
                  message={clientNotice.message}
                  onUpgrade={() => handleUpgrade('pro_monthly')}
                  onContact={() => {
                    window.location.href = 'mailto:hello@lena-app.com?subject=LENA%20Enterprise%20enquiry';
                  }}
                />
              )}
              {clientNotice?.kind === 'support' && !loading && (
                <ContactSupportCard
                  onContact={() => {
                    window.location.href = 'mailto:hello@lena-app.com?subject=LENA%20Support%20request';
                  }}
                />
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom search input */}
        <div
          className="border-t border-slate-200/80 bg-white/95 backdrop-blur-xl px-4 pt-3 shadow-[0_-1px_0_rgba(15,23,42,0.04)] safe-bottom"
          style={{ paddingBottom: keyboardInset > 0 ? `${keyboardInset + 12}px` : undefined }}
        >
          <div className="max-w-3xl mx-auto">
            {/* Active project pill - shows what context the next search
                will file into. Click X to exit project context and run
                free searches again. */}
            {isAuthenticated && activeProject && (
              <div className="mb-2 flex flex-wrap items-center gap-x-2 gap-y-1 px-3 py-2 bg-lena-50/90 border border-lena-200/70 rounded-lg text-[11px] text-lena-800">
                <span className="font-semibold">Project active:</span>
                <span>{activeProject.emoji || '📁'} {activeProject.name}</span>
                <span className="text-lena-600/90">— new searches and follow-ups save here</span>
                <button
                  onClick={() => setActiveView('projects')}
                  className="ml-auto text-lena-700 underline underline-offset-2 hover:text-lena-900"
                >
                  View project
                </button>
                <button
                  onClick={() => setActiveProjectId(null)}
                  aria-label="Exit project"
                  title="Exit project — searches won't file here"
                  className="text-lena-500 hover:text-lena-800"
                >
                  ✕
                </button>
              </div>
            )}
            {pendingAttachment && (
              <div className="mb-2 flex items-center gap-3 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-700">
                {pendingAttachment.previewUrl ? (
                  <img
                    src={pendingAttachment.previewUrl}
                    alt=""
                    className="w-10 h-10 rounded object-cover border border-slate-200 flex-shrink-0"
                  />
                ) : (
                  <span className="text-base flex-shrink-0">📎</span>
                )}
                <div className="min-w-0 flex-1">
                  <p className="font-medium truncate">{pendingAttachment.name}</p>
                  <p className="text-slate-500 truncate">
                    Label / document attached — LENA will read it with your question
                    {pendingAttachment.text ? ` (${pendingAttachment.text.length.toLocaleString()} chars extracted)` : ''}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    if (pendingAttachment.previewUrl) {
                      URL.revokeObjectURL(pendingAttachment.previewUrl);
                    }
                    setPendingAttachment(null);
                  }}
                  className="text-slate-400 hover:text-slate-700 flex-shrink-0"
                  aria-label="Remove attachment"
                >
                  ✕
                </button>
              </div>
            )}
            <div className="flex items-end gap-2.5 bg-white border border-slate-200/80 rounded-2xl px-3.5 py-2.5 focus-within:border-lena-400/70 focus-within:ring-2 focus-within:ring-lena-100/80 transition-all shadow-soft">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,.pdf,.txt,.csv,.md"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  e.target.value = '';
                  if (!file) return;
                  await attachFile(file);
                }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={attaching || loading}
                title="Attach label, PDF, or image"
                className="w-10 h-10 flex items-center justify-center rounded-xl text-slate-500 hover:bg-slate-100 hover:text-lena-700 disabled:opacity-40 flex-shrink-0"
              >
                {attaching ? (
                  <span className="text-[10px] font-medium">…</span>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                  </svg>
                )}
              </button>
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onPaste={(e) => {
                  const items = e.clipboardData?.items;
                  if (!items) return;
                  for (let i = 0; i < items.length; i++) {
                    const item = items[i];
                    if (item.type.startsWith('image/')) {
                      e.preventDefault();
                      const file = item.getAsFile();
                      if (file) void attachFile(file);
                      return;
                    }
                  }
                }}
                onKeyDown={handleKeyDown}
                placeholder="Ask LENA a research question — paste a product link or attach a label"
                rows={1}
                className="flex-1 bg-transparent border-none outline-none resize-none input-touch text-slate-800 placeholder-slate-400 max-h-[130px] py-0.5"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="w-11 h-11 flex items-center justify-center rounded-xl bg-lena-500 text-white hover:bg-lena-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all flex-shrink-0 shadow-sm touch-target"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </div>
            <div className="flex items-center justify-between mt-1.5 px-1">
              <span className="text-[11px] text-slate-400 hidden sm:inline">Paste URLs · paste or attach label photos · Shift+Enter new line</span>
              <span className="text-[11px] text-slate-400">{product.tagline}</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="app-shell h-dvh flex bg-canvas-50 overflow-hidden">
      {funnelOverlay}

      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Left Sidebar — overlay on mobile, inline on desktop */}
      <div className={`
        fixed inset-y-0 left-0 z-50 w-[min(280px,92vw)] transition-transform duration-200 lg:relative lg:z-auto lg:translate-x-0 lg:w-[280px]
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:hidden'}
      `}>
        <Sidebar
          activeView={activeView}
          onViewChange={(v) => { setActiveView(v); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          onNewSearch={() => { handleNewSearch(); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          recentSessions={recentSessions}
          onSearchClick={(sid, q) => { handleRecentSessionClick(sid, q); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          onDeleteSession={deleteRecentSession}
          onRenameSession={renameRecentSession}
          onUpgrade={() => handleUpgrade('pro_monthly')}
          onShareReferral={handleShareReferral}
          onStartProjectSearch={(pid) => { startFreshProjectChat(pid); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          userName={session.name || user?.name}
          userEmail={user?.email}
          isAuthenticated={isAuthenticated}
          onSignIn={() => router.push('/login')}
          onRegister={() => router.push('/register')}
          onLogout={logout}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar — two rows on mobile so filters don't crush action buttons */}
        <header className="relative z-30 border-b border-slate-200/80 bg-white/95 backdrop-blur-xl flex-shrink-0 shadow-[0_1px_0_rgba(15,23,42,0.04)] safe-top">
          <div className="flex items-center justify-between px-3 sm:px-4 min-h-[52px] gap-2">
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="touch-target flex items-center justify-center rounded-xl hover:bg-slate-100 transition-colors lg:hidden"
                aria-label={sidebarOpen ? 'Close menu' : 'Open menu'}
              >
                <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <div className="lg:hidden min-w-0 flex-shrink">
                <BrandMark height={branding.logoSizes.mobileHeader} style={{ maxWidth: 108 }} />
              </div>
            </div>

            {/* Desktop: filters inline with actions */}
            <div className="hidden lg:flex items-center gap-2 flex-1 min-w-0 justify-end flex-wrap">
              <SegmentedControl
                options={RESULT_MODE_OPTIONS}
                value={resultModes}
                onChange={handleResultModesChange}
              />
              {activeView === 'chat' && messages.length > 0 && (
                <button
                  onClick={() => { setSessionSearchOpen(o => !o); if (sessionSearchOpen) setSessionSearch(''); }}
                  title="Search within this session"
                  className={`flex items-center gap-1.5 px-3 py-2 border rounded-full text-xs font-medium transition-all min-h-[44px] ${
                    sessionSearchOpen
                      ? 'border-lena-300/70 bg-lena-50/60 text-lena-700'
                      : 'border-slate-200/70 text-slate-600 hover:border-slate-300 hover:text-slate-900'
                  }`}
                >
                  <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  Search session
                </button>
              )}
              <PersonaSelector />
              <button
                onClick={() => setPanelOpen(!panelOpen)}
                className={`flex items-center gap-1.5 px-3 py-2 border rounded-full text-xs font-medium transition-all min-h-[44px] ${
                  panelOpen
                    ? 'border-lena-300/70 bg-lena-50/60 text-lena-700'
                    : 'border-slate-200/70 text-slate-600 hover:border-slate-300 hover:text-slate-900'
                }`}
              >
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Research Summary
              </button>
            </div>

            {/* Mobile: compact icon actions */}
            <div className="flex items-center gap-1 lg:hidden ml-auto">
              {activeView === 'chat' && messages.length > 0 && (
                <button
                  onClick={() => { setSessionSearchOpen(o => !o); if (sessionSearchOpen) setSessionSearch(''); }}
                  aria-label="Search session"
                  className={`touch-target flex items-center justify-center rounded-xl transition-all ${
                    sessionSearchOpen ? 'bg-lena-50 text-lena-700' : 'text-slate-500 hover:bg-slate-100'
                  }`}
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </button>
              )}
              <PersonaSelector compact />
              <button
                onClick={() => setPanelOpen(!panelOpen)}
                aria-label="Research summary"
                className={`touch-target flex items-center justify-center rounded-xl transition-all ${
                  panelOpen ? 'bg-lena-50 text-lena-700' : 'text-slate-500 hover:bg-slate-100'
                }`}
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </button>
            </div>
          </div>

          {/* Mobile: full-width filter row */}
          <div className="lg:hidden px-3 pb-2 overflow-x-auto">
            <SegmentedControl
              options={RESULT_MODE_OPTIONS}
              value={resultModes}
              onChange={handleResultModesChange}
              className="w-max min-w-full"
            />
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 flex min-h-0">
          <div className="flex-1 flex flex-col min-w-0">
            {renderContent()}
          </div>

          {/* Right Research Panel — inline on desktop, slide-over on mobile */}
          {panelOpen && activeView === 'chat' && (
            <>
              {/* Mobile backdrop */}
              <div className="fixed inset-0 bg-black/40 z-40 md:hidden" onClick={() => setPanelOpen(false)} />
              <div className="fixed inset-y-0 right-0 w-full max-w-[360px] z-50 border-l border-slate-200 bg-white safe-top safe-bottom md:relative md:inset-auto md:w-[320px] md:z-auto md:max-w-none">
                <ResearchPanel
                  messages={messages.map(m => ({ type: m.type, content: m.content, response: m.response, timestamp: m.timestamp }))}
                  persona={session.persona}
                  activeModes={resultModes}
                  onClose={() => setPanelOpen(false)}
                />
              </div>
            </>
          )}
        </div>
      </div>

    </div>
  );
}

// Generate natural language summary from search results
function generateSummary(result: SearchResponse): string {
  if (result.guardrail_triggered && result.guardrail_message) {
    return result.guardrail_message;
  }

  const { pulse_report, total_results, sources_queried, response_time_ms } = result;

  if (!pulse_report) {
    return total_results
      ? `Found ${total_results} results across ${(sources_queried || []).length} databases.`
      : 'No results found for this query.';
  }

  const sourceCount = (sources_queried || []).length;
  const confidence = resolvePulseConfidencePercent(pulse_report);
  const statusLabel = {
    validated: 'strong consensus',
    edge_case: 'mixed evidence',
    insufficient_validation: 'limited evidence',
    pending: 'pending validation',
  }[pulse_report.status] || 'analysis complete';

  let summary = `Based on analysis across ${sourceCount} medical databases, I found ${total_results} relevant result${total_results !== 1 ? 's' : ''} in ${(response_time_ms / 1000).toFixed(1)} seconds.`;

  if (pulse_report.consensus_summary) {
    summary += `\n\n${pulse_report.consensus_summary}`;
  }

  summary += `\n\nPULSE Cross-Reference Score: ${confidence}% (${statusLabel})`;

  if (pulse_report.validated_count > 0) {
    summary += ` - ${pulse_report.validated_count} source${pulse_report.validated_count !== 1 ? 's' : ''} validated`;
  }
  if (pulse_report.edge_case_count > 0) {
    summary += `, ${pulse_report.edge_case_count} edge case${pulse_report.edge_case_count !== 1 ? 's' : ''}`;
  }

  if (pulse_report.consensus_keywords.length > 0) {
    summary += `\n\nKey themes: ${pulse_report.consensus_keywords.slice(0, 5).join(', ')}`;
  }

  return summary;
}
