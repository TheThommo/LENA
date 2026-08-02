'use client';

import { useMemo, useState } from 'react';
import type { PulseReport } from '@/lib/api';
import {
  formatPulseLens,
  formatSourceName,
  formatStudyType,
  pulseRingColor,
  resolvePulseConfidencePercent,
  resolvePulseStatusLabel,
} from '@/lib/pulseLabels';

interface PulseExplainerProps {
  report: PulseReport;
  sourcesQueried?: string[];
  sourcesFailed?: Record<string, string>;
  compact?: boolean;
}

function ConfidenceRing({
  percent,
  gateFailed,
  size = 88,
}: {
  percent: number;
  gateFailed?: boolean;
  size?: number;
}) {
  const stroke = 6;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const display = gateFailed ? 0 : percent;
  const offset = circumference - (display / 100) * circumference;
  const color = pulseRingColor(display, gateFailed);

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
        {gateFailed ? (
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wide">n/a</span>
        ) : (
          <span className="text-xl font-semibold text-slate-900 tabular-nums tracking-tight">{percent}</span>
        )}
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

  const gate = report.pulse_gate ?? report.confidence_breakdown?.gate;
  const gateFailed = gate?.passed === false;
  const confidencePct = resolvePulseConfidencePercent(report);
  const lens = formatPulseLens(report.pulse_lens ?? report.confidence_breakdown?.lens);
  const responding =
    report.responding_sources?.length ??
    report.confidence_breakdown?.responding_sources?.length ??
    report.source_count;
  const classes =
    report.source_classes ??
    report.confidence_breakdown?.source_classes ??
    [];
  const infraFailed = Object.keys(sourcesFailed || {}).length;

  const strongestEvidence = useMemo(() => {
    const order = ['systematic_review', 'meta_analysis', 'rct', 'cohort', 'observational'];
    for (const t of order) {
      const found = report.source_agreements?.some(sa => sa.study_types?.includes(t));
      if (found) return formatStudyType(t);
    }
    return null;
  }, [report.source_agreements]);

  const bd = report.confidence_breakdown;
  const justification =
    report.pulse_justification ??
    bd?.justification ??
    [];

  const statusLabel = resolvePulseStatusLabel(report);

  const statusTone =
    gateFailed || report.status === 'insufficient_validation'
      ? 'bg-slate-500/10 text-slate-600 ring-slate-500/20'
      : report.status === 'validated' || confidencePct >= 80
        ? 'bg-emerald-500/10 text-emerald-700 ring-emerald-500/20'
        : confidencePct >= 60
          ? 'bg-lena-500/10 text-lena-800 ring-lena-500/20'
          : 'bg-cyan-500/10 text-cyan-800 ring-cyan-500/20';

  return (
    <div className="rounded-3xl border border-slate-200/70 bg-gradient-to-br from-white via-slate-50/50 to-lena-50/30 shadow-soft overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-4 p-4 sm:p-5 text-left hover:bg-white/40 transition-colors"
      >
        <ConfidenceRing percent={confidencePct} gateFailed={gateFailed} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="text-sm font-semibold text-slate-900 tracking-tight">
              {gateFailed
                ? 'PULSE unavailable'
                : `PULSE ${confidencePct} · ${statusLabel}`}
            </span>
            <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ring-1 ${statusTone}`}>
              {lens}
            </span>
          </div>
          <p className="text-xs text-slate-500 leading-relaxed line-clamp-3">
            {justification[0] ||
              report.consensus_summary ||
              'Agreement quality among databases that returned evidence in this lens.'}
          </p>
          <p className="text-[10px] text-lena-600 font-medium mt-1.5">
            {expanded ? 'Tap to collapse' : 'Tap to see why this score'}
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
          {/* Always-on justification */}
          <div className="rounded-2xl bg-white/80 border border-slate-200/60 px-4 py-3">
            <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
              Why this score
            </p>
            <ul className="space-y-1.5">
              {(justification.length > 0
                ? justification
                : [gate?.reason || 'Cross-database agreement within the active research lens.']
              ).map((line, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-slate-600 leading-relaxed">
                  <span className="text-lena-500 mt-0.5">·</span>
                  {line}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            <MetricTile
              label="Responding DBs"
              value={responding}
              sub="scored universe"
            />
            <MetricTile
              label="Source classes"
              value={classes.length || '—'}
              sub={classes.join(' · ') || '—'}
            />
            <MetricTile
              label="Corroborated"
              value={report.total_cross_validations ?? 0}
              sub="matching claims"
            />
            <MetricTile
              label="Papers shown"
              value={(report.validated_count ?? 0) + (report.edge_case_count ?? 0)}
              sub={strongestEvidence ? `incl. ${strongestEvidence}` : 'top relevance'}
            />
          </div>

          {sourcesQueried.length > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Databases queried
              </p>
              <div className="flex flex-wrap gap-1.5">
                {sourcesQueried.map(src => {
                  const failedMsg = sourcesFailed[src];
                  const respondedSrc =
                    report.responding_sources?.includes(src) ||
                    report.source_agreements?.some(sa => sa.source === src);
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
                      title={
                        failedMsg
                          ? `Infrastructure issue: ${failedMsg}`
                          : respondedSrc
                            ? 'Included in PULSE score'
                            : 'No relevant results for this lens (not scored against)'
                      }
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${
                          failedMsg ? 'bg-rose-400' : respondedSrc ? 'bg-emerald-500' : 'bg-slate-300'
                        }`}
                      />
                      {formatSourceName(src)}
                    </span>
                  );
                })}
              </div>
              {infraFailed > 0 && (
                <p className="text-[10px] text-slate-400 mt-2">
                  {infraFailed} database{infraFailed === 1 ? '' : 's'} hit an infrastructure error
                  — shown for transparency, not used to lower confidence.
                </p>
              )}
            </div>
          )}

          {!gateFailed && bd && (
            <div className="rounded-2xl bg-white/70 border border-slate-200/60 p-4 space-y-3">
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Confidence formula
              </p>
              <BreakdownBar
                label="Claim corroboration"
                weight={`${Math.round((bd.weights?.claim_corroboration ?? bd.weights?.cross_validation_density ?? 0.55) * 100)}%`}
                value={bd.claim_corroboration ?? bd.cross_validation_density ?? 0}
                detail="Share of papers whose claims matched another independent work"
              />
              <BreakdownBar
                label="Source-class diversity"
                weight={`${Math.round((bd.weights?.source_class_diversity ?? bd.weights?.source_coverage ?? 0.25) * 100)}%`}
                value={bd.source_class_diversity ?? 0}
                detail="Independent classes (literature / trial / label) that contributed"
              />
              <BreakdownBar
                label="Theme agreement"
                weight={`${Math.round((bd.weights?.theme_agreement ?? bd.weights?.source_agreement ?? 0.20) * 100)}%`}
                value={bd.theme_agreement ?? bd.source_agreement ?? 0}
                detail="Responding sources sharing consensus themes"
              />
              {(bd.contradiction_penalty ?? 0) > 0 && (
                <p className="text-[10px] text-slate-500 pt-1">
                  Contradiction / supersession discount applied:{' '}
                  {Math.round((bd.contradiction_penalty ?? 0) * 100)}%
                </p>
              )}
            </div>
          )}

          {(report.reconciliation_edge_cases?.length ?? 0) > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Edge cases
              </p>
              <ul className="space-y-2">
                {report.reconciliation_edge_cases!.slice(0, 5).map((edge, i) => (
                  <li
                    key={edge.group_id || i}
                    className="rounded-2xl bg-white border border-amber-200/70 px-3 py-2.5 text-xs leading-relaxed"
                  >
                    <p className="font-semibold text-amber-800 mb-1">
                      {edge.divergence_type || edge.classification}: {edge.reason}
                    </p>
                    {(edge.claims || []).slice(0, 2).map((c, j) => (
                      <p key={c.claim_id || j} className="text-slate-600 mt-1">
                        <span className="text-slate-400">
                          [{(c.source_ids || []).map(formatSourceName).join(', ')}
                          {c.year ? `, ${c.year}` : ''}]
                        </span>{' '}
                        {c.span || c.text}
                      </p>
                    ))}
                  </li>
                ))}
              </ul>
            </div>
          )}

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

          {report.consensus_keywords.filter(kw => kw.includes(' ') || kw.includes('-')).length > 0 && (
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Consensus themes</p>
              <div className="flex flex-wrap gap-1.5">
                {report.consensus_keywords
                  .filter(kw => kw.includes(' ') || kw.includes('-'))
                  .slice(0, 10)
                  .map(kw => (
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
                  PULSE (Published Literature Source Evaluation) scores how strongly independent
                  findings agree inside the evidence that actually returned for your selected lens
                  (All, Pharma, Supplements…). Empty specialty databases do not lower the score.
                </p>
                <p>
                  Formula: 55% claim corroboration · 25% source-class diversity · 20% theme agreement,
                  with an explicit discount for contradictions or supersession. Below the evidence
                  gate, PULSE reports &quot;insufficient&quot; instead of a misleading low percentage.
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
