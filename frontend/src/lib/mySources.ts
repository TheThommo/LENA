/**
 * My Sources: local-first personal library of individual papers the user
 * has saved from search results. Separate from My Documents (which saves
 * whole research sessions). Persisted in localStorage for now; will move
 * to Supabase + sync across devices once the console ships.
 */

export interface SavedSource {
  id: string;                 // stable key: source + title (dedupe guard)
  source: string;             // "pubmed", "openalex", etc.
  title: string;
  url: string;
  doi: string | null;
  year: number;
  authors?: string[];
  keywords?: string[];
  query: string;              // the query that surfaced this paper
  saved_at: string;           // ISO timestamp
  is_favourite?: boolean;
  matched_modes?: string[];
}

const LS_KEY = 'lena_my_sources_v1';

function readAll(): SavedSource[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as SavedSource[]) : [];
  } catch {
    return [];
  }
}

function writeAll(list: SavedSource[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(list));
    // Notify any open views so they refresh without polling.
    window.dispatchEvent(new CustomEvent('lena:mysources-changed'));
  } catch {}
}

export function makeSourceId(source: string, title: string): string {
  return `${source}::${title}`.toLowerCase();
}

export function listSources(): SavedSource[] {
  return readAll();
}

export function isSaved(source: string, title: string): boolean {
  const id = makeSourceId(source, title);
  return readAll().some(s => s.id === id);
}

export function saveSource(s: Omit<SavedSource, 'id' | 'saved_at'>): SavedSource {
  const id = makeSourceId(s.source, s.title);
  const list = readAll();
  const existing = list.find(x => x.id === id);
  if (existing) return existing;
  const entry: SavedSource = { ...s, id, saved_at: new Date().toISOString() };
  writeAll([entry, ...list]);
  return entry;
}

export function removeSource(id: string) {
  writeAll(readAll().filter(s => s.id !== id));
}

export function toggleFavourite(id: string) {
  writeAll(readAll().map(s => (s.id === id ? { ...s, is_favourite: !s.is_favourite } : s)));
}
