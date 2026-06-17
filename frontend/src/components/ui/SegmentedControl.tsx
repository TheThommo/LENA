'use client';

import React from 'react';

export interface SegmentOption<T extends string> {
  id: T;
  label: string;
  shortLabel?: string;
}

interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[];
  value: T[];
  onChange: (next: T[]) => void;
  multi?: boolean;
  className?: string;
}

/**
 * iOS-style segmented control for filters and mode selection.
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  multi = true,
  className = '',
}: SegmentedControlProps<T>) {
  const isActive = (id: T) => value.includes(id);

  const toggle = (id: T) => {
    if (id === 'all' as T) {
      onChange(['all' as T]);
      return;
    }
    if (!multi) {
      onChange([id]);
      return;
    }
    let next = value.filter(v => v !== ('all' as T));
    if (isActive(id)) {
      next = next.filter(v => v !== id);
    } else {
      next = [...next, id];
    }
    if (next.length === 0) next = ['all' as T];
    onChange(next);
  };

  return (
    <div
      className={`inline-flex p-1 rounded-2xl bg-slate-100/90 backdrop-blur-sm border border-slate-200/60 gap-0.5 overflow-x-auto max-w-full ${className}`}
      role="tablist"
    >
      {options.map(opt => {
        const active = isActive(opt.id);
        return (
          <button
            key={opt.id}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => toggle(opt.id)}
            className={`
              flex-shrink-0 px-3 py-1.5 rounded-xl text-[11px] font-semibold transition-all duration-200
              ${active
                ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200/80'
                : 'text-slate-500 hover:text-slate-700'
              }
            `}
          >
            <span className="hidden sm:inline">{opt.label}</span>
            <span className="sm:hidden">{opt.shortLabel || opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
