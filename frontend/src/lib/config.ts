/**
 * Application configuration
 * Reads from environment variables with sensible defaults
 */

/** Production backend when NEXT_PUBLIC_API_URL is not baked into the build. */
const PRODUCTION_API_DEFAULT = 'https://lena-production-health.up.railway.app/api';

/**
 * Resolve the API base URL.
 * - Browser on deployed frontend → same-origin `/api` (middleware proxies to backend)
 * - NEXT_PUBLIC_API_URL at build time for SSR/server fallbacks
 * - Development → /api (Next.js rewrite to localhost:8000)
 */
export function resolveApiBase(): string {
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (
      host === 'lena-app.up.railway.app'
      || host.endsWith('.up.railway.app')
      || host.includes('lena-app')
      || host === 'localhost'
      || host === '127.0.0.1'
    ) {
      return '/api';
    }
  }

  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv) return fromEnv.replace(/\/$/, '');

  if (process.env.NODE_ENV === 'production') {
    return PRODUCTION_API_DEFAULT;
  }

  return '/api';
}

export const API_URL = resolveApiBase();

export const APP_ENV = (process.env.NEXT_PUBLIC_APP_ENV || 'development') as
  | 'development'
  | 'staging'
  | 'production';

export function isProduction(): boolean {
  return APP_ENV === 'production';
}

export function isStaging(): boolean {
  return APP_ENV === 'staging';
}

export function isDevelopment(): boolean {
  return APP_ENV === 'development';
}

export function isRunningOnRailway(): boolean {
  return !!process.env.RAILWAY_ENVIRONMENT_NAME;
}

/**
 * Get the full API endpoint URL
 * Handles both absolute URLs and relative paths
 */
export function getApiUrl(path: string): string {
  const base = resolveApiBase();
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (base.startsWith('http')) {
    return `${base}${normalizedPath}`;
  }
  return `${base}${normalizedPath}`;
}
