/** Client-side JWT helpers for session persistence (no signature verify). */

export function decodeJwtExpMs(token: string): number | null {
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const json = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
    const payload = JSON.parse(json) as { exp?: number };
    return typeof payload.exp === 'number' ? payload.exp * 1000 : null;
  } catch {
    return null;
  }
}

/** True when the token exists and its exp claim is still in the future. */
export function isTokenStillValid(token: string | null, skewMs = 60_000): boolean {
  if (!token) return false;
  const expMs = decodeJwtExpMs(token);
  if (!expMs) return true;
  return Date.now() < expMs - skewMs;
}

export const SESSION_STORAGE_KEYS = {
  token: 'lena_token',
  user: 'lena_user',
  expiresAt: 'lena_token_expires_at',
} as const;

export function persistAuthSession(token: string, user: unknown): void {
  const expMs = decodeJwtExpMs(token);
  localStorage.setItem(SESSION_STORAGE_KEYS.token, token);
  localStorage.setItem(SESSION_STORAGE_KEYS.user, JSON.stringify(user));
  if (expMs) {
    localStorage.setItem(SESSION_STORAGE_KEYS.expiresAt, String(expMs));
  }
}

export function clearAuthSession(): void {
  localStorage.removeItem(SESSION_STORAGE_KEYS.token);
  localStorage.removeItem(SESSION_STORAGE_KEYS.user);
  localStorage.removeItem(SESSION_STORAGE_KEYS.expiresAt);
}
