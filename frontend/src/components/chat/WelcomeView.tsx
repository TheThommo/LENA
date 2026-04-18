'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

interface WelcomeViewProps {
  persona: string;
  onPromptClick: (query: string) => void;
}

interface TrendingTopic {
  topic: string;
  count: number;
  trend?: 'up' | 'down' | 'flat';
  is_fallback?: boolean;
}

function formatPersonaLabel(persona: string): string {
  return persona
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function WelcomeView({ persona, onPromptClick }: WelcomeViewProps) {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [trending, setTrending] = useState<TrendingTopic[]>([]);
  const [suggestionsSource, setSuggestionsSource] = useState<string>('loading');
  const [trendingSource, setTrendingSource] = useState<string>('loading');

  // Fetch suggestions based on persona
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/discover/suggestions?persona=${encodeURIComponent(persona)}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setSuggestions(data.suggestions || []);
          setSuggestionsSource(data.source || 'curated');
        }
      } catch {
        if (!cancelled) {
          setSuggestions([]);
          setSuggestionsSource('error');
        }
      }
    })();
    return () => { cancelled = true; };
  }, [persona]);

  // Fetch trending topics
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/discover/trending`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (!cancelled) {
          setTrending(data.trending || []);
          setTrendingSource(data.source || 'curated');
        }
      } catch {
        if (!cancelled) {
          setTrending([]);
          setTrendingSource('error');
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="flex flex-col items-center justify-center max-w-2xl mx-auto px-4 py-16">
      {/* LENA avatar */}
      <Image
        src={branding.avatarSrc}
        alt={branding.name}
        width={72}
        height={72}
        className="rounded-2xl mb-6 shadow-lg shadow-[#1B6B93]/20"
      />

      {/* Heading */}
      <h1 className="text-3xl font-bold text-slate-900 text-center mb-3">
        What would you like to research?
      </h1>
      <p className="text-slate-500 text-center mb-10 max-w-lg leading-relaxed">
        Search 250M+ medical papers across 6 databases in seconds, cross-referenced by AI for accuracy.
      </p>

      {/* Suggested prompts */}
      {suggestions.length > 0 && (
        <div className="w-full mb-10">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {suggestionsSource === 'search_data'
                ? `Popular with ${formatPersonaLabel(persona)}s`
                : `Suggested for ${formatPersonaLabel(persona)}`}
            </span>
          </div>

          <div className="space-y-3">
            {suggestions.map((prompt) => (
              <button
                key={prompt}
                onClick={() => onPromptClick(prompt)}
                className="w-full flex items-center gap-3 p-4 text-left rounded-xl border border-slate-200 bg-white hover:border-[#1B6B93]/30 hover:bg-[#1B6B93]/5 hover:shadow-sm transition-all group"
              >
                <div className="w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-[#1B6B93]/10 flex items-center justify-center flex-shrink-0 transition-colors">
                  <svg className="w-4 h-4 text-slate-400 group-hover:text-[#1B6B93]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <span className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors">
                  {prompt}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Trending topics */}
      {trending.length > 0 && (
        <div className="w-full">
          <div className="flex items-center gap-2 mb-4">
            <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              {trendingSource === 'search_data' ? 'Trending this week' : 'Popular research topics'}
            </span>
          </div>

          <div className="flex flex-wrap gap-2">
            {trending.map(({ topic, count, trend, is_fallback }) => (
              <button
                key={topic}
                onClick={() => onPromptClick(topic)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-slate-200 bg-white hover:border-[#1B6B93]/30 hover:bg-[#1B6B93]/5 transition-all group"
              >
                <span className="text-sm text-slate-700 group-hover:text-slate-900">{topic}</span>
                {!is_fallback && count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-slate-500 bg-slate-100 rounded-full group-hover:bg-[#1B6B93]/10 group-hover:text-[#1B6B93]">
                    {count}
                    {trend === 'up' && (
                      <svg className="w-3 h-3 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                      </svg>
                    )}
                    {trend === 'down' && (
                      <svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                      </svg>
                    )}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
