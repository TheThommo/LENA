/**
 * Branding Configuration
 *
 * All visual brand assets are configured here.
 * Change logos, avatars, and brand identity in one place.
 */

export const branding = {
  /** App name displayed in sidebar and UI */
  name: 'LENA',

  /** Subtitle under the app name (also used in logo alt text) */
  subtitle: 'Literature Evidence based Navigation Agent',

  /** Full wordmark — transparent PNG in /public (falls back to logoFallbackSrc) */
  logoSrc: '/lena_logo_1.png',

  /** Shown when logoSrc is missing or fails to load */
  logoFallbackSrc: '/lena-logo.jpg',

  /** Wordmark PNG aspect (width / height) after tight crop */
  logoAspect: 551 / 530,

  /** Display heights (px) — ~10% under max so a partner logo can sit alongside */
  logoSizes: {
    sidebar: 151,
    auth: 126,
    mobileHeader: 72,
    /** Landing page header wordmark */
    landing: 160,
  },

  /** Max rendered width for sidebar wordmark (room for co-brand partner) */
  logoMaxWidth: 227,

  /** Agent avatar used in chat messages and thinking indicator */
  avatarSrc: '/lena-avatar.jpg',

  /** Primary brand color */
  primaryColor: '#136B7A',

  /** Dark variant of brand color */
  primaryDark: '#0D4854',
} as const;

/**
 * Product constants - single source of truth for GTM.
 *
 * These numbers appear across the frontend (landing page, welcome view,
 * search bar, funnel modals, How It Works). Changing them here updates
 * everywhere.
 */
export const product = {
  /** Total papers indexed across all sources */
  paperCount: '250M+',

  /** Number of live data sources queried in parallel */
  sourceCount: 11,

  /** Source names for display */
  sourceNames: [
    'PubMed',
    'Cochrane',
    'OpenAlex',
    'Semantic Scholar',
    'Europe PMC',
    'ClinicalTrials.gov',
    'WHO IRIS',
    'CDC',
    'FDA DailyMed',
    'NIH DSLD',
    'openFDA',
  ],

  get sourceList() {
    return this.sourceNames.join(', ');
  },

  sourceListShort: 'PubMed, Cochrane, OpenAlex, Semantic Scholar & more',

  /** Anonymous visitors: free searches without signup */
  freeAnonSearchLimit: 3,

  /** Free tier: 10 searches per calendar month (registered) */
  freeSearchLimit: 10,

  /** Pro individual price (USD) — must match Stripe */
  proMonthlyUsd: 19,
  proAnnualUsd: 190,

  get tagline() {
    return `LENA cross-validates ${this.paperCount} papers across ${this.sourceCount} databases`;
  },

  get description() {
    return `Ask a health research question. LENA queries ${this.sourceCount} sources in parallel, validates evidence with PULSE, and returns a shareable brief — in seconds.`;
  },
} as const;
