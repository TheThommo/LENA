'use client';

import { useState, useEffect } from 'react';

const STEPS = [
  'Understanding your query...',
  'Searching 40M+ papers across 5 databases...',
  'Cross-referencing sources with PULSE...',
  'Synthesizing results...',
  'Preparing your response...',
];

export default function ThinkingIndicator() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setStep(1), 800),
      setTimeout(() => setStep(2), 2000),
      setTimeout(() => setStep(3), 3500),
      setTimeout(() => setStep(4), 5000),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6 max-w-lg shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        <div className="w-8 h-8 rounded-full flex items-center justify-center animate-pulse-glow" style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C12 2 14.5 8.5 15.5 9.5C16.5 10.5 22 12 22 12C22 12 16.5 13.5 15.5 14.5C14.5 15.5 12 22 12 22C12 22 9.5 15.5 8.5 14.5C7.5 13.5 2 12 2 12C2 12 7.5 10.5 8.5 9.5C9.5 8.5 12 2 12 2Z" />
          </svg>
        </div>
        <span className="text-sm font-semibold text-lena-600">LENA is thinking...</span>
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {STEPS.map((text, i) => (
          <div key={i} className="flex items-center gap-2.5 py-0.5">
            {i < step ? (
              <svg className="w-4 h-4 text-green-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            ) : i === step ? (
              <div className="w-4 h-4 border-2 border-lena-500 border-t-transparent rounded-full flex-shrink-0" style={{ animation: 'spin 0.8s linear infinite' }} />
            ) : (
              <div className="w-4 h-4 rounded-full border-2 border-slate-200 flex-shrink-0" />
            )}
            <span className={`text-sm ${i < step ? 'text-slate-400' : i === step ? 'text-lena-600 font-medium' : 'text-slate-300'}`}>
              {text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
