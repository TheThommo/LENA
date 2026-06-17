'use client';

import { useState } from 'react';
import { product } from '@/config/branding';

interface FaqItem {
  question: string;
  answer: string;
}

const WORKFLOW_STEPS = [
  {
    title: 'Chat — discover evidence',
    body: 'Ask a clinical or research question. LENA searches PubMed, Cochrane, OpenAlex, and more, then cross-validates results with PULSE.',
    where: 'Sidebar → Chat',
  },
  {
    title: 'Projects — stay on topic',
    body: 'Create a project for each research topic (like a Cowork workspace). Select it before searching and every thread on that topic stays grouped together in the cloud.',
    where: 'Sidebar → Projects (+)',
  },
  {
    title: 'My Documents — save papers',
    body: 'When you find a paper worth keeping, expand the source in Chat and click Save to Documents. Build your personal evidence library over time.',
    where: 'Sidebar → My Documents',
  },
  {
    title: 'Profile — personalise LENA',
    body: 'Set your specialty, preferred databases, and communication style. Personal health uploads will live here too, with your consent.',
    where: 'Gear icon → Profile & Settings',
  },
];

const SAVE_GUIDE = [
  { item: 'A single paper from search results', saveTo: 'My Documents', how: 'Expand source → Save to Documents' },
  { item: 'A whole research thread on one topic', saveTo: 'Projects', how: 'Select project → search, or Add to Project' },
  { item: 'Your background & preferences', saveTo: 'Profile & Settings', how: 'Gear icon → fill in profile → Save' },
  { item: 'Preferred databases to search', saveTo: 'Profile & Settings', how: 'Preferred Databases section' },
  { item: 'Export an evidence brief', saveTo: 'Download (not saved)', how: 'Research Panel → Export Evidence Brief' },
];

const FAQ_ITEMS: FaqItem[] = [
  {
    question: 'What is the difference between Projects and My Documents?',
    answer:
      'Projects organise whole research threads by topic — every query, follow-up, and session on that subject stays together (cloud-synced when signed in). My Documents is your evidence library of individual papers you have bookmarked from search results. Think of Projects as the workspace and Documents as the filing cabinet.',
  },
  {
    question: 'Where did My Sources and My Brain go?',
    answer:
      'My Sources merged into My Documents — one place for saved papers. My Brain became Profile & Settings under the gear icon, with personal context and uploads planned for that section.',
  },
  {
    question: 'What is PULSE?',
    answer:
      'PULSE (Published Literature Source Evaluation) cross-references your query against multiple peer-reviewed databases and scores how well the evidence agrees across independent sources.',
  },
  {
    question: 'What do confidence levels mean?',
    answer:
      'High (80%+): strong consensus across sources. Medium (60–79%): moderate agreement. Edge Case (40–59%): evidence exists but sources diverge. Low (<40%): limited agreement — topic may be emerging or under-researched.',
  },
  {
    question: 'Where does LENA get its data?',
    answer:
      `LENA queries ${product.sourceCount} major biomedical databases in real time: ${product.sourceList}. All sources are peer-reviewed or government-maintained.`,
  },
  {
    question: 'Is my data private?',
    answer:
      'Yes. LENA is GDPR and CCPA compliant. Search queries are never sold to third parties. Profile and saved documents are stored on your device today; cloud sync will be optional and consent-based.',
  },
  {
    question: 'Is this medical advice?',
    answer:
      'No. LENA is a research aggregation and validation tool — not a medical professional. Always consult a qualified healthcare provider for medical decisions.',
  },
];

const STATS = [
  { value: product.paperCount, label: 'Papers Indexed' },
  { value: String(product.sourceCount), label: 'Databases' },
  { value: '<30s', label: 'Search Time' },
  { value: '100%', label: 'Peer-Reviewed' },
];

export default function HowItWorks() {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">How It Works</h1>
          <p className="text-sm text-slate-500">
            A clear map of LENA — where to search, where to save, and how it all fits together.
          </p>
        </div>

        {/* 30-second pitch */}
        <section className="mb-10 rounded-2xl bg-gradient-to-br from-lena-500 to-lena-700 p-6 text-white shadow-card">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-white/70 mb-3">The 30-second pitch</p>
          <p className="text-[15px] leading-relaxed text-white/95">
            LENA separates research into four layers: <strong>Chat</strong> to discover evidence across {product.paperCount} papers,
            {' '}<strong>Projects</strong> to keep topic work organised, <strong>My Documents</strong> to build your evidence library,
            and <strong>Profile</strong> so answers are personalised to you — with clear consent and privacy controls.
          </p>
        </section>

        {/* Workflow */}
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Your research flow</h2>
          <div className="space-y-3">
            {WORKFLOW_STEPS.map((step, index) => (
              <div key={step.title} className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 rounded-full bg-lena-50 text-lena-700 text-xs font-bold flex items-center justify-center">
                    {index + 1}
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900">{step.title}</h3>
                    <p className="text-sm text-slate-600 leading-relaxed mt-1">{step.body}</p>
                    <p className="text-[11px] font-medium text-lena-600 mt-2">{step.where}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Where to save what */}
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Where to save what</h2>
          <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/80">
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">You have…</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">Save to…</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wide hidden sm:table-cell">How</th>
                </tr>
              </thead>
              <tbody>
                {SAVE_GUIDE.map((row) => (
                  <tr key={row.item} className="border-b border-slate-100 last:border-0">
                    <td className="px-4 py-3 text-slate-700">{row.item}</td>
                    <td className="px-4 py-3 font-medium text-lena-700">{row.saveTo}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs hidden sm:table-cell">{row.how}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* FAQ */}
        <section className="mb-10">
          <h2 className="text-sm font-semibold text-slate-900 mb-4">Common questions</h2>
          <div className="space-y-3">
            {FAQ_ITEMS.map((item, index) => {
              const isOpen = openIndex === index;
              return (
                <div
                  key={item.question}
                  className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm"
                >
                  <button
                    onClick={() => setOpenIndex(isOpen ? null : index)}
                    className="w-full flex items-center justify-between px-5 py-4 text-left"
                  >
                    <span className="text-sm font-semibold text-slate-900 pr-4">{item.question}</span>
                    <svg
                      className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  <div className={`overflow-hidden transition-all duration-300 ${isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'}`}>
                    <div className="px-5 pb-4">
                      <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{item.answer}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <div className="bg-gradient-to-br from-lena-500 to-lena-700 rounded-2xl p-6 text-white shadow-card">
          <h2 className="text-center text-sm font-semibold uppercase tracking-wide text-white/80 mb-6">
            LENA by the Numbers
          </h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-xs text-white/70 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
