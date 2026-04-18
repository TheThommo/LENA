'use client';

import React, { useState } from 'react';
import ModalOverlay from './ModalOverlay';
import { product } from '@/config/branding';

export interface WelcomeCapturePayload {
  name: string;
  email: string;
  disclaimerAccepted: boolean;
  dataConsentAccepted: boolean;
  institution?: string;
}

interface WelcomeCaptureModalProps {
  isOpen: boolean;
  onSubmit: (data: WelcomeCapturePayload) => Promise<void> | void;
  onLogin: () => void;
  brandName?: string;
}

export default function WelcomeCaptureModal({
  isOpen,
  onSubmit,
  onLogin,
  brandName = 'LENA',
}: WelcomeCaptureModalProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [institution, setInstitution] = useState('');
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);
  const [dataConsentAccepted, setDataConsentAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    name.trim().length > 0 &&
    /\S+@\S+\.\S+/.test(email.trim()) &&
    disclaimerAccepted &&
    dataConsentAccepted &&
    !submitting;

  const handleSubmit = async () => {
    if (!canSubmit) return;
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        name: name.trim(),
        email: email.trim(),
        institution: institution.trim() || undefined,
        disclaimerAccepted,
        dataConsentAccepted,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong. Please try again.');
      setSubmitting(false);
    }
  };

  return (
    <ModalOverlay isOpen={isOpen} blocking={true}>
      <div className="p-8">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-lena-500 to-lena-700 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Welcome to {brandName}</h1>
            <p className="text-xs text-slate-500">{product.freeSearchLimit} free searches a day - no credit card</p>
          </div>
        </div>

        <div className="space-y-3 mb-5">
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">First name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Sarah"
              className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lena-200 focus:border-lena-400"
              autoFocus
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lena-200 focus:border-lena-400"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-500 mb-1.5">
              Institution <span className="font-normal text-slate-400">(optional)</span>
            </label>
            <input
              type="text"
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              placeholder="e.g. Mount Sinai Hospital"
              className="w-full px-3.5 py-2.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-lena-200 focus:border-lena-400"
            />
          </div>
        </div>

        <div className="space-y-2.5 mb-5 text-xs text-slate-600 leading-relaxed">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={disclaimerAccepted}
              onChange={(e) => setDisclaimerAccepted(e.target.checked)}
              className="mt-0.5 w-4 h-4 text-lena-600 rounded border-slate-300 focus:ring-lena-400"
            />
            <span>
              I understand LENA is a research tool and <strong>not medical advice</strong>. Clinical
              decisions must involve a qualified practitioner.
            </span>
          </label>
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={dataConsentAccepted}
              onChange={(e) => setDataConsentAccepted(e.target.checked)}
              className="mt-0.5 w-4 h-4 text-lena-600 rounded border-slate-300 focus:ring-lena-400"
            />
            <span>
              I consent to LENA processing my email and usage data to deliver the service and send a
              confirmation email. I can revoke consent at any time.
            </span>
          </label>
        </div>

        {error && (
          <div className="mb-3 p-2.5 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="w-full bg-gradient-to-r from-lena-500 to-lena-700 hover:from-lena-600 hover:to-lena-800 disabled:from-slate-300 disabled:to-slate-300 text-white font-semibold py-3 px-4 rounded-xl transition-all duration-200 shadow-sm text-sm"
        >
          {submitting ? 'Sending confirmation…' : 'Get started'}
        </button>

        <div className="text-center mt-4">
          <button
            onClick={onLogin}
            className="text-xs text-lena-600 hover:text-lena-700 font-medium"
          >
            Already have an account? Sign in
          </button>
        </div>
      </div>
    </ModalOverlay>
  );
}
