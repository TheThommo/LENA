'use client';

import { useMemo } from 'react';
import type { SearchResponse } from '@/lib/api';

interface InsightsPanelProps {
  responses: SearchResponse[];
  isOpen: boolean;
  onClose: () => void;
}

const SOURCE_COLORS: Record<string, string> = {
  PubMed: '#2563EB',
  'ClinicalTrials.gov': '#7C3AED',
  Cochrane: '#EA580C',
  'WHO IRIS': '#0891B2',
  CDC: '#059669',
};

export default function InsightsPanel({ responses, isOpen, onClose }: InsightsPanelProps) {
  const insights = useMemo(() => {
    if (responses.length === 0) {
      return {
        sourceDistribution: {} as Record<string, number>,
        yearDistribution: {} as Record<number, number>,
        avgConfidence: 0,
        totalResults: 0,
        sourcesUsed: 0,
        avgResponseTime: 0,
      };
    }

    // Source distribution: count how many times each source was queried
    const sourceDistribution: Record<string, number> = {};
    responses.forEach((r) => {
      r.sources_queried.forEach((source) => {
        sourceDistribution[source] = (sourceDistribution[source] || 0) + 1;
      });
    });

    // Publication years from pulse report validated results
    const yearDistribution: Record<number, number> = {};
    for (let y = 2020; y <= 2025; y++) {
      yearDistribution[y] = 0;
    }
    responses.forEach((r) => {
      if (r.pulse_report?.validated_results) {
        r.pulse_report.validated_results.forEach((vr) => {
          const year = vr.year;
          if (year && year >= 2020 && year <= 2025) {
            yearDistribution[year] = (yearDistribution[year] || 0) + 1;
          }
        });
      }
    });

    // Average confidence
    const confidences = responses
      .filter((r) => r.pulse_report?.confidence_ratio !== undefined)
      .map((r) => r.pulse_report.confidence_ratio);
    const avgConfidence =
      confidences.length > 0
        ? confidences.reduce((a, b) => a + b, 0) / confidences.length
        : 0;

    // Total results
    const totalResults = responses.reduce((sum, r) => sum + r.total_results, 0);

    // Unique sources used
    const allSources = new Set<string>();
    responses.forEach((r) => r.sources_queried.forEach((s) => allSources.add(s)));

    // Average response time
    const avgResponseTime =
      responses.length > 0
        ? responses.reduce((sum, r) => sum + r.response_time_ms, 0) / responses.length
        : 0;

    return {
      sourceDistribution,
      yearDistribution,
      avgConfidence,
      totalResults,
      sourcesUsed: allSources.size,
      avgResponseTime,
    };
  }, [responses]);

  const maxSourceCount = Math.max(...Object.values(insights.sourceDistribution), 1);
  const maxYearCount = Math.max(...Object.values(insights.yearDistribution), 1);

  const confidenceColor =
    insights.avgConfidence >= 80
      ? 'bg-green-100 text-green-800'
      : insights.avgConfidence >= 60
        ? 'bg-yellow-100 text-yellow-800'
        : insights.avgConfidence >= 40
          ? 'bg-orange-100 text-orange-800'
          : 'bg-red-100 text-red-800';

  const confidenceLabel =
    insights.avgConfidence >= 80
      ? 'High'
      : insights.avgConfidence >= 60
        ? 'Medium'
        : insights.avgConfidence >= 40
          ? 'Edge Case'
          : 'Low';

  if (!isOpen) return null;

  return (
    <aside
      className="fixed right-0 top-0 h-full w-[300px] bg-white border-l border-gray-200 shadow-xl z-40 flex flex-col overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-[#1B6B93]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h2 className="text-sm font-semibold text-gray-900">Research Insights</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close insights panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {responses.length === 0 ? (
          <p className="text-sm text-gray-500 text-center mt-8">
            Run a search to see insights here.
          </p>
        ) : (
          <>
            {/* Source Distribution */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Source Distribution
              </h3>
              <div className="space-y-2">
                {Object.entries(SOURCE_COLORS).map(([source, color]) => {
                  const count = insights.sourceDistribution[source] || 0;
                  const pct = maxSourceCount > 0 ? (count / maxSourceCount) * 100 : 0;
                  return (
                    <div key={source}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-gray-700 truncate">{source}</span>
                        <span className="text-gray-500 font-medium ml-2">{count}</span>
                      </div>
                      <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                          className="h-2 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, backgroundColor: color }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Publication Years */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Publication Years
              </h3>
              <div className="flex items-end gap-1.5 h-20">
                {Object.entries(insights.yearDistribution)
                  .sort(([a], [b]) => Number(a) - Number(b))
                  .map(([year, count]) => {
                    const pct = maxYearCount > 0 ? (count / maxYearCount) * 100 : 0;
                    return (
                      <div key={year} className="flex-1 flex flex-col items-center gap-1">
                        <div className="w-full flex items-end justify-center" style={{ height: '56px' }}>
                          <div
                            className="w-full rounded-t transition-all duration-500"
                            style={{
                              height: `${Math.max(pct, 4)}%`,
                              backgroundColor: '#1B6B93',
                              opacity: pct > 0 ? 1 : 0.3,
                            }}
                          />
                        </div>
                        <span className="text-[10px] text-gray-500">{String(year).slice(2)}</span>
                      </div>
                    );
                  })}
              </div>
            </section>

            {/* PULSE Confidence */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                PULSE Confidence
              </h3>
              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-gray-900">
                  {Math.round(insights.avgConfidence)}%
                </span>
                <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${confidenceColor}`}>
                  {confidenceLabel}
                </span>
              </div>
            </section>

            {/* Quick Stats */}
            <section>
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Quick Stats
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-[#FFFBF0] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold text-gray-900">{insights.totalResults}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5">Total Results</div>
                </div>
                <div className="bg-[#FFFBF0] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold text-gray-900">
                    {Math.round(insights.avgConfidence)}%
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">Avg PULSE %</div>
                </div>
                <div className="bg-[#FFFBF0] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold text-gray-900">{insights.sourcesUsed}</div>
                  <div className="text-[10px] text-gray-500 mt-0.5">Sources Used</div>
                </div>
                <div className="bg-[#FFFBF0] rounded-lg p-3 text-center">
                  <div className="text-lg font-bold text-gray-900">
                    {(insights.avgResponseTime / 1000).toFixed(1)}s
                  </div>
                  <div className="text-[10px] text-gray-500 mt-0.5">Response Time</div>
                </div>
              </div>
            </section>
          </>
        )}
      </div>
    </aside>
  );
}
