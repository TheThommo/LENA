import type { SearchResponse, ValidatedResult } from '@/lib/api';

const SOURCE_LABELS: Record<string, string> = {
  pubmed: 'PubMed',
  clinical_trials: 'ClinicalTrials.gov',
  cochrane: 'Cochrane',
  who_iris: 'WHO IRIS',
  cdc: 'CDC',
  openalex: 'OpenAlex',
  ods_dsld: 'NIH DSLD',
  openfda: 'openFDA',
};

export interface ResearchSharePayload {
  /** Full plain-text brief for copy, email, WhatsApp */
  fullText: string;
  /** Short teaser for X / LinkedIn quote params */
  socialTeaser: string;
  emailSubject: string;
  shareUrl: string;
}

function sourceLabel(source: string): string {
  return SOURCE_LABELS[source]
    || source.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/** Strip markdown to readable plain text for sharing outside the app. */
export function markdownToPlainText(markdown: string): string {
  return markdown
    .replace(/##\s*Suggested Follow[- ]?Ups?[\s\S]*$/i, '')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/\[(.+?)\]\((.+?)\)/g, '$1 ($2)')
    .replace(/^\s*[-*]\s+/gm, '• ')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function formatSourceLine(result: ValidatedResult, index: number): string {
  const label = sourceLabel(result.source);
  const year = result.year ? `, ${result.year}` : '';
  const line = `${index}. ${result.title} (${label}${year})`;
  return result.url ? `${line}\n   ${result.url}` : line;
}

function firstSentence(text: string, maxLen = 160): string {
  const trimmed = text.trim();
  if (!trimmed) return '';
  const match = trimmed.match(/^[^.!?]+[.!?]/);
  const sentence = match ? match[0].trim() : trimmed;
  if (sentence.length <= maxLen) return sentence;
  return `${sentence.slice(0, maxLen - 1).trim()}…`;
}

function resolveSummaryText(response: SearchResponse, content: string): string {
  if (response.guardrail_triggered) {
    return response.guardrail_message || content;
  }
  const raw = response.llm_summary || content;
  return markdownToPlainText(raw);
}

function buildEvidenceSection(response: SearchResponse): string[] {
  const lines: string[] = [];
  const pr = response.pulse_report;
  if (!pr) return lines;

  const confidence = Math.round((pr.confidence_ratio || 0) * 100);
  const dbCount = response.sources_queried?.length || 0;

  lines.push('Evidence snapshot');
  lines.push(`• PULSE confidence: ${confidence}%`);
  lines.push(
    `• ${response.total_results} result${response.total_results === 1 ? '' : 's'}`
    + (dbCount ? ` across ${dbCount} database${dbCount === 1 ? '' : 's'}` : ''),
  );
  if (pr.status) {
    lines.push(`• Status: ${pr.status.replace(/_/g, ' ')}`);
  }
  if (pr.consensus_summary) {
    lines.push(`• Key finding: ${pr.consensus_summary}`);
  }
  return lines;
}

function buildSourcesSection(response: SearchResponse, maxSources = 5): string[] {
  const results = response.pulse_report?.validated_results || [];
  if (results.length === 0) return [];

  const top = [...results]
    .sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0))
    .slice(0, maxSources);

  return [
    'Top sources',
    ...top.map((r, i) => formatSourceLine(r, i + 1)),
  ];
}

/**
 * Build shareable research brief text from a chat bubble + search response.
 * Includes summary content, evidence snapshot, top citations, disclaimer, and LENA URL.
 */
export function buildResearchSharePayload(options: {
  response: SearchResponse;
  content: string;
  shareUrl?: string;
  maxSources?: number;
}): ResearchSharePayload {
  const { response, content, maxSources = 5 } = options;
  const shareUrl = options.shareUrl
    || (typeof window !== 'undefined' ? window.location.origin : 'https://lena-app.up.railway.app');

  const query = response.query?.trim() || 'Research question';
  const summary = resolveSummaryText(response, content);
  const sections: string[] = [
    'LENA Research Brief',
    '━━━━━━━━━━━━━━━━━━━━',
    '',
    'Question',
    query,
    '',
  ];

  if (summary) {
    sections.push('Summary', summary, '');
  }

  const evidence = buildEvidenceSection(response);
  if (evidence.length > 0) {
    sections.push(...evidence, '');
  }

  const sources = buildSourcesSection(response, maxSources);
  if (sources.length > 0) {
    sections.push(...sources, '');
  }

  sections.push(
    '—',
    'Research evidence, not medical advice. Consult a qualified healthcare provider for personal decisions.',
    '',
    'Explore more on LENA:',
    shareUrl,
  );

  const fullText = sections.join('\n').trim();
  const teaserBase = summary || response.pulse_report?.consensus_summary || query;
  const socialTeaser = `LENA research: "${query}" — ${firstSentence(teaserBase)}`;
  const shortQuery = query.length > 80 ? `${query.slice(0, 77)}…` : query;
  const emailSubject = `LENA research: ${shortQuery}`;

  return { fullText, socialTeaser, emailSubject, shareUrl };
}
