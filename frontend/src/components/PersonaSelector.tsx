'use client';

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useSession, PERSONAS, PersonaId } from '@/contexts/SessionContext';

interface PersonaSelectorProps {
  /** Icon-only on small screens — saves header space on mobile */
  compact?: boolean;
}

export default function PersonaSelector({ compact = false }: PersonaSelectorProps) {
  const { session, setPersona } = useSession();
  const [open, setOpen] = useState(false);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number; width: number } | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const current = PERSONAS.find(p => p.id === session.persona) || PERSONAS[7];

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  useEffect(() => {
    if (!open || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const menuWidth = Math.min(240, window.innerWidth - 16);
    const left = Math.min(Math.max(8, rect.right - menuWidth), window.innerWidth - menuWidth - 8);
    setMenuPos({ top: rect.bottom + 6, left, width: menuWidth });
  }, [open]);

  const menu = open && menuPos && typeof document !== 'undefined'
    ? createPortal(
        <div
          className="fixed bg-white border border-slate-200/80 rounded-xl p-1 shadow-xl shadow-slate-900/10 z-[9999] max-h-[min(320px,60dvh)] overflow-y-auto"
          style={{ top: menuPos.top, left: menuPos.left, width: menuPos.width }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <div className="text-[10px] text-slate-400 px-2.5 py-1.5 font-medium tracking-wider uppercase sticky top-0 bg-white">
            I am a
          </div>
          {PERSONAS.map(p => (
            <button
              key={p.id}
              onClick={() => { setPersona(p.id as PersonaId); setOpen(false); }}
              className={`flex items-center gap-2 w-full px-2.5 py-2.5 rounded-lg text-sm transition-all min-h-[44px] ${
                p.id === session.persona
                  ? 'bg-lena-50/70 text-lena-700 font-medium'
                  : 'text-slate-700 hover:bg-slate-50'
              }`}
            >
              <span>{p.icon}</span>
              <span>{p.label}</span>
            </button>
          ))}
        </div>,
        document.body,
      )
    : null;

  return (
    <div ref={ref} className="relative">
      <button
        ref={triggerRef}
        onClick={() => setOpen(!open)}
        aria-label={`Persona: ${current.label}`}
        aria-expanded={open}
        className={`flex items-center gap-1.5 border border-slate-200/70 rounded-full bg-white
                   hover:border-slate-300 hover:text-slate-900 text-xs font-medium text-slate-600 transition-all
                   ${compact ? 'touch-target justify-center px-2' : 'px-3 py-2 min-h-[44px]'}`}
      >
        <span className="text-sm leading-none">{current.icon}</span>
        {!compact && (
          <>
            <span className="hidden sm:inline">{current.label}</span>
            <svg className={`w-2.5 h-2.5 transition-transform ${open ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </>
        )}
      </button>
      {menu}
    </div>
  );
}
