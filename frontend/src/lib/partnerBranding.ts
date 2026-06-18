/**
 * Partner / affiliation co-branding — persisted client-side until billing wires entitlements.
 */

export type PartnerSegment =
  | 'university'
  | 'hospital'
  | 'clinic'
  | 'pharmacy'
  | 'doctors_room'
  | 'corporate'
  | 'individual';

export interface AffiliationBranding {
  code: string;
  partnerId: string;
  partnerName: string;
  partnerSlug: string;
  segment: PartnerSegment;
  logoUrl?: string | null;
  websiteUrl?: string | null;
  benefitType: 'percent_discount' | 'free_months' | 'trial_extension' | 'custom';
  benefitValue: number;
  benefitDescription?: string | null;
  coBrandDurationDays?: number | null;
  label?: string | null;
  /** When co-branding expires (ISO string); null = follow subscription */
  coBrandUntil?: string | null;
  appliedAt: string;
}

export const AFFILIATION_STORAGE_KEY = 'lena_affiliation_v1';

export const PARTNER_SEGMENT_LABELS: Record<PartnerSegment, string> = {
  university: 'University',
  hospital: 'Hospital',
  clinic: 'Clinic',
  pharmacy: 'Pharmacy',
  doctors_room: "Doctor's rooms",
  corporate: 'Organisation',
  individual: 'Individual',
};

export function normalizeAffiliationCode(raw: string): string {
  return raw.trim().toUpperCase().replace(/\s+/g, '-');
}

export function loadStoredAffiliation(): AffiliationBranding | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(AFFILIATION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AffiliationBranding;
    if (parsed.coBrandUntil && new Date(parsed.coBrandUntil) < new Date()) {
      localStorage.removeItem(AFFILIATION_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function saveStoredAffiliation(branding: AffiliationBranding): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(AFFILIATION_STORAGE_KEY, JSON.stringify(branding));
  } catch {
    /* quota / private mode */
  }
}

export function clearStoredAffiliation(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(AFFILIATION_STORAGE_KEY);
  } catch {}
}

export function affiliationFromApiResponse(data: Record<string, unknown>): AffiliationBranding {
  const days = data.co_brand_duration_days as number | null | undefined;
  const appliedAt = new Date().toISOString();
  let coBrandUntil: string | null = null;
  if (days && days > 0) {
    const until = new Date();
    until.setDate(until.getDate() + days);
    coBrandUntil = until.toISOString();
  }
  return {
    code: String(data.code),
    partnerId: String(data.partner_id),
    partnerName: String(data.partner_name),
    partnerSlug: String(data.partner_slug),
    segment: (data.segment as PartnerSegment) || 'corporate',
    logoUrl: (data.logo_url as string | null) ?? null,
    websiteUrl: (data.website_url as string | null) ?? null,
    benefitType: (data.benefit_type as AffiliationBranding['benefitType']) || 'custom',
    benefitValue: Number(data.benefit_value) || 0,
    benefitDescription: (data.benefit_description as string | null) ?? null,
    coBrandDurationDays: days ?? null,
    label: (data.label as string | null) ?? null,
    coBrandUntil,
    appliedAt,
  };
}

export function formatAffiliationBenefit(a: AffiliationBranding): string {
  if (a.benefitDescription) return a.benefitDescription;
  switch (a.benefitType) {
    case 'percent_discount':
      return `${a.benefitValue}% off subscription`;
    case 'free_months':
      return `${a.benefitValue} month${a.benefitValue === 1 ? '' : 's'} free`;
    case 'trial_extension':
      return `${a.benefitValue} extra trial days`;
    default:
      return 'Partner benefit applied at checkout';
  }
}

/** URL params: ?ref=CODE or ?affiliate=CODE */
export function readAffiliationCodeFromSearch(search: string): string | null {
  const params = new URLSearchParams(search);
  const ref = params.get('ref') || params.get('affiliate') || params.get('code');
  return ref ? normalizeAffiliationCode(ref) : null;
}
