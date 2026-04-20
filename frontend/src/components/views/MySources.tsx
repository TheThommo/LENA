'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  listSources,
  removeSource,
  toggleFavourite,
  type SavedSource,
} from '@/lib/mySources';

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

export default function MySources() {
  const [sources, setSources] = useState<SavedSource[]>([]);
  const [filter, setFilter] = useState<'all' | 'favourites'>('all');
  const [search, setSearch] = useState('');

  const refresh = useCallback(() => {
    setSources(listSources());
  }, []);

  useEffect(() => {
    refresh();
    if (typeof window === 'undefined') return;
    const handler = () => refresh();
    window.addEventListener('lena:mysources-changed', handler);
    return () => window.removeEventListener('lena:mysources-changed', handler);
  }, [refresh]);

  const handleToggleFav = useCallback((id: string) => {
    toggleFavourite(id);
    refresh();
  }, [refresh]);

  const handleRemove = useCallback((id: string) => {
    removeSource(id);
    refresh();
  }, [refresh]);

  const filtered = useMemo(() => {
    let list = sources;
    if (filter === 'favourites') list = list.filter(s => s.is_favourite);
    const needles = search.trim().toLowerCase().split(/\s+/).filter(Boolean);
    if (needles.length > 0) {
      list = list.filter(s => {
        const hay = `${s.title} ${s.source} ${(s.keywords || []).join(' ')} ${s.year} ${(s.authors || []).join(' ')} ${s.query}`.toLowerCase();
        return needles.every(n => hay.includes(n));
      });
    }
    // Favourites pinned, then newest saved first.
    return [...list].sort((a, b) => {
      if (!!a.is_favourite !== !!b.is_favourite) return a.is_favourite ? -1 : 1;
      return new Date(b.saved_at).getTime() - new Date(a.saved_at).getTime();
    });
  }, [sources, filter, search]);

  const favCount = sources.filter(s => s.is_favourite).length;

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-900 mb-1">My Sources</h2>
            <p className="text-sm text-slate-500">Individual papers you&apos;ve saved from search results</p>
          </div>
          <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-0.5 self-start sm:self-auto">
            {[
              { key: 'all' as const, label: 'All' },
              { key: 'favourites' as const, label: `Favourites${favCount ? ` (${favCount})` : ''}` },
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
            placeholder="Search saved sources..."
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
              style={{ background: 'linear-gradient(135deg, rgba(27,107,147,0.1), rgba(20,83,114,0.06))' }}
            >
              <svg className="w-8 h-8 text-[#1B6B93]" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 8h14M5 12h14M5 16h9" />
              </svg>
            </div>
            <p className="text-sm font-medium text-slate-700 mb-1">
              {filter === 'favourites'
                ? 'No favourites yet - tap the heart on a saved source to pin it here'
                : 'No saved sources yet'}
            </p>
            <p className="text-xs text-slate-400 max-w-sm mx-auto leading-relaxed">
              In any search result, expand a source card and click <strong>Save</strong> to add the paper here for future reference.
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((s) => (
              <div
                key={s.id}
                className={`bg-white border rounded-xl p-4 transition-all group ${
                  s.is_favourite ? 'border-rose-200 bg-rose-50/30' : 'border-slate-200 hover:border-slate-300'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-slate-100 text-slate-700 tracking-wide">
                        {SOURCE_LABEL[s.source] || s.source}
                      </span>
                      {s.year > 0 && (
                        <span className="text-[10px] text-slate-400 tabular-nums">{s.year}</span>
                      )}
                      <span className="text-[10px] text-slate-400">
                        Saved {new Date(s.saved_at).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
                      </span>
                    </div>
                    <a
                      href={s.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium text-slate-800 hover:text-lena-600 transition-colors line-clamp-2"
                    >
                      {s.title}
                    </a>
                    {s.authors && s.authors.length > 0 && (
                      <p className="text-xs text-slate-500 mt-1">
                        {s.authors.slice(0, 3).join(', ')}
                        {s.authors.length > 3 && ` +${s.authors.length - 3}`}
                      </p>
                    )}
                    {s.query && (
                      <p className="text-[11px] text-slate-400 mt-1.5 italic">
                        From: &quot;{s.query}&quot;
                      </p>
                    )}
                    {s.doi && (
                      <p className="text-[10px] text-slate-400 mt-1 font-mono">DOI: {s.doi}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 flex-shrink-0">
                    <button
                      onClick={() => handleToggleFav(s.id)}
                      aria-label={s.is_favourite ? 'Unfavourite' : 'Favourite'}
                      title={s.is_favourite ? 'Unfavourite' : 'Favourite (pin to top)'}
                      className={`p-1.5 rounded-md transition-colors ${
                        s.is_favourite
                          ? 'text-rose-500 hover:bg-rose-100'
                          : 'text-slate-300 hover:text-rose-500 hover:bg-rose-50 sm:opacity-0 sm:group-hover:opacity-100'
                      }`}
                    >
                      <svg className="w-4 h-4" fill={s.is_favourite ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleRemove(s.id)}
                      aria-label="Remove"
                      className="p-1.5 text-slate-300 hover:text-red-500 transition-colors rounded-md hover:bg-red-50 sm:opacity-0 sm:group-hover:opacity-100"
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
      </div>
    </div>
  );
}
