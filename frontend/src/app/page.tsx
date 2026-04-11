'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar, { SearchBarOptions } from '@/components/search/SearchBar';
import PulseReport from '@/components/search/PulseReport';
import ResultsList from '@/components/search/ResultsList';
import SearchStats from '@/components/search/SearchStats';
import ThinkingIndicator from '@/components/search/ThinkingIndicator';
import FunnelManager from '@/components/funnel/FunnelManager';
import { useSession } from '@/contexts/SessionContext';
import { useAuth } from '@/contexts/AuthContext';
import { useTenant } from '@/contexts/TenantContext';
import PersonaSelector from '@/components/PersonaSelector';
import { searchLiterature, SearchResponse } from '@/lib/api';

export default function Home() {
  const router = useRouter();
  const { session, captureName, acceptDisclaimer, captureEmail, incrementSearch } = useSession();
  const { isAuthenticated } = useAuth();
  const { tenant } = useTenant();
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);

  const handleSearch = async (options: SearchBarOptions) => {
    setLoading(true);
    setError(null);

    try {
      const result = await searchLiterature(options.query, {
        sources: options.sources,
        includeAltMedicine: options.includeAltMedicine,
        maxResults: 50,
        sessionId: session.sessionId || undefined,
        sessionToken: session.sessionToken || undefined,
        tenantId: tenant.id,
        persona: session.persona,
      });
      setResponse(result);
      setHasSearched(true);
      incrementSearch();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      setError(errorMessage);
      setResponse(null);
    } finally {
      setLoading(false);
    }
  };

  const showHeroLayout = !hasSearched && !loading;

  // Funnel overlay (renders modals based on session state)
  const funnelOverlay = (
    <FunnelManager
      sessionState={{
        name: session.name || undefined,
        email: session.email || undefined,
        disclaimerAccepted: session.disclaimerAccepted,
        searchCount: session.searchCount,
        isRegistered: isAuthenticated,
        brandName: tenant.brandName,
      }}
      onNameSubmit={(name) => captureName(name)}
      onDisclaimerAccept={(_timestamp: string) => acceptDisclaimer()}
      onEmailSubmit={(email) => captureEmail(email)}
      onEmailSkip={() => {}}
      onRegister={() => router.push(`/register?session_id=${session.sessionId || ''}`)}
      onLogin={() => router.push('/login')}
    />
  );

  if (showHeroLayout) {
    return (
      <main className="min-h-screen bg-warm-50 flex flex-col items-center justify-center px-4 py-12">
        {funnelOverlay}
        <div className="max-w-2xl w-full">
          {/* Logo / Title */}
          <div className="text-center mb-10">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-lena-500 to-lena-700 mb-4 shadow-lg">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h1 className="text-5xl font-bold text-lena-700 mb-3 tracking-tight">{tenant.brandName}</h1>
            <p className="text-lg text-slate-500 max-w-md mx-auto leading-relaxed">
              {tenant.tagline}
            </p>
          </div>

          {/* Persona Selector */}
          <div className="flex justify-center mb-4">
            <PersonaSelector />
          </div>

          {/* Search Bar - Full Featured */}
          <SearchBar onSearch={handleSearch} isLoading={loading} persona={session.persona} />

          {/* Trust Indicators */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-6 text-sm text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-400"></span>
              40M+ papers indexed
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-400"></span>
              5 databases cross-referenced
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-purple-400"></span>
              PULSE validated
            </span>
          </div>
        </div>

        {/* Footer disclaimer link */}
        <footer className="absolute bottom-4 text-xs text-slate-400">
          <a href="#disclaimer" className="hover:text-lena-600 transition-colors">Medical Disclaimer</a>
          <span className="mx-2">·</span>
          <a href="#privacy" className="hover:text-lena-600 transition-colors">Privacy Policy</a>
        </footer>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-warm-50">
      {funnelOverlay}
      {/* Header with Logo */}
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-slate-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-lena-500 to-lena-700 flex items-center justify-center flex-shrink-0">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-lena-700">{tenant.brandName}</h1>
          <div className="ml-auto flex items-center gap-3">
            <PersonaSelector />
            {session.name && (
              <span className="text-sm text-slate-400">
                {session.name}
              </span>
            )}
          </div>
        </div>
      </header>

      {/* Search and Results Container */}
      <div className="max-w-6xl mx-auto px-4 py-6">
        {/* Search Bar - Compact */}
        <div className="mb-6">
          <SearchBar onSearch={handleSearch} isLoading={loading} compact={true} persona={session.persona} />
        </div>

        {/* Loading State - Thinking Indicator */}
        {loading && (
          <div className="animate-fade-in">
            <ThinkingIndicator />
          </div>
        )}

        {/* Results Section */}
        {response && !loading && (
          <div className="space-y-6 animate-fade-in">
            {/* Search Stats */}
            <SearchStats response={response} />

            {/* PULSE Report */}
            <PulseReport report={response.pulse_report} />

            {/* Results List */}
            <ResultsList response={response} isLoading={loading} error={error} />
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-white rounded-xl border border-red-200 p-6 text-center">
            <div className="w-12 h-12 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-3">
              <svg className="w-6 h-6 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <p className="text-red-600 font-medium">{error}</p>
            <p className="text-sm text-slate-400 mt-1">Please try again or refine your search.</p>
          </div>
        )}
      </div>
    </main>
  );
}
