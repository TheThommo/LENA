'use client';

import React from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';

interface UpgradeCTACardProps {
  onUpgrade: () => void;
  onContact: () => void;
  message?: string | null;
}

export default function UpgradeCTACard({ onUpgrade, onContact, message }: UpgradeCTACardProps) {
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
          That&apos;s your <strong>5 free searches</strong> for today. Upgrade to <strong>Pro</strong> for
          unlimited searches, saved history, project folders, and export - or reach out and we&apos;ll
          tailor a plan for your team.
        </p>

        {message && (
          <p className="mt-2 text-[12px] text-slate-500 leading-relaxed">
            Your free tier resets in 24 hours.
          </p>
        )}

        <div className="mt-3 flex flex-col sm:flex-row gap-2">
          <button
            onClick={onUpgrade}
            className="flex-1 px-4 py-2 text-[13px] font-semibold text-white bg-lena-600 hover:bg-lena-700 rounded-lg transition-colors"
          >
            Upgrade to Pro
          </button>
          <button
            onClick={onContact}
            className="flex-1 px-4 py-2 text-[13px] font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Contact us
          </button>
        </div>

        <p className="mt-2 text-[11px] text-slate-400">
          $30/mo or $300/yr. Founding 10: $50/yr (first 10 members only).
        </p>
      </div>
    </div>
  );
}
