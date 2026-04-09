/**
 * Application configuration
 * Reads from environment variables with sensible defaults
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

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
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  if (API_URL.startsWith('http')) {
    return `${API_URL}${normalizedPath}`;
  }
  return `${API_URL}${normalizedPath}`;
}
