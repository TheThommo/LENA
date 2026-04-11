'use client';

import React, { useState } from 'react';
import ModalOverlay from './ModalOverlay';

interface EmailCaptureModalProps {
  isOpen: boolean;
  onSubmit: (email: string) => void;
  onSkip: () => void;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function EmailCaptureModal({
  isOpen,
  onSubmit,
  onSkip,
}: EmailCaptureModalProps) {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');

  const isValidEmail = EMAIL_REGEX.test(email);

  const handleSubmit = () => {
    if (!isValidEmail) {
      setError('Please enter a valid email address');
      return;
    }
    onSubmit(email.trim());
    setEmail('');
    setError('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isValidEmail) {
      handleSubmit();
    }
  };

  const handleSkip = () => {
    setEmail('');
    setError('');
    onSkip();
  };

  return (
    <ModalOverlay isOpen={isOpen} onClose={handleSkip}>
      <div className="p-8">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2">
          Save your research
        </h1>
        <p className="text-slate-600 mb-6">
          Drop your email to save results and get personalized recommendations
        </p>

        <div className="mb-6">
          <input
            type="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError('');
            }}
            onKeyPress={handleKeyPress}
            placeholder="your@email.com"
            className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lena-500 focus:border-transparent text-slate-900 placeholder-slate-400"
            autoFocus
          />
          {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
        </div>

        <button
          onClick={handleSubmit}
          disabled={!isValidEmail}
          className="w-full bg-lena-600 hover:bg-lena-700 disabled:bg-slate-300 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 mb-3"
        >
          Continue
        </button>

        <button
          onClick={handleSkip}
          className="w-full text-slate-600 hover:text-slate-900 text-sm font-medium py-2 px-4 transition-colors duration-200"
        >
          Skip for now
        </button>
      </div>
    </ModalOverlay>
  );
}
