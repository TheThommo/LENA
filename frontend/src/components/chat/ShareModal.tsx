'use client';

import { useState, useEffect, useCallback } from 'react';

interface ShareModalProps {
  isOpen: boolean;
  onClose: () => void;
  resultTitle?: string;
  onShare?: (data: { recipient: string; email: string; note: string }) => void;
}

const RECIPIENTS = [
  { id: 'patient', label: 'Patient', icon: '\u2764\uFE0F' },
  { id: 'colleague', label: 'Colleague', icon: '\uD83E\uDE7A' },
  { id: 'student', label: 'Student', icon: '\uD83C\uDF93' },
  { id: 'supervisor', label: 'Supervisor', icon: '\uD83D\uDCD6' },
  { id: 'family', label: 'Family', icon: '\uD83D\uDC68\u200D\uD83D\uDC69\u200D\uD83D\uDC67\u200D\uD83D\uDC66' },
  { id: 'other', label: 'Other', icon: '\uD83D\uDD17' },
] as const;

export default function ShareModal({ isOpen, onClose, resultTitle, onShare }: ShareModalProps) {
  const [selectedRecipient, setSelectedRecipient] = useState<string | null>(null);
  const [email, setEmail] = useState('');
  const [note, setNote] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);

  const resetForm = useCallback(() => {
    setSelectedRecipient(null);
    setEmail('');
    setNote('');
    setShowSuccess(false);
  }, []);

  useEffect(() => {
    if (!isOpen) {
      resetForm();
    }
  }, [isOpen, resetForm]);

  const handleShare = () => {
    if (!selectedRecipient) return;

    onShare?.({
      recipient: selectedRecipient,
      email,
      note,
    });

    setShowSuccess(true);

    setTimeout(() => {
      onClose();
    }, 1500);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {showSuccess ? (
          /* Success State */
          <div className="flex flex-col items-center justify-center py-16 px-6">
            <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-gray-900">Shared successfully!</p>
          </div>
        ) : (
          <>
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-[#1B6B93]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
                </svg>
                <h2 className="text-lg font-semibold text-gray-900">Share Research</h2>
              </div>
              <button
                onClick={onClose}
                className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Close share modal"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Body */}
            <div className="px-6 py-5 space-y-5">
              {/* Result Title */}
              {resultTitle && (
                <p className="text-sm text-gray-600 italic">{resultTitle}</p>
              )}

              {/* Recipient Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Who are you sharing with?
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {RECIPIENTS.map((r) => {
                    const isSelected = selectedRecipient === r.id;
                    return (
                      <button
                        key={r.id}
                        onClick={() => setSelectedRecipient(r.id)}
                        className={`flex flex-col items-center gap-1 py-3 px-2 rounded-lg border-2 transition-all text-sm ${
                          isSelected
                            ? 'border-teal-500 bg-teal-50'
                            : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        <span className="text-xl">{r.icon}</span>
                        <span className={`text-xs font-medium ${isSelected ? 'text-teal-700' : 'text-gray-700'}`}>
                          {r.label}
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Email */}
              <div>
                <label htmlFor="share-email" className="block text-xs text-gray-500 mb-1">
                  Email (optional)
                </label>
                <input
                  id="share-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="recipient@example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[#1B6B93]/30 focus:border-[#1B6B93] transition-colors"
                />
              </div>

              {/* Note */}
              <div>
                <label htmlFor="share-note" className="block text-xs text-gray-500 mb-1">
                  Note (optional)
                </label>
                <textarea
                  id="share-note"
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  placeholder="Add a note about this research..."
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-[#1B6B93]/30 focus:border-[#1B6B93] transition-colors"
                />
              </div>

              {/* Share Button */}
              <button
                onClick={handleShare}
                disabled={!selectedRecipient}
                className={`w-full py-2.5 rounded-lg text-sm font-semibold transition-all ${
                  selectedRecipient
                    ? 'bg-[#1B6B93] text-white hover:bg-[#145372] active:scale-[0.98]'
                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                }`}
              >
                Share Results
              </button>

              {/* Disclaimer */}
              <p className="text-[10px] text-gray-400 text-center leading-tight">
                Share data helps LENA understand how research is used across personas
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
