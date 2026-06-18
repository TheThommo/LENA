'use client';

import Image from 'next/image';
import { LenaLogo, CoBrandLogo } from '@/components/brand/LenaLogo';
import { usePartnerBranding } from '@/contexts/PartnerBrandingContext';
import { PARTNER_SEGMENT_LABELS } from '@/lib/partnerBranding';

interface BrandMarkProps {
  height?: number;
  className?: string;
  priority?: boolean;
}

/**
 * Renders LENA alone, or LENA + partner when an affiliation is active.
 */
export function BrandMark({ height = 64, className = '', priority = false }: BrandMarkProps) {
  const { affiliation, hasCoBrand } = usePartnerBranding();

  if (hasCoBrand && affiliation) {
    return (
      <CoBrandLogo
        partnerName={affiliation.partnerName}
        partnerLogoUrl={affiliation.logoUrl}
        partnerSegment={affiliation.segment}
        height={height}
        className={className}
        priority={priority}
      />
    );
  }

  return <LenaLogo height={height} className={className} priority={priority} />;
}

interface PartnerBenefitPillProps {
  className?: string;
}

/** Compact benefit callout for signup / profile */
export function PartnerBenefitPill({ className = '' }: PartnerBenefitPillProps) {
  const { affiliation } = usePartnerBranding();
  if (!affiliation) return null;

  const segment = PARTNER_SEGMENT_LABELS[affiliation.segment] || 'Partner';

  return (
    <div
      className={`rounded-2xl border border-lena-200/70 bg-gradient-to-br from-lena-50/80 to-white px-4 py-3 ${className}`}
    >
      <p className="text-[11px] font-semibold text-lena-700 uppercase tracking-wide">
        {segment} partnership · {affiliation.code}
      </p>
      <p className="text-sm font-medium text-slate-800 mt-0.5">{affiliation.partnerName}</p>
      {affiliation.benefitDescription && (
        <p className="text-xs text-slate-600 mt-1">{affiliation.benefitDescription}</p>
      )}
    </div>
  );
}
