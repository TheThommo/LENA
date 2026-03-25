'use client';

import { useState } from 'react';

export default function Home() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    // TODO: Wire up to backend API
    console.log('Searching:', query);
    setLoading(false);
  };

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4">
      <div className="max-w-2xl w-full text-center">
        {/* Logo / Title */}
        <h1 className="text-5xl font-bold text-lena-700 mb-2">LENA</h1>
        <p className="text-lg text-slate-500 mb-8">
          Literature and Evidence Navigation Agent
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask LENA a clinical research question..."
            className="w-full px-6 py-4 text-lg rounded-2xl border-2 border-slate-200
                       focus:border-lena-400 focus:outline-none focus:ring-2 focus:ring-lena-100
                       shadow-sm transition-all duration-200"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 px-6 py-2
                       bg-lena-600 text-white rounded-xl font-medium
                       hover:bg-lena-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors duration-200"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>

        {/* Source Badges */}
        <div className="flex flex-wrap justify-center gap-2 mt-6">
          {['PubMed', 'ClinicalTrials.gov', 'Cochrane', 'WHO', 'CDC'].map((source) => (
            <span
              key={source}
              className="px-3 py-1 text-xs font-medium text-lena-700 bg-lena-50
                         rounded-full border border-lena-100"
            >
              {source}
            </span>
          ))}
        </div>

        {/* Tagline */}
        <p className="mt-8 text-sm text-slate-400">
          Cross-referenced. Validated. Evidence-based.
        </p>
      </div>
    </main>
  );
}
