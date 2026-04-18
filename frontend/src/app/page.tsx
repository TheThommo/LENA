'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { product } from '@/config/branding';
import WelcomeView from '@/components/chat/WelcomeView';
import ChatMessage from '@/components/chat/ChatMessage';
import ResearchPanel from '@/components/chat/ResearchPanel';
import ShareModal from '@/components/chat/ShareModal';
import ThinkingIndicator from '@/components/search/ThinkingIndicator';
import FunnelManager from '@/components/funnel/FunnelManager';
import PersonaSelector from '@/components/PersonaSelector';
import ComingSoon, { COMMUNITY_CONFIG, CONTRIBUTION_CONFIG } from '@/components/views/ComingSoon';
import HowItWorks from '@/components/views/HowItWorks';
import MyDocuments from '@/components/views/MyDocuments';
import MyBrain from '@/components/views/MyBrain';
import { useSession } from '@/contexts/SessionContext';
import { useProjects } from '@/contexts/ProjectsContext';
import { useAuth } from '@/contexts/AuthContext';
import { useTenant } from '@/contexts/TenantContext';
import { searchLiterature, SearchResponse, ResultMode, listProjectSearches, type ProjectSearch } from '@/lib/api';

interface Message {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  response?: SearchResponse;
  timestamp: Date;
}

interface RecentSession {
  id: string;
  firstQuery: string;
  queries: string[];
  time: string;
}

export default function Home() {
  const router = useRouter();
  const { session, captureAll, incrementSearch } = useSession();
  const { activeProject, activeProjectId, setActiveProjectId, refresh: refreshProjects, projects, assignSearch } = useProjects();
  const { isAuthenticated, isLoading: authLoading, user, token: authToken, logout } = useAuth();
  const { tenant } = useTenant();

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [activeView, setActiveView] = useState('chat');
  const [panelOpen, setPanelOpen] = useState(false);
  const [shareModal, setShareModal] = useState<{ isOpen: boolean; title?: string }>({ isOpen: false });
  // Result-mode multi-select: 'all' (default), 'herbal', 'outlier'. Multiple may be active.
  const [resultModes, setResultModes] = useState<ResultMode[]>(['all']);
  const [modesOpen, setModesOpen] = useState(false);
  const modesMenuRef = useRef<HTMLDivElement>(null);

  const toggleMode = (mode: ResultMode) => {
    setResultModes(prev => {
      const has = prev.includes(mode);
      let next: ResultMode[] = has ? prev.filter(m => m !== mode) : [...prev, mode];
      // If user deselects everything, fall back to 'all'
      if (next.length === 0) next = ['all'];
      // 'all' is exclusive of the others — selecting 'all' clears filters;
      // selecting a filter removes 'all'.
      if (!has && mode === 'all') next = ['all'];
      else if (!has && mode !== 'all') next = next.filter(m => m !== 'all');
      return next;
    });
  };

  // Close mode dropdown on outside click
  useEffect(() => {
    if (!modesOpen) return;
    const handler = (e: MouseEvent) => {
      if (modesMenuRef.current && !modesMenuRef.current.contains(e.target as Node)) {
        setModesOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [modesOpen]);
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
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
        setError(null);
      }
      prevUserIdRef.current = null;
      return;
    }
    // User changed (login / switch account) — load their sessions
    if (prevUserIdRef.current !== uid) {
      prevUserIdRef.current = uid;
      try {
        const stored = localStorage.getItem(sessionsKey);
        setRecentSessions(stored ? JSON.parse(stored) : []);
      } catch {
        setRecentSessions([]);
      }
    }
  }, [isAuthenticated, user?.id, sessionsKey]);

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
    setRecentSessions(prev => {
      const existing = prev.find(s => s.id === sid);
      let updated: RecentSession[];
      if (existing) {
        // Append query to existing session, move to top
        updated = [
          { ...existing, queries: [...existing.queries, query], time: 'Just now' },
          ...prev.filter(s => s.id !== sid),
        ];
      } else {
        // New session
        updated = [
          { id: sid, firstQuery: query, queries: [query], time: 'Just now' },
          ...prev,
        ];
      }
      updated = updated.slice(0, 8);
      if (sessionsKey) {
        localStorage.setItem(sessionsKey, JSON.stringify(updated));
      }
      return updated;
    });
  }, [isAuthenticated, sessionsKey]);

  // Handle search
  const handleSend = async (text?: string) => {
    const query = (text || input).trim();
    if (!query || loading) return;

    setInput('');
    setError(null);
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
    }

    // Add user message
    const userMsg: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: query,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    addRecentSearch(query);

    try {
      const result = await searchLiterature(query, {
        sources: ['pubmed', 'clinical_trials', 'cochrane', 'who_iris', 'cdc', 'openalex'],
        modes: resultModes,
        maxResults: 50,
        sessionId: session.sessionId || undefined,
        sessionToken: authToken || session.sessionToken || undefined,
        tenantId: tenant.id,
        persona: session.persona,
        // File this search under the active project (auth-only; backend
        // silently drops project_id for anon callers).
        projectId: isAuthenticated && activeProjectId ? activeProjectId : undefined,
      });

      // Guardrail responses (off-topic, profanity, self-harm) have no
      // pulse_report or llm_summary — show the guardrail message directly.
      const summary = result.guardrail_triggered && result.guardrail_message
        ? result.guardrail_message
        : (result.llm_summary || generateSummary(result));

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: summary,
        response: result,
        timestamp: new Date(),
      };
      setMessages(prev => {
        const next = [...prev, assistantMsg];
        // Persist so clicking this session in 'Recent Sessions' restores from
        // local state without re-calling the backend (which would re-bill).
        if (isAuthenticated) {
          persistSessionThread(currentSessionIdRef.current, next);
        }
        return next;
      });
      // Don't count guardrail blocks as a search (they don't cost anything
      // and shouldn't burn the user's free-tier allowance).
      if (!result.guardrail_triggered) {
        incrementSearch();
      }
      // Update the project's search_count badge in the sidebar
      if (isAuthenticated && activeProjectId) {
        refreshProjects();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      const errorMsg: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: `I wasn't able to complete your search. ${errorMessage}. Please try again.`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  // Restore a prior session's thread from localStorage without re-hitting the
  // backend. Falls back to running a fresh search only if the thread is
  // missing (e.g. storage cleared, cross-device).
  const handleRecentSessionClick = useCallback((sessionId: string, fallbackQuery: string) => {
    const thread = loadSessionThread(sessionId);
    if (thread && thread.length > 0) {
      currentSessionIdRef.current = sessionId;
      setMessages(thread);
      setError(null);
      setActiveView('chat');
      return;
    }
    // No persisted thread — run the query as a last resort
    setActiveView('chat');
    handleSend(fallbackQuery);
  }, [loadSessionThread]);

  // Handle keyboard
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // New search — starts a fresh conversation session
  const handleNewSearch = () => {
    setMessages([]);
    setError(null);
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
      const v = (e.state && e.state.lenaView) || 'chat';
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
    if (realResponseCount === 1 && !panelOpenRef.current) {
      setPanelOpen(true);
    }
  }, [realResponseCount]);

  // Funnel overlay — don't render while auth is still loading (prevents flash for signed-in users)
  const funnelOverlay = authLoading ? null : (
    <FunnelManager
      sessionState={{
        name: session.name || undefined,
        email: session.email || undefined,
        disclaimerAccepted: session.disclaimerAccepted,
        searchCount: session.searchCount,
        isRegistered: isAuthenticated,
        brandName: tenant.brandName,
      }}
      onCapture={(data) => captureAll(data)}
      onRegister={() => router.push(`/register?session_id=${session.sessionId || ''}`)}
      onLogin={() => router.push('/login')}
    />
  );

  // Render active view content
  const renderContent = () => {
    switch (activeView) {
      case 'community':
        return <ComingSoon {...COMMUNITY_CONFIG} />;
      case 'contribution':
        return <ComingSoon {...CONTRIBUTION_CONFIG} />;
      case 'how-it-works':
        return <HowItWorks />;
      case 'documents':
        return <MyDocuments />;
      case 'brain':
        return <MyBrain />;
      case 'projects':
        return renderProjectView();
      default:
        return renderChat();
    }
  };

  // Project detail view — shows all searches filed under the active project
  const [projectSearches, setProjectSearches] = useState<ProjectSearch[]>([]);
  const [projectLoading, setProjectLoading] = useState(false);

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
  }, [activeView, activeProjectId, authToken]);

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

    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto">
          {/* Project header */}
          <div className="flex items-start gap-4 mb-8">
            <div className="text-3xl">{activeProject.emoji || '📁'}</div>
            <div className="flex-1">
              <h2 className="text-xl font-bold text-slate-900">{activeProject.name}</h2>
              {activeProject.description && (
                <p className="text-sm text-slate-500 mt-1">{activeProject.description}</p>
              )}
              <div className="flex items-center gap-4 mt-2 text-xs text-slate-400">
                <span>{activeProject.search_count} search{activeProject.search_count !== 1 ? 'es' : ''}</span>
                <span>Created {new Date(activeProject.created_at).toLocaleDateString()}</span>
              </div>
            </div>
            <button
              onClick={() => { setActiveProjectId(activeProject.id); setActiveView('chat'); }}
              className="px-3 py-1.5 bg-lena-500 text-white text-xs font-medium rounded-lg hover:bg-lena-600 transition-colors"
            >
              Search in project
            </button>
          </div>

          {/* Search threads */}
          {projectLoading && (
            <div className="text-center py-8 text-slate-400 text-sm">Loading searches...</div>
          )}
          {!projectLoading && projectSearches.length === 0 && (
            <div className="text-center py-12 text-slate-400">
              <p>No searches filed under this project yet.</p>
              <p className="text-xs mt-1">Run a search while this project is active to see it here.</p>
            </div>
          )}
          {!projectLoading && projectSearches.length > 0 && (
            <div className="space-y-2">
              {projectSearches.map((s) => (
                <div
                  key={s.id}
                  className="w-full text-left p-4 bg-white border border-slate-200 rounded-xl hover:border-lena-300 transition-colors"
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
                    </div>
                  </div>
                </div>
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

    return (
      <div className="flex flex-col h-full">
        {/* Messages area */}
        <div className="flex-1 overflow-y-auto">
          {showWelcome ? (
            <WelcomeView persona={session.persona} onPromptClick={(q) => handleSend(q)} />
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-1">
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  type={msg.type}
                  content={msg.content}
                  response={msg.response}
                  activeModes={resultModes}
                  onFollowUp={(q) => handleSend(q)}
                  onShare={(title) => setShareModal({ isOpen: true, title })}
                  projects={isAuthenticated ? projects.filter(p => !p.archived_at).map(p => ({
                    id: p.id, name: p.name, emoji: p.emoji,
                  })) : undefined}
                  onAddToProject={isAuthenticated ? (searchId, projectId) => {
                    assignSearch(searchId, projectId);
                  } : undefined}
                />
              ))}
              {loading && (
                <div className="py-4">
                  <ThinkingIndicator />
                </div>
              )}
              {error && !loading && (
                <div className="bg-red-50 border border-red-200 rounded-xl p-4">
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Bottom search input */}
        <div className="border-t border-slate-200/70 bg-white/80 backdrop-blur-xl px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-2.5 bg-white border border-slate-200/80 rounded-xl px-3.5 py-2.5 focus-within:border-lena-400/60 focus-within:ring-2 focus-within:ring-lena-100/60 transition-all shadow-sm">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask LENA a research question"
                rows={1}
                className="flex-1 bg-transparent border-none outline-none resize-none text-[14px] text-slate-800 placeholder-slate-400 max-h-[130px] py-0.5"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="w-8 h-8 flex items-center justify-center rounded-lg bg-lena-500 text-white hover:bg-lena-600 disabled:opacity-30 disabled:cursor-not-allowed transition-all flex-shrink-0 shadow-sm"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </div>
            <div className="flex items-center justify-between mt-1.5 px-1">
              <span className="text-[11px] text-slate-400 hidden sm:inline">Shift + Enter for new line</span>
              <span className="text-[11px] text-slate-400">{product.tagline}</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-[100dvh] flex bg-warm-50 overflow-hidden">
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
        fixed inset-y-0 left-0 z-50 w-[280px] transition-transform duration-200 lg:relative lg:z-auto lg:translate-x-0
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:hidden'}
      `}>
        <Sidebar
          activeView={activeView}
          onViewChange={(v) => { setActiveView(v); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          onNewSearch={() => { handleNewSearch(); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          recentSessions={recentSessions}
          onSearchClick={(sid, q) => { handleRecentSessionClick(sid, q); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          userName={session.name || user?.name}
          userEmail={user?.email}
          isAuthenticated={isAuthenticated}
          onSignIn={() => router.push('/login')}
          onLogout={logout}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="min-h-[52px] border-b border-slate-200/70 bg-white/80 backdrop-blur-xl flex items-center justify-between px-3 sm:px-4 flex-shrink-0 gap-2">
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="w-9 h-9 flex items-center justify-center rounded-lg hover:bg-slate-100 transition-colors lg:hidden"
            >
              <svg className="w-5 h-5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-2 flex-wrap justify-end">
            {/* Active-project chip — shows which project new searches file under */}
            {isAuthenticated && activeProject && (
              <button
                onClick={() => setActiveView('projects')}
                className="flex items-center gap-1.5 px-2.5 py-1.5 border border-lena-300 bg-lena-50 rounded-full text-xs font-medium text-lena-700 hover:bg-lena-100 transition-all max-w-[200px] truncate"
                title={`Searches file under "${activeProject.name}". Click to open project.`}
              >
                <span>{activeProject.emoji || '📁'}</span>
                <span className="truncate">{activeProject.name}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setActiveProjectId(null); }}
                  className="ml-0.5 text-lena-400 hover:text-lena-700"
                  title="Stop filing searches under this project"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </button>
            )}

            {/* Result-mode checkbox dropdown (scalable for future filters) */}
            {(() => {
              const MODE_OPTIONS: { id: ResultMode; label: string; desc: string }[] = [
                { id: 'all',     label: 'All results',   desc: 'Unfiltered corpus' },
                { id: 'herbal',  label: 'Herbal / Alt',  desc: 'Supplements, botanicals, integrative' },
                { id: 'outlier', label: 'Outlier',       desc: 'Heterodox peer-reviewed authors' },
              ];
              const activeNonAll = resultModes.filter(m => m !== 'all');
              const buttonLabel =
                resultModes.includes('all') && activeNonAll.length === 0
                  ? 'All results'
                  : activeNonAll.length === 1
                    ? MODE_OPTIONS.find(o => o.id === activeNonAll[0])?.label ?? 'Filters'
                    : `${activeNonAll.length} filters`;
              return (
                <div className="relative" ref={modesMenuRef}>
                  <button
                    type="button"
                    onClick={() => setModesOpen(o => !o)}
                    aria-haspopup="listbox"
                    aria-expanded={modesOpen}
                    title="PULSE scores within the selected scope."
                    className="flex items-center gap-1.5 px-2.5 py-1.5 border border-slate-200 rounded-full text-xs font-medium text-slate-600 hover:text-slate-900 hover:border-lena-300 bg-white transition-all"
                  >
                    <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                    </svg>
                    <span className="hidden sm:inline">{buttonLabel}</span>
                    <span className="sm:hidden">Filters</span>
                    <svg className={`w-3 h-3 transition-transform ${modesOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {modesOpen && (
                    <div
                      role="listbox"
                      aria-label="Result modes"
                      className="absolute right-0 mt-1.5 w-64 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden"
                    >
                      <div className="px-3 py-2 text-[11px] uppercase tracking-wide text-slate-400 border-b border-slate-100 bg-slate-50">
                        Result lenses
                      </div>
                      {MODE_OPTIONS.map(opt => {
                        const checked = resultModes.includes(opt.id);
                        return (
                          <label
                            key={opt.id}
                            className="flex items-start gap-2.5 px-3 py-2 hover:bg-slate-50 cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={checked}
                              onChange={() => toggleMode(opt.id)}
                              className="mt-0.5 w-4 h-4 text-lena-600 border-slate-300 rounded focus:ring-lena-500 focus:ring-1"
                            />
                            <span className="flex-1 min-w-0">
                              <span className="block text-xs font-medium text-slate-800">{opt.label}</span>
                              <span className="block text-[11px] text-slate-500">{opt.desc}</span>
                            </span>
                          </label>
                        );
                      })}
                      <div className="px-3 py-2 border-t border-slate-100 bg-slate-50 text-[11px] text-slate-500">
                        PULSE scores within your selected scope.
                      </div>
                    </div>
                  )}
                </div>
              );
            })()}

            {/* Persona Selector */}
            <PersonaSelector />

            {/* Research Panel Toggle */}
            <button
              onClick={() => setPanelOpen(!panelOpen)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 border rounded-full text-xs font-medium transition-all ${
                panelOpen
                  ? 'border-lena-400 bg-lena-50 text-lena-700'
                  : 'border-slate-200 text-slate-500 hover:border-lena-300'
              }`}
            >
              <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <span className="hidden sm:inline">Research Summary</span>
            </button>
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
              <div className="fixed inset-y-0 right-0 w-[85vw] max-w-[360px] z-50 border-l border-slate-200 bg-white md:relative md:inset-auto md:w-[320px] md:z-auto md:max-w-none">
                <ResearchPanel
                  messages={messages.map(m => ({ type: m.type, content: m.content, response: m.response, timestamp: m.timestamp }))}
                  persona={session.persona}
                  onClose={() => setPanelOpen(false)}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Share Modal */}
      <ShareModal
        isOpen={shareModal.isOpen}
        onClose={() => setShareModal({ isOpen: false })}
        resultTitle={shareModal.title}
        onShare={(data) => {
          console.log('Share:', data);
          setShareModal({ isOpen: false });
        }}
      />
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
  const confidence = Math.round((pulse_report.confidence_ratio || 0) * 100);
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
