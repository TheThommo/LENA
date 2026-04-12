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

  /** Logo image used in sidebar header (compass/DNA mark) */
  logoSrc: '/lena-logo.png',

  /** Agent avatar used in chat messages and thinking indicator */
  avatarSrc: '/lena-avatar.png',

  /** Primary brand color */
  primaryColor: '#1B6B93',

  /** Dark variant of brand color */
  primaryDark: '#145372',
} as const;
