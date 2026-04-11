'use client';

import React from 'react';
import ModalOverlay from './ModalOverlay';

interface SearchLimitModalProps {
  isOpen: boolean;
  onRegister: () => void;
  onLogin: () => void;
}

const FEATURES = [
  '40M+ papers',
  '8+ databases',
  'PULSE validation',
  'Seconds, not hours',
];

export default function SearchLimitModal({
  isOpen,
  onRegister,
  onLogin,
}: SearchLimitModalProps) {
  return (
    <ModalOverlay isOpen={isOpen} blocking={true}>
      <div className="p-8">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2">
          You've explored your free searches
        </h1>
        <p className="text-slate-600 mb-8">
          Sign up to unlock unlimited access to LENA's cross-referenced research
        </p>

        <button
          onClick={onRegister}
          className="w-full bg-lena-600 hover:bg-lena-700 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 mb-3"
        >
          Create Free Account
        </button>

        <button
          onClick={onLogin}
          className="w-full text-lena-600 hover:text-lena-700 font-medium py-3 px-4 transition-colors duration-200"
        >
          Sign In
        </button>

        <div className="mt-8 pt-8 border-t border-slate-200">
          <p className="text-xs text-slate-500 uppercase tracking-wider mb-4">
            What you'll get access to
          </p>
          <ul className="space-y-2">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-center text-slate-700 text-sm">
                <div className="w-1.5 h-1.5 bg-lena-600 rounded-full mr-3" />
                {feature}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </ModalOverlay>
  );
}
