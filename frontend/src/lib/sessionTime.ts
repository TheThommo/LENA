/** Recent session metadata persisted in localStorage (per authenticated user). */
export interface RecentSessionRecord {
  id: string;
  firstQuery: string;
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
