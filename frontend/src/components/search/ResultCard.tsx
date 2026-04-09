'use client';

import { ValidatedResult } from '@/lib/api';

interface ResultCardProps {
  result: ValidatedResult;
  isEdgeCase?: boolean;
  compact?: boolean;
}

const SOURCE_COLORS: Record<string, { badge: string; label: string }> = {
  pubmed: { badge: 'bg-blue-50 text-blue-700 border-blue-200', label: 'PubMed' },
  clinical_trials: { badge: 'bg-green-50 text-green-700 border-green-200', label: 'ClinicalTrials.gov' },
  cochrane: { badge: 'bg-purple-50 text-purple-700 border-purple-200', label: 'Cochrane' },
  who_iris: { badge: 'bg-red-50 text-red-700 border-red-200', label: 'WHO' },
  cdc: { badge: 'bg-orange-50 text-orange-700 border-orange-200', label: 'CDC' },
};

export default function ResultCard({ result, isEdgeCase = false, compact = false }: ResultCardProps) {
  const sourceConfig = SOURCE_COLORS[result.source] || {
    badge: 'bg-slate-50 text-slate-700 border-slate-200',
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
      className={`block p-5 rounded-xl border-2 transition-all hover:shadow-md
                   ${
                     isEdgeCase
                       ? 'bg-yellow-50 border-yellow-200 hover:bg-yellow-100 hover:border-yellow-300'
                       : 'bg-white border-slate-200 hover:bg-slate-50 hover:border-lena-300'
                   }`}
    >
      {/* Header with Badge and Title */}
      <div className="space-y-3">
        <div className="flex items-start gap-3">
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${sourceConfig.badge} whitespace-nowrap`}>
            {sourceConfig.label}
          </span>
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
      <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-slate-600 border-t border-slate-100 pt-4">
        {result.year && (
          <div className="flex items-center gap-1">
            <span className="font-medium text-slate-700">{result.year}</span>
            <span className="text-slate-400">•</span>
          </div>
        )}

        {result.doi && (
          <div className="flex items-center gap-1">
            <span className="font-mono text-xs text-lena-600">{result.doi}</span>
          </div>
        )}

        {/* Relevance Score */}
        <div className="flex items-center gap-2 ml-auto">
          <span className="text-xs font-medium text-slate-500">Relevance</span>
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
          <p className="text-xs font-medium text-slate-600">Keywords</p>
          <div className="flex flex-wrap gap-2">
            {result.keywords.map((keyword) => (
              <span
                key={keyword}
                className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-slate-100 rounded-full border border-slate-200 hover:border-slate-300 transition-colors"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}
    </a>
  );
}
