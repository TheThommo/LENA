'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
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
import { useAuth } from '@/contexts/AuthContext';
import { useTenant } from '@/contexts/TenantContext';
import { searchLiterature, SearchResponse, ResultMode } from '@/lib/api';

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

  const toggleMode = (mode: ResultMode) => {
    setResultModes(prev => {
      const has = prev.includes(mode);
      let next: ResultMode[] = has ? prev.filter(m => m !== mode) : [...prev, mode];
      // If user deselects everything, fall back to 'all'
      if (next.length === 0) next = ['all'];
      return next;
    });
  };
  const [recentSessions, setRecentSessions] = useState<RecentSession[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const currentSessionIdRef = useRef<string>(Date.now().toString());

  // Load recent sessions from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem('lena_recent_sessions');
      if (stored) setRecentSessions(JSON.parse(stored));
    } catch {}
  }, []);

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

  // Save recent search — grouped by session
  const addRecentSearch = useCallback((query: string) => {
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
      localStorage.setItem('lena_recent_sessions', JSON.stringify(updated));
      return updated;
    });
  }, []);

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
      });

      // Prefer LLM-generated summary from backend, fall back to local generation
      const summary = result.llm_summary || generateSummary(result);

      const assistantMsg: Message = {
        id: `assistant-${Date.now()}`,
        type: 'assistant',
        content: summary,
        response: result,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMsg]);
      incrementSearch();
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

  // Auto-open research panel on first result
  const responseCount = messages.filter(m => m.response).length;
  const panelOpenRef = useRef(panelOpen);
  panelOpenRef.current = panelOpen;
  useEffect(() => {
    if (responseCount === 1 && !panelOpenRef.current) {
      setPanelOpen(true);
    }
  }, [responseCount]);

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
      case 'research':
        return renderMyResearch();
      case 'documents':
        return <MyDocuments />;
      case 'brain':
        return <MyBrain />;
      default:
        return renderChat();
    }
  };

  // My Research view
  const renderMyResearch = () => {
    const searchHistory = messages.filter(m => m.type === 'user');
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <h2 className="text-xl font-bold text-slate-900 mb-1">My Research</h2>
        <p className="text-sm text-slate-500 mb-6">Your recent search conversations</p>
        {searchHistory.length === 0 ? (
          <div className="text-center py-12 text-slate-400">
            <p>No searches yet. Start a conversation to see your history here.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {searchHistory.map((msg) => (
              <button
                key={msg.id}
                onClick={() => { setActiveView('chat'); }}
                className="w-full text-left p-4 bg-white border border-slate-200 rounded-xl hover:border-lena-300 transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-lena-50 flex items-center justify-center flex-shrink-0">
                    <svg className="w-4 h-4 text-lena-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate group-hover:text-lena-600 transition-colors">{msg.content}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{msg.timestamp.toLocaleDateString()}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
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
                  onFollowUp={(q) => handleSend(q)}
                  onShare={(title) => setShareModal({ isOpen: true, title })}
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
        <div className="border-t border-slate-200 bg-white p-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-3 bg-slate-50 border border-slate-200 rounded-2xl px-4 py-3 focus-within:border-lena-400 focus-within:ring-2 focus-within:ring-lena-100 transition-all">
              <textarea
                ref={inputRef}
                value={input}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask LENA a research question..."
                rows={1}
                className="flex-1 bg-transparent border-none outline-none resize-none text-sm text-slate-800 placeholder-slate-400 max-h-[130px]"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || loading}
                className="w-9 h-9 flex items-center justify-center rounded-xl bg-lena-500 text-white hover:bg-lena-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </div>
            <div className="flex items-center justify-between mt-2 px-1">
              <span className="text-xs text-slate-400 hidden sm:inline">Shift + Enter for new line</span>
              <span className="text-xs text-slate-400">LENA searches 250M+ papers across 6 databases</span>
            </div>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="h-screen flex bg-warm-50 overflow-hidden">
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
          onSearchClick={(q) => { setActiveView('chat'); handleSend(q); if (window.innerWidth < 1024) setSidebarOpen(false); }}
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
        <header className="min-h-[3.5rem] border-b border-slate-200 bg-white flex items-center justify-between px-3 sm:px-4 flex-shrink-0 gap-2">
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
            {/* Result-mode multi-select */}
            <div
              className="flex items-center gap-1 p-1 rounded-full border border-slate-200 bg-slate-50"
              role="group"
              aria-label="Result modes"
              title="Select one or more lenses. PULSE scores within the selected scope."
            >
              {([
                { id: 'all',     label: 'All',     short: 'All' },
                { id: 'herbal',  label: 'Herbal / Alt', short: 'Herbal' },
                { id: 'outlier', label: 'Outlier', short: 'Outlier' },
              ] as { id: ResultMode; label: string; short: string }[]).map((m) => {
                const active = resultModes.includes(m.id);
                return (
                  <button
                    key={m.id}
                    onClick={() => toggleMode(m.id)}
                    aria-pressed={active}
                    className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                      active
                        ? 'bg-[#1B6B93] text-white shadow-sm'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-white'
                    }`}
                  >
                    <span className="hidden sm:inline">{m.label}</span>
                    <span className="sm:hidden">{m.short}</span>
                  </button>
                );
              })}
            </div>

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
  const { pulse_report, total_results, sources_queried, response_time_ms, persona } = result;

  if (result.guardrail_triggered && result.guardrail_message) {
    return result.guardrail_message;
  }

  const sourceCount = sources_queried.length;
  const confidence = Math.round(pulse_report.confidence_ratio * 100);
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
