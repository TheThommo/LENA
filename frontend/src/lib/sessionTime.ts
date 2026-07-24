/** Recent session metadata persisted in localStorage (per authenticated user). */
export interface RecentSessionRecord {
  id: string;
  firstQuery: string;
  /** Optional user label; falls back to firstQuery in the sidebar. */
  title?: string;
  queries: string[];
  projectId?: string | null;
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

/** Dedupe key for chats filed under a project (same query = same chat). */
export function projectChatDedupeKey(
  s: Pick<RecentSessionRecord, 'projectId' | 'firstQuery'>,
): string {
  return `${s.projectId || ''}::${(s.firstQuery || '').trim().toLowerCase()}`;
}

function preferProjectSession(a: RecentSessionRecord, b: RecentSessionRecord): RecentSessionRecord {
  // Prefer custom title, then local Date.now-style ids, then richer query lists.
  const aTitle = Boolean(a.title?.trim());
  const bTitle = Boolean(b.title?.trim());
  if (aTitle !== bTitle) return aTitle ? a : b;
  const aLocal = /^\d+$/.test(a.id);
  const bLocal = /^\d+$/.test(b.id);
  if (aLocal !== bLocal) return aLocal ? a : b;
  if (a.queries.length !== b.queries.length) {
    return a.queries.length > b.queries.length ? a : b;
  }
  return a;
}

/**
 * Merge local + remote project chats without duplicates.
 * Same projectId + firstQuery collapses to one row (fixes sidebar duplication).
 */
export function mergeProjectSessions(
  local: RecentSessionRecord[],
  remote: RecentSessionRecord[],
): RecentSessionRecord[] {
  const byKey = new Map<string, RecentSessionRecord>();
  // Remote first, then local wins on conflicts via preferProjectSession.
  for (const s of remote) {
    const key = projectChatDedupeKey(s);
    const prev = byKey.get(key);
    byKey.set(key, prev ? preferProjectSession(prev, s) : s);
  }
  for (const s of local) {
    const key = projectChatDedupeKey(s);
    const prev = byKey.get(key);
    byKey.set(key, prev ? preferProjectSession(prev, s) : s);
  }
  return Array.from(byKey.values()).sort(
    (a, b) => new Date(b.lastActivityAt).getTime() - new Date(a.lastActivityAt).getTime(),
  );
}

/**
 * Apply a sidebar rename without creating duplicate rows.
 * Matches by session id OR (projectId + firstQuery) when seed is provided.
 */
export function applySessionRename(
  prev: RecentSessionRecord[],
  sessionId: string,
  title: string,
  seed?: RecentSessionRecord,
): RecentSessionRecord[] {
  const trimmed = title.trim();
  const matches = (s: RecentSessionRecord) =>
    s.id === sessionId ||
    Boolean(
      seed &&
        s.projectId &&
        seed.projectId &&
        s.projectId === seed.projectId &&
        s.firstQuery.trim().toLowerCase() === seed.firstQuery.trim().toLowerCase(),
    );

  const existing = prev.filter(matches);
  const others = prev.filter(s => !matches(s));

  if (existing.length === 0) {
    if (!seed) return prev;
    const row: RecentSessionRecord = {
      ...seed,
      id: sessionId,
      ...(trimmed && trimmed !== seed.firstQuery ? { title: trimmed } : {}),
    };
    if (!trimmed || trimmed === seed.firstQuery) {
      const { title: _drop, ...rest } = row;
      return [rest, ...others];
    }
    return [row, ...others];
  }

  // Keep a single canonical row (prefer local titled / Date.now id).
  const canonical = existing.reduce(preferProjectSession);
  const nextCanonical: RecentSessionRecord = (!trimmed || trimmed === canonical.firstQuery)
    ? (() => { const { title: _drop, ...rest } = canonical; return rest; })()
    : { ...canonical, title: trimmed };

  return [nextCanonical, ...others];
}
