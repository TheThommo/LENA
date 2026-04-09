'use client';

import React, { useState } from 'react';
import ModalOverlay from './ModalOverlay';

interface DisclaimerModalProps {
  isOpen: boolean;
  onAccept: (timestamp: string) => void;
}

export default function DisclaimerModal({
  isOpen,
  onAccept,
}: DisclaimerModalProps) {
  const [accepted, setAccepted] = useState(false);

  const handleAccept = () => {
    if (accepted) {
      const timestamp = new Date().toISOString();
      onAccept(timestamp);
      setAccepted(false);
    }
  };

  return (
    <ModalOverlay isOpen={isOpen} blocking={true}>
      <div className="p-8">
        {/* Header */}
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800">
            Medical Disclaimer
          </h1>
        </div>

        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
          <p className="text-slate-700 text-sm leading-relaxed">
            LENA is an AI-powered research tool, <strong>not a medical professional</strong>.
            Information provided should not be used as a substitute for professional medical advice,
            diagnosis, or treatment. Always consult with a qualified healthcare provider before making
            any health decisions.
          </p>
        </div>

        <div className="bg-slate-50 rounded-xl p-4 mb-6">
          <ul className="space-y-2 text-xs text-slate-600">
            <li className="flex items-start gap-2">
              <svg className="w-4 h-4 text-lena-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              LENA searches published research databases and cross-references findings
            </li>
            <li className="flex items-start gap-2">
              <svg className="w-4 h-4 text-lena-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Results are scored by PULSE for consensus, not clinical recommendation
            </li>
            <li className="flex items-start gap-2">
              <svg className="w-4 h-4 text-lena-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Your acceptance is logged with a timestamp for compliance
            </li>
          </ul>
        </div>

        <label className="flex items-start gap-3 mb-6 cursor-pointer group">
          <input
            type="checkbox"
            id="disclaimer-accept"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-0.5 w-4 h-4 rounded border-slate-300 text-lena-600 focus:ring-lena-200 cursor-pointer"
          />
          <span className="text-sm text-slate-600 group-hover:text-slate-800 transition-colors">
            I understand that LENA provides research summaries, not medical advice, and I accept this disclaimer
          </span>
        </label>

        <button
          onClick={handleAccept}
          disabled={!accepted}
          className="w-full bg-gradient-to-r from-lena-500 to-lena-700 hover:from-lena-600 hover:to-lena-800 disabled:from-slate-300 disabled:to-slate-300 text-white font-semibold py-3 px-4 rounded-xl transition-all duration-200 shadow-sm"
        >
          Accept &amp; Start Searching
        </button>
      </div>
    </ModalOverlay>
  );
}
