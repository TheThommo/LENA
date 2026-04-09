'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SearchBar, { SearchBarOptions } from '@/components/search/SearchBar';
import PulseReport from '@/components/search/PulseReport';
import ResultsList from '@/components/search/ResultsList';
import SearchStats from '@/components/search/SearchStats';
import FunnelManager from '@/components/funnel/FunnelManager';
import { useSession } from '@/contexts/SessionContext';
import { useAuth } from '@/contexts/AuthContext';
import { useTenant } from '@/contexts/TenantContext';
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
        tenantId: tenant.id,
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

  const showHeroLayout = !hasSearched;

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
      <main className="min-h-screen flex flex-col items-center justify-center px-4 py-12">
        {funnelOverlay}
        <div className="max-w-2xl w-full">
          {/* Logo / Title */}
          <div className="text-center mb-12">
            <h1 className="text-5xl font-bold text-lena-700 mb-2">{tenant.brandName}</h1>
            <p className="text-lg text-slate-500">
              {tenant.tagline}
            </p>
          </div>

          {/* Search Bar - Full Featured */}
          <SearchBar onSearch={handleSearch} isLoading={loading} />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-white">
      {funnelOverlay}
      {/* Header with Logo */}
      <header className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-lena-700">{tenant.brandName}</h1>
        </div>
      </header>

      {/* Search and Results Container */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* Search Bar - Compact */}
        <div className="mb-8">
          <SearchBar onSearch={handleSearch} isLoading={loading} compact={true} />
        </div>

        {/* Results Section */}
        {response && !loading && (
          <div className="space-y-8">
            {/* Search Stats */}
            <SearchStats response={response} />

            {/* PULSE Report */}
            <PulseReport report={response.pulse_report} />

            {/* Results List */}
            <ResultsList response={response} isLoading={loading} error={error} />
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="space-y-8">
            <ResultsList response={null} isLoading={true} error={null} />
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <ResultsList response={null} isLoading={false} error={error} />
        )}
      </div>
    </main>
  );
}
