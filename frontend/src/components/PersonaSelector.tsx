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
        className="flex items-center gap-1.5 px-2.5 py-1 border border-slate-200/70 rounded-full bg-white
                   hover:border-slate-300 hover:text-slate-900 text-[11px] font-medium text-slate-600 transition-all"
      >
        <span className="text-[11px]">{current.icon}</span>
        <span>{current.label}</span>
        <svg className={`w-2.5 h-2.5 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 bg-white border border-slate-200/80 rounded-lg p-1
                        min-w-[180px] shadow-xl shadow-slate-900/5 z-50">
          <div className="text-[10px] text-slate-400 px-2.5 py-1.5 font-medium tracking-wider uppercase">
            I am a
          </div>
          {PERSONAS.map(p => (
            <button
              key={p.id}
              onClick={() => { setPersona(p.id); setOpen(false); }}
              className={`flex items-center gap-2 w-full px-2.5 py-1.5 rounded-md text-[12px] transition-all ${
                p.id === session.persona
                  ? 'bg-lena-50/70 text-lena-700 font-medium'
                  : 'text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span className="text-[12px]">{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
