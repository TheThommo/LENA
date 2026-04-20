'use client';

import { useState, useMemo, useEffect, useRef } from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';
import type { SearchResponse, ValidatedResult, ResultMode } from '@/lib/api';

/* ────────────────────────────────────────
   Lightweight Markdown → JSX renderer
   Handles: headers, bold, italic, lists,
   numbered lists, inline code, paragraphs,
   blockquotes, horizontal rules
   ──────────────────────────────────────── */
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split('\n');
  const elements: React.ReactNode[] = [];
  let listItems: React.ReactNode[] = [];
  let listType: 'ul' | 'ol' | null = null;
  let key = 0;

  const flushList = () => {
    if (listItems.length > 0 && listType) {
      const Tag = listType;
      elements.push(
        <Tag key={key++} className={`${listType === 'ul' ? 'list-disc' : 'list-decimal'} ml-5 space-y-1 text-sm text-slate-700`}>
          {listItems}
        </Tag>
      );
      listItems = [];
      listType = null;
    }
  };

  const formatInline = (str: string): React.ReactNode => {
    // Process bold, italic, inline code, links, and citation refs like [4]
    const parts: React.ReactNode[] = [];
    let remaining = str;
    let i = 0;

    // Order matters: bold before italic, markdown links before bare citation refs
    const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(\[(.+?)\]\((.+?)\))|(\[(\d+)\])/g;
    let match;
    let lastIndex = 0;

    while ((match = regex.exec(remaining)) !== null) {
      if (match.index > lastIndex) {
        parts.push(remaining.slice(lastIndex, match.index));
      }
      if (match[1]) {
        parts.push(<strong key={`b${i++}`} className="font-semibold text-slate-900">{match[2]}</strong>);
      } else if (match[3]) {
        parts.push(<em key={`i${i++}`}>{match[4]}</em>);
      } else if (match[5]) {
        parts.push(<code key={`c${i++}`} className="px-1.5 py-0.5 bg-slate-100 text-slate-800 rounded text-xs font-mono">{match[6]}</code>);
      } else if (match[7]) {
        parts.push(<a key={`a${i++}`} href={match[9]} target="_blank" rel="noopener noreferrer" className="text-[#1B6B93] underline hover:text-[#155a7a]">{match[8]}</a>);
      } else if (match[10]) {
        // Citation reference like [4] — clickable, scrolls to source card
        const refNum = parseInt(match[11], 10);
        parts.push(
          <button
            key={`ref${i++}`}
            className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold text-white bg-[#1B6B93] rounded-full hover:bg-[#155a7a] transition-colors cursor-pointer align-text-top mx-0.5"
            title={`Jump to source ${refNum}`}
            onClick={() => {
              const scrollToCard = () => {
                const card = document.querySelector(`[data-source-index="${refNum - 1}"]`);
                if (card) {
                  card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  card.classList.add('ring-2', 'ring-[#1B6B93]');
                  setTimeout(() => card.classList.remove('ring-2', 'ring-[#1B6B93]'), 2000);
                }
              };
              // If card not visible, expand the source list first
              if (!document.querySelector(`[data-source-index="${refNum - 1}"]`)) {
                document.dispatchEvent(new Event('lena:expand-sources'));
                setTimeout(scrollToCard, 100);
              } else {
                scrollToCard();
              }
            }}
          >
            {refNum}
          </button>
        );
      }
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < remaining.length) {
      parts.push(remaining.slice(lastIndex));
    }
    return parts.length === 1 ? parts[0] : <>{parts}</>;
  };

  for (const line of lines) {
    const trimmed = line.trim();

    // Horizontal rule
    if (/^[-*_]{3,}$/.test(trimmed)) {
      flushList();
      elements.push(<hr key={key++} className="border-slate-200 my-3" />);
      continue;
    }

    // Headers
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(<h4 key={key++} className="text-sm font-bold text-slate-900 mt-4 mb-1.5">{formatInline(trimmed.slice(4))}</h4>);
      continue;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(<h3 key={key++} className="text-sm font-bold text-slate-900 mt-4 mb-1.5">{formatInline(trimmed.slice(3))}</h3>);
      continue;
    }
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(<h2 key={key++} className="text-base font-bold text-slate-900 mt-4 mb-2">{formatInline(trimmed.slice(2))}</h2>);
      continue;
    }

    // Blockquote
    if (trimmed.startsWith('> ')) {
      flushList();
      elements.push(
        <blockquote key={key++} className="border-l-3 border-[#1B6B93] pl-3 py-1 text-sm text-slate-600 italic bg-slate-50 rounded-r-md my-2">
          {formatInline(trimmed.slice(2))}
        </blockquote>
      );
      continue;
    }

    // Unordered list
    if (/^[-*+]\s/.test(trimmed)) {
      if (listType !== 'ul') {
        flushList();
        listType = 'ul';
      }
      listItems.push(<li key={`li${key++}`} className="text-sm text-slate-700 leading-relaxed">{formatInline(trimmed.replace(/^[-*+]\s/, ''))}</li>);
      continue;
    }

    // Ordered list
    if (/^\d+\.\s/.test(trimmed)) {
      if (listType !== 'ol') {
        flushList();
        listType = 'ol';
      }
      listItems.push(<li key={`li${key++}`} className="text-sm text-slate-700 leading-relaxed">{formatInline(trimmed.replace(/^\d+\.\s/, ''))}</li>);
      continue;
    }

    // Empty line — flush list and add spacing
    if (trimmed === '') {
      flushList();
      continue;
    }

    // Regular paragraph
    flushList();
    elements.push(<p key={key++} className="text-sm text-slate-700 leading-relaxed">{formatInline(trimmed)}</p>);
  }

  flushList();
  return elements;
}

/** Memoised formatted content block */
function FormattedContent({ text }: { text: string }) {
  const rendered = useMemo(() => renderMarkdown(text), [text]);
  return <div className="space-y-2">{rendered}</div>;
}

interface ProjectOption {
  id: string;
  name: string;
  emoji: string | null;
}

interface ChatMessageProps {
  type: 'user' | 'assistant';
  content: string;
  response?: SearchResponse;
  /** Currently active result-mode filters; used for client-side filtering of
   *  results returned by the backend. ['all'] (or missing) means show everything. */
  activeModes?: ResultMode[];
  onFollowUp?: (query: string) => void;
  onShare?: (title?: string) => void;
  /** Available projects for "Add to Project" action */
  projects?: ProjectOption[];
  /** Called when user picks a project to file this search under */
  onAddToProject?: (searchId: string, projectId: string) => void;
  /** Create a new project inline. When provided, picker shows "+ New project". */
  onCreateProject?: (name: string) => Promise<ProjectOption>;
}

const SOURCE_COLORS: Record<string, { border: string; bg: string; text: string; label: string }> = {
  pubmed:          { border: 'border-l-[#2563EB]', bg: 'bg-blue-50',    text: 'text-blue-700',    label: 'PubMed' },
  clinical_trials: { border: 'border-l-[#7C3AED]', bg: 'bg-purple-50',  text: 'text-purple-700',  label: 'ClinicalTrials.gov' },
  cochrane:        { border: 'border-l-[#EA580C]', bg: 'bg-orange-50',  text: 'text-orange-700',  label: 'Cochrane' },
  who_iris:        { border: 'border-l-[#0891B2]', bg: 'bg-cyan-50',    text: 'text-cyan-700',    label: 'WHO IRIS' },
  cdc:             { border: 'border-l-[#059669]', bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'CDC' },
  openalex:        { border: 'border-l-[#DC2626]', bg: 'bg-red-50',     text: 'text-red-700',     label: 'OpenAlex' },
  ods_dsld:        { border: 'border-l-[#0D9488]', bg: 'bg-teal-50',    text: 'text-teal-700',    label: 'NIH DSLD' },
  openfda:         { border: 'border-l-[#B91C1C]', bg: 'bg-rose-50',    text: 'text-rose-700',    label: 'openFDA CAERS' },
};

function getSourceStyle(source: string) {
  return SOURCE_COLORS[source] || {
    border: 'border-l-slate-400',
    bg: 'bg-slate-50',
    text: 'text-slate-700',
    label: source.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
  };
}

function getPulseScoreBadge(score: number) {
  if (score >= 0.75) return { className: 'bg-green-100 text-green-800', label: 'High' };
  if (score >= 0.5) return { className: 'bg-yellow-100 text-yellow-800', label: 'Medium' };
  if (score >= 0.25) return { className: 'bg-purple-100 text-purple-800', label: 'Edge' };
  return { className: 'bg-red-100 text-red-800', label: 'Low' };
}

function generateSummary(response: SearchResponse): string {
  const sourceCount = response.sources_queried.length;
  const { total_results, pulse_report } = response;
  const confidence = Math.round(pulse_report.confidence_ratio * 100);

  let summary = `Based on analysis across ${sourceCount} medical database${sourceCount !== 1 ? 's' : ''}, I found ${total_results} relevant result${total_results !== 1 ? 's' : ''} for your query.`;

  if (pulse_report.consensus_summary) {
    summary += ` ${pulse_report.consensus_summary}`;
  }

  summary += ` PULSE confidence is at ${confidence}% with ${pulse_report.validated_count} validated result${pulse_report.validated_count !== 1 ? 's' : ''}`;
  if (pulse_report.edge_case_count > 0) {
    summary += ` and ${pulse_report.edge_case_count} edge case${pulse_report.edge_case_count !== 1 ? 's' : ''}`;
  }
  summary += '.';

  return summary;
}

/**
 * Extract follow-up suggestions from the LLM response markdown.
 *
 * The system prompt instructs the LLM to end every response with:
 *   ## Suggested Follow-Ups
 *   - [question 1]
 *   - [question 2]
 *   - [question 3]
 *
 * We parse them out so they render as clickable chips, and strip the
 * section from the main summary body (it would look odd as rendered markdown).
 */
function extractFollowUps(summary: string): { cleanSummary: string; followUps: string[] } {
  // Match the follow-ups section at the end of the markdown
  const marker = /##\s*Suggested Follow[- ]?Ups?\s*\n([\s\S]*?)$/i;
  const match = summary.match(marker);

  if (!match) {
    return { cleanSummary: summary, followUps: [] };
  }

  const cleanSummary = summary.slice(0, match.index).trimEnd();
  const block = match[1];

  // Each follow-up is a markdown list item: "- question text"
  const followUps = block
    .split('\n')
    .map(line => line.replace(/^[-*]\s*/, '').trim())
    .filter(line => line.length > 10) // skip empty / too-short lines
    .slice(0, 3);

  return { cleanSummary, followUps };
}

/**
 * Fallback: generate basic follow-ups from PULSE keywords when the LLM
 * doesn't include them (e.g. cached responses, non-LLM summaries).
 */
function generateFollowUpsFallback(response: SearchResponse): string[] {
  if (!response.pulse_report) return [];
  const keywords = (response.pulse_report.consensus_keywords || []).slice(0, 3);
  const query = response.query;
  const suggestions: string[] = [];

  if (keywords.length > 0) {
    suggestions.push(`What are the latest RCTs on ${keywords[0]}?`);
  }
  if (keywords.length > 1) {
    suggestions.push(`Compare ${keywords[0]} vs ${keywords[1]} outcomes`);
  }
  suggestions.push(`Show systematic reviews related to "${query}"`);

  return suggestions.slice(0, 3);
}

function SourceCard({ result, isEdgeCase, index, query }: { result: ValidatedResult; isEdgeCase: boolean; index: number; query: string }) {
  const [expanded, setExpanded] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    import('@/lib/mySources').then(m => {
      setSaved(m.isSaved(result.source, result.title));
    }).catch(() => {});
  }, [result.source, result.title]);

  const handleSave = async () => {
    const m = await import('@/lib/mySources');
    if (saved) {
      m.removeSource(m.makeSourceId(result.source, result.title));
      setSaved(false);
    } else {
      m.saveSource({
        source: result.source,
        title: result.title,
        url: result.url,
        doi: result.doi,
        year: result.year,
        authors: result.authors,
        keywords: result.keywords,
        query,
        matched_modes: result.matched_modes,
      });
      setSaved(true);
    }
  };
  const style = getSourceStyle(result.source);
  const scoreBadge = getPulseScoreBadge(result.relevance_score);

  return (
    <div
      data-source-index={index}
      className={`rounded-lg border border-slate-200/70 bg-white transition-all hover:border-slate-300/80 hover:shadow-sm`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex-1 min-w-0 flex items-center gap-1.5">
            <span className={`px-1.5 py-0.5 text-[9px] font-semibold rounded ${style.bg} ${style.text} flex-shrink-0 tracking-wide`}>
              {style.label}
            </span>
            {result.year > 0 && (
              <span className="text-[10px] text-slate-400 flex-shrink-0 tabular-nums">{result.year}</span>
            )}
            <span className={`px-1.5 py-0.5 text-[9px] font-semibold rounded-full ${scoreBadge.className} flex-shrink-0`}>
              {scoreBadge.label}
            </span>
            {isEdgeCase && (
              <span className="px-1.5 py-0.5 text-[9px] font-semibold rounded-full bg-purple-50 text-purple-700 flex-shrink-0">
                Edge
              </span>
            )}
            {result.matched_modes?.includes('supplements') && (
              <span className="px-1.5 py-0.5 text-[9px] font-semibold rounded-full bg-teal-50 text-teal-700 flex-shrink-0" title="Vitamin, mineral, probiotic or nutraceutical supplement">
                Supplement
              </span>
            )}
            {result.matched_modes?.includes('herbal') && (
              <span className="px-1.5 py-0.5 text-[9px] font-semibold rounded-full bg-emerald-50 text-emerald-700 flex-shrink-0" title="Botanical / herbal medicine result">
                Herbal
              </span>
            )}
            {result.matched_modes?.includes('alternatives') && (
              <span className="px-1.5 py-0.5 text-[9px] font-semibold rounded-full bg-violet-50 text-violet-700 flex-shrink-0" title="Alternative / complementary practice (acupuncture, TCM, Ayurveda, etc.)">
                Alternative
              </span>
            )}
            {result.matched_modes?.includes('outlier') && (
              <span className="px-1.5 py-0.5 text-[9px] font-semibold rounded-full bg-amber-50 text-amber-700 flex-shrink-0" title="Authored by a researcher in the outlier list">
                Outlier
              </span>
            )}
            <p className="text-[12px] font-medium text-slate-900 truncate leading-snug">
              {result.title}
            </p>
          </div>
          <span
            className={`text-slate-400 text-[10px] transition-transform flex-shrink-0 ${
              expanded ? 'rotate-180' : ''
            }`}
          >
            &#9660;
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-3 pb-2.5 space-y-2 border-t border-slate-100 pt-2">
          {result.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {result.keywords.map((kw) => (
                <span
                  key={kw}
                  className="px-1.5 py-0.5 text-[10px] text-slate-600 bg-slate-100 rounded-full"
                >
                  {kw}
                </span>
              ))}
            </div>
          )}

          {result.authors && result.authors.length > 0 && (
            <p className="text-[10px] text-slate-600">
              <span className="font-semibold">Authors:</span> {result.authors.slice(0, 3).join(', ')}
              {result.authors.length > 3 && ` +${result.authors.length - 3}`}
            </p>
          )}

          {result.doi && (
            <p className="text-[10px] text-slate-500 font-mono">DOI: {result.doi}</p>
          )}

          <div className="flex flex-wrap gap-1.5">
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium text-white bg-[#1B6B93] rounded-md hover:bg-[#155a7a] transition-colors"
            >
              View Full
            </a>
            <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors">
              Cite
            </button>
            <button
              onClick={handleSave}
              className={`inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium rounded-md transition-colors ${
                saved
                  ? 'text-emerald-700 bg-emerald-50 hover:bg-emerald-100'
                  : 'text-slate-700 bg-slate-100 hover:bg-slate-200'
              }`}
              title={saved ? 'Saved to My Sources - click to remove' : 'Save to My Sources'}
            >
              {saved ? 'Saved' : 'Save'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const INITIAL_VISIBLE = 3;

function SourceCardList({ allResults, query }: { allResults: { result: ValidatedResult; isEdge: boolean }[]; query: string }) {
  const [showAll, setShowAll] = useState(false);

  // Listen for citation clicks that need the list expanded
  useEffect(() => {
    const handler = () => setShowAll(true);
    document.addEventListener('lena:expand-sources', handler);
    return () => document.removeEventListener('lena:expand-sources', handler);
  }, []);

  const visible = showAll ? allResults : allResults.slice(0, INITIAL_VISIBLE);
  const hiddenCount = allResults.length - INITIAL_VISIBLE;

  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-medium text-slate-500 tracking-wide">
        Sources ({allResults.length})
      </p>
      <div className="space-y-1.5">
        {visible.map(({ result, isEdge }, i) => (
          <SourceCard key={`${result.source}-${result.title}-${i}`} result={result} isEdgeCase={isEdge} index={i} query={query} />
        ))}
      </div>
      {hiddenCount > 0 && !showAll && (
        <button
          onClick={() => setShowAll(true)}
          className="text-xs font-medium text-[#1B6B93] hover:text-[#155a7a] transition-colors"
        >
          Show all {allResults.length} sources
        </button>
      )}
      {showAll && hiddenCount > 0 && (
        <button
          onClick={() => setShowAll(false)}
          className="text-xs font-medium text-slate-500 hover:text-slate-700 transition-colors"
        >
          Show fewer
        </button>
      )}
    </div>
  );
}

export default function ChatMessage({
  type,
  content,
  response,
  onFollowUp,
  onShare,
  activeModes,
  projects,
  onAddToProject,
  onCreateProject,
}: ChatMessageProps) {
  const [projectPickerOpen, setProjectPickerOpen] = useState(false);
  const [projectSaved, setProjectSaved] = useState<string | null>(null);
  const [creatingProject, setCreatingProject] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [creatingBusy, setCreatingBusy] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const pickerRef = useRef<HTMLDivElement>(null);

  // Close picker on outside click
  useEffect(() => {
    if (!projectPickerOpen) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setProjectPickerOpen(false);
        setCreatingProject(false);
        setNewProjectName('');
        setCreateError(null);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [projectPickerOpen]);
  if (type === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div
          className="max-w-[75%] px-4 py-2.5 rounded-2xl rounded-br-lg text-white shadow-sm"
          style={{ backgroundColor: '#1B6B93' }}
        >
          <p className="text-[14px] leading-relaxed">{content}</p>
        </div>
      </div>
    );
  }

  // Guardrail responses have no pulse_report / llm_summary — show the
  // guardrail message directly and skip all results rendering.
  const isGuardrail = response?.guardrail_triggered && response?.guardrail_message;

  // Assistant message — prefer LLM summary from backend, fall back to local generation
  const rawSummary = isGuardrail
    ? response!.guardrail_message!
    : (response?.llm_summary || (response ? generateSummary(response) : content));

  // Parse LLM-generated follow-ups from the markdown and strip them from the body
  const { cleanSummary: summary, followUps: llmFollowUps } = extractFollowUps(rawSummary);
  // Fall back to keyword-based suggestions if the LLM didn't generate any
  const followUps = isGuardrail ? [] : (llmFollowUps.length > 0 ? llmFollowUps : (response ? generateFollowUpsFallback(response) : []));
  const allResults: { result: ValidatedResult; isEdge: boolean }[] = [];

  if (response && response.pulse_report) {
    (response.pulse_report.validated_results || []).forEach((r) =>
      allResults.push({ result: r, isEdge: false })
    );
    (response.pulse_report.edge_cases || []).forEach((r) =>
      allResults.push({ result: r, isEdge: true })
    );
  }

  // Client-side mode filter: re-narrow a past result set when the user
  // changes the lens AFTER the search has already returned. 'all' (or no
  // selection) shows everything. Any other mode shows only results whose
  // matched_modes intersects the active selection.
  const filterModes: ResultMode[] = (activeModes ?? ['all']).filter((m) => m !== 'all');
  const filterSet = new Set<string>(filterModes);
  const filteredResults =
    filterModes.length === 0
      ? allResults
      : allResults.filter(({ result }) =>
          (result.matched_modes ?? []).some((m) => filterSet.has(m)),
        );
  const hiddenByFilter = allResults.length - filteredResults.length;

  return (
    <div className="mb-5 w-full">
      {/* Header row */}
      <div className="flex items-center justify-between mb-2.5">
        <div className="flex items-center gap-2">
          {/* LENA avatar */}
          <Image
            src={branding.avatarSrc}
            alt={branding.name}
            width={24}
            height={24}
            className="rounded-full flex-shrink-0 ring-1 ring-black/5"
          />
          <span className="text-[13px] font-semibold text-slate-700 tracking-tight">{branding.name}</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Add to Project */}
          {response && response.search_id && onAddToProject && !response.guardrail_triggered && (
            <div className="relative" ref={pickerRef}>
              {projectSaved ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-emerald-700 bg-emerald-50 rounded-md">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                  </svg>
                  Saved to {projectSaved}
                </span>
              ) : (
                <button
                  onClick={() => setProjectPickerOpen(!projectPickerOpen)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100/80 rounded-md hover:bg-slate-200/80 transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  Add to Project
                </button>
              )}

              {projectPickerOpen && (
                <div className="absolute right-0 top-full mt-1 w-64 bg-white border border-slate-200/80 rounded-lg shadow-xl shadow-slate-900/5 z-50 overflow-hidden">
                  <div className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-slate-400 border-b border-slate-100 bg-slate-50/80 font-medium">
                    Save to project
                  </div>
                  {(projects || []).map(p => (
                    <button
                      key={p.id}
                      onClick={() => {
                        if (response.search_id) {
                          onAddToProject(response.search_id, p.id);
                          setProjectSaved(p.name);
                          setProjectPickerOpen(false);
                        }
                      }}
                      className="flex items-center gap-2 w-full px-3 py-2 text-[13px] text-slate-700 hover:bg-slate-50 transition-colors"
                    >
                      <span className="text-[13px]">{p.emoji || '📁'}</span>
                      <span className="truncate">{p.name}</span>
                    </button>
                  ))}

                  {onCreateProject && !creatingProject && (
                    <button
                      onClick={() => {
                        setCreatingProject(true);
                        setCreateError(null);
                      }}
                      className="flex items-center gap-2 w-full px-3 py-2 text-[13px] text-lena-600 hover:bg-lena-50 transition-colors border-t border-slate-100"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      <span>{(projects && projects.length > 0) ? 'New project' : 'Create your first project'}</span>
                    </button>
                  )}

                  {onCreateProject && creatingProject && (
                    <form
                      onSubmit={async (e) => {
                        e.preventDefault();
                        const name = newProjectName.trim();
                        if (!name || creatingBusy) return;
                        setCreatingBusy(true);
                        setCreateError(null);
                        try {
                          const created = await onCreateProject(name);
                          if (response.search_id) {
                            onAddToProject(response.search_id, created.id);
                            setProjectSaved(created.name);
                          }
                          setProjectPickerOpen(false);
                          setCreatingProject(false);
                          setNewProjectName('');
                        } catch (err) {
                          setCreateError(err instanceof Error ? err.message : 'Failed to create project');
                        } finally {
                          setCreatingBusy(false);
                        }
                      }}
                      className="border-t border-slate-100 p-2 bg-slate-50/60"
                    >
                      <input
                        autoFocus
                        type="text"
                        value={newProjectName}
                        onChange={(e) => setNewProjectName(e.target.value)}
                        placeholder="Project name"
                        maxLength={80}
                        className="w-full px-2.5 py-1.5 text-[13px] bg-white border border-slate-200 rounded-md outline-none focus:border-lena-400 focus:ring-2 focus:ring-lena-100 text-slate-800 placeholder-slate-400"
                      />
                      {createError && (
                        <p className="text-[11px] text-red-600 mt-1.5 px-0.5">{createError}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2">
                        <button
                          type="submit"
                          disabled={!newProjectName.trim() || creatingBusy}
                          className="flex-1 px-2.5 py-1 text-[12px] font-medium text-white bg-lena-600 rounded-md hover:bg-lena-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                        >
                          {creatingBusy ? 'Creating…' : 'Create & save'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setCreatingProject(false);
                            setNewProjectName('');
                            setCreateError(null);
                          }}
                          className="px-2.5 py-1 text-[12px] font-medium text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Share */}
          {response && onShare && (
            <button
              onClick={() => onShare(response.query)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-600 bg-slate-100/80 rounded-md hover:bg-slate-200/80 transition-colors"
            >
              <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share
            </button>
          )}
        </div>
      </div>

      {/* Natural language summary */}
      <div className="ml-10 space-y-4">
        <FormattedContent text={summary} />

        {/* PULSE status badge — only when pulse_report exists (not for guardrail responses) */}
        {response && response.pulse_report && (
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`px-2 py-0.5 text-[10px] font-semibold rounded-full tracking-wide ${
                response.pulse_report.status === 'validated'
                  ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200/60'
                  : response.pulse_report.status === 'edge_case'
                  ? 'bg-purple-50 text-purple-700 ring-1 ring-purple-200/60'
                  : response.pulse_report.status === 'insufficient_validation'
                  ? 'bg-red-50 text-red-700 ring-1 ring-red-200/60'
                  : 'bg-slate-100 text-slate-600'
              }`}
            >
              PULSE · {(response.pulse_report.status || 'pending').replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())}
            </span>
            <span className="text-[11px] text-slate-500 tabular-nums">
              {Math.round((response.pulse_report.confidence_ratio || 0) * 100)}% confidence
              <span className="mx-1 text-slate-300">·</span>
              {response.response_time_ms}ms
            </span>
          </div>
        )}

        {/* Source status indicators — only when sources exist (not for guardrail responses) */}
        {response && response.sources_queried && response.sources_queried.length > 0 && (
          <div className="flex items-center gap-1 flex-wrap">
            {response.sources_queried.map((src) => {
              const style = getSourceStyle(src);
              return (
                <span key={src} className={`px-1.5 py-0.5 text-[9px] font-semibold rounded ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
              );
            })}
            {Object.keys(response.sources_failed || {}).map((src) => {
              const style = getSourceStyle(src);
              return (
                <span key={src} className="px-1.5 py-0.5 text-[9px] font-semibold rounded bg-slate-50 text-slate-400 line-through">
                  {style.label}
                </span>
              );
            })}
          </div>
        )}

        {/* Source cards — collapsed by default, show top 3 */}
        {filteredResults.length > 0 && (
          <>
            {hiddenByFilter > 0 && (
              <p className="text-xs text-slate-500 italic">
                Filter hiding {hiddenByFilter} result{hiddenByFilter === 1 ? '' : 's'} — select <span className="font-medium">All results</span> to see everything.
              </p>
            )}
            <SourceCardList allResults={filteredResults} query={response?.query || ''} />
          </>
        )}
        {filteredResults.length === 0 && allResults.length > 0 && (
          <p className="text-sm text-slate-500 italic">
            No results match the active filter ({filterModes.join(', ')}).
            Select <span className="font-medium">All results</span> to see {allResults.length} hidden source{allResults.length === 1 ? '' : 's'}.
          </p>
        )}

        {/* Follow-up suggestions */}
        {followUps.length > 0 && onFollowUp && (
          <div className="space-y-2 pt-1">
            <p className="text-[11px] font-medium text-slate-500 tracking-wide">
              Follow-up questions
            </p>
            <div className="flex flex-wrap gap-1.5">
              {followUps.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => onFollowUp(suggestion)}
                  className="px-3 py-1.5 text-[12px] font-medium text-lena-600 bg-lena-50/70 border border-lena-200/50 rounded-full hover:bg-lena-100 hover:border-lena-300/60 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
