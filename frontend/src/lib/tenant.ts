/**
 * Tenant Configuration and Theming
 * Handles white-label support for different organizations
 */

export interface TenantColors {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  accent: string;
  surface: string;
}

export interface TenantFeatures {
  altMedicine: boolean;
  contributionRepo: boolean;
}

export interface TenantConfig {
  id: string;
  name: string;
  brandName: string;
  tagline: string;
  logoUrl?: string;
  faviconUrl?: string;
  colors: TenantColors;
  features: TenantFeatures;
  footerText: string;
}

export const DEFAULT_TENANT: TenantConfig = {
  id: 'lena',
  name: 'LENA',
  brandName: 'LENA',
  tagline: 'Literature and Evidence Navigation Agent',
  logoUrl: undefined,
  faviconUrl: undefined,
  colors: {
    primary: '0 116 197',
    primaryLight: '186 224 253',
    primaryDark: '1 93 160',
    accent: '12 147 231',
    surface: '240 247 255',
  },
  features: {
    altMedicine: true,
    contributionRepo: true,
  },
  footerText: 'Powered by LENA',
};

/**
 * Get tenant configuration by ID
 * Currently returns DEFAULT_TENANT; will be API-driven in future
 */
export function getTenantConfig(tenantId: string): TenantConfig {
  // TODO: Fetch from API endpoint when multi-tenant setup is ready
  if (tenantId === 'lena' || tenantId === 'default') {
    return DEFAULT_TENANT;
  }
  return DEFAULT_TENANT;
}

/**
 * Apply tenant theme colors to document CSS variables
 */
export function applyTenantTheme(config: TenantConfig): void {
  if (typeof document === 'undefined') return;

  const root = document.documentElement;
  root.style.setProperty('--brand-primary', config.colors.primary);
  root.style.setProperty('--brand-primary-light', config.colors.primaryLight);
  root.style.setProperty('--brand-primary-dark', config.colors.primaryDark);
  root.style.setProperty('--brand-accent', config.colors.accent);
  root.style.setProperty('--brand-surface', config.colors.surface);
  root.style.setProperty('--brand-name', config.brandName);
}
