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
        <h1 className="text-2xl font-semibold text-gray-900 mb-2">
          Welcome to {brandName}
        </h1>
        <p className="text-gray-600 mb-6">
          What should we call you?
        </p>

        <div className="mb-6">
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Your name"
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lena-500 focus:border-transparent text-gray-900 placeholder-gray-400"
            autoFocus
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={!name.trim()}
          className="w-full bg-lena-600 hover:bg-lena-700 disabled:bg-gray-300 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
        >
          Continue
        </button>
      </div>
    </ModalOverlay>
  );
}
