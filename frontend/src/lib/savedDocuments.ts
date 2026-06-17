/**
 * My Documents — personal evidence library of saved papers from research.
 * Per-user localStorage with optional cloud sync when authenticated.
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

const LEGACY_LS_KEY = 'lena_saved_documents_v1';
const LEGACY_SOURCES_KEY = 'lena_my_sources_v1';
const LEGACY_STARRED_KEY = 'lena_starred_citation_data';
const MIGRATION_FLAG = 'lena_documents_migrated_v2';

export const DOCUMENTS_CHANGED_EVENT = 'lena:documents-changed';

let currentUserId: string | null = null;
let currentToken: string | null = null;
let cloudSyncFns: {
  listRemote: (token: string) => Promise<SavedDocument[]>;
  upsertRemote: (token: string, doc: SavedDocument) => Promise<void>;
  deleteRemote: (token: string, docKey: string) => Promise<void>;
} | null = null;

function storageKey(userId?: string | null): string {
  const uid = userId ?? currentUserId;
  return uid ? `lena_saved_documents_${uid}` : LEGACY_LS_KEY;
}

export function configureDocumentsSync(
  userId: string | null,
  token: string | null,
  sync?: typeof cloudSyncFns,
) {
  currentUserId = userId;
  currentToken = token;
  cloudSyncFns = sync ?? null;
}

function readAll(): SavedDocument[] {
  if (typeof window === 'undefined') return [];
  migrateLegacyData();
  try {
    const raw = localStorage.getItem(storageKey());
    return raw ? (JSON.parse(raw) as SavedDocument[]) : [];
  } catch {
    return [];
  }
}

function writeAll(list: SavedDocument[]) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(storageKey(), JSON.stringify(list));
    window.dispatchEvent(new CustomEvent(DOCUMENTS_CHANGED_EVENT));
  } catch {}
}

async function syncDocToCloud(doc: SavedDocument) {
  if (!currentToken || !cloudSyncFns) return;
  try {
    await cloudSyncFns.upsertRemote(currentToken, doc);
  } catch {}
}

async function deleteDocFromCloud(docKey: string) {
  if (!currentToken || !cloudSyncFns) return;
  try {
    await cloudSyncFns.deleteRemote(currentToken, docKey);
  } catch {}
}

export async function hydrateDocumentsFromCloud(): Promise<void> {
  if (!currentToken || !cloudSyncFns || typeof window === 'undefined') return;
  try {
    const remote = await cloudSyncFns.listRemote(currentToken);
    const local = readAll();
    const merged = new Map<string, SavedDocument>();
    for (const doc of local) merged.set(doc.id, doc);
    for (const doc of remote) {
      const existing = merged.get(doc.id);
      if (!existing || Date.parse(doc.saved_at) >= Date.parse(existing.saved_at)) {
        merged.set(doc.id, doc);
      }
    }
    writeAll(Array.from(merged.values()).sort(
      (a, b) => Date.parse(b.saved_at) - Date.parse(a.saved_at),
    ));
  } catch {}
}

export function makeDocumentId(source: string, title: string): string {
  return `${source}::${title}`.toLowerCase();
}

function migrateLegacyData() {
  if (typeof window === 'undefined') return;
  const flagKey = currentUserId ? `${MIGRATION_FLAG}_${currentUserId}` : MIGRATION_FLAG;
  if (localStorage.getItem(flagKey)) return;
  localStorage.setItem(flagKey, '1');

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
    for (const [, item] of Object.entries(starred)) {
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
    const existing = readAll();
    for (const doc of existing) merged.set(doc.id, doc);
    writeAll(Array.from(merged.values()));
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
    void syncDocToCloud(updated);
    return updated;
  }

  const created: SavedDocument = {
    ...entry,
    id,
    saved_at: new Date().toISOString(),
  };
  writeAll([created, ...list]);
  void syncDocToCloud(created);
  return created;
}

export function removeDocument(id: string) {
  writeAll(readAll().filter((doc) => doc.id !== id));
  void deleteDocFromCloud(id);
}

export function toggleDocumentFavourite(id: string) {
  const list = readAll();
  const updated = list.map((doc) =>
    doc.id === id ? { ...doc, is_favourite: !doc.is_favourite } : doc,
  );
  writeAll(updated);
  const doc = updated.find(d => d.id === id);
  if (doc) void syncDocToCloud(doc);
}

export function setDocumentFavourite(source: string, title: string, favourite: boolean) {
  const id = makeDocumentId(source, title);
  const list = readAll();
  const existing = list.find((doc) => doc.id === id);
  if (existing) {
    const updated = list.map((doc) => (doc.id === id ? { ...doc, is_favourite: favourite } : doc));
    writeAll(updated);
    const doc = updated.find(d => d.id === id);
    if (doc) void syncDocToCloud(doc);
    return;
  }
  if (!favourite) return;
}
