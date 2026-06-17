/**
 * My Documents — personal evidence library of saved papers from research.
 * Migrated from legacy My Sources + starred citations on first load.
 */

export interface SavedDocument {
  id: string;
  source: string;
  title: string;
  url: string;
  doi: string | null;
  year: number;
  authors?: string[];
  keywords?: string[];
  query: string;
  saved_at: string;
  is_favourite?: boolean;
  matched_modes?: string[];
  evidence_level?: string;
}

const LS_KEY = 'lena_saved_documents_v1';
const LEGACY_SOURCES_KEY = 'lena_my_sources_v1';
const LEGACY_STARRED_KEY = 'lena_starred_citation_data';
const MIGRATION_FLAG = 'lena_documents_migrated_v2';

export const DOCUMENTS_CHANGED_EVENT = 'lena:documents-changed';

function readAll(): SavedDocument[] {
  if (typeof window === 'undefined') return [];
  migrateLegacyData();
  try {
    const raw = localStorage.getItem(LS_KEY);
    return raw ? (JSON.parse(raw) as SavedDocument[]) : [];
  } catch {
    return [];
  }
}

function writeAll(list: SavedDocument[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(list));
    window.dispatchEvent(new CustomEvent(DOCUMENTS_CHANGED_EVENT));
  } catch {}
}

export function makeDocumentId(source: string, title: string): string {
  return `${source}::${title}`.toLowerCase();
}

function migrateLegacyData() {
  if (typeof window === 'undefined') return;
  if (localStorage.getItem(MIGRATION_FLAG)) return;
  localStorage.setItem(MIGRATION_FLAG, '1');

  const merged = new Map<string, SavedDocument>();

  try {
    const legacySources = JSON.parse(localStorage.getItem(LEGACY_SOURCES_KEY) || '[]') as SavedDocument[];
    for (const item of legacySources) {
      merged.set(item.id || makeDocumentId(item.source, item.title), {
        ...item,
        id: item.id || makeDocumentId(item.source, item.title),
      });
    }
  } catch {}

  try {
    const starred = JSON.parse(localStorage.getItem(LEGACY_STARRED_KEY) || '{}') as Record<
      string,
      {
        source: string;
        title: string;
        url: string;
        doi: string | null;
        year: number;
        evidenceLevel?: string;
        query?: string;
        keywords?: string[];
        starredAt?: string;
      }
    >;
    for (const [key, item] of Object.entries(starred)) {
      const id = makeDocumentId(item.source, item.title);
      const existing = merged.get(id);
      merged.set(id, {
        id,
        source: item.source,
        title: item.title,
        url: item.url,
        doi: item.doi,
        year: item.year || 0,
        keywords: item.keywords,
        query: item.query || '',
        saved_at: item.starredAt || existing?.saved_at || new Date().toISOString(),
        is_favourite: true,
        evidence_level: item.evidenceLevel,
        authors: existing?.authors,
        matched_modes: existing?.matched_modes,
      });
    }
  } catch {}

  if (merged.size > 0) {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(Array.from(merged.values())));
      window.dispatchEvent(new CustomEvent(DOCUMENTS_CHANGED_EVENT));
    } catch {}
  }
}

export function listDocuments(): SavedDocument[] {
  return readAll();
}

export function isDocumentSaved(source: string, title: string): boolean {
  const id = makeDocumentId(source, title);
  return readAll().some((doc) => doc.id === id);
}

export function saveDocument(entry: Omit<SavedDocument, 'id' | 'saved_at'>): SavedDocument {
  const id = makeDocumentId(entry.source, entry.title);
  const list = readAll();
  const existing = list.find((doc) => doc.id === id);
  if (existing) {
    const updated: SavedDocument = {
      ...existing,
      ...entry,
      id,
      saved_at: existing.saved_at,
      is_favourite: entry.is_favourite ?? existing.is_favourite,
    };
    writeAll(list.map((doc) => (doc.id === id ? updated : doc)));
    return updated;
  }

  const created: SavedDocument = {
    ...entry,
    id,
    saved_at: new Date().toISOString(),
  };
  writeAll([created, ...list]);
  return created;
}

export function removeDocument(id: string) {
  writeAll(readAll().filter((doc) => doc.id !== id));
}

export function toggleDocumentFavourite(id: string) {
  writeAll(
    readAll().map((doc) =>
      doc.id === id ? { ...doc, is_favourite: !doc.is_favourite } : doc,
    ),
  );
}

export function setDocumentFavourite(source: string, title: string, favourite: boolean) {
  const id = makeDocumentId(source, title);
  const list = readAll();
  const existing = list.find((doc) => doc.id === id);
  if (existing) {
    writeAll(list.map((doc) => (doc.id === id ? { ...doc, is_favourite: favourite } : doc)));
    return;
  }
  if (!favourite) return;
}
