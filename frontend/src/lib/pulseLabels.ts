/** Human-readable labels for PULSE engine fields shown in the UI. */

export const PULSE_STATUS_LABELS: Record<string, string> = {
  validated: 'Strong agreement',
  insufficient_validation: 'Insufficient for PULSE',
  pending: 'Awaiting data',
  edge_case: 'Emerging agreement',
};

export const PULSE_LENS_LABELS: Record<string, string> = {
  all: 'All',
  pharma: 'Pharma',
  supplements: 'Supplements',
  herbal: 'Herbal',
  alternatives: 'Alt.',
  outlier: 'Outlier',
};

export const STUDY_TYPE_LABELS: Record<string, string> = {
  systematic_review: 'Systematic review',
  meta_analysis: 'Meta-analysis',
  rct: 'Randomised trial',
  cohort: 'Cohort study',
  case_control: 'Case-control',
  case_report: 'Case report',
  observational: 'Observational',
  editorial: 'Editorial / opinion',
  unknown: 'Research paper',
};

export const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  clinical_trials: 'ClinicalTrials.gov',
  cochrane: 'Cochrane',
  who_iris: 'WHO IRIS',
  cdc: 'CDC',
  openalex: 'OpenAlex',
  semantic_scholar: 'Semantic Scholar',
  europe_pmc: 'Europe PMC',
  dailymed: 'FDA DailyMed',
  ods_dsld: 'NIH DSLD',
  openfda: 'openFDA',
};

export function formatSourceName(source: string): string {
  return SOURCE_LABELS[source] || source.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export function formatStudyType(studyType: string): string {
  return STUDY_TYPE_LABELS[studyType] || studyType.replace(/_/g, ' ');
}

export function formatPulseLens(lens?: string | null): string {
  if (!lens || lens === 'all') return 'All';
  return lens
    .split('+')
    .map(part => PULSE_LENS_LABELS[part] || part)
    .join(' · ');
}

/** Resolve PULSE % for display — avoids rounding real scores down to 0. */
export function resolvePulseConfidencePercent(report: {
  confidence_ratio?: number;
  confidence_breakdown?: { ratio?: number };
  validated_count?: number;
  edge_case_count?: number;
  pulse_gate?: { passed?: boolean };
}): number {
  if (report.pulse_gate && report.pulse_gate.passed === false) {
    return 0;
  }
  const papers = (report.validated_count ?? 0) + (report.edge_case_count ?? 0);
  let ratio = report.confidence_ratio;
  if ((ratio == null || ratio === 0) && report.confidence_breakdown?.ratio != null) {
    ratio = report.confidence_breakdown.ratio;
  }
  const pct = Math.round((ratio ?? 0) * 100);
  if (papers > 0 && pct === 0 && (ratio ?? 0) >= 0.005) {
    return Math.max(1, Math.ceil((ratio ?? 0) * 100));
  }
  return pct;
}

/**
 * Human-readable status band.
 * Fine-grained copy uses the percent when status alone is coarse.
 */
export function resolvePulseStatusLabel(report: {
  status: string;
  confidence_ratio?: number;
  validated_count?: number;
  edge_case_count?: number;
  pulse_gate?: { passed?: boolean };
}): string {
  if (report.pulse_gate && report.pulse_gate.passed === false) {
    return 'Insufficient for PULSE';
  }
  const papers = (report.validated_count ?? 0) + (report.edge_case_count ?? 0);
  if (papers > 0 && report.status === 'pending') {
    return PULSE_STATUS_LABELS.insufficient_validation;
  }
  const pct = Math.round((report.confidence_ratio ?? 0) * 100);
  if (report.status === 'validated' || pct >= 80) return 'Strong agreement';
  if (pct >= 60) return 'Solid agreement';
  if (pct >= 40 || report.status === 'edge_case') return 'Emerging agreement';
  return PULSE_STATUS_LABELS[report.status] || report.status.replace(/_/g, ' ');
}

/** Ring colour bands aligned with the v2 confidence story. */
export function pulseRingColor(percent: number, gateFailed = false): string {
  if (gateFailed || percent <= 0) return '#94A3B8';
  if (percent >= 80) return '#10B981';
  if (percent >= 60) return '#136B7A';
  if (percent >= 40) return '#0E7490';
  return '#94A3B8';
}
