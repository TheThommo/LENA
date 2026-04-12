'use client';

import { useState } from 'react';

interface HowItWorksProps {}

interface FaqItem {
  question: string;
  answer: string;
}

const FAQ_ITEMS: FaqItem[] = [
  {
    question: 'What is PULSE?',
    answer:
      'PULSE stands for Published Literature Source Evaluation. It is LENA\'s cross-reference validation engine that compares your query against multiple peer-reviewed databases simultaneously, scoring how well the available evidence agrees across independent sources.',
  },
  {
    question: 'What do confidence levels mean?',
    answer:
      'High (80%+): Strong consensus across multiple peer-reviewed sources. Medium (60-79%): Moderate agreement with some variation between sources. Edge Case (40-59%): A unique angle where evidence exists but sources diverge. Low (<40%): Limited agreement across databases \u2014 the topic may be emerging or under-researched.',
  },
  {
    question: 'Where does LENA get its data?',
    answer:
      'LENA queries five major biomedical databases in real time: PubMed (NIH/NLM), ClinicalTrials.gov, the Cochrane Library, WHO IRIS (World Health Organization), and CDC Open Data. All sources are peer-reviewed or government-maintained.',
  },
  {
    question: 'What does the Natural & Herbal toggle do?',
    answer:
      'When enabled, the Natural & Herbal toggle includes results from alternative and complementary medicine sources alongside conventional databases. These results are scored with the same PULSE rigor \u2014 no special treatment or inflated confidence.',
  },
  {
    question: 'How does persona detection work?',
    answer:
      'LENA detects whether you are a clinician, researcher, student, or general user and adjusts the tone, terminology depth, and summary style accordingly. Importantly, persona detection never changes the underlying results or PULSE scoring \u2014 only presentation.',
  },
  {
    question: 'Who can I share results with?',
    answer:
      'You can share research results with six recipient types: Patient, Colleague, Student, Supervisor, Family, or Other. Sharing helps LENA understand how research flows between different personas and improves future recommendations.',
  },
  {
    question: 'Is my data private?',
    answer:
      'Yes. LENA is fully GDPR and CCPA compliant. Your search queries and session data are never sold or shared with third parties. Analytics are aggregated and anonymised. You can request data deletion at any time.',
  },
  {
    question: 'Is this medical advice?',
    answer:
      'No. LENA is a research aggregation and validation tool \u2014 not a medical professional. It surfaces and scores published evidence but does not diagnose, treat, or recommend. Always consult a qualified healthcare provider for medical decisions.',
  },
];

const STATS = [
  { value: '250M+', label: 'Papers Indexed' },
  { value: '6', label: 'Databases' },
  { value: '<30s', label: 'Search Time' },
  { value: '100%', label: 'Peer-Reviewed' },
];

export default function HowItWorks({}: HowItWorksProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  const toggle = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="text-center mb-10">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">How It Works</h1>
        <p className="text-sm text-gray-500">
          Everything you need to know about LENA and the PULSE engine.
        </p>
      </div>

      {/* FAQ Accordion */}
      <div className="space-y-3 mb-12">
        {FAQ_ITEMS.map((item, index) => {
          const isOpen = openIndex === index;
          return (
            <div
              key={index}
              className="bg-white border border-gray-200 rounded-xl overflow-hidden shadow-sm transition-shadow hover:shadow-md"
            >
              <button
                onClick={() => toggle(index)}
                className="w-full flex items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-sm font-semibold text-gray-900 pr-4">
                  {item.question}
                </span>
                <svg
                  className={`w-4 h-4 text-gray-400 flex-shrink-0 transition-transform duration-200 ${
                    isOpen ? 'rotate-180' : ''
                  }`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              <div
                className={`overflow-hidden transition-all duration-300 ease-in-out ${
                  isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                }`}
              >
                <div className="px-5 pb-4">
                  <p className="text-sm text-gray-600 leading-relaxed whitespace-pre-line">
                    {item.answer}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* LENA by the Numbers */}
      <div className="bg-gradient-to-br from-[#1B6B93] to-[#145372] rounded-2xl p-6 text-white shadow-lg">
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
  );
}
