'use client';

import Image from 'next/image';
import { branding } from '@/config/branding';
import type { PartnerSegment } from '@/lib/partnerBranding';
import { PARTNER_SEGMENT_LABELS } from '@/lib/partnerBranding';

interface LenaLogoProps {
  /** Max height in pixels */
  height?: number;
  className?: string;
  priority?: boolean;
}

/**
 * Full LENA wordmark — transparent PNG, no background box.
 */
export function LenaLogo({ height = 64, className = '', priority = false }: LenaLogoProps) {
  return (
    <Image
      src={branding.logoSrc}
      alt={`${branding.name} — ${branding.subtitle}`}
      width={Math.round(height * 2.8)}
      height={height}
      priority={priority}
      className={`w-auto object-contain object-left ${className}`}
      style={{ height, width: 'auto', maxWidth: '100%' }}
    />
  );
}

function PartnerMark({
  name,
  logoUrl,
  segment,
  height,
}: {
  name: string;
  logoUrl?: string | null;
  segment?: PartnerSegment;
  height: number;
}) {
  if (logoUrl) {
    return (
      <Image
        src={logoUrl}
        alt={name}
        width={Math.round(height * 2.2)}
        height={height}
        className="w-auto object-contain object-left flex-shrink min-w-0"
        style={{ height, width: 'auto', maxWidth: '120px' }}
        unoptimized
      />
    );
  }

  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map(w => w[0])
    .join('')
    .toUpperCase();

  const segmentLabel = segment ? PARTNER_SEGMENT_LABELS[segment] : 'Partner';

  return (
    <div
      className="flex items-center gap-2 flex-shrink min-w-0"
      title={name}
    >
      <div
        className="flex items-center justify-center rounded-xl bg-slate-100 border border-slate-200/80 text-slate-700 font-bold flex-shrink-0"
        style={{ width: height, height, fontSize: Math.max(10, height * 0.32) }}
      >
        {initials || 'P'}
      </div>
      <div className="min-w-0 hidden sm:block">
        <p className="text-xs font-semibold text-slate-800 truncate leading-tight">{name}</p>
        <p className="text-[10px] text-slate-400 truncate">{segmentLabel}</p>
      </div>
    </div>
  );
}

interface CoBrandLogoProps {
  partnerName: string;
  partnerLogoUrl?: string | null;
  partnerSegment?: PartnerSegment;
  height?: number;
  className?: string;
  priority?: boolean;
}

/**
 * LENA + partner logo for B2B / affiliation co-branding.
 */
export function CoBrandLogo({
  partnerName,
  partnerLogoUrl,
  partnerSegment,
  height = 40,
  className = '',
  priority = false,
}: CoBrandLogoProps) {
  return (
    <div className={`flex items-center gap-2.5 sm:gap-3 min-w-0 ${className}`}>
      <LenaLogo height={height} priority={priority} />
      <div className="w-px self-stretch min-h-[28px] bg-slate-200/80 flex-shrink-0" aria-hidden />
      <PartnerMark
        name={partnerName}
        logoUrl={partnerLogoUrl}
        segment={partnerSegment}
        height={Math.round(height * 0.85)}
      />
    </div>
  );
}
