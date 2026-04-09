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
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-lena-500 to-lena-700 flex items-center justify-center animate-pulse-glow">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
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
