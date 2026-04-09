'use client';

import { SearchResponse } from '@/lib/api';

interface SearchStatsProps {
  response: SearchResponse;
  compact?: boolean;
}

export default function SearchStats({ response, compact = false }: SearchStatsProps) {
  const personaDisplay = response.persona?.display_name || 'General';
  const responseTimeMs = response.response_time_ms;
  const responseTimeSecs = (responseTimeMs / 1000).toFixed(1);

  if (compact) {
    return (
      <div className="text-xs text-slate-600 space-y-1">
        <p>Results in {responseTimeSecs}s across {response.sources_queried.length} sources</p>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-4 sm:gap-6 p-4 bg-slate-50 rounded-lg border border-slate-200 text-sm">
      {/* Response Time */}
      <div className="flex items-center gap-2">
        <span className="text-slate-500">Response Time</span>
        <span className="font-semibold text-slate-900">{responseTimeSecs}s</span>
      </div>

      <div className="hidden sm:block w-px h-5 bg-slate-300" />

      {/* Total Results */}
      <div className="flex items-center gap-2">
        <span className="text-slate-500">Total Results</span>
        <span className="font-semibold text-slate-900">{response.total_results}</span>
      </div>

      <div className="hidden sm:block w-px h-5 bg-slate-300" />

      {/* Sources Queried */}
      <div className="flex items-center gap-2">
        <span className="text-slate-500">Sources Queried</span>
        <span className="font-semibold text-slate-900">{response.sources_queried.length}</span>
      </div>

      <div className="hidden sm:block w-px h-5 bg-slate-300" />

      {/* Detected Persona */}
      <div className="flex items-center gap-2 ml-auto sm:ml-0">
        <span className="text-slate-500">Persona</span>
        <span
          className="px-2.5 py-1 text-xs font-medium text-lena-700 bg-lena-50 rounded-full border border-lena-200"
        >
          {personaDisplay}
        </span>
      </div>
    </div>
  );
}
