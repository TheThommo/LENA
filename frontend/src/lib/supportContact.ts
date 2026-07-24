/** Canonical LENA support / contact address (owner). */
export const SUPPORT_EMAIL = 'mark@cero-international.com';

export function supportMailto(subject = 'LENA Support request', body?: string): string {
  const q = new URLSearchParams({ subject });
  if (body) q.set('body', body);
  return `mailto:${SUPPORT_EMAIL}?${q.toString()}`;
}

export function openSupportMail(subject = 'LENA Support request', body?: string): void {
  if (typeof window === 'undefined') return;
  window.location.href = supportMailto(subject, body);
}

/** True for LenaUpgradeRequiredError across module boundaries (instanceof can fail). */
export function isUpgradeRequiredError(err: unknown): err is Error & { feature?: string; message: string } {
  if (!err || typeof err !== 'object') return false;
  const e = err as { name?: string; feature?: string; message?: string };
  return e.name === 'LenaUpgradeRequiredError' || typeof e.feature === 'string';
}
