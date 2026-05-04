'use client';

import { useState } from 'react';
import type { SupplementVerification } from '@/lib/api';

interface SupplementVerificationCardProps {
  verification: SupplementVerification;
}

const TRUST_STYLES: Record<string, { bg: string; border: string; text: string; badge: string; icon: string; label: string }> = {
  verified: {
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-800',
    badge: 'bg-emerald-500',
    icon: 'text-emerald-500',
    label: 'VERIFIED',
  },
  caution: {
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-800',
    badge: 'bg-amber-500',
    icon: 'text-amber-500',
    label: 'CAUTION',
  },
  warning: {
    bg: 'bg-orange-50',
    border: 'border-orange-200',
    text: 'text-orange-800',
    badge: 'bg-orange-500',
    icon: 'text-orange-500',
    label: 'WARNING',
  },
  alert: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-800',
    badge: 'bg-red-500',
    icon: 'text-red-500',
    label: 'ALERT',
  },
};

const STATUS_ICONS: Record<string, string> = {
  pass: 'text-emerald-500',
  strong: 'text-emerald-500',
  good: 'text-emerald-500',
  low: 'text-emerald-400',
  moderate: 'text-amber-500',
  minor: 'text-amber-400',
  caution: 'text-amber-500',
  limited: 'text-amber-600',
  fail: 'text-red-500',
  warning: 'text-orange-500',
  critical: 'text-red-600',
  none: 'text-slate-400',
};

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
    </svg>
  );
}

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
    </svg>
  );
}

export default function SupplementVerificationCard({ verification: v }: SupplementVerificationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const style = TRUST_STYLES[v.trust_level] || TRUST_STYLES.alert;

  return (
    <div className={`rounded-xl border-2 ${style.border} ${style.bg} overflow-hidden transition-all`}>
      {/* Header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:opacity-90 transition-opacity"
      >
        {/* Trust badge */}
        <div className="flex-shrink-0">
          <div className={`w-12 h-12 rounded-xl ${style.badge} flex items-center justify-center shadow-sm`}>
            {v.trust_level === 'verified' ? (
              <ShieldIcon className="w-6 h-6 text-white" />
            ) : (
              <AlertIcon className="w-6 h-6 text-white" />
            )}
          </div>
        </div>

        {/* Score + name */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-xs font-bold tracking-wider ${style.text}`}>
              LENA SUPPLEMENT {style.label}
            </span>
            <span className={`text-lg font-bold ${style.text}`}>{v.trust_score}/100</span>
          </div>
          <p className="text-sm font-medium text-slate-800 truncate mt-0.5">
            {v.supplement_name}{v.brand ? ` by ${v.brand}` : ''}
          </p>
        </div>

        {/* Expand arrow */}
        <svg
          className={`w-4 h-4 text-slate-400 transition-transform flex-shrink-0 ${expanded ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Quick stats bar — always visible */}
      <div className="px-4 pb-3 flex items-center gap-4 flex-wrap text-[11px]">
        <span className="flex items-center gap-1">
          <span className={v.dsld.registered ? 'text-emerald-500' : 'text-red-400'}>
            {v.dsld.registered ? '~' : '~'}
          </span>
          <span className="text-slate-600">
            {v.dsld.registered ? `${v.dsld.products_found} in NIH DSLD` : 'Not in DSLD'}
          </span>
        </span>
        <span className="flex items-center gap-1">
          <span className={v.fda_recalls.total === 0 ? 'text-emerald-500' : 'text-red-500'}>
            {v.fda_recalls.total === 0 ? '~' : '!'}
          </span>
          <span className="text-slate-600">
            {v.fda_recalls.total === 0 ? 'No recalls' : `${v.fda_recalls.total} recall(s)`}
          </span>
        </span>
        <span className="flex items-center gap-1">
          <span className={v.adverse_events.total === 0 ? 'text-emerald-500' : 'text-amber-500'}>
            {v.adverse_events.total === 0 ? '~' : '!'}
          </span>
          <span className="text-slate-600">
            {v.adverse_events.total === 0 ? 'No adverse events' : `${v.adverse_events.total} reports`}
          </span>
        </span>
        <span className="flex items-center gap-1 text-slate-600">
          {v.clinical_evidence.papers_found} papers
          {v.clinical_evidence.cochrane_reviews > 0 && ` (${v.clinical_evidence.cochrane_reviews} Cochrane)`}
        </span>
        {v.market_presence && v.market_presence.iherb_products_found > 0 && (
          <span className="flex items-center gap-1 text-slate-600">
            {v.market_presence.iherb_avg_rating >= 4.0 ? '★' : '☆'} {v.market_presence.iherb_avg_rating.toFixed(1)} iHerb ({v.market_presence.iherb_total_reviews} reviews)
          </span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-slate-200/60 bg-white/60 px-4 py-4 space-y-4">
          {/* Trust breakdown */}
          <div>
            <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Trust Score Breakdown
            </h4>
            <div className="space-y-2">
              {Object.entries(v.trust_breakdown).map(([key, check]) => (
                <div key={key} className="flex items-start gap-2">
                  <div className="flex-shrink-0 mt-0.5">
                    {check.status === 'pass' || check.status === 'strong' || check.status === 'good' ? (
                      <CheckIcon className={`w-3.5 h-3.5 ${STATUS_ICONS[check.status] || 'text-slate-400'}`} />
                    ) : (
                      <AlertIcon className={`w-3.5 h-3.5 ${STATUS_ICONS[check.status] || 'text-slate-400'}`} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-700">
                        {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                      </span>
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        check.points >= 20 ? 'bg-emerald-100 text-emerald-700' :
                        check.points >= 10 ? 'bg-amber-100 text-amber-700' :
                        'bg-red-100 text-red-700'
                      }`}>
                        +{check.points} pts
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 mt-0.5">{check.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* DSLD products */}
          {v.dsld.sample_products.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                NIH-Registered Products ({v.dsld.products_found})
              </h4>
              <div className="space-y-1">
                {v.dsld.sample_products.map((p, i) => (
                  <a
                    key={i}
                    href={p.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block text-xs text-slate-600 hover:text-lena-600 transition-colors truncate"
                  >
                    <span className="font-medium">{p.name}</span>
                    {p.brand && <span className="text-slate-400 ml-1">({p.brand})</span>}
                  </a>
                ))}
              </div>
            </div>
          )}

          {/* FDA Recalls */}
          {v.fda_recalls.recent.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-red-700 uppercase tracking-wider mb-2">
                FDA Recall History ({v.fda_recalls.total})
              </h4>
              <div className="space-y-2">
                {v.fda_recalls.recent.map((r, i) => (
                  <div key={i} className="bg-red-50/50 border border-red-200/60 rounded-lg p-2.5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        r.severity === 'critical' ? 'bg-red-200 text-red-800' :
                        r.severity === 'moderate' ? 'bg-orange-200 text-orange-800' :
                        'bg-amber-200 text-amber-800'
                      }`}>
                        {r.classification}
                      </span>
                      <span className="text-[10px] text-slate-400">{r.date}</span>
                      <span className="text-[10px] text-slate-500">{r.firm}</span>
                    </div>
                    <p className="text-[11px] text-slate-700 line-clamp-2">{r.reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Adverse events */}
          {v.adverse_events.total > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                FDA Adverse Event Reports
              </h4>
              <div className="grid grid-cols-4 gap-2">
                <div className="text-center">
                  <p className="text-lg font-bold text-slate-800">{v.adverse_events.total}</p>
                  <p className="text-[10px] text-slate-500">Total Reports</p>
                </div>
                <div className="text-center">
                  <p className={`text-lg font-bold ${v.adverse_events.serious > 0 ? 'text-orange-600' : 'text-slate-400'}`}>
                    {v.adverse_events.serious}
                  </p>
                  <p className="text-[10px] text-slate-500">Serious</p>
                </div>
                <div className="text-center">
                  <p className={`text-lg font-bold ${v.adverse_events.hospitalizations > 0 ? 'text-orange-600' : 'text-slate-400'}`}>
                    {v.adverse_events.hospitalizations}
                  </p>
                  <p className="text-[10px] text-slate-500">Hospitalizations</p>
                </div>
                <div className="text-center">
                  <p className={`text-lg font-bold ${v.adverse_events.deaths > 0 ? 'text-red-600' : 'text-slate-400'}`}>
                    {v.adverse_events.deaths}
                  </p>
                  <p className="text-[10px] text-slate-500">Deaths</p>
                </div>
              </div>
            </div>
          )}

          {/* Market Presence — iHerb brand data */}
          {v.market_presence && v.market_presence.iherb_products_found > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Market Presence — iHerb
              </h4>
              <div className="grid grid-cols-3 gap-2 mb-2">
                <div className="text-center">
                  <p className="text-lg font-bold text-slate-800">{v.market_presence.iherb_products_found}</p>
                  <p className="text-[10px] text-slate-500">Products</p>
                </div>
                <div className="text-center">
                  <p className={`text-lg font-bold ${v.market_presence.iherb_avg_rating >= 4.0 ? 'text-emerald-600' : v.market_presence.iherb_avg_rating >= 3.0 ? 'text-amber-600' : 'text-red-600'}`}>
                    {v.market_presence.iherb_avg_rating > 0 ? `${v.market_presence.iherb_avg_rating}★` : '—'}
                  </p>
                  <p className="text-[10px] text-slate-500">Avg Rating</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-bold text-slate-800">
                    {v.market_presence.iherb_total_reviews > 1000
                      ? `${(v.market_presence.iherb_total_reviews / 1000).toFixed(1)}k`
                      : v.market_presence.iherb_total_reviews}
                  </p>
                  <p className="text-[10px] text-slate-500">Reviews</p>
                </div>
              </div>
              {v.market_presence.iherb_top_products.length > 0 && (
                <div className="space-y-1">
                  {v.market_presence.iherb_top_products.map((p, i) => (
                    <a
                      key={i}
                      href={p.url || v.market_presence!.iherb_brand_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center justify-between text-xs text-slate-600 hover:text-lena-600 transition-colors"
                    >
                      <span className="truncate font-medium">{p.name}</span>
                      <span className="flex-shrink-0 ml-2 text-slate-400">
                        {p.rating > 0 && `${p.rating}★`}
                        {p.review_count > 0 && ` · ${p.review_count} reviews`}
                      </span>
                    </a>
                  ))}
                </div>
              )}
              <a
                href={v.market_presence.iherb_brand_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-1.5 text-[10px] text-lena-600 hover:text-lena-700 font-medium"
              >
                View on iHerb →
              </a>
            </div>
          )}

          {/* Footer */}
          <div className="pt-2 border-t border-slate-200/60">
            <p className="text-[10px] text-slate-400 leading-relaxed">
              Verified in {Math.round(v.verification_time_ms)}ms across NIH DSLD, FDA CAERS,
              FDA Enforcement, PubMed and Cochrane Library. This score is informational
              and does not constitute medical advice.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
