'use client';

import { useState, useMemo, useEffect } from 'react';
import Image from 'next/image';
import { branding } from '@/config/branding';
import type { SearchResponse, ValidatedResult } from '@/lib/api';

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

interface ChatMessageProps {
  type: 'user' | 'assistant';
  content: string;
  response?: SearchResponse;
  onFollowUp?: (query: string) => void;
  onShare?: (title?: string) => void;
}

const SOURCE_COLORS: Record<string, { border: string; bg: string; text: string; label: string }> = {
  pubmed:          { border: 'border-l-[#2563EB]', bg: 'bg-blue-50',    text: 'text-blue-700',    label: 'PubMed' },
  clinical_trials: { border: 'border-l-[#7C3AED]', bg: 'bg-purple-50',  text: 'text-purple-700',  label: 'ClinicalTrials.gov' },
  cochrane:        { border: 'border-l-[#EA580C]', bg: 'bg-orange-50',  text: 'text-orange-700',  label: 'Cochrane' },
  who_iris:        { border: 'border-l-[#0891B2]', bg: 'bg-cyan-50',    text: 'text-cyan-700',    label: 'WHO IRIS' },
  cdc:             { border: 'border-l-[#059669]', bg: 'bg-emerald-50', text: 'text-emerald-700', label: 'CDC' },
  openalex:        { border: 'border-l-[#DC2626]', bg: 'bg-red-50',     text: 'text-red-700',     label: 'OpenAlex' },
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

function generateFollowUps(response: SearchResponse): string[] {
  const keywords = response.pulse_report.consensus_keywords.slice(0, 3);
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

function SourceCard({ result, isEdgeCase, index }: { result: ValidatedResult; isEdgeCase: boolean; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const style = getSourceStyle(result.source);
  const scoreBadge = getPulseScoreBadge(result.relevance_score);

  return (
    <div
      data-source-index={index}
      className={`border-l-3 ${style.border} rounded-md border border-slate-200 bg-white transition-all hover:shadow-sm`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left px-3 py-2"
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex-1 min-w-0 flex items-center gap-2">
            <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded ${style.bg} ${style.text} flex-shrink-0`}>
              {style.label}
            </span>
            {result.year > 0 && (
              <span className="text-[10px] text-slate-400 flex-shrink-0">{result.year}</span>
            )}
            <span className={`px-1.5 py-0.5 text-[10px] font-semibold rounded-full ${scoreBadge.className} flex-shrink-0`}>
              {scoreBadge.label}
            </span>
            {isEdgeCase && (
              <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-purple-100 text-purple-800 flex-shrink-0">
                Edge
              </span>
            )}
            {result.matched_modes?.includes('herbal') && (
              <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-100 text-emerald-800 flex-shrink-0" title="Herbal / alternative medicine result">
                Herbal
              </span>
            )}
            {result.matched_modes?.includes('outlier') && (
              <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded-full bg-amber-100 text-amber-800 flex-shrink-0" title="Authored by a researcher in the outlier list">
                Outlier
              </span>
            )}
            <p className="text-xs font-medium text-slate-900 truncate">
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
            <button className="inline-flex items-center gap-1 px-2.5 py-1 text-[10px] font-medium text-slate-700 bg-slate-100 rounded-md hover:bg-slate-200 transition-colors">
              Save
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

const INITIAL_VISIBLE = 3;

function SourceCardList({ allResults }: { allResults: { result: ValidatedResult; isEdge: boolean }[] }) {
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
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
        Sources ({allResults.length})
      </p>
      <div className="space-y-1.5">
        {visible.map(({ result, isEdge }, i) => (
          <SourceCard key={`${result.source}-${result.title}-${i}`} result={result} isEdgeCase={isEdge} index={i} />
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
}: ChatMessageProps) {
  if (type === 'user') {
    return (
      <div className="flex justify-end mb-4">
        <div
          className="max-w-[75%] px-5 py-3 rounded-2xl rounded-br-md text-white"
          style={{ backgroundColor: '#1B6B93' }}
        >
          <p className="text-sm leading-relaxed">{content}</p>
        </div>
      </div>
    );
  }

  // Assistant message — prefer LLM summary from backend, fall back to local generation
  const summary = response?.llm_summary || (response ? generateSummary(response) : content);
  const followUps = response ? generateFollowUps(response) : [];
  const allResults: { result: ValidatedResult; isEdge: boolean }[] = [];

  if (response) {
    response.pulse_report.validated_results.forEach((r) =>
      allResults.push({ result: r, isEdge: false })
    );
    response.pulse_report.edge_cases.forEach((r) =>
      allResults.push({ result: r, isEdge: true })
    );
  }

  return (
    <div className="mb-6 w-full">
      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2.5">
          {/* LENA avatar */}
          <Image
            src={branding.avatarSrc}
            alt={branding.name}
            width={28}
            height={28}
            className="rounded-full flex-shrink-0"
          />
          <span className="text-sm font-semibold text-slate-700">{branding.name}</span>
        </div>

        {response && onShare && (
          <button
            onClick={() => onShare(response.query)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
            </svg>
            Share All
          </button>
        )}
      </div>

      {/* Natural language summary */}
      <div className="ml-10 space-y-4">
        <FormattedContent text={summary} />

        {/* PULSE status badge */}
        {response && (
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`px-2.5 py-1 text-xs font-semibold rounded-full ${
                response.pulse_report.status === 'validated'
                  ? 'bg-green-100 text-green-800'
                  : response.pulse_report.status === 'edge_case'
                  ? 'bg-purple-100 text-purple-800'
                  : response.pulse_report.status === 'insufficient_validation'
                  ? 'bg-red-100 text-red-800'
                  : 'bg-slate-100 text-slate-700'
              }`}
            >
              PULSE: {response.pulse_report.status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
            </span>
            <span className="text-xs text-slate-500">
              {Math.round(response.pulse_report.confidence_ratio * 100)}% confidence
              &middot; {response.response_time_ms}ms
            </span>
          </div>
        )}

        {/* Source status indicators */}
        {response && (
          <div className="flex items-center gap-1.5 flex-wrap">
            {response.sources_queried.map((src) => {
              const style = getSourceStyle(src);
              return (
                <span key={src} className={`px-1.5 py-0.5 text-[10px] font-semibold rounded ${style.bg} ${style.text}`}>
                  {style.label} ✓
                </span>
              );
            })}
            {Object.keys(response.sources_failed).map((src) => {
              const style = getSourceStyle(src);
              return (
                <span key={src} className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-red-50 text-red-400 line-through">
                  {style.label}
                </span>
              );
            })}
          </div>
        )}

        {/* Source cards — collapsed by default, show top 3 */}
        {allResults.length > 0 && (
          <SourceCardList allResults={allResults} />
        )}

        {/* Follow-up suggestions */}
        {followUps.length > 0 && onFollowUp && (
          <div className="space-y-2 pt-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Follow-up questions
            </p>
            <div className="flex flex-wrap gap-2">
              {followUps.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => onFollowUp(suggestion)}
                  className="px-3.5 py-2 text-xs font-medium text-[#1B6B93] bg-[#1B6B93]/5 border border-[#1B6B93]/20 rounded-full hover:bg-[#1B6B93]/10 hover:border-[#1B6B93]/40 transition-all"
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
