'use client';

import { useState, useRef, useEffect } from 'react';
import { useSession, PERSONAS, PersonaId } from '@/contexts/SessionContext';

export default function PersonaSelector() {
  const { session, setPersona } = useSession();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const current = PERSONAS.find(p => p.id === session.persona) || PERSONAS[7];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-200 rounded-lg bg-white
                   hover:border-lena-300 text-xs text-slate-600 transition-all duration-200"
      >
        <span>{current.icon}</span>
        <span>{current.label}</span>
        <svg className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 bg-white border border-slate-200 rounded-xl p-1.5
                        min-w-[180px] shadow-lg z-50">
          <div className="text-[10px] text-slate-400 px-2.5 py-1.5 font-semibold uppercase tracking-wider">
            I am a...
          </div>
          {PERSONAS.map(p => (
            <button
              key={p.id}
              onClick={() => { setPersona(p.id); setOpen(false); }}
              className={`flex items-center gap-2 w-full px-2.5 py-2 rounded-lg text-xs transition-all duration-150 ${
                p.id === session.persona
                  ? 'bg-lena-50 text-lena-700 font-medium'
                  : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
