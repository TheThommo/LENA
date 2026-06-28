/** Human-readable labels for PULSE engine fields shown in the UI. */

export const PULSE_STATUS_LABELS: Record<string, string> = {
  validated: 'Strong agreement',
  insufficient_validation: 'Limited agreement',
  pending: 'Awaiting data',
  edge_case: 'Mixed signals',
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

/** Resolve PULSE % for display — avoids rounding real scores down to 0. */
export function resolvePulseConfidencePercent(report: {
  confidence_ratio?: number;
  confidence_breakdown?: { ratio?: number };
  validated_count?: number;
  edge_case_count?: number;
}): number {
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

/** Human-readable status — never "Awaiting data" when papers were returned. */
export function resolvePulseStatusLabel(report: {
  status: string;
  validated_count?: number;
  edge_case_count?: number;
}): string {
  const papers = (report.validated_count ?? 0) + (report.edge_case_count ?? 0);
  if (papers > 0 && report.status === 'pending') {
    return PULSE_STATUS_LABELS.insufficient_validation;
  }
  return PULSE_STATUS_LABELS[report.status] || report.status.replace(/_/g, ' ');
}
