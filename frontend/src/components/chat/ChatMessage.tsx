'use client';

import { useState } from 'react';
import { Sparkles } from 'lucide-react';
import type { SearchResponse, ValidatedResult } from '@/lib/api';

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

function SourceCard({ result, isEdgeCase }: { result: ValidatedResult; isEdgeCase: boolean }) {
  const [expanded, setExpanded] = useState(false);
  const style = getSourceStyle(result.source);
  const scoreBadge = getPulseScoreBadge(result.relevance_score);

  return (
    <div
      className={`border-l-4 ${style.border} rounded-lg border border-slate-200 bg-white transition-all hover:shadow-sm`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full text-left p-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1.5">
              <span className={`px-2 py-0.5 text-xs font-semibold rounded ${style.bg} ${style.text}`}>
                {style.label}
              </span>
              {result.year > 0 && (
                <span className="text-xs text-slate-400">{result.year}</span>
              )}
              <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${scoreBadge.className}`}>
                {scoreBadge.label}
              </span>
              {isEdgeCase && (
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                  Edge Case
                </span>
              )}
            </div>
            <p className="text-sm font-medium text-slate-900 leading-snug line-clamp-2">
              {result.title}
            </p>
          </div>
          <span
            className={`text-slate-400 text-xs mt-1 transition-transform flex-shrink-0 ${
              expanded ? 'rotate-180' : ''
            }`}
          >
            &#9660;
          </span>
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-slate-100 pt-3">
          {/* Keywords as summary */}
          {result.keywords.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.keywords.map((kw) => (
                <span
                  key={kw}
                  className="px-2 py-0.5 text-xs text-slate-600 bg-slate-100 rounded-full"
                >
                  {kw}
                </span>
              ))}
            </div>
          )}

          {result.doi && (
            <p className="text-xs text-slate-500 font-mono">DOI: {result.doi}</p>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            <a
              href={result.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-[#1B6B93] rounded-lg hover:bg-[#155a7a] transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              View Full
            </a>
            <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
              </svg>
              Cite
            </button>
            <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
              </svg>
              Save
            </button>
            <button className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors">
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z" />
              </svg>
              Share
            </button>
          </div>
        </div>
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

  // Assistant message
  const summary = response ? generateSummary(response) : content;
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
          <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0" style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}>
            <Sparkles size={14} color="white" />
          </div>
          <span className="text-sm font-semibold text-slate-700">LENA</span>
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
        <p className="text-sm text-slate-700 leading-relaxed">{summary}</p>

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

        {/* Source cards */}
        {allResults.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Sources ({allResults.length})
            </p>
            <div className="space-y-2">
              {allResults.map(({ result, isEdge }, i) => (
                <SourceCard key={`${result.source}-${result.title}-${i}`} result={result} isEdgeCase={isEdge} />
              ))}
            </div>
          </div>
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
