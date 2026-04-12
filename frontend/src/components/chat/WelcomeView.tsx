'use client';

import { Sparkles } from 'lucide-react';

interface WelcomeViewProps {
  persona: string;
  onPromptClick: (query: string) => void;
}

const PERSONA_PROMPTS: Record<string, string[]> = {
  general: [
    'Find recent research on COVID-19 long-term effects',
    'What does the evidence say about intermittent fasting?',
    'Compare treatment options for migraine prevention',
  ],
  clinician: [
    'Recent RCTs on GLP-1 agonists for cardiovascular outcomes',
    'Evidence for early vs delayed surgery in appendicitis',
    'Drug interactions with metformin in elderly patients',
  ],
  medical_student: [
    'What are the latest guidelines for managing hypertension?',
    'Compare ACE inhibitors vs ARBs for first-line treatment',
    'Explain the pathophysiology of Type 2 diabetes',
  ],
  pharmacist: [
    'Drug interactions with direct oral anticoagulants',
    'Biosimilar efficacy compared to reference biologics',
    'Pharmacogenomics and warfarin dosing',
  ],
  researcher: [
    'Systematic reviews on CRISPR applications in oncology',
    'Meta-analysis methodology for heterogeneous clinical trials',
    'Research gaps in rare disease therapeutics',
  ],
  lecturer: [
    'Evidence-based medicine teaching methodologies',
    'Simulation-based education outcomes in nursing',
    'Competency assessment tools for clinical training',
  ],
  physiotherapist: [
    'Manual therapy vs exercise for chronic low back pain',
    'Exercise prescription evidence for type 2 diabetes',
    'Dry needling evidence for myofascial trigger points',
  ],
  patient: [
    'Natural remedies for anxiety with clinical evidence',
    'What does research say about intermittent fasting?',
    'Probiotics for gut health - what does the evidence say?',
  ],
};

const TRENDING_TOPICS = [
  { topic: 'GLP-1 receptor agonists', count: 47 },
  { topic: 'Long COVID treatment', count: 34 },
  { topic: 'AI in diagnostic imaging', count: 28 },
];

function formatPersonaLabel(persona: string): string {
  return persona
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function WelcomeView({ persona, onPromptClick }: WelcomeViewProps) {
  const prompts = PERSONA_PROMPTS[persona] || PERSONA_PROMPTS.general;

  return (
    <div className="flex flex-col items-center justify-center max-w-2xl mx-auto px-4 py-16">
      {/* LENA avatar */}
      <div className="w-14 h-14 flex items-center justify-center mb-6 shadow-lg shadow-[#1B6B93]/20" style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)', borderRadius: 16 }}>
        <Sparkles size={28} color="white" />
      </div>

      {/* Heading */}
      <h1 className="text-3xl font-bold text-slate-900 text-center mb-3">
        What would you like to research?
      </h1>
      <p className="text-slate-500 text-center mb-10 max-w-lg leading-relaxed">
        Search 40+ million medical papers in seconds, cross-referenced by AI for accuracy.
      </p>

      {/* Suggested prompts */}
      <div className="w-full mb-10">
        <div className="flex items-center gap-2 mb-4">
          {/* Gear icon */}
          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Suggested for {formatPersonaLabel(persona)}
          </span>
        </div>

        <div className="space-y-3">
          {prompts.map((prompt) => (
            <button
              key={prompt}
              onClick={() => onPromptClick(prompt)}
              className="w-full flex items-center gap-3 p-4 text-left rounded-xl border border-slate-200 bg-white hover:border-[#1B6B93]/30 hover:bg-[#1B6B93]/5 hover:shadow-sm transition-all group"
            >
              {/* Search icon */}
              <div className="w-8 h-8 rounded-lg bg-slate-100 group-hover:bg-[#1B6B93]/10 flex items-center justify-center flex-shrink-0 transition-colors">
                <svg className="w-4 h-4 text-slate-400 group-hover:text-[#1B6B93]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
              <span className="text-sm text-slate-700 group-hover:text-slate-900 transition-colors">
                {prompt}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Trending topics */}
      <div className="w-full">
        <div className="flex items-center gap-2 mb-4">
          {/* Trend icon */}
          <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Trending this week
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          {TRENDING_TOPICS.map(({ topic, count }) => (
            <button
              key={topic}
              onClick={() => onPromptClick(topic)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-slate-200 bg-white hover:border-[#1B6B93]/30 hover:bg-[#1B6B93]/5 transition-all group"
            >
              <span className="text-sm text-slate-700 group-hover:text-slate-900">{topic}</span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium text-slate-500 bg-slate-100 rounded-full group-hover:bg-[#1B6B93]/10 group-hover:text-[#1B6B93]">
                {count}
                {/* Small trend-up arrow */}
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 10l7-7m0 0l7 7m-7-7v18" />
                </svg>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
