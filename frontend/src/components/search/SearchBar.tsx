'use client';

import { useState } from 'react';
import { PersonaId } from '@/contexts/SessionContext';

export interface SearchBarOptions {
  query: string;
  sources: string[];
  includeAltMedicine: boolean;
  persona?: PersonaId;
}

interface SearchBarProps {
  onSearch: (options: SearchBarOptions) => void;
  isLoading: boolean;
  compact?: boolean;
  persona?: PersonaId;
}

const SOURCES = [
  { id: 'pubmed', label: 'PubMed', color: 'bg-blue-50 border-blue-200 text-blue-700', activeColor: 'bg-blue-100' },
  { id: 'clinical_trials', label: 'ClinicalTrials.gov', color: 'bg-purple-50 border-purple-200 text-purple-700', activeColor: 'bg-purple-100' },
  { id: 'cochrane', label: 'Cochrane', color: 'bg-orange-50 border-orange-200 text-orange-700', activeColor: 'bg-orange-100' },
  { id: 'who_iris', label: 'WHO IRIS', color: 'bg-cyan-50 border-cyan-200 text-cyan-700', activeColor: 'bg-cyan-100' },
  { id: 'cdc', label: 'CDC', color: 'bg-emerald-50 border-emerald-200 text-emerald-700', activeColor: 'bg-emerald-100' },
];

const SUGGESTED_PROMPTS: Record<string, string[]> = {
  medical_student: [
    'Pathophysiology of Type 2 diabetes mellitus',
    'Compare ACE inhibitors vs ARBs for hypertension',
    'Evidence-based approach to chest pain differential diagnosis',
  ],
  clinician: [
    'Latest guidelines for atrial fibrillation management',
    'Compare SSRIs vs SNRIs efficacy for major depression',
    'Evidence for early mobilisation in ICU patients',
  ],
  pharmacist: [
    'Drug interactions with direct oral anticoagulants',
    'Pharmacokinetics of monoclonal antibody therapies',
    'Evidence for biosimilar interchangeability',
  ],
  researcher: [
    'Systematic review methodology for clinical interventions',
    'Meta-analysis of CRISPR gene therapy outcomes',
    'Recent advances in mRNA vaccine technology',
  ],
  lecturer: [
    'Teaching evidence-based medicine to undergraduates',
    'Systematic review of simulation-based medical education',
    'Assessment methods in clinical competency evaluation',
  ],
  physiotherapist: [
    'Evidence for manual therapy in chronic low back pain',
    'Exercise prescription for osteoarthritis of the knee',
    'Effectiveness of dry needling for myofascial pain',
  ],
  patient: [
    'What does the evidence say about intermittent fasting?',
    'Natural remedies for anxiety - what works?',
    'How effective are probiotics for gut health?',
  ],
  general: [
    'What does the evidence say about intermittent fasting?',
    'Compare treatment options for migraine prevention',
    'Recent research on gut microbiome and mental health',
  ],
};

export default function SearchBar({ onSearch, isLoading, compact = false, persona = 'general' }: SearchBarProps) {
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
      persona,
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
      <form onSubmit={handleSubmit} className="w-full">
        <div className="flex gap-3 items-center">
          <div className="relative flex-1">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Refine your search..."
              className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200
                         focus:border-lena-400 focus:outline-none focus:ring-2 focus:ring-lena-100
                         transition-all duration-200 bg-white"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="px-5 py-2.5 bg-gradient-to-r from-lena-500 to-lena-700 text-white rounded-xl font-medium text-sm
                       hover:from-lena-600 hover:to-lena-800 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 whitespace-nowrap shadow-sm"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="space-y-5">
        {/* Main Search Input */}
        <div className="relative">
          <svg className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a clinical research question..."
            className="w-full pl-14 pr-28 py-4 text-lg rounded-2xl border-2 border-slate-200 bg-white
                       focus:border-lena-400 focus:outline-none focus:ring-2 focus:ring-lena-100
                       shadow-sm hover:shadow-md transition-all duration-200 placeholder:text-slate-400"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-3 top-1/2 -translate-y-1/2 px-6 py-2.5
                       bg-gradient-to-r from-lena-500 to-lena-700 text-white rounded-xl font-semibold
                       hover:from-lena-600 hover:to-lena-800 disabled:opacity-50 disabled:cursor-not-allowed
                       transition-all duration-200 shadow-sm"
          >
            {isLoading ? 'Searching...' : 'Search'}
          </button>
        </div>

        {/* Suggested Prompts */}
        {!query && (
          <div className="flex flex-wrap gap-2">
            {(SUGGESTED_PROMPTS[persona] || SUGGESTED_PROMPTS.general).map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => setQuery(prompt)}
                className="px-3 py-1.5 text-xs text-slate-500 bg-white border border-slate-200 rounded-full
                           hover:border-lena-300 hover:text-lena-600 hover:bg-lena-50 transition-all duration-200"
              >
                {prompt}
              </button>
            ))}
          </div>
        )}

        {/* Source Filters */}
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Search sources</p>
          <div className="flex flex-wrap gap-2">
            {SOURCES.map((source) => (
              <button
                key={source.id}
                type="button"
                onClick={() => toggleSource(source.id)}
                className={`px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 ${
                  selectedSources.includes(source.id)
                    ? source.color + ' border-current shadow-sm'
                    : 'bg-slate-50 border-slate-200 text-slate-400 opacity-60 hover:opacity-80'
                }`}
              >
                {source.label}
              </button>
            ))}
          </div>
        </div>

        {/* Alternative Medicine Toggle */}
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setIncludeAltMedicine(!includeAltMedicine)}
            className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-full border transition-all duration-200 ${
              includeAltMedicine
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-white border-slate-200 text-slate-400'
            }`}
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
            </svg>
            Natural &amp; Herbal Remedies
            <div className={`w-7 h-4 rounded-full relative transition-all duration-200 ${includeAltMedicine ? 'bg-emerald-500' : 'bg-slate-300'}`}>
              <div className={`w-3 h-3 rounded-full bg-white absolute top-0.5 transition-all duration-200 shadow-sm ${includeAltMedicine ? 'left-3.5' : 'left-0.5'}`} />
            </div>
          </button>
        </div>

        {/* Tagline */}
        <p className="text-xs text-slate-400 flex items-center gap-1.5">
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          Cross-referenced. Validated. Evidence-based.
        </p>
      </div>
    </form>
  );
}
