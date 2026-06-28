'use client';

import React from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';
import { defaultContactHandler } from '@/components/chat/UpgradeCTACard';

interface ContactSupportCardProps {
  onContact?: () => void;
}

/**
 * Shown when something unexpected fails — never raw stack traces or HTTP codes.
 */
export default function ContactSupportCard({ onContact = defaultContactHandler }: ContactSupportCardProps) {
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
          Something didn&apos;t work on our side — sorry about that. Please tap{' '}
          <strong>Contact us</strong> and tell us what you were trying to do; we&apos;ll sort it out.
        </p>
        <button
          type="button"
          onClick={onContact}
          className="mt-3 w-full sm:w-auto px-4 py-2 text-[13px] font-semibold text-white bg-lena-600 hover:bg-lena-700 rounded-lg transition-colors"
        >
          Contact us
        </button>
      </div>
    </div>
  );
}
