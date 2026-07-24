/** Recent session metadata persisted in localStorage (per authenticated user). */
export interface RecentSessionRecord {
  id: string;
  firstQuery: string;
  /** Optional user label; falls back to firstQuery in the sidebar. */
  title?: string;
  queries: string[];
  projectId?: string | null;
  /**
   * Backend search id when known (search_logs / searches). Used to alias a
   * local Date.now thread with its remote row without collapsing distinct
   * searches that happen to share the same query text.
   */
  searchId?: string | null;
  createdAt: string;
  lastActivityAt: string;
}

type LegacySession = Partial<RecentSessionRecord> & {
  id: string;
  firstQuery: string;
  queries: string[];
  time?: string;
};

/** Human-readable relative time for sidebar session labels. */
export function formatSessionRelativeTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return 'Recently';

  const diffMs = Date.now() - date.getTime();
  if (diffMs < 60_000) return 'Just now';

  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);
  if (days === 1) return 'Yesterday';
  if (days < 7) return `${days}d ago`;

  const year = date.getFullYear();
  const nowYear = new Date().getFullYear();
  return date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    ...(year !== nowYear ? { year: 'numeric' as const } : {}),
  });
}

function timestampFromSessionId(id: string): string | null {
  if (!/^\d+$/.test(id)) return null;
  const ms = Number(id);
  if (!Number.isFinite(ms) || ms <= 0) return null;
  return new Date(ms).toISOString();
}

/** Upgrade legacy sessions that only stored `time: 'Just now'`. */
export function normalizeRecentSession(raw: LegacySession): RecentSessionRecord {
  const fromId = timestampFromSessionId(raw.id);
  const createdAt = raw.createdAt || fromId || new Date().toISOString();
  const lastActivityAt = raw.lastActivityAt || raw.createdAt || fromId || createdAt;

  return {
    id: raw.id,
    firstQuery: raw.firstQuery,
    title: raw.title?.trim() || undefined,
    queries: raw.queries ?? [],
    projectId: raw.projectId ?? null,
    searchId: raw.searchId ?? null,
    createdAt,
    lastActivityAt,
  };
}

export function sessionNeedsTimestampMigration(raw: LegacySession): boolean {
  return !raw.createdAt || !raw.lastActivityAt;
}

export function formatSessionSubtitle(session: RecentSessionRecord): string {
  const when = formatSessionRelativeTime(session.lastActivityAt);
  if (session.queries.length > 1) {
    return `${session.queries.length} queries · ${when}`;
  }
  return when;
}

/** Sidebar label: custom title when set, otherwise the first search query. */
export function getSessionDisplayTitle(session: RecentSessionRecord): string {
  const custom = session.title?.trim();
  return custom || session.firstQuery;
}

/** Dedupe key: one row per search identity — never collapse by query text. */
export function projectChatDedupeKey(
  s: Pick<RecentSessionRecord, 'id' | 'searchId'>,
): string {
  const searchId = (s.searchId || '').trim();
  if (searchId) return `search:${searchId}`;
  return `id:${s.id}`;
}

function preferProjectSession(a: RecentSessionRecord, b: RecentSessionRecord): RecentSessionRecord {
  // Prefer custom title, then stamped searchId, then local Date.now-style ids.
  const aTitle = Boolean(a.title?.trim());
  const bTitle = Boolean(b.title?.trim());
  if (aTitle !== bTitle) return aTitle ? a : b;
  const aSearch = Boolean(a.searchId?.trim());
  const bSearch = Boolean(b.searchId?.trim());
  if (aSearch !== bSearch) return aSearch ? a : b;
  const aLocal = /^\d+$/.test(a.id);
  const bLocal = /^\d+$/.test(b.id);
  if (aLocal !== bLocal) return aLocal ? a : b;
  if (a.queries.length !== b.queries.length) {
    return a.queries.length > b.queries.length ? a : b;
  }
  // Prefer newer activity when aliasing local + remote of the same search.
  const aTs = new Date(a.lastActivityAt).getTime();
  const bTs = new Date(b.lastActivityAt).getTime();
  if (aTs !== bTs) return aTs >= bTs ? a : b;
  return a;
}

function mergeAliasPair(a: RecentSessionRecord, b: RecentSessionRecord): RecentSessionRecord {
  const preferred = preferProjectSession(a, b);
  const other = preferred === a ? b : a;
  return {
    ...preferred,
    searchId: preferred.searchId || other.searchId || null,
    title: preferred.title?.trim() || other.title?.trim() || undefined,
    queries: preferred.queries.length >= other.queries.length ? preferred.queries : other.queries,
    projectId: preferred.projectId ?? other.projectId ?? null,
    createdAt:
      new Date(preferred.createdAt).getTime() <= new Date(other.createdAt).getTime()
        ? preferred.createdAt
        : other.createdAt,
    lastActivityAt:
      new Date(preferred.lastActivityAt).getTime() >= new Date(other.lastActivityAt).getTime()
        ? preferred.lastActivityAt
        : other.lastActivityAt,
  };
}

/**
 * Merge local + remote project chats without duplicates.
 * Alias only when ids or searchIds match — same query text stays distinct.
 */
export function mergeProjectSessions(
  local: RecentSessionRecord[],
  remote: RecentSessionRecord[],
): RecentSessionRecord[] {
  const byKey = new Map<string, RecentSessionRecord>();

  const upsert = (s: RecentSessionRecord) => {
    const key = projectChatDedupeKey(s);
    const prev = byKey.get(key);
    byKey.set(key, prev ? mergeAliasPair(prev, s) : s);

    // If this row also has a bare id key that differs, fold them together
    // (local Date.now id later stamped with searchId).
    if (s.searchId && s.searchId !== s.id) {
      const idKey = `id:${s.id}`;
      const idPrev = byKey.get(idKey);
      if (idPrev && idPrev !== byKey.get(key)) {
        const merged = mergeAliasPair(idPrev, byKey.get(key)!);
        byKey.delete(idKey);
        byKey.set(key, merged);
      }
    }
  };

  for (const s of remote) upsert(s);
  for (const s of local) upsert(s);

  // Second pass: local without searchId matching remote by id === remote.searchId
  // already handled via keys. Fold remaining id↔searchId pairs sharing identity.
  const rows = Array.from(byKey.values());
  const out = new Map<string, RecentSessionRecord>();
  for (const s of rows) {
    const key = projectChatDedupeKey(s);
    const prev = out.get(key);
    out.set(key, prev ? mergeAliasPair(prev, s) : s);
  }

  return Array.from(out.values()).sort(
    (a, b) => new Date(b.lastActivityAt).getTime() - new Date(a.lastActivityAt).getTime(),
  );
}

/**
 * Apply a sidebar rename without creating duplicate rows.
 * Matches by session id or searchId only — never by query text.
 */
export function applySessionRename(
  prev: RecentSessionRecord[],
  sessionId: string,
  title: string,
  seed?: RecentSessionRecord,
): RecentSessionRecord[] {
  const trimmed = title.trim();
  const seedSearch = seed?.searchId?.trim() || '';
  const matches = (s: RecentSessionRecord) =>
    s.id === sessionId ||
    Boolean(seedSearch && s.searchId && s.searchId === seedSearch) ||
    Boolean(seedSearch && s.id === seedSearch) ||
    Boolean(seed && s.searchId && s.searchId === sessionId);

  const existing = prev.filter(matches);
  const others = prev.filter(s => !matches(s));

  if (existing.length === 0) {
    if (!seed) return prev;
    const row: RecentSessionRecord = {
      ...seed,
      id: sessionId,
      searchId: seed.searchId || (seed.id !== sessionId ? seed.id : null),
      ...(trimmed && trimmed !== seed.firstQuery ? { title: trimmed } : {}),
    };
    if (!trimmed || trimmed === seed.firstQuery) {
      const { title: _drop, ...rest } = row;
      return [rest, ...others];
    }
    return [row, ...others];
  }

  const canonical = existing.reduce((a, b) => mergeAliasPair(a, b));
  const nextCanonical: RecentSessionRecord = (!trimmed || trimmed === canonical.firstQuery)
    ? (() => { const { title: _drop, ...rest } = canonical; return rest; })()
    : { ...canonical, title: trimmed };

  return [nextCanonical, ...others];
}
