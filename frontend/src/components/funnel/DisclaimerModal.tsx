'use client';

import React, { useState } from 'react';
import ModalOverlay from './ModalOverlay';

interface DisclaimerModalProps {
  isOpen: boolean;
  onAccept: (timestamp: string) => void;
}

const DISCLAIMER_TEXT =
  'LENA is an AI-powered research tool, not a medical professional. Information provided should not be used as a substitute for professional medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider.';

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
        <h1 className="text-2xl font-semibold text-gray-900 mb-6">
          Important Medical Disclaimer
        </h1>

        <div className="bg-lena-50 border border-lena-200 rounded-lg p-4 mb-6">
          <p className="text-gray-700 text-sm leading-relaxed">
            {DISCLAIMER_TEXT}
          </p>
        </div>

        <div className="mb-6 flex items-start">
          <input
            type="checkbox"
            id="disclaimer-accept"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-1 w-4 h-4 rounded border-gray-300 text-lena-600 focus:ring-lena-500 cursor-pointer"
          />
          <label
            htmlFor="disclaimer-accept"
            className="ml-3 text-sm text-gray-700 cursor-pointer"
          >
            I understand and accept this disclaimer
          </label>
        </div>

        <button
          onClick={handleAccept}
          disabled={!accepted}
          className="w-full bg-lena-600 hover:bg-lena-700 disabled:bg-gray-300 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200"
        >
          Accept & Continue
        </button>
      </div>
    </ModalOverlay>
  );
}
