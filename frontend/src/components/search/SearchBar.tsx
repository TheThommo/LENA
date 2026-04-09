'use client';

import { useState } from 'react';

export interface SearchBarOptions {
  query: string;
  sources: string[];
  includeAltMedicine: boolean;
}

interface SearchBarProps {
  onSearch: (options: SearchBarOptions) => void;
  isLoading: boolean;
  compact?: boolean;
}

const SOURCES = [
  { id: 'pubmed', label: 'PubMed', color: 'bg-blue-50 border-blue-200 text-blue-700' },
  { id: 'clinical_trials', label: 'ClinicalTrials.gov', color: 'bg-green-50 border-green-200 text-green-700' },
  { id: 'cochrane', label: 'Cochrane', color: 'bg-purple-50 border-purple-200 text-purple-700' },
  { id: 'who_iris', label: 'WHO', color: 'bg-red-50 border-red-200 text-red-700' },
  { id: 'cdc', label: 'CDC', color: 'bg-orange-50 border-orange-200 text-orange-700' },
];

export default function SearchBar({ onSearch, isLoading, compact = false }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [selectedSources, setSelectedSources] = useState<string[]>([
    'pubmed',
    'clinical_trials',
    'cochrane',
    'who_iris',
    'cdc',
  ]);
  const [includeAltMedicine, setIncludeAltMedicine] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSearch({
      query: query.trim(),
      sources: selectedSources,
      includeAltMedicine,
    });
  };

  const toggleSource = (sourceId: string) => {
    setSelectedSources((prev) =>
      prev.includes(sourceId)
        ? prev.filter((s) => s !== sourceId)
        : [...prev, sourceId]
    );
  };

  if (compact) {
    return (
      <form onSubmit={handleSubmit} className="w-full mb-8">
        <div className="flex gap-3 items-center">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Refine your search..."
            className="flex-1 px-4 py-2 text-base rounded-lg border border-slate-200
                       focus:border-lena-400 focus:outline-none focus:ring-1 focus:ring-lena-200
                       transition-all duration-200"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-4 py-2 bg-lena-600 text-white rounded-lg font-medium
                       hover:bg-lena-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors duration-200 whitespace-nowrap"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="space-y-6">
        {/* Main Search Input */}
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask LENA a clinical research question..."
            className="w-full px-6 py-4 text-lg rounded-2xl border-2 border-slate-200
                       focus:border-lena-400 focus:outline-none focus:ring-2 focus:ring-lena-100
                       shadow-sm transition-all duration-200"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 px-6 py-2
                       bg-lena-600 text-white rounded-xl font-medium
                       hover:bg-lena-700 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-colors duration-200"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Source Filters */}
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-600">Search sources</p>
          <div className="flex flex-wrap gap-2">
            {SOURCES.map((source) => (
              <button
                key={source.id}
                type="button"
                onClick={() => toggleSource(source.id)}
                className={`px-3 py-1.5 text-sm font-medium rounded-full border transition-all duration-200 ${
                  selectedSources.includes(source.id)
                    ? source.color + ' border-current'
                    : 'bg-slate-50 border-slate-200 text-slate-500 opacity-50'
                }`}
              >
                {source.label}
              </button>
            ))}
          </div>
        </div>

        {/* Alternative Medicine Toggle */}
        <div className="flex items-center justify-between pt-2">
          <label className="flex items-center cursor-pointer gap-3">
            <input
              type="checkbox"
              checked={includeAltMedicine}
              onChange={(e) => setIncludeAltMedicine(e.target.checked)}
              className="w-4 h-4 text-lena-600 rounded border-slate-300
                         focus:ring-lena-200 focus:ring-2 cursor-pointer"
            />
            <span className="text-sm font-medium text-slate-700">
              Include alternative and natural remedies
            </span>
          </label>
        </div>

        {/* Tagline */}
        <p className="text-sm text-slate-400 pt-2">
          Cross-referenced. Validated. Evidence-based.
        </p>
      </div>
    </form>
  );
}
