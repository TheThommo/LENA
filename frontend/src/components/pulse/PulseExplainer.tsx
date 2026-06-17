'use client';

import { useMemo, useState } from 'react';
import type { PulseReport } from '@/lib/api';
import { formatSourceName, formatStudyType, PULSE_STATUS_LABELS } from '@/lib/pulseLabels';

interface PulseExplainerProps {
  report: PulseReport;
  sourcesQueried?: string[];
  sourcesFailed?: Record<string, string>;
  compact?: boolean;
}

function ConfidenceRing({ percent, size = 88 }: { percent: number; size?: number }) {
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const color =
    percent >= 70 ? '#10B981' : percent >= 45 ? '#136B7A' : percent >= 25 ? '#F59E0B' : '#94A3B8';

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(15,23,42,0.06)"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-700 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-semibold text-slate-900 tabular-nums tracking-tight">{percent}</span>
        <span className="text-[9px] font-medium text-slate-400 uppercase tracking-wider">PULSE</span>
      </div>
    </div>
  );
}

function MetricTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-2xl bg-white/80 backdrop-blur-sm border border-slate-200/60 px-3 py-2.5 min-w-0">
      <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide truncate">{label}</p>
      <p className="text-lg font-semibold text-slate-900 tabular-nums leading-tight mt-0.5">{value}</p>
      {sub && <p className="text-[10px] text-slate-500 mt-0.5 truncate">{sub}</p>}
    </div>
  );
}

function BreakdownBar({ label, weight, value, detail }: { label: string; weight: string; value: number; detail: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-xs">
        <span className="text-slate-600 font-medium">{label}</span>
        <span className="text-slate-400 tabular-nums">{weight} · {pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-lena-400 to-lena-600 transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[10px] text-slate-400 leading-snug">{detail}</p>
    </div>
  );
}

export default function PulseExplainer({
  report,
  sourcesQueried = [],
  sourcesFailed = {},
  compact = false,
}: PulseExplainerProps) {
  const [expanded, setExpanded] = useState(!compact);
  const [showMethodology, setShowMethodology] = useState(false);

  const confidencePct = Math.round((report.confidence_ratio || 0) * 100);
  const attempted = report.sources_attempted ?? report.source_count;
  const failed = report.sources_failed ?? 0;
  const responded = report.source_count;

  const strongestEvidence = useMemo(() => {
    const order = ['systematic_review', 'meta_analysis', 'rct', 'cohort', 'observational'];
    for (const t of order) {
      const found = report.source_agreements?.some(sa => sa.study_types?.includes(t));
      if (found) return formatStudyType(t);
    }
    return null;
  }, [report.source_agreements]);

  const bd = report.confidence_breakdown;

  const whyNotHigher = useMemo(() => {
    const reasons: string[] = [];
    if (failed > 0) {
      reasons.push(`${failed} database${failed === 1 ? '' : 's'} returned no results for this query`);
    }
    if ((report.total_cross_validations || 0) === 0) {
      reasons.push('No findings were corroborated across independent databases yet');
    }
    if (bd && bd.source_coverage < 0.5) {
      reasons.push('Less than half of queried sources returned usable papers');
    }
    if (bd && bd.edge_case_penalty > 0.1) {
      reasons.push('Some papers sit outside the main consensus themes');
    }
    if ((report.total_contradictions ?? 0) > 0) {
      reasons.push(`${report.total_contradictions} directly opposing claim(s) detected`);
    }
    return reasons.slice(0, 4);
  }, [report, failed, bd]);
  const statusLabel = PULSE_STATUS_LABELS[report.status] || report.status.replace(/_/g, ' ');

  const statusTone =
    report.status === 'validated'
      ? 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20'
      : report.status === 'insufficient_validation'
        ? 'bg-amber-500/10 text-amber-800 ring-amber-500/20'
        : 'bg-slate-500/10 text-slate-600 ring-slate-500/20';

  return (
    <div className="rounded-3xl border border-slate-200/70 bg-gradient-to-br from-white via-slate-50/50 to-lena-50/30 shadow-soft overflow-hidden">
      {/* Header */}
      <button
        type="button"
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-4 p-4 sm:p-5 text-left hover:bg-white/40 transition-colors"
      >
        <ConfidenceRing percent={confidencePct} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-slate-900 tracking-tight">How PULSE scored this</span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ${statusTone}`}>
              {statusLabel}
            </span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed line-clamp-2">
            {report.consensus_summary || 'Cross-database validation of published literature claims.'}
          </p>
          <p className="text-[10px] text-lena-600 font-medium mt-1.5">
            {expanded ? 'Tap to collapse' : 'Tap to see full breakdown'}
          </p>
        </div>
        <svg
          className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="px-4 sm:px-5 pb-5 space-y-5 border-t border-slate-200/50 pt-4">
          {/* Key metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <MetricTile
              label="Sources responded"
              value={`${responded}/${attempted}`}
              sub="databases with papers"
            />
            <MetricTile
              label="Cross-validated"
              value={report.total_cross_validations ?? 0}
              sub="matching claims"
            />
            <MetricTile
              label="Claims read"
              value={report.total_claims_extracted ?? '—'}
              sub="from abstracts"
            />
            <MetricTile
              label="Papers shown"
              value={report.validated_count ?? 0}
              sub={strongestEvidence ? `incl. ${strongestEvidence}` : 'top relevance'}
            />
          </div>

          {/* Source map */}
          <div>
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Database coverage</p>
            <div className="flex flex-wrap gap-1.5">
              {sourcesQueried.map(src => {
                const failedMsg = sourcesFailed[src];
                const respondedSrc = report.source_agreements?.some(sa => sa.source === src);
                return (
                  <span
                    key={src}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors ${
                      failedMsg
                        ? 'bg-slate-100 text-slate-400 line-through'
                        : respondedSrc
                          ? 'bg-lena-500/10 text-lena-800 ring-1 ring-lena-500/20'
                          : 'bg-slate-100 text-slate-500'
                    }`}
                    title={failedMsg || undefined}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        failedMsg ? 'bg-slate-300' : respondedSrc ? 'bg-emerald-500' : 'bg-amber-400'
                      }`}
                    />
                    {formatSourceName(src)}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Confidence breakdown */}
          {bd && (
            <div className="rounded-2xl bg-white/70 border border-slate-200/60 p-4 space-y-3">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Confidence formula
              </p>
              <BreakdownBar
                label="Finding corroboration"
                weight="45%"
                value={bd.cross_validation_density}
                detail="Share of papers whose claims matched another database"
              />
              <BreakdownBar
                label="Source coverage"
                weight="30%"
                value={bd.source_coverage}
                detail="How many databases returned results"
              />
              <BreakdownBar
                label="Theme agreement"
                weight="25%"
                value={bd.source_agreement}
                detail="Sources sharing consensus keywords"
              />
            </div>
          )}

          {/* Cross-validations */}
          {(report.cross_validations?.length ?? 0) > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Corroborated findings
              </p>
              <ul className="space-y-2">
                {report.cross_validations!.slice(0, 5).map((xv, i) => (
                  <li
                    key={i}
                    className="rounded-2xl bg-white border border-slate-200/70 px-3 py-2.5 text-xs leading-relaxed"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-semibold text-lena-700">{formatSourceName(xv.source_a)}</span>
                      <span className="text-slate-300">↔</span>
                      <span className="font-semibold text-lena-700">{formatSourceName(xv.source_b)}</span>
                      <span className="ml-auto text-[10px] text-slate-400 tabular-nums">
                        {Math.round(xv.similarity * 100)}% match
                      </span>
                    </div>
                    <p className="text-slate-600 line-clamp-2">{xv.paper_a}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Why not higher */}
          {whyNotHigher.length > 0 && confidencePct < 85 && (
            <div className="rounded-2xl bg-amber-50/60 border border-amber-200/50 px-4 py-3">
              <p className="text-[11px] font-semibold text-amber-800 uppercase tracking-wider mb-2">
                Why confidence isn&apos;t higher
              </p>
              <ul className="space-y-1">
                {whyNotHigher.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-amber-900/80">
                    <span className="text-amber-500 mt-0.5">·</span>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Themes */}
          {report.consensus_keywords.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Consensus themes</p>
              <div className="flex flex-wrap gap-1.5">
                {report.consensus_keywords.slice(0, 10).map(kw => (
                  <span
                    key={kw}
                    className="px-2 py-0.5 rounded-full bg-slate-100 text-[11px] font-medium text-slate-600"
                  >
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Methodology */}
          <div className="border-t border-slate-200/50 pt-3">
            <button
              type="button"
              onClick={() => setShowMethodology(m => !m)}
              className="text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors"
            >
              {showMethodology ? 'Hide' : 'What is PULSE?'}
            </button>
            {showMethodology && (
              <div className="mt-2 text-xs text-slate-500 leading-relaxed space-y-2">
                <p>
                  PULSE (Published Literature Source Evaluation) reads claims from paper abstracts,
                  then checks whether independent databases report the same finding — weighted by evidence
                  type (systematic reviews rank highest).
                </p>
                <p className="text-slate-400">
                  This is research evidence, not medical advice. Always consult your care team for personal decisions.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
