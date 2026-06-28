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
