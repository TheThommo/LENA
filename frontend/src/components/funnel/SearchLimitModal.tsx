'use client';

import React from 'react';
import ModalOverlay from './ModalOverlay';
import { product } from '@/config/branding';

interface SearchLimitModalProps {
  isOpen: boolean;
  onRegister: () => void;
  onLogin: () => void;
}

const FEATURES = [
  { icon: '📚', text: `${product.paperCount} academic papers`, detail: product.sourceListShort },
  { icon: '🔬', text: `${product.sourceCount} scientific databases`, detail: 'Queried simultaneously in real-time' },
  { icon: '✅', text: 'PULSE validation engine', detail: 'Cross-reference scoring & consensus detection' },
  { icon: '🤖', text: 'AI evidence synthesis', detail: 'Persona-aware summaries powered by GPT-4o' },
  { icon: '⚡', text: 'Results in seconds', detail: 'What used to take hours of manual review' },
];

export default function SearchLimitModal({
  isOpen,
  onRegister,
  onLogin,
}: SearchLimitModalProps) {
  return (
    <ModalOverlay isOpen={isOpen} blocking={true}>
      <div className="p-8">
        {/* Badge */}
        <div className="flex justify-center mb-4">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-50 text-amber-700 text-xs font-semibold rounded-full border border-amber-200">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Free preview limit reached
          </span>
        </div>

        <h1 className="text-2xl font-bold text-slate-900 mb-2 text-center">
          Unlock Full Research Access
        </h1>
        <p className="text-slate-500 mb-6 text-center text-sm leading-relaxed">
          Create a free account to continue searching with LENA&apos;s full evidence pipeline
        </p>

        <button
          onClick={onRegister}
          className="w-full font-semibold py-3.5 px-4 rounded-xl text-white transition-all duration-200 mb-3 shadow-md hover:shadow-lg"
          style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
        >
          Create Free Account
        </button>

        <button
          onClick={onLogin}
          className="w-full text-lena-600 hover:text-lena-700 font-medium py-2.5 px-4 transition-colors duration-200 text-sm"
        >
          Already have an account? Sign In
        </button>

        <div className="mt-6 pt-6 border-t border-slate-100">
          <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mb-3 text-center">
            What you get with a free account
          </p>
          <div className="space-y-3">
            {FEATURES.map((f) => (
              <div key={f.text} className="flex items-start gap-3">
                <span className="text-base flex-shrink-0 mt-0.5">{f.icon}</span>
                <div>
                  <p className="text-sm font-medium text-slate-800">{f.text}</p>
                  <p className="text-[11px] text-slate-400 leading-tight">{f.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </ModalOverlay>
  );
}
