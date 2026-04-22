'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';

interface SavedCitation {
  source: string;
  title: string;
  url: string;
  doi: string | null;
  year: number;
  relevanceScore?: number;
  keywords?: string[];
  query?: string;
  evidenceLevel?: string;
}

// Mirrors the shape written by ResearchPanel.toggleStar
interface StarredCitation {
  source: string;
  title: string;
  url: string;
  doi: string | null;
  year: number;
  evidenceLevel: string;
  query: string;
  keywords: string[];
  starredAt: string;
}

const LS_KEY_STARRED = 'lena_starred_citation_data';

interface SavedResearch {
  id: string;
  date: string;
  persona: string;
  queries: string[];
  citationCount: number;
  avgConfidence: number;
  totalResults: number;
  evidenceLevel?: string;
  is_favourite?: boolean;
  citations?: SavedCitation[];
}

const PERSONA_LABELS: Record<string, string> = {
  general: 'General',
  clinician: 'Clinician',
  medical_student: 'Medical Student',
  pharmacist: 'Pharmacist',
  researcher: 'Researcher',
  lecturer: 'Lecturer',
  physiotherapist: 'Physiotherapist',
  patient: 'Patient',
};

const SOURCE_LABEL: Record<string, string> = {
  pubmed: 'PubMed',
  clinical_trials: 'ClinicalTrials.gov',
  cochrane: 'Cochrane',
  who_iris: 'WHO IRIS',
  cdc: 'CDC',
  openalex: 'OpenAlex',
  ods_dsld: 'NIH DSLD',
  openfda: 'openFDA',
};

const LS_KEY = 'lena_saved_research';

export default function MyDocuments() {
  const [documents, setDocuments] = useState<SavedResearch[]>([]);
  const [starredCitations, setStarredCitations] = useState<Record<string, StarredCitation>>({});
  const [filter, setFilter] = useState<'all' | 'favourites' | 'high' | 'recent' | 'starred'>('all');
  const [search, setSearch] = useState('');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
      setDocuments(saved);
    } catch {}
    try {
      const stars = JSON.parse(localStorage.getItem(LS_KEY_STARRED) || '{}');
      setStarredCitations(stars);
    } catch {}
  }, []);

  const persist = useCallback((next: SavedResearch[]) => {
    try { localStorage.setItem(LS_KEY, JSON.stringify(next)); } catch {}
    setDocuments(next);
  }, []);

  const deleteDocument = useCallback((id: string) => {
    persist(documents.filter(d => d.id !== id));
  }, [documents, persist]);

  const toggleFavourite = useCallback((id: string) => {
    persist(documents.map(d => d.id === id ? { ...d, is_favourite: !d.is_favourite } : d));
  }, [documents, persist]);

  const filteredDocs = useMemo(() => {
    let list = documents;
    if (filter === 'favourites') list = list.filter(d => d.is_favourite);
    else if (filter === 'high') list = list.filter(d => d.avgConfidence >= 70);
    else if (filter === 'recent') {
      const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
      list = list.filter(d => new Date(d.date).getTime() > weekAgo);
    }
    const needles = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (needles.length > 0) {
      list = list.filter(d => {
        const hay = [
          ...(d.queries || []),
          ...(d.citations || []).flatMap(c => [c.title, c.source, ...(c.keywords || []), String(c.year || '')]),
        ].join(' ').toLowerCase();
        return needles.every(n => hay.includes(n));
      });
    }
    return [...list].sort((a, b) => {
      if (!!a.is_favourite !== !!b.is_favourite) return a.is_favourite ? -1 : 1;
      return new Date(b.date).getTime() - new Date(a.date).getTime();
    });
  }, [documents, filter, search]);

  const confidenceColor = (c: number) =>
    c >= 80 ? 'text-emerald-600' : c >= 60 ? 'text-amber-600' : 'text-red-500';

  const favCount = documents.filter(d => d.is_favourite).length;
  const starredCount = Object.keys(starredCitations).length;

  // For the 'starred' tab, build a sorted list from the starred data object
  const starredList = useMemo(
    () => Object.values(starredCitations).sort((a, b) =>
      new Date(b.starredAt).getTime() - new Date(a.starredAt).getTime()
    ),
    [starredCitations],
  );

  // Unstar handler: mirrors ResearchPanel toggleStar
  const unstar = useCallback((key: string) => {
    setStarredCitations(prev => {
      const next = { ...prev };
      delete next[key];
      try {
        localStorage.setItem(LS_KEY_STARRED, JSON.stringify(next));
        // Also remove from the keys array used by ResearchPanel
        const keys: string[] = JSON.parse(localStorage.getItem('lena_starred_citations') || '[]');
        localStorage.setItem('lena_starred_citations', JSON.stringify(keys.filter(k => k !== key)));
      } catch {}
      return next;
    });
  }, []);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">My Documents</h2>
            <p className="text-sm text-slate-500">Saved research sessions, evidence briefs and starred citations</p>
          </div>
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5 self-start sm:self-auto flex-wrap">
            {[
              { key: 'all' as const, label: 'All' },
              { key: 'starred' as const, label: `Starred${starredCount > 0 ? ` (${starredCount})` : ''}` },
              { key: 'favourites' as const, label: `Favourites${favCount > 0 ? ` (${favCount})` : ''}` },
              { key: 'high' as const, label: 'High Evidence' },
              { key: 'recent' as const, label: 'This Week' },
            ].map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                  filter === f.key
                    ? 'bg-white text-slate-900 shadow-sm'
                    : 'text-slate-500 hover:text-slate-700'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
        </div>

        {/* Search */}
        <div className="relative mb-6">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search within documents and citations..."
            className="w-full pl-10 pr-10 py-2 text-sm bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-lena-400 text-slate-700 placeholder-slate-400"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              aria-label="Clear"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {/* ── Starred Citations tab ───────────────────────────────── */}
        {filter === 'starred' && (
          starredList.length === 0 ? (
            <div className="text-center py-16">
              <div
                className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
                style={{ background: 'linear-gradient(135deg, rgba(251,191,36,0.15), rgba(245,158,11,0.08))' }}
              >
                <svg className="w-8 h-8 text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                </svg>
              </div>
              <p className="text-sm font-medium text-slate-700 mb-1">No starred citations yet</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
                Open the Research Panel, go to References, and tap the ★ next to any citation to save it here.
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold mb-3">
                {starredList.length} starred citation{starredList.length !== 1 ? 's' : ''}
              </p>
              {starredList.map((c) => {
                const key = `${c.source}::${c.title}`;
                return (
                  <div
                    key={key}
                    className="bg-white border border-amber-200 bg-amber-50/20 rounded-xl p-3.5 group"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        {c.url ? (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-slate-800 hover:text-lena-600 transition-colors line-clamp-2"
                          >
                            {c.title}
                          </a>
                        ) : (
                          <p className="text-sm font-medium text-slate-800 line-clamp-2">{c.title}</p>
                        )}
                        <div className="flex items-center gap-2 flex-wrap mt-1.5">
                          <span className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                            {SOURCE_LABEL[c.source] || c.source}
                          </span>
                          {c.year > 0 && (
                            <span className="text-[10px] text-slate-400 tabular-nums">{c.year}</span>
                          )}
                          {c.evidenceLevel && (
                            <span className="text-[10px] font-semibold bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                              Level {c.evidenceLevel}
                            </span>
                          )}
                          {c.query && (
                            <span className="text-[10px] text-slate-400 italic truncate max-w-[200px]">
                              from: {c.query}
                            </span>
                          )}
                        </div>
                        {c.doi && (
                          <p className="text-[10px] text-slate-400 font-mono mt-1 truncate">{c.doi}</p>
                        )}
                      </div>
                      <button
                        onClick={() => unstar(key)}
                        className="p-1.5 text-amber-400 hover:text-slate-400 transition-colors rounded-md hover:bg-slate-100 flex-shrink-0"
                        title="Remove star"
                        aria-label="Remove star"
                      >
                        <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor" stroke="currentColor" strokeWidth={1.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                        </svg>
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )
        )}

        {/* ── Documents tabs (all / favourites / high / recent) ─── */}
        {filter !== 'starred' && filteredDocs.length === 0 ? (
          <div className="text-center py-16">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'linear-gradient(135deg, rgba(27,107,147,0.1), rgba(20,83,114,0.06))' }}
            >
              <svg className="w-8 h-8 text-[#1B6B93]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-700 mb-1">
              {filter === 'all' ? 'No saved documents yet' : filter === 'favourites' ? 'No favourites yet - tap the heart on a document to pin it here' : 'No documents match this filter'}
            </p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
              When you find valuable research, use the &quot;Save to Documents&quot; button in the Research Panel to store it here for future reference.
            </p>
          </div>
        ) : filter !== 'starred' ? (
          <div className="space-y-3">
            {filteredDocs.map((doc) => {
              const isOpen = expandedId === doc.id;
              const citations = doc.citations || [];
              return (
                <div
                  key={doc.id}
                  className={`bg-white border rounded-xl transition-all group ${
                    doc.is_favourite ? 'border-rose-200 bg-rose-50/30' : 'border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="p-4 flex items-start justify-between gap-3">
                    <button
                      onClick={() => setExpandedId(isOpen ? null : doc.id)}
                      className="flex-1 min-w-0 text-left"
                    >
                      <p className="text-sm font-medium text-slate-800 truncate mb-1">
                        {doc.queries[0] || 'Untitled Research'}
                      </p>
                      {doc.queries.length > 1 && (
                        <p className="text-xs text-slate-400 mb-2">
                          +{doc.queries.length - 1} more quer{doc.queries.length - 1 > 1 ? 'ies' : 'y'}
                        </p>
                      )}

                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="text-xs text-slate-400">
                          {new Date(doc.date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' })}
                        </span>
                        <span className="text-xs text-slate-400">
                          {PERSONA_LABELS[doc.persona] || doc.persona}
                        </span>
                        <span className="text-xs text-slate-500 font-medium">
                          {doc.citationCount} citation{doc.citationCount !== 1 ? 's' : ''}
                        </span>
                        <span className={`text-xs font-semibold ${confidenceColor(doc.avgConfidence)}`}>
                          {doc.avgConfidence}% PULSE
                        </span>
                        {doc.evidenceLevel && (
                          <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                            Level {doc.evidenceLevel}
                          </span>
                        )}
                        {citations.length > 0 && (
                          <span className="text-[10px] text-lena-600 font-medium">
                            {isOpen ? 'Hide citations' : 'Show citations'}
                          </span>
                        )}
                      </div>
                    </button>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => toggleFavourite(doc.id)}
                        aria-label={doc.is_favourite ? 'Unfavourite' : 'Favourite'}
                        title={doc.is_favourite ? 'Unfavourite' : 'Favourite (pin to top)'}
                        className={`p-1.5 rounded-md transition-colors ${
                          doc.is_favourite
                            ? 'text-rose-500 hover:bg-rose-100'
                            : 'text-slate-300 hover:text-rose-500 hover:bg-rose-50 sm:opacity-0 sm:group-hover:opacity-100'
                        }`}
                      >
                        <svg className="w-4 h-4" fill={doc.is_favourite ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                        </svg>
                      </button>

                      <button
                        onClick={() => deleteDocument(doc.id)}
                        className="p-1.5 text-slate-300 hover:text-red-500 transition-colors rounded-md hover:bg-red-50 sm:opacity-0 sm:group-hover:opacity-100"
                        aria-label="Delete document"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>

                  {isOpen && citations.length > 0 && (
                    <div className="border-t border-slate-100 bg-slate-50/40 px-4 py-3 space-y-2">
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">
                        Citations ({citations.length})
                      </p>
                      {citations.map((c, i) => (
                        <div
                          key={`${c.source}-${c.title}-${i}`}
                          className="bg-white border border-slate-200/80 rounded-lg p-2.5"
                        >
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-100 text-slate-700 tracking-wide">
                              {SOURCE_LABEL[c.source] || c.source}
                            </span>
                            {c.year > 0 && (
                              <span className="text-[10px] text-slate-400 tabular-nums">{c.year}</span>
                            )}
                            {c.evidenceLevel && (
                              <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                Level {c.evidenceLevel}
                              </span>
                            )}
                          </div>
                          {c.url ? (
                            <a
                              href={c.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-[13px] font-medium text-slate-800 hover:text-lena-600 transition-colors"
                            >
                              {c.title}
                            </a>
                          ) : (
                            <p className="text-[13px] font-medium text-slate-800">{c.title}</p>
                          )}
                          {c.doi && (
                            <p className="text-[10px] text-slate-400 mt-1 font-mono">DOI: {c.doi}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {isOpen && citations.length === 0 && (
                    <div className="border-t border-slate-100 bg-amber-50/50 px-4 py-2">
                      <p className="text-[11px] text-amber-700">
                        This document was saved before citation links were stored. Re-run the query and save again to capture clickable sources.
                      </p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : null}

        <div className="mt-8 bg-slate-50 rounded-xl p-4 border border-slate-100">
          <p className="text-xs text-slate-500 leading-relaxed">
            Documents are stored locally on this device. In a future update, saved research will sync across devices when you sign in, and you will be able to upload external PDFs and papers to build your personal research library.
          </p>
        </div>
      </div>
    </div>
  );
}
