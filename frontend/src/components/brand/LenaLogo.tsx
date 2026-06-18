'use client';

import Image from 'next/image';
import { branding } from '@/config/branding';

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

interface CoBrandLogoProps {
  partnerLogoUrl: string;
  partnerName: string;
  height?: number;
  className?: string;
}

/**
 * LENA + partner logo for B2B / affiliation co-branding.
 */
export function CoBrandLogo({ partnerLogoUrl, partnerName, height = 40, className = '' }: CoBrandLogoProps) {
  return (
    <div className={`flex items-center gap-3 min-w-0 ${className}`}>
      <LenaLogo height={height} />
      <div className="w-px h-8 bg-slate-200/80 flex-shrink-0" aria-hidden />
      <Image
        src={partnerLogoUrl}
        alt={partnerName}
        width={Math.round(height * 2.2)}
        height={height}
        className="w-auto object-contain object-left flex-shrink min-w-0"
        style={{ height, width: 'auto', maxWidth: '120px' }}
        unoptimized
      />
    </div>
  );
}
