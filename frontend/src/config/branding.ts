/**
 * Branding Configuration
 *
 * All visual brand assets are configured here.
 * Change logos, avatars, and brand identity in one place.
 */

export const branding = {
  /** App name displayed in sidebar and UI */
  name: 'LENA',

  /** Subtitle under the app name */
  subtitle: 'Research Agent',

  /** Logo image used in sidebar header (full brand logo with text) */
  logoSrc: '/lena-logo.jpg',

  /** Agent avatar used in chat messages and thinking indicator */
  avatarSrc: '/lena-avatar.jpg',

  /** Primary brand color */
  primaryColor: '#1B6B93',

  /** Dark variant of brand color */
  primaryDark: '#145372',
} as const;


/**
 * Product constants - single source of truth.
 *
 * These numbers appear across the frontend (welcome page, search bar,
 * thinking indicator, funnel modals, How It Works). Changing them here
 * updates everywhere. NO hardcoded "250M+" or "6 databases" anywhere else.
 */
export const product = {
  /** Total papers indexed across all sources */
  paperCount: '250M+',

  /** Number of data sources queried */
  sourceCount: 8,

  /** Source names for display */
  sourceNames: ['PubMed', 'ClinicalTrials.gov', 'Cochrane', 'WHO IRIS', 'CDC', 'OpenAlex', 'NIH DSLD', 'openFDA CAERS'],

  /** Source names as a readable string */
  get sourceList() {
    return this.sourceNames.join(', ');
  },

  /** Short source list for compact UI */
  sourceListShort: 'PubMed, Cochrane, OpenAlex & more',

  /** Free tier search limit per session */
  freeSearchLimit: 5,

  /** Tagline used in search bar, welcome page, etc. */
  get tagline() {
    return `LENA searches ${this.paperCount} papers across ${this.sourceCount} databases`;
  },

  /** Longer description for welcome/marketing */
  get description() {
    return `Search ${this.paperCount} medical papers across ${this.sourceCount} databases in seconds, cross-referenced by AI for accuracy.`;
  },
} as const;
