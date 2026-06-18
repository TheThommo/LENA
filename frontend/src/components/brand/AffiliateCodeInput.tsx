'use client';

import { useState } from 'react';
import { usePartnerBranding } from '@/contexts/PartnerBrandingContext';
import { formatAffiliationBenefit } from '@/lib/partnerBranding';

interface AffiliateCodeInputProps {
  /** Pre-fill from URL ?ref= */
  initialCode?: string;
  className?: string;
  onApplied?: () => void;
}

export function AffiliateCodeInput({ initialCode = '', className = '', onApplied }: AffiliateCodeInputProps) {
  const { affiliation, applyCode, clearAffiliation, isLoading, error } = usePartnerBranding();
  const [code, setCode] = useState(initialCode);
  const [localError, setLocalError] = useState<string | null>(null);

  if (affiliation) {
    return (
      <div className={`rounded-xl border border-emerald-200 bg-emerald-50/60 px-4 py-3 ${className}`}>
        <div className="flex items-start justify-between gap-2">
          <div>
            <p className="text-xs font-semibold text-emerald-800">Affiliation applied</p>
            <p className="text-sm text-emerald-900 mt-0.5">
              {affiliation.partnerName} · <span className="font-mono text-xs">{affiliation.code}</span>
            </p>
            <p className="text-xs text-emerald-700/90 mt-1">{formatAffiliationBenefit(affiliation)}</p>
            <p className="text-[10px] text-emerald-600/80 mt-1">
              Partner logo stays visible for your subscription period.
            </p>
          </div>
          <button
            type="button"
            onClick={() => {
              clearAffiliation();
              setCode('');
            }}
            className="text-xs text-emerald-700 hover:text-emerald-900 underline flex-shrink-0"
          >
            Remove
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      <label className="block text-sm font-medium text-slate-700 mb-1.5">
        Affiliation code <span className="text-slate-400 font-normal">(optional)</span>
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={code}
          onChange={(e) => {
            setCode(e.target.value.toUpperCase());
            setLocalError(null);
          }}
          placeholder="e.g. DEMO-UNI"
          className="flex-1 input-touch border border-slate-200 rounded-xl px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-lena-100 focus:border-lena-400"
          disabled={isLoading}
        />
        <button
          type="button"
          disabled={!code.trim() || isLoading}
          onClick={async () => {
            try {
              await applyCode(code);
              onApplied?.();
            } catch (err) {
              setLocalError(err instanceof Error ? err.message : 'Invalid code');
            }
          }}
          className="px-4 py-2.5 rounded-xl bg-slate-100 text-slate-700 text-sm font-semibold hover:bg-slate-200 disabled:opacity-40 min-h-[44px]"
        >
          {isLoading ? '…' : 'Apply'}
        </button>
      </div>
      {(localError || error) && (
        <p className="text-xs text-red-600 mt-1.5">{localError || error}</p>
      )}
      <p className="text-[11px] text-slate-400 mt-1.5">
        From your university, hospital, or clinic? Enter their code for co-branded access and partner pricing.
      </p>
    </div>
  );
}
