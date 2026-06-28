'use client';

import React from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';

const SUPPORT_MAIL = 'mailto:hello@lena-app.com?subject=LENA%20Support%20request';

interface UpgradeCTACardProps {
  onUpgrade: () => void;
  onContact: () => void;
  /** Primary body copy — welcoming tone, not an error message */
  message?: string | null;
  /** Optional secondary line (e.g. reset timing) */
  subtext?: string | null;
  upgradeLabel?: string;
  contactLabel?: string;
}

const DEFAULT_MESSAGE =
  "You've reached a Free plan limit. Upgrade to **Pro** for unlimited searches, project folders, saved history, and export — or tell us what you need and we'll help.";

export default function UpgradeCTACard({
  onUpgrade,
  onContact,
  message,
  subtext,
  upgradeLabel = 'Upgrade to Pro',
  contactLabel = 'Contact us',
}: UpgradeCTACardProps) {
  const body = message?.trim() || DEFAULT_MESSAGE;

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

        <p
          className="text-[14px] text-slate-800 leading-relaxed whitespace-pre-line"
          dangerouslySetInnerHTML={{
            __html: body.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>'),
          }}
        />

        {subtext && (
          <p className="mt-2 text-[12px] text-slate-500 leading-relaxed">{subtext}</p>
        )}

        <div className="mt-3 flex flex-col sm:flex-row gap-2">
          <button
            type="button"
            onClick={onUpgrade}
            className="flex-1 px-4 py-2 text-[13px] font-semibold text-white bg-lena-600 hover:bg-lena-700 rounded-lg transition-colors"
          >
            {upgradeLabel}
          </button>
          <button
            type="button"
            onClick={onContact}
            className="flex-1 px-4 py-2 text-[13px] font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            {contactLabel}
          </button>
        </div>

        <p className="mt-2 text-[11px] text-slate-400">
          $30/mo or $300/yr. Founding 10: $50/yr (first 10 members only).
        </p>
      </div>
    </div>
  );
}

export function defaultContactHandler() {
  window.location.href = SUPPORT_MAIL;
}
