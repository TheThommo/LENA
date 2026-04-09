'use client';

import { useState } from 'react';
import { PulseReport } from '@/lib/api';

interface PulseReportProps {
  report: PulseReport;
  compact?: boolean;
}

export default function PulseReportComponent({ report, compact = false }: PulseReportProps) {
  const [showMethodology, setShowMethodology] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'validated':
        return { badge: 'bg-green-50 text-green-700 border-green-200', label: 'Validated' };
      case 'edge_case':
        return { badge: 'bg-yellow-50 text-yellow-700 border-yellow-200', label: 'Edge Case' };
      case 'insufficient_validation':
        return { badge: 'bg-red-50 text-red-700 border-red-200', label: 'Insufficient Validation' };
      case 'pending':
        return { badge: 'bg-slate-50 text-slate-700 border-slate-200', label: 'Pending' };
      default:
        return { badge: 'bg-slate-50 text-slate-700 border-slate-200', label: status };
    }
  };

  const statusColor = getStatusColor(report.status);
  const confidencePercent = Math.round(report.confidence_ratio * 100);

  if (compact) {
    return (
      <div className="space-y-3 p-4 bg-slate-50 rounded-lg border border-slate-200">
        <div className="flex items-center justify-between">
          <span className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${statusColor.badge}`}>
            {statusColor.label}
          </span>
          <span className="text-xs font-medium text-slate-600">
            {report.agreement_count} of {report.source_count} sources agree
          </span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-1.5">
          <div
            className="bg-lena-600 h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 bg-gradient-to-br from-slate-50 to-white rounded-2xl border border-slate-200 shadow-sm">
      {/* Header with Status and Confidence */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <span className={`px-3 py-1.5 text-sm font-semibold rounded-full border ${statusColor.badge}`}>
              {statusColor.label}
            </span>
            <span className="text-sm font-medium text-slate-600">
              {report.agreement_count} of {report.source_count} sources agree
            </span>
          </div>
          <p className="text-xs text-slate-500">{report.source_count} databases queried</p>
        </div>
      </div>

      {/* Confidence Ratio Visualization */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-slate-700">Confidence Level</span>
          <span className="text-sm font-semibold text-lena-600">{confidencePercent}%</span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2.5 overflow-hidden">
          <div
            className="bg-gradient-to-r from-lena-500 to-lena-600 h-2.5 rounded-full transition-all duration-300"
            style={{ width: `${confidencePercent}%` }}
          />
        </div>
      </div>

      {/* Consensus Summary */}
      {report.consensus_summary && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">Consensus Summary</p>
          <p className="text-sm text-slate-600 leading-relaxed">{report.consensus_summary}</p>
        </div>
      )}

      {/* Consensus Keywords */}
      {report.consensus_keywords.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">Key Findings</p>
          <div className="flex flex-wrap gap-2">
            {report.consensus_keywords.map((keyword) => (
              <span
                key={keyword}
                className="px-2.5 py-1 text-xs font-medium text-lena-700 bg-lena-50 rounded-full border border-lena-200"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Result Counts */}
      <div className="grid grid-cols-2 gap-4">
        <div className="p-3 bg-green-50 rounded-lg border border-green-200">
          <p className="text-xs font-medium text-green-600 uppercase">Validated Results</p>
          <p className="text-2xl font-bold text-green-700 mt-1">{report.validated_count}</p>
        </div>
        {report.edge_case_count > 0 && (
          <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-200">
            <p className="text-xs font-medium text-yellow-600 uppercase">Edge Cases</p>
            <p className="text-2xl font-bold text-yellow-700 mt-1">{report.edge_case_count}</p>
          </div>
        )}
      </div>

      {/* Source Breakdown */}
      <div className="space-y-3">
        <p className="text-sm font-medium text-slate-700">Source Agreement</p>
        <div className="space-y-2">
          {report.source_agreements.map((agreement) => (
            <div
              key={agreement.source}
              className="p-3 bg-white rounded-lg border border-slate-200 hover:border-slate-300 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-slate-700 capitalize">
                  {agreement.source.replace('_', ' ')}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-500">
                    {agreement.result_count} results
                  </span>
                  {agreement.is_consensus && (
                    <span className="px-1.5 py-0.5 text-xs font-semibold text-green-700 bg-green-50 rounded">
                      Consensus
                    </span>
                  )}
                </div>
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-slate-500">Overlap Score</span>
                  <span className="text-xs font-semibold text-slate-700">
                    {Math.round(agreement.overlap_score * 100)}%
                  </span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-1.5">
                  <div
                    className="bg-lena-500 h-1.5 rounded-full"
                    style={{ width: `${agreement.overlap_score * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Methodology */}
      <div className="border-t border-slate-200 pt-4">
        <button
          onClick={() => setShowMethodology(!showMethodology)}
          className="flex items-center justify-between w-full text-sm font-medium text-slate-700
                     hover:text-slate-900 transition-colors"
        >
          <span>How PULSE Validation Works</span>
          <span className={`text-slate-500 transition-transform ${showMethodology ? 'rotate-180' : ''}`}>
            ▼
          </span>
        </button>
        {showMethodology && (
          <div className="mt-3 text-sm text-slate-600 space-y-2">
            <p>
              PULSE cross-references results across multiple authoritative databases to identify consensus
              findings.
            </p>
            <ul className="list-disc list-inside space-y-1 text-xs">
              <li>Validated results appear in multiple sources or have high agreement scores</li>
              <li>Edge cases conflict with consensus or come from a single source</li>
              <li>Confidence ratio reflects the proportion of sources that agree on the findings</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
