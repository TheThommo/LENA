'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  DOCUMENTS_CHANGED_EVENT,
  listDocuments,
  removeDocument,
  toggleDocumentFavourite,
  type SavedDocument,
} from '@/lib/savedDocuments';

const SOURCE_LABEL: Record<string, string> = {
  pubmed: 'PubMed',
  clinical_trials: 'ClinicalTrials.gov',
  cochrane: 'Cochrane',
  who_iris: 'WHO IRIS',
  cdc: 'CDC',
  openalex: 'OpenAlex',
  semantic_scholar: 'Semantic Scholar',
  europe_pmc: 'Europe PMC',
  dailymed: 'FDA DailyMed',
  ods_dsld: 'NIH DSLD',
  openfda: 'openFDA',
};

export default function MyDocuments() {
  const [documents, setDocuments] = useState<SavedDocument[]>([]);
  const [filter, setFilter] = useState<'all' | 'favourites'>('all');
  const [search, setSearch] = useState('');

  const refresh = useCallback(() => {
    setDocuments(listDocuments());
  }, []);

  useEffect(() => {
    refresh();
    if (typeof window === 'undefined') return;
    const handler = () => refresh();
    window.addEventListener(DOCUMENTS_CHANGED_EVENT, handler);
    return () => window.removeEventListener(DOCUMENTS_CHANGED_EVENT, handler);
  }, [refresh]);

  const handleToggleFav = useCallback((id: string) => {
    toggleDocumentFavourite(id);
    refresh();
  }, [refresh]);

  const handleRemove = useCallback((id: string) => {
    removeDocument(id);
    refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    let list = documents;
    if (filter === 'favourites') list = list.filter((doc) => doc.is_favourite);
    const needles = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (needles.length > 0) {
      list = list.filter((doc) => {
        const hay = `${doc.title} ${doc.source} ${(doc.keywords || []).join(' ')} ${doc.year} ${(doc.authors || []).join(' ')} ${doc.query}`.toLowerCase();
        return needles.every((n) => hay.includes(n));
      });
    }
    return [...list].sort((a, b) => {
      if (!!a.is_favourite !== !!b.is_favourite) return a.is_favourite ? -1 : 1;
      return new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime();
    });
  }, [documents, filter, search]);

  const favCount = documents.filter((doc) => doc.is_favourite).length;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">My Documents</h2>
            <p className="text-sm text-slate-500">
              Your evidence library — papers saved from PubMed, Cochrane, and other research databases.
            </p>
          </div>
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5 self-start sm:self-auto">
            {[
              { key: 'all' as const, label: 'All' },
              { key: 'favourites' as const, label: `Favourites${favCount ? ` (${favCount})` : ''}` },
            ].map((f) => (
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

        <div className="relative mb-6">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search saved papers..."
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

        {filtered.length === 0 ? (
          <div className="text-center py-16">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'linear-gradient(135deg, rgba(19,107,122,0.12), rgba(13,72,84,0.08))' }}
            >
              <svg className="w-8 h-8 text-lena-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-700 mb-1">
              {filter === 'favourites'
                ? 'No favourites yet — tap the heart on a saved paper to pin it here'
                : 'No saved papers yet'}
            </p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
              In Chat, expand any source from your search results and click <strong>Save to Documents</strong>.
              Use <strong>Projects</strong> in the sidebar to keep whole research threads organised by topic.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((doc) => (
              <div
                key={doc.id}
                className={`bg-white border rounded-xl p-4 transition-all group ${
                  doc.is_favourite ? 'border-rose-200 bg-rose-50/30' : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-100 text-slate-700 tracking-wide">
                        {SOURCE_LABEL[doc.source] || doc.source}
                      </span>
                      {doc.year > 0 && (
                        <span className="text-[10px] text-slate-400 tabular-nums">{doc.year}</span>
                      )}
                      <span className="text-[10px] text-slate-400">
                        Saved {new Date(doc.saved_at).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
                      </span>
                    </div>
                    <a
                      href={doc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-slate-800 hover:text-lena-600 transition-colors line-clamp-2"
                    >
                      {doc.title}
                    </a>
                    {doc.authors && doc.authors.length > 0 && (
                      <p className="text-xs text-slate-500 mt-1">
                        {doc.authors.slice(0, 3).join(', ')}
                        {doc.authors.length > 3 && ` +${doc.authors.length - 3}`}
                      </p>
                    )}
                    {doc.query && (
                      <p className="text-[11px] text-slate-400 mt-1.5 italic">
                        From: &quot;{doc.query}&quot;
                      </p>
                    )}
                    {doc.doi && (
                      <p className="text-[10px] text-slate-400 mt-1 font-mono">DOI: {doc.doi}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleToggleFav(doc.id)}
                      aria-label={doc.is_favourite ? 'Unfavourite' : 'Favourite'}
                      title={doc.is_favourite ? 'Unfavourite' : 'Favourite (pin to top)'}
                      className={`p-1.5 rounded-md transition-colors ${
                        doc.is_favourite
                          ? 'text-rose-500 hover:bg-rose-100'
                          : 'text-slate-300 hover:text-rose-500 hover:bg-rose-50 lg:opacity-0 lg:group-hover:opacity-100'
                      }`}
                    >
                      <svg className="w-4 h-4" fill={doc.is_favourite ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleRemove(doc.id)}
                      aria-label="Remove"
                      className="touch-target flex items-center justify-center text-slate-300 hover:text-red-500 transition-colors rounded-md hover:bg-red-50 lg:opacity-0 lg:group-hover:opacity-100"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-8 bg-slate-50 rounded-xl p-4 border border-slate-100 space-y-2">
          <p className="text-xs font-semibold text-slate-600">Where to save what</p>
          <ul className="text-xs text-slate-500 leading-relaxed space-y-1 list-disc pl-4">
            <li><strong className="text-slate-600">My Documents</strong> — individual papers from search results (this page).</li>
            <li><strong className="text-slate-600">Projects</strong> — whole research threads on one topic (sidebar).</li>
            <li><strong className="text-slate-600">Profile &amp; Settings</strong> — your background, preferences, and personal context (gear icon).</li>
          </ul>
          <p className="text-[11px] text-slate-400 pt-1">
            Saved papers sync to your account when signed in. PDF uploads are planned next.
          </p>
        </div>
      </div>
    </div>
  );
}
