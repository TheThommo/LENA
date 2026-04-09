'use client';

import React, { useState } from 'react';
import ModalOverlay from './ModalOverlay';

interface NameCaptureModalProps {
  isOpen: boolean;
  onSubmit: (name: string) => void;
  brandName?: string;
}

export default function NameCaptureModal({
  isOpen,
  onSubmit,
  brandName = 'LENA',
}: NameCaptureModalProps) {
  const [name, setName] = useState('');

  const handleSubmit = () => {
    if (name.trim()) {
      onSubmit(name.trim());
      setName('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && name.trim()) {
      handleSubmit();
    }
  };

  return (
    <ModalOverlay isOpen={isOpen}>
      <div className="p-8">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-lena-500 to-lena-700 flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <h1 className="text-xl font-bold text-slate-800">
            Welcome to {brandName}
          </h1>
        </div>

        <p className="text-slate-500 mb-6 text-sm leading-relaxed">
          What should we call you? We just need your first name to personalize your research experience.
        </p>

        <div className="mb-6">
          <label className="block text-xs font-semibold text-slate-500 mb-1.5">First Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="e.g. Sarah"
            className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-lena-200 focus:border-lena-400 text-slate-800 placeholder-slate-400 transition-all duration-200"
            autoFocus
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={!name.trim()}
          className="w-full bg-gradient-to-r from-lena-500 to-lena-700 hover:from-lena-600 hover:to-lena-800 disabled:from-slate-300 disabled:to-slate-300 text-white font-semibold py-3 px-4 rounded-xl transition-all duration-200 shadow-sm"
        >
          Continue
        </button>

        <p className="text-center text-xs text-slate-400 mt-4">
          Search your first question free - no signup required
        </p>
      </div>
    </ModalOverlay>
  );
}
