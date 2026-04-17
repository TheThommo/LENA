'use client';

import ResultCard from './ResultCard';
import { SearchResponse } from '@/lib/api';

interface ResultsListProps {
  response: SearchResponse | null;
  isLoading: boolean;
  error: string | null;
  compact?: boolean;
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className="p-5 rounded-xl border-2 border-slate-200 bg-white animate-pulse">
          <div className="h-4 bg-slate-200 rounded w-24 mb-3" />
          <div className="h-5 bg-slate-200 rounded w-full mb-2" />
          <div className="h-4 bg-slate-200 rounded w-5/6 mb-4" />
          <div className="flex gap-2">
            <div className="h-6 bg-slate-200 rounded-full w-16" />
            <div className="h-6 bg-slate-200 rounded-full w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ResultsList({
  response,
  isLoading,
  error,
  compact = false,
}: ResultsListProps) {
  if (isLoading) {
    return (
      <div className={compact ? '' : 'space-y-6'}>
        <LoadingSkeleton />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="p-6 rounded-xl border-2 border-red-200 bg-red-50 text-center"
      >
        <p className="text-red-700 font-medium">Search Error</p>
        <p className="text-red-600 text-sm mt-2">{error}</p>
      </div>
    );
  }

  if (!response) {
    return (
      <div className="text-center text-slate-500 py-12">
        <p className="text-base">Enter a search query to get started</p>
      </div>
    );
  }

  // Guardrail triggered - show medical advice message
  if (response.guardrail_triggered) {
    return (
      <div className="p-6 rounded-xl border-2 border-amber-200 bg-amber-50">
        <div className="flex gap-3">
          <div className="flex-shrink-0 text-xl">⚕</div>
          <div>
            <p className="font-semibold text-amber-900 mb-2">Medical Consultation Recommended</p>
            <p className="text-amber-800 text-sm leading-relaxed">
              {response.guardrail_message ||
                'Your question touches on a topic that requires professional medical judgment. Please consult with a qualified healthcare provider for personalized medical advice.'}
            </p>
            <p className="text-amber-700 text-xs mt-3">
              LENA provides research summaries, not medical advice.
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (response.total_results === 0) {
    return (
      <div className="text-center text-slate-500 py-12">
        <p className="text-base font-medium">No results found</p>
        <p className="text-sm mt-2">Try refining your search or adjusting your filters</p>
      </div>
    );
  }

  if (!response.pulse_report) {
    return null;
  }

  const validatedResults = response.pulse_report.validated_results || [];
  const edgeCases = response.pulse_report.edge_cases || [];

  return (
    <div className={`space-y-${compact ? '3' : '8'}`}>
      {/* Validated Results Section */}
      {validatedResults.length > 0 && (
        <div>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900">
              Validated Results
              <span className="ml-2 text-sm font-normal text-slate-500">
                ({validatedResults.length})
              </span>
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              These results have been cross-referenced and validated across multiple sources.
            </p>
          </div>
          <div className={`space-y-3 ${!compact && 'space-y-4'}`}>
            {validatedResults.map((result) => (
              <ResultCard
                key={`${result.source}-${result.title}`}
                result={result}
                isEdgeCase={false}
                compact={compact}
              />
            ))}
          </div>
        </div>
      )}

      {/* Edge Cases Section */}
      {edgeCases.length > 0 && (
        <div>
          <div className="mb-4 pt-6 border-t border-slate-200">
            <h2 className="text-lg font-bold text-slate-900">
              Edge Cases
              <span className="ml-2 text-sm font-normal text-slate-500">
                ({edgeCases.length})
              </span>
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              These results conflict with the consensus or come from a single source. Review with caution.
            </p>
          </div>
          <div className={`space-y-3 ${!compact && 'space-y-4'}`}>
            {edgeCases.map((result) => (
              <ResultCard
                key={`${result.source}-${result.title}`}
                result={result}
                isEdgeCase={true}
                compact={compact}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
