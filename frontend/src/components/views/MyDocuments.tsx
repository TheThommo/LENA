'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';

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

const LS_KEY = 'lena_saved_research';

export default function MyDocuments() {
  const [documents, setDocuments] = useState<SavedResearch[]>([]);
  const [filter, setFilter] = useState<'all' | 'favourites' | 'high' | 'recent'>('all');

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(LS_KEY) || '[]');
      setDocuments(saved);
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
    // Favourites pinned to top regardless of filter, then newest first.
    return [...list].sort((a, b) => {
      if (!!a.is_favourite !== !!b.is_favourite) return a.is_favourite ? -1 : 1;
      return new Date(b.date).getTime() - new Date(a.date).getTime();
    });
  }, [documents, filter]);

  const confidenceColor = (c: number) =>
    c >= 80 ? 'text-emerald-600' : c >= 60 ? 'text-amber-600' : 'text-red-500';

  const favCount = documents.filter(d => d.is_favourite).length;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">My Documents</h2>
            <p className="text-sm text-slate-500">Saved research sessions and evidence briefs</p>
          </div>
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5 self-start sm:self-auto">
            {[
              { key: 'all' as const, label: 'All' },
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

        {filteredDocs.length === 0 ? (
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
        ) : (
          <div className="space-y-3">
            {filteredDocs.map((doc) => (
              <div
                key={doc.id}
                className={`bg-white border rounded-xl p-4 hover:shadow-sm transition-all group ${
                  doc.is_favourite ? 'border-rose-200 bg-rose-50/30' : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    {/* Primary query as title */}
                    <p className="text-sm font-medium text-slate-800 truncate mb-1">
                      {doc.queries[0] || 'Untitled Research'}
                    </p>
                    {doc.queries.length > 1 && (
                      <p className="text-xs text-slate-400 mb-2">
                        +{doc.queries.length - 1} more quer{doc.queries.length - 1 > 1 ? 'ies' : 'y'}
                      </p>
                    )}

                    {/* Meta row */}
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
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    {/* Favourite (heart) */}
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

                    {/* Delete button */}
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
              </div>
            ))}
          </div>
        )}

        {/* Info footer */}
        <div className="mt-8 bg-slate-50 rounded-xl p-4 border border-slate-100">
          <p className="text-xs text-slate-500 leading-relaxed">
            Documents are stored locally on this device. In a future update, saved research will sync across devices when you sign in, and you will be able to upload external PDFs and papers to build your personal research library.
          </p>
        </div>
      </div>
    </div>
  );
}
