'use client';

import { ValidatedResult } from '@/lib/api';

interface ResultCardProps {
  result: ValidatedResult;
  isEdgeCase?: boolean;
  compact?: boolean;
}

const SOURCE_COLORS: Record<string, { badge: string; bar: string; label: string }> = {
  pubmed: { badge: 'bg-blue-50 text-blue-700 border-blue-200', bar: 'bg-blue-500', label: 'PubMed' },
  clinical_trials: { badge: 'bg-purple-50 text-purple-700 border-purple-200', bar: 'bg-purple-500', label: 'ClinicalTrials.gov' },
  cochrane: { badge: 'bg-orange-50 text-orange-700 border-orange-200', bar: 'bg-orange-500', label: 'Cochrane' },
  who_iris: { badge: 'bg-cyan-50 text-cyan-700 border-cyan-200', bar: 'bg-cyan-500', label: 'WHO IRIS' },
  cdc: { badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', bar: 'bg-emerald-500', label: 'CDC' },
};

export default function ResultCard({ result, isEdgeCase = false, compact = false }: ResultCardProps) {
  const sourceConfig = SOURCE_COLORS[result.source] || {
    badge: 'bg-slate-50 text-slate-700 border-slate-200',
    bar: 'bg-slate-500',
    label: result.source,
  };
  const relevancePercent = Math.round(result.relevance_score * 100);

  if (compact) {
    return (
      <a
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
        className={`block p-3 rounded-lg border transition-all hover:shadow-md hover:border-lena-300
                     ${
                       isEdgeCase
                         ? 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100'
                         : 'bg-white border-slate-200 hover:bg-slate-50'
                     }`}
      >
        <div className="flex items-start gap-2">
          <span className={`px-2 py-0.5 text-xs font-semibold rounded border whitespace-nowrap ${sourceConfig.badge}`}>
            {sourceConfig.label}
          </span>
          <p className="text-sm font-medium text-slate-900 line-clamp-2">{result.title}</p>
        </div>
        {result.keywords.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {result.keywords.slice(0, 2).map((keyword) => (
              <span key={keyword} className="text-xs text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                {keyword}
              </span>
            ))}
          </div>
        )}
      </a>
    );
  }

  return (
    <a
      href={result.url}
      target="_blank"
      rel="noopener noreferrer"
      className={`block rounded-xl border transition-all hover:shadow-md overflow-hidden
                   ${
                     isEdgeCase
                       ? 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100 hover:border-yellow-300'
                       : 'bg-white border-slate-200 hover:bg-slate-50 hover:border-lena-300'
                   }`}
    >
      <div className="flex">
        {/* Source color bar */}
        <div className={`w-1 flex-shrink-0 ${sourceConfig.bar}`} />
        <div className="p-5 flex-1">
      {/* Header with Badge and Title */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${sourceConfig.badge} whitespace-nowrap`}>
            {sourceConfig.label}
          </span>
          {result.year && (
            <span className="text-xs text-slate-400">{result.year}</span>
          )}
          {isEdgeCase && (
            <span className="px-2.5 py-1 text-xs font-semibold text-yellow-700 bg-yellow-100 rounded-full border border-yellow-300">
              Edge Case
            </span>
          )}
        </div>

        <h3 className="text-base font-semibold text-slate-900 leading-snug hover:text-lena-700 transition-colors">
          {result.title}
        </h3>
      </div>

      {/* Metadata Row */}
      <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-600 border-t border-slate-100 pt-3">
        {result.doi && (
          <span className="font-mono text-xs text-lena-600">{result.doi}</span>
        )}

        {/* Relevance Score */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs text-slate-400">Relevance</span>
          <div className="w-12 h-1.5 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-1.5 bg-lena-500 rounded-full"
              style={{ width: `${relevancePercent}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-slate-700">{relevancePercent}%</span>
        </div>
      </div>

      {/* Keywords */}
      {result.keywords.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex flex-wrap gap-1.5">
            {result.keywords.map((keyword) => (
              <span
                key={keyword}
                className="px-2 py-0.5 text-xs text-slate-600 bg-slate-100 rounded-full"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}
        </div>
      </div>
    </a>
  );
}
