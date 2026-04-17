'use client';

import { useMemo, useState, useCallback, useEffect } from 'react';
import type { SearchResponse, ValidatedResult, SourceAgreement } from '@/lib/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ResearchPanelProps {
  messages: { type: 'user' | 'assistant'; content: string; response?: SearchResponse; timestamp: Date }[];
  persona: string;
  onClose: () => void;
}

interface CitationEntry {
  index: number;
  source: string;
  title: string;
  url: string;
  doi: string | null;
  year: number;
  relevanceScore: number;
  keywords: string[];
  query: string;
  evidenceLevel: EvidenceLevel;
}

type EvidenceLevel = 'I' | 'II' | 'III' | 'IV' | 'V';

type CitationFilterMode = 'all' | 'starred' | string; // string = source key or evidence level
type CitationSortMode = 'relevance' | 'year';
type ActiveSection = 'overview' | 'agreement' | 'references' | 'gaps' | 'export';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SOURCE_META: Record<string, { color: string; label: string }> = {
  pubmed:          { color: '#2563EB', label: 'PubMed' },
  clinical_trials: { color: '#7C3AED', label: 'ClinicalTrials.gov' },
  cochrane:        { color: '#EA580C', label: 'Cochrane' },
  who_iris:        { color: '#0891B2', label: 'WHO IRIS' },
  cdc:             { color: '#059669', label: 'CDC' },
  openalex:        { color: '#DC2626', label: 'OpenAlex' },
};

const EVIDENCE_LEVEL_MAP: Record<string, EvidenceLevel> = {
  cochrane:        'I',
  who_iris:        'I',
  clinical_trials: 'II',
  cdc:             'II',
  pubmed:          'III',
  openalex:        'III',
};

const EVIDENCE_LEVEL_LABELS: Record<EvidenceLevel, string> = {
  'I':   'Level I -- Systematic Reviews & Guidelines',
  'II':  'Level II -- RCTs & Controlled Trials',
  'III': 'Level III -- Observational Studies',
  'IV':  'Level IV -- Case Series & Reports',
  'V':   'Level V -- Expert Opinion',
};

const EVIDENCE_LEVEL_SHORT: Record<EvidenceLevel, string> = {
  'I':   'Systematic Reviews',
  'II':  'Controlled Trials',
  'III': 'Observational',
  'IV':  'Case Reports',
  'V':   'Expert Opinion',
};

const EVIDENCE_LEVEL_COLORS: Record<EvidenceLevel, { bg: string; text: string; border: string }> = {
  'I':   { bg: 'bg-emerald-50',  text: 'text-emerald-700', border: 'border-emerald-200' },
  'II':  { bg: 'bg-blue-50',     text: 'text-blue-700',    border: 'border-blue-200' },
  'III': { bg: 'bg-amber-50',    text: 'text-amber-700',   border: 'border-amber-200' },
  'IV':  { bg: 'bg-orange-50',   text: 'text-orange-700',  border: 'border-orange-200' },
  'V':   { bg: 'bg-slate-50',    text: 'text-slate-600',   border: 'border-slate-200' },
};

const PERSONA_LABELS: Record<string, string> = {
  general: 'General User',
  clinician: 'Clinician',
  medical_student: 'Medical Student',
  pharmacist: 'Pharmacist',
  researcher: 'Researcher',
  lecturer: 'Lecturer',
  physiotherapist: 'Physiotherapist',
  patient: 'Patient',
};

const SECTION_TABS: { key: ActiveSection; label: string }[] = [
  { key: 'overview',   label: 'Overview' },
  { key: 'agreement',  label: 'Agreement' },
  { key: 'references', label: 'References' },
  { key: 'gaps',       label: 'Gaps' },
  { key: 'export',     label: 'Export' },
];

const LS_KEY_STARS = 'lena_starred_citations';
const LS_KEY_NOTES = 'lena_citation_notes';
const LS_KEY_SAVED = 'lena_saved_research';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getSourceLabel(source: string): string {
  return SOURCE_META[source]?.label || source.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function getSourceColor(source: string): string {
  return SOURCE_META[source]?.color || '#64748B';
}

function formatPersona(persona: string): string {
  return PERSONA_LABELS[persona] || persona.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function inferEvidenceLevel(source: string): EvidenceLevel {
  return EVIDENCE_LEVEL_MAP[source] || 'IV';
}

function highestEvidenceLevel(levels: EvidenceLevel[]): EvidenceLevel {
  const order: EvidenceLevel[] = ['I', 'II', 'III', 'IV', 'V'];
  let best = 4;
  for (const l of levels) {
    const idx = order.indexOf(l);
    if (idx < best) best = idx;
  }
  return order[best];
}

function confidenceInterpretation(score: number): string {
  if (score >= 90) return 'Strong cross-source consensus. Findings are well-supported across multiple high-quality databases and suitable for informing clinical reasoning.';
  if (score >= 75) return 'Good agreement across sources. Evidence is converging, though some databases may show minor variations in emphasis or scope.';
  if (score >= 60) return 'Moderate consensus. Sources broadly agree on key findings but notable differences exist -- consider reviewing divergent sources directly.';
  if (score >= 40) return 'Mixed evidence. Substantial disagreement between sources. Exercise caution and review contradictions before drawing conclusions.';
  if (score >= 20) return 'Limited validation. Few sources agree. The evidence base for this query is sparse or contested -- further primary research is recommended.';
  return 'Insufficient consensus. The available evidence does not converge. Treat all findings as preliminary and unvalidated.';
}

function citationKey(c: CitationEntry): string {
  return `${c.source}::${c.title}`;
}

function loadJsonFromLS<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SparklesIcon({ size = 12, className = '' }: { size?: number; className?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
      <path d="M12 2C12 2 14.5 8.5 15.5 9.5C16.5 10.5 22 12 22 12C22 12 16.5 13.5 15.5 14.5C14.5 15.5 12 22 12 22C12 22 9.5 15.5 8.5 14.5C7.5 13.5 2 12 2 12C2 12 7.5 10.5 8.5 9.5C9.5 8.5 12 2 12 2Z" />
    </svg>
  );
}

function EvidencePyramidIcon({ level, size = 20 }: { level: EvidenceLevel; size?: number }) {
  const colors = EVIDENCE_LEVEL_COLORS[level];
  // Simple layered pyramid: highlight the active tier
  const tiers: { y: number; w: number; level: EvidenceLevel }[] = [
    { y: 2,  w: 6,  level: 'I' },
    { y: 6,  w: 10, level: 'II' },
    { y: 10, w: 14, level: 'III' },
    { y: 14, w: 18, level: 'IV' },
    { y: 18, w: 22, level: 'V' },
  ];
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" className="flex-shrink-0">
      {tiers.map(t => {
        const x = (24 - t.w) / 2;
        const isActive = t.level === level;
        return (
          <rect
            key={t.level}
            x={x}
            y={t.y}
            width={t.w}
            height={3.2}
            rx={1}
            fill={isActive ? (level === 'I' ? '#059669' : level === 'II' ? '#2563EB' : level === 'III' ? '#D97706' : level === 'IV' ? '#EA580C' : '#64748B') : '#E2E8F0'}
          />
        );
      })}
    </svg>
  );
}

function EvidenceBadge({ level, compact = false }: { level: EvidenceLevel; compact?: boolean }) {
  const c = EVIDENCE_LEVEL_COLORS[level];
  return (
    <span className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border ${c.bg} ${c.text} ${c.border}`}>
      {level}
      {!compact && <span className="font-medium">{EVIDENCE_LEVEL_SHORT[level]}</span>}
    </span>
  );
}

function AgreementDot({ type }: { type: 'consensus' | 'divergent' | 'contradiction' }) {
  const cls = type === 'consensus'
    ? 'bg-emerald-500'
    : type === 'divergent'
    ? 'bg-amber-500'
    : 'bg-red-500';
  return <span className={`inline-block w-2 h-2 rounded-full ${cls} flex-shrink-0`} />;
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ResearchPanel({ messages, persona, onClose }: ResearchPanelProps) {
  const [activeSection, setActiveSection] = useState<ActiveSection>('overview');
  const [citationFilter, setCitationFilter] = useState<CitationFilterMode>('all');
  const [citationSort, setCitationSort] = useState<CitationSortMode>('relevance');
  const [starredKeys, setStarredKeys] = useState<Set<string>>(new Set());
  const [citationNotes, setCitationNotes] = useState<Record<string, string>>({});
  const [editingNoteKey, setEditingNoteKey] = useState<string | null>(null);
  const [noteInput, setNoteInput] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);
  const [savedToLibrary, setSavedToLibrary] = useState(false);

  // Load persisted stars / notes from localStorage on mount
  useEffect(() => {
    setStarredKeys(new Set(loadJsonFromLS<string[]>(LS_KEY_STARS, [])));
    setCitationNotes(loadJsonFromLS<Record<string, string>>(LS_KEY_NOTES, {}));
  }, []);

  // Persist stars
  const toggleStar = useCallback((key: string) => {
    setStarredKeys(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      try { localStorage.setItem(LS_KEY_STARS, JSON.stringify(Array.from(next))); } catch {}
      return next;
    });
  }, []);

  // Persist notes
  const saveNote = useCallback((key: string, note: string) => {
    setCitationNotes(prev => {
      const next = { ...prev };
      if (note.trim()) next[key] = note.trim();
      else delete next[key];
      try { localStorage.setItem(LS_KEY_NOTES, JSON.stringify(next)); } catch {}
      return next;
    });
    setEditingNoteKey(null);
    setNoteInput('');
  }, []);

  // ---------------------------------------------------------------------------
  // Analysis memo
  // ---------------------------------------------------------------------------

  const analysis = useMemo(() => {
    // Filter out guardrail responses (null pulse_report) so the panel
    // never crashes on .validated_results / .consensus_keywords / etc.
    const responses = messages
      .filter(m => m.response && m.response.pulse_report)
      .map(m => m.response!);
    const userQueries = messages.filter(m => m.type === 'user').map(m => m.content);

    // Collect all citations
    const citations: CitationEntry[] = [];
    const seenTitles = new Set<string>();
    let idx = 0;

    responses.forEach(r => {
      const addResults = (results: ValidatedResult[], query: string) => {
        results.forEach(vr => {
          if (!seenTitles.has(vr.title)) {
            seenTitles.add(vr.title);
            idx++;
            citations.push({
              index: idx,
              source: vr.source,
              title: vr.title,
              url: vr.url,
              doi: vr.doi,
              year: vr.year,
              relevanceScore: vr.relevance_score,
              keywords: vr.keywords,
              query,
              evidenceLevel: inferEvidenceLevel(vr.source),
            });
          }
        });
      };
      addResults(r.pulse_report.validated_results, r.query);
      addResults(r.pulse_report.edge_cases, r.query);
    });

    // Source counts
    const sourceCounts: Record<string, number> = {};
    citations.forEach(c => {
      sourceCounts[c.source] = (sourceCounts[c.source] || 0) + 1;
    });

    // All keywords
    const keywordCounts: Record<string, number> = {};
    responses.forEach(r => {
      r.pulse_report.consensus_keywords.forEach(kw => {
        keywordCounts[kw] = (keywordCounts[kw] || 0) + 1;
      });
    });
    const topKeywords = Object.entries(keywordCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 8)
      .map(([kw]) => kw);

    // Average confidence
    const confidences = responses.map(r => r.pulse_report.confidence_ratio);
    const avgConfidence = confidences.length > 0
      ? Math.round((confidences.reduce((a, b) => a + b, 0) / confidences.length) * 100)
      : 0;

    // Total results
    const totalResults = responses.reduce((sum, r) => sum + r.total_results, 0);

    // Unique sources queried & failed
    const uniqueSources = new Set<string>();
    const allFailedSources: Record<string, string> = {};
    responses.forEach(r => {
      r.sources_queried.forEach(s => uniqueSources.add(s));
      if (r.sources_failed) {
        Object.entries(r.sources_failed).forEach(([k, v]) => { allFailedSources[k] = v; });
      }
    });

    // Year range
    const years = citations.map(c => c.year).filter(y => y > 0);
    const yearRange = years.length > 0
      ? { min: Math.min(...years), max: Math.max(...years) }
      : null;

    // Highest evidence level
    const evidenceLevels = citations.map(c => c.evidenceLevel);
    const bestEvidence = evidenceLevels.length > 0 ? highestEvidenceLevel(evidenceLevels) : null;

    // Source agreements (flatten from all responses)
    const sourceAgreements: (SourceAgreement & { query: string })[] = [];
    responses.forEach(r => {
      r.pulse_report.source_agreements.forEach(sa => {
        sourceAgreements.push({ ...sa, query: r.query });
      });
    });

    // Contradictions
    const contradictions = sourceAgreements.filter(sa => !sa.is_consensus && sa.overlap_score < 0.3);
    const divergences = sourceAgreements.filter(sa => !sa.is_consensus && sa.overlap_score >= 0.3);

    // Research gaps
    const gaps: string[] = [];
    const edgeCaseTotal = responses.reduce((s, r) => s + r.pulse_report.edge_case_count, 0);
    if (edgeCaseTotal > 0) {
      gaps.push(`${edgeCaseTotal} edge-case result${edgeCaseTotal > 1 ? 's' : ''} found where evidence diverges from mainstream consensus.`);
    }
    const failedSourceNames = Object.keys(allFailedSources);
    if (failedSourceNames.length > 0) {
      gaps.push(`${failedSourceNames.map(getSourceLabel).join(', ')} returned no results or failed -- potential coverage gap.`);
    }
    if (yearRange && (yearRange.max - yearRange.min) < 3) {
      gaps.push(`Publication date range is narrow (${yearRange.min}--${yearRange.max}). There may be recency bias or limited longitudinal data.`);
    }
    const validatedSources = new Set(citations.map(c => c.source));
    if (validatedSources.size <= 2 && citations.length > 0) {
      gaps.push(`Evidence found in only ${validatedSources.size} database${validatedSources.size === 1 ? '' : 's'}. Cross-validation is limited.`);
    }
    if (avgConfidence < 50 && citations.length > 0) {
      gaps.push('Overall PULSE confidence is below 50%. The evidence base for this query area is not well-established.');
    }

    return {
      citations,
      sourceCounts,
      topKeywords,
      avgConfidence,
      totalResults,
      uniqueSources: uniqueSources.size,
      uniqueSourcesList: Array.from(uniqueSources),
      yearRange,
      queryCount: userQueries.length,
      userQueries,
      responses,
      bestEvidence,
      sourceAgreements,
      contradictions,
      divergences,
      gaps,
      allFailedSources,
      edgeCaseTotal: responses.reduce((s, r) => s + r.pulse_report.edge_case_count, 0),
    };
  }, [messages]);

  // ---------------------------------------------------------------------------
  // Filtered & sorted citations
  // ---------------------------------------------------------------------------

  const filteredCitations = useMemo(() => {
    let list = analysis.citations;
    if (citationFilter === 'starred') {
      list = list.filter(c => starredKeys.has(citationKey(c)));
    } else if (citationFilter.startsWith('level:')) {
      const lv = citationFilter.replace('level:', '') as EvidenceLevel;
      list = list.filter(c => c.evidenceLevel === lv);
    } else if (citationFilter !== 'all') {
      list = list.filter(c => c.source === citationFilter);
    }
    if (citationSort === 'year') {
      list = [...list].sort((a, b) => b.year - a.year);
    } else {
      list = [...list].sort((a, b) => b.relevanceScore - a.relevanceScore);
    }
    return list;
  }, [analysis.citations, citationFilter, citationSort, starredKeys]);

  // ---------------------------------------------------------------------------
  // Derived values
  // ---------------------------------------------------------------------------

  const confidenceColor = analysis.avgConfidence >= 80
    ? 'text-emerald-600' : analysis.avgConfidence >= 60
    ? 'text-amber-600' : 'text-red-500';

  const confidenceBarColor = analysis.avgConfidence >= 80
    ? '#059669' : analysis.avgConfidence >= 60
    ? '#D97706' : '#EF4444';

  const confidenceLabel = analysis.avgConfidence >= 80
    ? 'High Consensus' : analysis.avgConfidence >= 60
    ? 'Moderate Consensus' : analysis.avgConfidence >= 40
    ? 'Mixed Evidence' : 'Limited Evidence';

  // ---------------------------------------------------------------------------
  // Report generation
  // ---------------------------------------------------------------------------

  const generateReport = useCallback(() => {
    const now = new Date();
    const personaLabel = formatPersona(persona);
    const { responses, userQueries, citations, avgConfidence, bestEvidence, gaps, contradictions, uniqueSourcesList, yearRange } = analysis;

    const line = (char: string, len: number) => char.repeat(len);
    const W = 55;
    let r = '';

    r += `LENA EVIDENCE SUMMARY\n`;
    r += `${line('=', W)}\n\n`;
    r += `PREPARED FOR: ${personaLabel} | DATE: ${now.toLocaleDateString('en-AU', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}\n`;
    r += `EVIDENCE LEVEL: ${bestEvidence ? `Level ${bestEvidence} (${EVIDENCE_LEVEL_SHORT[bestEvidence]})` : 'N/A'} | PULSE: ${avgConfidence}%\n\n`;

    // 1. Research Questions
    r += `${line('-', W)}\n`;
    r += `1. RESEARCH QUESTION(S)\n`;
    r += `${line('-', W)}\n\n`;
    userQueries.forEach((q, i) => {
      r += `  ${i + 1}. ${q}\n`;
    });
    r += '\n';

    // 2. Search Strategy
    r += `${line('-', W)}\n`;
    r += `2. SEARCH STRATEGY\n`;
    r += `${line('-', W)}\n\n`;
    r += `  Databases: ${uniqueSourcesList.map(getSourceLabel).join(', ')}\n`;
    if (yearRange) {
      r += `  Date range: ${yearRange.min} - ${yearRange.max}\n`;
    }
    const activeModes = Array.from(
      new Set(responses.flatMap(resp => resp.modes || ['all']))
    ).join(', ');
    r += `  Result modes: ${activeModes || 'all'}\n`;
    r += `  Total results: ${analysis.totalResults} across ${analysis.uniqueSources} databases\n`;
    r += '\n';

    // 3. Evidence Summary
    r += `${line('-', W)}\n`;
    r += `3. EVIDENCE SUMMARY\n`;
    r += `${line('-', W)}\n\n`;

    responses.forEach(resp => {
      const pr = resp.pulse_report;
      const qLevel = highestEvidenceLevel(pr.validated_results.map(vr => inferEvidenceLevel(vr.source)));
      r += `  Question: "${resp.query}"\n`;
      r += `  Evidence Level: ${qLevel} (${EVIDENCE_LEVEL_SHORT[qLevel]})\n`;
      r += `  Consensus: ${pr.status.replace(/_/g, ' ')} -- ${Math.round(pr.confidence_ratio * 100)}%\n`;
      if (pr.consensus_summary) {
        r += `  Key Finding: ${pr.consensus_summary}\n`;
      }
      r += `  Source Agreement: ${pr.agreement_count} of ${pr.source_count} sources agree\n`;

      // Contradictions for this query
      const queryCont = contradictions.filter(c => c.query === resp.query);
      if (queryCont.length > 0) {
        r += `\n  Contradictions/Divergences:\n`;
        queryCont.forEach(c => {
          r += `  - ${getSourceLabel(c.source)} (overlap: ${Math.round(c.overlap_score * 100)}%) -- unique keywords: ${c.unique_keywords.join(', ')}\n`;
        });
      }
      r += '\n';
    });

    // 4. Gaps & Limitations
    r += `${line('-', W)}\n`;
    r += `4. GAPS & LIMITATIONS\n`;
    r += `${line('-', W)}\n\n`;
    if (gaps.length > 0) {
      gaps.forEach(g => { r += `  - ${g}\n`; });
    } else {
      r += `  No significant gaps identified.\n`;
    }
    r += '\n';

    // 5. References
    r += `${line('-', W)}\n`;
    r += `5. REFERENCES\n`;
    r += `${line('-', W)}\n\n`;
    citations.forEach((c, i) => {
      r += `  [${i + 1}] ${c.title}. ${getSourceLabel(c.source)}`;
      if (c.year > 0) r += ` (${c.year})`;
      r += '.';
      if (c.doi) r += ` DOI: ${c.doi}.`;
      r += ` URL: ${c.url}`;
      r += '\n';
    });
    r += '\n';

    // 6. Starred References & Notes
    const starredCitations = citations.filter(c => starredKeys.has(citationKey(c)));
    if (starredCitations.length > 0 || Object.keys(citationNotes).length > 0) {
      r += `${line('-', W)}\n`;
      r += `6. STARRED REFERENCES & NOTES\n`;
      r += `${line('-', W)}\n\n`;
      starredCitations.forEach(c => {
        const key = citationKey(c);
        r += `  * [${c.index}] ${c.title}\n`;
        if (citationNotes[key]) {
          r += `    Note: ${citationNotes[key]}\n`;
        }
        r += '\n';
      });
    }

    // Methodology
    r += `${line('-', W)}\n`;
    r += `METHODOLOGY\n`;
    r += `${line('-', W)}\n\n`;
    r += `  Cross-referenced via PULSE engine across ${analysis.uniqueSources} databases.\n`;
    r += `  Databases: ${uniqueSourcesList.map(getSourceLabel).join(', ')}\n\n`;
    r += `  DISCLAIMER: This is a research aggregation tool, not medical\n`;
    r += `  advice. Always consult a qualified healthcare provider for\n`;
    r += `  clinical decisions.\n\n`;
    r += `${line('=', W)}\n`;
    r += `Generated by LENA | lena.health\n`;
    r += `${line('=', W)}\n`;

    return r;
  }, [analysis, persona, starredKeys, citationNotes]);

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  const handleExport = useCallback(() => {
    setExporting(true);
    try {
      const report = generateReport();
      const blob = new Blob([report], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `LENA-Evidence-Brief-${new Date().toISOString().slice(0, 10)}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setExportSuccess(true);
      setTimeout(() => setExportSuccess(false), 3000);
    } finally {
      setExporting(false);
    }
  }, [generateReport]);

  const handleCopy = useCallback(() => {
    const report = generateReport();
    navigator.clipboard.writeText(report).then(() => {
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 3000);
    });
  }, [generateReport]);

  const handleSaveToDocuments = useCallback(() => {
    try {
      const saved = loadJsonFromLS<unknown[]>(LS_KEY_SAVED, []);
      saved.unshift({
        id: `research-${Date.now()}`,
        date: new Date().toISOString(),
        persona,
        queries: analysis.userQueries,
        citationCount: analysis.citations.length,
        avgConfidence: analysis.avgConfidence,
        totalResults: analysis.totalResults,
        evidenceLevel: analysis.bestEvidence,
      });
      localStorage.setItem(LS_KEY_SAVED, JSON.stringify(saved.slice(0, 50)));
      setSavedToLibrary(true);
      setTimeout(() => setSavedToLibrary(false), 3000);
    } catch {}
  }, [analysis, persona]);

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const hasData = analysis.queryCount > 0;

  const renderEmptyState = () => (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center">
      <div
        className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'linear-gradient(135deg, rgba(27,107,147,0.12), rgba(20,83,114,0.08))' }}
      >
        <SparklesIcon size={24} className="text-[#1B6B93]" />
      </div>
      <p className="text-sm font-medium text-slate-700 mb-2">Your research panel is ready</p>
      <p className="text-xs text-slate-400 leading-relaxed max-w-[240px]">
        Ask LENA a clinical question to see evidence quality analysis, source agreement mapping, Vancouver-format citations, and research gap identification here.
      </p>
    </div>
  );

  // --- Section: Evidence Quality Overview ---
  const renderOverview = () => {
    const { bestEvidence, avgConfidence: conf, totalResults, uniqueSources, yearRange: yr } = analysis;
    return (
      <div className="space-y-4">
        {/* Evidence Level Hero */}
        {bestEvidence && (
          <div className="flex items-start gap-3 p-3 rounded-xl bg-gradient-to-br from-slate-50 to-white border border-slate-100">
            <EvidencePyramidIcon level={bestEvidence} size={36} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Highest Evidence</span>
                <EvidenceBadge level={bestEvidence} />
              </div>
              <p className="text-[11px] text-slate-500 leading-snug">{EVIDENCE_LEVEL_LABELS[bestEvidence]}</p>
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-slate-900">{totalResults}</div>
            <div className="text-[10px] text-slate-500 font-medium mt-0.5">Results Found</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-slate-900">{analysis.citations.length}</div>
            <div className="text-[10px] text-slate-500 font-medium mt-0.5">Citations</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-slate-900">{uniqueSources}</div>
            <div className="text-[10px] text-slate-500 font-medium mt-0.5">Databases</div>
          </div>
          <div className="bg-slate-50 rounded-xl p-3 text-center">
            <div className="text-lg font-bold text-slate-900">
              {yr ? `${yr.min}--${yr.max}` : '--'}
            </div>
            <div className="text-[10px] text-slate-500 font-medium mt-0.5">Year Range</div>
          </div>
        </div>

        {/* PULSE Confidence */}
        <div className="bg-slate-50 rounded-xl p-3">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">PULSE Confidence</span>
            <span className={`text-xs font-semibold ${confidenceColor}`}>{conf}% -- {confidenceLabel}</span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2 mb-2">
            <div
              className="h-2 rounded-full transition-all duration-700"
              style={{ width: `${conf}%`, background: confidenceBarColor }}
            />
          </div>
          <p className="text-[10px] text-slate-500 leading-relaxed">
            {confidenceInterpretation(conf)}
          </p>
        </div>

        {/* Key Themes */}
        {analysis.topKeywords.length > 0 && (
          <div>
            <h3 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Consensus Themes</h3>
            <div className="flex flex-wrap gap-1.5">
              {analysis.topKeywords.map(kw => (
                <span key={kw} className="px-2 py-1 text-[11px] text-slate-600 bg-slate-100 rounded-md font-medium">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Source Breakdown */}
        {Object.keys(analysis.sourceCounts).length > 0 && (
          <div>
            <h3 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Sources</h3>
            <div className="space-y-1.5">
              {Object.entries(analysis.sourceCounts)
                .sort((a, b) => b[1] - a[1])
                .map(([source, count]) => (
                  <div key={source} className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: getSourceColor(source) }} />
                    <span className="text-xs text-slate-600 flex-1 truncate">{getSourceLabel(source)}</span>
                    <EvidenceBadge level={inferEvidenceLevel(source)} compact />
                    <span className="text-xs text-slate-400 font-medium tabular-nums">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  // --- Section: Source Agreement Matrix ---
  const renderAgreement = () => {
    const { sourceAgreements, contradictions, responses } = analysis;

    if (sourceAgreements.length === 0) {
      return (
        <div className="text-center py-8 px-4">
          <p className="text-xs text-slate-400">Source agreement data will appear once multiple databases return results for a query.</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        {/* Legend */}
        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          <span className="flex items-center gap-1"><AgreementDot type="consensus" /> Consensus</span>
          <span className="flex items-center gap-1"><AgreementDot type="divergent" /> Divergent</span>
          <span className="flex items-center gap-1"><AgreementDot type="contradiction" /> Contradiction</span>
        </div>

        {/* Contradictions callout */}
        {contradictions.length > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
            <div className="flex items-center gap-1.5 mb-1.5">
              <svg className="w-3.5 h-3.5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <span className="text-[11px] font-semibold text-amber-700">
                {contradictions.length} Contradiction{contradictions.length > 1 ? 's' : ''} Detected
              </span>
            </div>
            <p className="text-[10px] text-amber-600 leading-relaxed">
              Sources below have minimal keyword overlap and disagree on key findings. Review these sources directly before drawing conclusions.
            </p>
          </div>
        )}

        {/* Per-query agreement */}
        {responses.map((resp, ri) => {
          const qAgreements = sourceAgreements.filter(sa => sa.query === resp.query);
          if (qAgreements.length === 0) return null;

          return (
            <div key={ri} className="space-y-2">
              <h4 className="text-[11px] font-medium text-slate-700 truncate" title={resp.query}>
                Q{ri + 1}: {resp.query}
              </h4>
              <div className="space-y-1.5">
                {qAgreements.map((sa, si) => {
                  const type: 'consensus' | 'divergent' | 'contradiction' =
                    sa.is_consensus ? 'consensus'
                    : sa.overlap_score < 0.3 ? 'contradiction'
                    : 'divergent';

                  return (
                    <div key={si} className="bg-white border border-slate-100 rounded-lg p-2.5">
                      <div className="flex items-center gap-2 mb-1">
                        <AgreementDot type={type} />
                        <span className="text-[11px] font-medium text-slate-700">{getSourceLabel(sa.source)}</span>
                        <span className="text-[10px] text-slate-400 ml-auto">{sa.result_count} results</span>
                      </div>
                      {/* Overlap bar */}
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className="text-[10px] text-slate-400 w-14 flex-shrink-0">Overlap</span>
                        <div className="flex-1 bg-slate-100 rounded-full h-1.5">
                          <div
                            className="h-1.5 rounded-full transition-all"
                            style={{
                              width: `${Math.round(sa.overlap_score * 100)}%`,
                              background: type === 'consensus' ? '#059669' : type === 'divergent' ? '#D97706' : '#EF4444',
                            }}
                          />
                        </div>
                        <span className="text-[10px] text-slate-500 font-medium tabular-nums w-8 text-right">
                          {Math.round(sa.overlap_score * 100)}%
                        </span>
                      </div>
                      {/* Keywords */}
                      {sa.shared_keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1 mb-1">
                          {sa.shared_keywords.slice(0, 4).map(kw => (
                            <span key={kw} className="px-1.5 py-0.5 text-[9px] text-emerald-700 bg-emerald-50 rounded font-medium">
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}
                      {sa.unique_keywords.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {sa.unique_keywords.slice(0, 4).map(kw => (
                            <span key={kw} className="px-1.5 py-0.5 text-[9px] text-amber-700 bg-amber-50 rounded font-medium">
                              {kw}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  // --- Section: References ---
  const renderReferences = () => {
    return (
      <div className="space-y-3">
        {/* Filter bar */}
        <div className="flex items-center gap-2">
          <select
            value={citationFilter}
            onChange={e => setCitationFilter(e.target.value)}
            className="flex-1 text-[10px] text-slate-600 bg-white border border-slate-200 rounded-md px-2 py-1 focus:outline-none focus:border-[#1B6B93]"
          >
            <option value="all">All ({analysis.citations.length})</option>
            <option value="starred">Starred ({analysis.citations.filter(c => starredKeys.has(citationKey(c))).length})</option>
            <optgroup label="By Source">
              {Object.entries(analysis.sourceCounts).map(([src, cnt]) => (
                <option key={src} value={src}>{getSourceLabel(src)} ({cnt})</option>
              ))}
            </optgroup>
            <optgroup label="By Evidence Level">
              {(['I', 'II', 'III', 'IV', 'V'] as EvidenceLevel[])
                .filter(lv => analysis.citations.some(c => c.evidenceLevel === lv))
                .map(lv => (
                  <option key={lv} value={`level:${lv}`}>
                    Level {lv} ({analysis.citations.filter(c => c.evidenceLevel === lv).length})
                  </option>
                ))}
            </optgroup>
          </select>
          <button
            onClick={() => setCitationSort(s => s === 'relevance' ? 'year' : 'relevance')}
            className="text-[10px] text-slate-500 border border-slate-200 rounded-md px-2 py-1 hover:bg-slate-50 transition-colors flex-shrink-0"
            title={`Sort by ${citationSort === 'relevance' ? 'year' : 'relevance'}`}
          >
            {citationSort === 'relevance' ? 'By Relevance' : 'By Year'}
          </button>
        </div>

        {/* Citation cards */}
        <div className="space-y-1.5 max-h-[calc(100dvh-320px)] overflow-y-auto pr-0.5">
          {filteredCitations.length === 0 && (
            <p className="text-xs text-slate-400 text-center py-4">
              {citationFilter === 'starred' ? 'No starred citations yet. Star references you want to highlight in your export.' : 'No citations match this filter.'}
            </p>
          )}
          {filteredCitations.map(c => {
            const key = citationKey(c);
            const isStarred = starredKeys.has(key);
            const note = citationNotes[key];
            const isEditing = editingNoteKey === key;

            return (
              <div
                key={key}
                className={`p-2.5 bg-white border rounded-lg transition-all ${isStarred ? 'border-amber-200 bg-amber-50/30' : 'border-slate-100 hover:border-slate-200'}`}
              >
                <div className="flex items-start gap-2">
                  {/* Citation number */}
                  <span className="text-[10px] font-bold text-slate-400 mt-0.5 w-5 flex-shrink-0 text-right tabular-nums">
                    [{c.index}]
                  </span>
                  <div className="flex-1 min-w-0">
                    {/* Title */}
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[11px] font-medium text-slate-800 leading-snug line-clamp-2 hover:text-[#1B6B93] transition-colors"
                    >
                      {c.title}
                    </a>
                    {/* Meta row */}
                    <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                      <span className="text-[10px] text-slate-400">{getSourceLabel(c.source)}</span>
                      {c.year > 0 && <span className="text-[10px] text-slate-400">({c.year})</span>}
                      <EvidenceBadge level={c.evidenceLevel} compact />
                      {c.doi && (
                        <>
                          <span className="text-[10px] text-slate-300">|</span>
                          <span className="text-[10px] text-slate-400 font-mono truncate max-w-[100px]">{c.doi}</span>
                        </>
                      )}
                    </div>
                    {/* Note display */}
                    {note && !isEditing && (
                      <div className="mt-1.5 text-[10px] text-slate-500 italic bg-slate-50 rounded px-2 py-1">
                        {note}
                      </div>
                    )}
                    {/* Note editing */}
                    {isEditing && (
                      <div className="mt-1.5 flex gap-1">
                        <input
                          type="text"
                          value={noteInput}
                          onChange={e => setNoteInput(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') saveNote(key, noteInput); if (e.key === 'Escape') { setEditingNoteKey(null); setNoteInput(''); } }}
                          placeholder="Why is this paper relevant?"
                          className="flex-1 text-[10px] border border-slate-200 rounded px-2 py-1 focus:outline-none focus:border-[#1B6B93]"
                          autoFocus
                        />
                        <button
                          onClick={() => saveNote(key, noteInput)}
                          className="text-[10px] text-white px-2 py-1 rounded"
                          style={{ background: '#1B6B93' }}
                        >
                          Save
                        </button>
                      </div>
                    )}
                  </div>
                  {/* Action buttons */}
                  <div className="flex flex-col gap-1 flex-shrink-0">
                    {/* Star toggle */}
                    <button
                      onClick={() => toggleStar(key)}
                      className={`p-1 rounded transition-colors ${isStarred ? 'text-amber-500 hover:text-amber-600' : 'text-slate-300 hover:text-amber-400'}`}
                      aria-label={isStarred ? 'Remove star' : 'Star citation'}
                    >
                      <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill={isStarred ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                      </svg>
                    </button>
                    {/* Note toggle */}
                    <button
                      onClick={() => {
                        if (isEditing) {
                          setEditingNoteKey(null);
                          setNoteInput('');
                        } else {
                          setEditingNoteKey(key);
                          setNoteInput(note || '');
                        }
                      }}
                      className={`p-1 rounded transition-colors ${note ? 'text-[#1B6B93]' : 'text-slate-300 hover:text-slate-500'}`}
                      aria-label="Add note"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // --- Section: Research Gaps ---
  const renderGaps = () => {
    const { gaps, allFailedSources, edgeCaseTotal, responses } = analysis;

    return (
      <div className="space-y-4">
        <p className="text-[11px] text-slate-500 leading-relaxed">
          Identifying what is missing from the evidence base is as important as what is found. The items below flag where caution is warranted.
        </p>

        {gaps.length === 0 ? (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3 text-center">
            <p className="text-[11px] text-emerald-700 font-medium">No significant research gaps identified</p>
            <p className="text-[10px] text-emerald-600 mt-0.5">Evidence coverage appears adequate across available databases.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {gaps.map((gap, i) => (
              <div key={i} className="flex items-start gap-2 p-2.5 bg-amber-50/60 border border-amber-100 rounded-lg">
                <svg className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <p className="text-[11px] text-slate-700 leading-relaxed">{gap}</p>
              </div>
            ))}
          </div>
        )}

        {/* Failed sources detail */}
        {Object.keys(allFailedSources).length > 0 && (
          <div>
            <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Source Failures</h4>
            <div className="space-y-1">
              {Object.entries(allFailedSources).map(([src, reason]) => (
                <div key={src} className="flex items-center gap-2 text-[10px]">
                  <div className="w-2 h-2 rounded-full bg-red-400 flex-shrink-0" />
                  <span className="text-slate-600 font-medium">{getSourceLabel(src)}</span>
                  <span className="text-slate-400 truncate">{reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Edge cases summary */}
        {edgeCaseTotal > 0 && (
          <div>
            <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Edge Cases</h4>
            <p className="text-[10px] text-slate-500 leading-relaxed">
              {edgeCaseTotal} result{edgeCaseTotal > 1 ? 's' : ''} classified as edge cases -- findings that diverge from the main body of evidence. These may represent emerging research, niche populations, or methodological outliers.
            </p>
          </div>
        )}

        {/* Queries covered */}
        <div>
          <h4 className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2">Queries Analysed</h4>
          <div className="space-y-1">
            {analysis.userQueries.map((q, i) => {
              const resp = responses[i];
              const status = resp?.pulse_report?.status;
              return (
                <div key={i} className="flex items-start gap-2 py-1">
                  <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-500 text-[10px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-xs text-slate-600 leading-relaxed flex-1">{q}</span>
                  {status && (
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded flex-shrink-0 ${
                      status === 'validated' ? 'text-emerald-700 bg-emerald-50'
                      : status === 'edge_case' ? 'text-amber-700 bg-amber-50'
                      : 'text-slate-500 bg-slate-100'
                    }`}>
                      {status.replace(/_/g, ' ')}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  // --- Section: Export ---
  const renderExport = () => {
    return (
      <div className="space-y-4">
        <p className="text-[11px] text-slate-500 leading-relaxed">
          Generate a structured evidence brief suitable for clinical review, grant applications, or literature review documentation.
        </p>

        {/* Preview outline */}
        <div className="bg-slate-50 rounded-xl p-3 space-y-1.5">
          <h4 className="text-[11px] font-semibold text-slate-600 mb-2">Brief Contents</h4>
          {[
            `1. Research Questions (${analysis.userQueries.length})`,
            `2. Search Strategy (${analysis.uniqueSources} databases)`,
            `3. Evidence Summary (Level ${analysis.bestEvidence || '--'}, ${analysis.avgConfidence}% PULSE)`,
            `4. Gaps & Limitations (${analysis.gaps.length} identified)`,
            `5. References (${analysis.citations.length} citations, Vancouver format)`,
            `6. Starred References & Notes (${analysis.citations.filter(c => starredKeys.has(citationKey(c))).length} starred)`,
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2">
              <svg className="w-3 h-3 text-emerald-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-[10px] text-slate-600">{item}</span>
            </div>
          ))}
        </div>

        {/* Export actions are in bottom bar */}
        <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
          <p className="text-[10px] text-blue-700 leading-relaxed">
            Star citations and add notes in the References tab to include personalised annotations in your exported brief.
          </p>
        </div>
      </div>
    );
  };

  const renderActiveSection = () => {
    switch (activeSection) {
      case 'overview':   return renderOverview();
      case 'agreement':  return renderAgreement();
      case 'references': return renderReferences();
      case 'gaps':       return renderGaps();
      case 'export':     return renderExport();
    }
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <aside className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div
            className="w-5 h-5 rounded flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
          >
            <SparklesIcon size={10} className="text-white" />
          </div>
          <h2 className="text-sm font-semibold text-slate-900">Research Panel</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition-colors"
          aria-label="Close panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Tab navigation */}
      {hasData && (
        <div className="flex border-b border-slate-200 flex-shrink-0 overflow-x-auto">
          {SECTION_TABS.map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveSection(tab.key)}
              className={`flex-1 min-w-0 px-1 py-2 text-[10px] font-medium transition-colors whitespace-nowrap ${
                activeSection === tab.key
                  ? 'text-[#1B6B93] border-b-2 border-[#1B6B93]'
                  : 'text-slate-400 hover:text-slate-600'
              }`}
            >
              {tab.label}
              {tab.key === 'gaps' && analysis.gaps.length > 0 && (
                <span className="ml-0.5 inline-flex items-center justify-center w-3.5 h-3.5 text-[8px] font-bold text-amber-700 bg-amber-100 rounded-full">
                  {analysis.gaps.length}
                </span>
              )}
              {tab.key === 'references' && (
                <span className="ml-0.5 text-[9px] text-slate-400">{analysis.citations.length}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {!hasData ? renderEmptyState() : (
          <div className="p-4">
            {renderActiveSection()}
          </div>
        )}
      </div>

      {/* Bottom Actions */}
      {hasData && (
        <div className="border-t border-slate-200 p-3 space-y-2 flex-shrink-0 bg-white">
          <button
            onClick={handleExport}
            disabled={exporting}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-white rounded-xl transition-all disabled:opacity-50 hover:opacity-90"
            style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
          >
            {exportSuccess ? (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                Brief Downloaded
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {exporting ? 'Generating...' : 'Export Evidence Brief'}
              </>
            )}
          </button>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                copySuccess
                  ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                  : 'text-slate-600 bg-slate-100 hover:bg-slate-200'
              }`}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              {copySuccess ? 'Copied' : 'Copy to Clipboard'}
            </button>
            <button
              onClick={handleSaveToDocuments}
              className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg transition-colors ${
                savedToLibrary
                  ? 'text-emerald-700 bg-emerald-50 border border-emerald-200'
                  : 'text-slate-600 bg-slate-100 hover:bg-slate-200'
              }`}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              {savedToLibrary ? 'Saved' : 'Save to Documents'}
            </button>
          </div>
        </div>
      )}
    </aside>
  );
}
