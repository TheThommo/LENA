'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { branding, product } from '@/config/branding';

const STEPS = [
  { text: 'Parsing clinical query & detecting persona...', detail: 'NLP analysis' },
  { text: `Searching ${product.paperCount} papers across ${product.sourceCount} databases...`, detail: product.sourceNames.join(' \u00B7 ') },
  { text: 'Running PULSE cross-reference validation...', detail: 'Claim matching \u00B7 Source consensus \u00B7 Evidence hierarchy' },
  { text: 'Scoring evidence & ranking by relevance...', detail: 'Systematic reviews weighted \u00B7 Retraction check' },
  { text: 'Generating intelligent summary with AI...', detail: 'Persona-aware \u00B7 Structured markdown' },
];

export default function ThinkingIndicator() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timers = [
      setTimeout(() => setStep(1), 900),
      setTimeout(() => setStep(2), 2200),
      setTimeout(() => setStep(3), 3800),
      setTimeout(() => setStep(4), 5500),
    ];
    return () => timers.forEach(clearTimeout);
  }, []);

  const progress = Math.min(((step + 1) / STEPS.length) * 100, 100);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 sm:p-6 max-w-lg shadow-sm">
      {/* Header */}
      <div className="flex items-center gap-3 mb-1">
        <div className="relative">
          <Image
            src={branding.avatarSrc}
            alt={branding.name}
            width={36}
            height={36}
            className="rounded-full"
          />
          <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-400 border-2 border-white rounded-full" />
        </div>
        <div>
          <span className="text-sm font-bold text-slate-800">LENA is analysing...</span>
          <p className="text-[11px] text-slate-400 leading-tight">Evidence pipeline active</p>
        </div>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 bg-slate-100 rounded-full mt-3 mb-4 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${progress}%`,
            background: 'linear-gradient(90deg, #1B6B93, #2A8AB5)',
          }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-2.5">
        {STEPS.map(({ text, detail }, i) => (
          <div key={i} className={`flex items-start gap-2.5 transition-all duration-300 ${i > step ? 'opacity-40' : ''}`}>
            {i < step ? (
              <div className="w-5 h-5 rounded-full bg-emerald-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                <svg className="w-3 h-3 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
            ) : i === step ? (
              <div className="w-5 h-5 rounded-full bg-lena-50 flex items-center justify-center flex-shrink-0 mt-0.5">
                <div className="w-3 h-3 border-2 border-lena-500 border-t-transparent rounded-full" style={{ animation: 'spin 0.8s linear infinite' }} />
              </div>
            ) : (
              <div className="w-5 h-5 rounded-full border border-slate-200 flex-shrink-0 mt-0.5" />
            )}
            <div className="min-w-0">
              <span className={`text-sm leading-snug block ${
                i < step ? 'text-slate-500' : i === step ? 'text-slate-800 font-semibold' : 'text-slate-400'
              }`}>
                {text}
              </span>
              {i <= step && (
                <span className="text-[10px] text-slate-400 leading-tight block mt-0.5">
                  {detail}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
