'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';

interface DisclaimerCardProps {
  onAccept: () => Promise<void>;
}

/**
 * Inline LENA message that asks the visitor to acknowledge the medical
 * disclaimer before the first search runs. Renders as an assistant chat
 * bubble with an "Accept & run search" action. Acceptance is logged
 * server-side (session + IP/UA fingerprint) so a refresh cannot bypass it.
 */
export default function DisclaimerCard({ onAccept }: DisclaimerCardProps) {
  const [accepting, setAccepting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const handleClick = async () => {
    if (accepting) return;
    setAccepting(true);
    setError(null);
    try {
      await onAccept();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not accept disclaimer.');
      setAccepting(false);
    }
  };

  return (
    <div className="flex justify-start mb-4 animate-fade-in">
      <div className="max-w-[85%] rounded-2xl rounded-bl-lg bg-white border border-slate-200/70 shadow-sm px-4 py-3">
        <div className="flex items-center gap-2 mb-2">
          <Image
            src={branding.avatarSrc}
            alt={branding.name}
            width={24}
            height={24}
            className="rounded-full flex-shrink-0 ring-1 ring-black/5"
          />
          <span className="text-[13px] font-semibold text-slate-700 tracking-tight">{branding.name}</span>
        </div>

        <p className="text-[14px] text-slate-800 leading-relaxed">
          Before I dive in, a quick note: I share <strong>research evidence</strong>, not medical advice.
          Accept the disclaimer and I&apos;ll run your first search on the house.
        </p>

        {expanded && (
          <div className="mt-3 bg-slate-50 border border-slate-200/70 rounded-lg p-3 text-[12px] text-slate-600 leading-relaxed space-y-2">
            <p>
              LENA searches peer-reviewed biomedical literature and summarises what the evidence says.
              Results are NOT medical advice, diagnosis, or treatment. Always consult a qualified clinician
              before making health decisions.
            </p>
            <p>
              Acceptance is logged with a timestamp against your session and device for compliance.
              You can review the full text at any time from the footer.
            </p>
          </div>
        )}

        <button
          onClick={() => setExpanded(v => !v)}
          className="mt-2 text-[11px] text-slate-500 hover:text-slate-700 underline underline-offset-2"
        >
          {expanded ? 'Hide details' : 'Read full disclaimer'}
        </button>

        {error && (
          <p className="mt-2 text-[12px] text-red-600">{error}</p>
        )}

        <button
          onClick={handleClick}
          disabled={accepting}
          className="mt-3 w-full px-4 py-2 text-[13px] font-semibold text-white bg-lena-600 hover:bg-lena-700 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {accepting ? 'Saving…' : 'Accept & run my search'}
        </button>
      </div>
    </div>
  );
}
