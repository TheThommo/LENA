'use client';

import React, { useState } from 'react';
import { registerFeatureInterest } from '@/lib/api';

interface ComingSoonProps {
  title: string;
  description: string;
  features?: { icon: string; title: string; description: string }[];
  badgeText?: string;
  feature?: string;
  authToken?: string | null;
}

export default function ComingSoon({
  title,
  description,
  features,
  badgeText = 'Early access waitlist',
  feature = 'general',
  authToken,
}: ComingSoonProps) {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'done' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleNotify = async () => {
    const trimmed = email.trim();
    if (!trimmed) return;
    setStatus('sending');
    try {
      const res = await registerFeatureInterest(trimmed, feature, authToken);
      setMessage(res.message);
      setStatus('done');
    } catch {
      setStatus('error');
      setMessage('Could not save your email — try again later.');
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] px-6">
      <div className="max-w-lg w-full text-center">
        <span className="inline-block px-3 py-1 bg-amber-100 text-amber-700 text-xs font-semibold rounded-full mb-4">
          {badgeText}
        </span>
        <h2 className="text-2xl font-bold text-slate-900 mb-2">{title}</h2>
        <p className="text-slate-500 mb-8 leading-relaxed">{description}</p>

        {features && features.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            {features.map((f, i) => (
              <div key={i} className="border border-slate-200 rounded-xl p-4 text-left bg-white">
                <span className="text-2xl mb-2 block">{f.icon}</span>
                <h4 className="text-sm font-semibold text-slate-800 mb-1">{f.title}</h4>
                <p className="text-xs text-slate-500 leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        )}

        <div className="bg-lena-50 border border-lena-200 rounded-xl p-6">
          <p className="text-sm text-lena-700 font-medium mb-3">Get notified when this launches</p>
          <div className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleNotify(); }}
              placeholder="your@email.com"
              disabled={status === 'sending' || status === 'done'}
              className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:border-lena-500"
            />
            <button
              onClick={handleNotify}
              disabled={status === 'sending' || status === 'done' || !email.trim()}
              className="px-4 py-2 bg-lena-500 text-white text-sm font-medium rounded-lg hover:bg-lena-600 transition-colors disabled:opacity-50"
            >
              {status === 'done' ? 'On the list' : 'Notify Me'}
            </button>
          </div>
          {message && (
            <p className={`text-xs mt-3 ${status === 'error' ? 'text-red-600' : 'text-lena-700'}`}>
              {message}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export const COMMUNITY_CONFIG = {
  title: 'Community',
  description: 'Connect with researchers, clinicians, and students. Share insights, discuss findings, and collaborate on evidence-based research.',
  feature: 'community',
  features: [
    { icon: '💬', title: 'Discussion Forums', description: 'Topic-based discussions on latest research' },
    { icon: '👥', title: 'Peer Groups', description: 'Connect with others in your specialty' },
    { icon: '📊', title: 'Shared Research', description: 'Collaborative research collections' },
    { icon: '🏆', title: 'Expert Panels', description: 'Q&A with leading researchers' },
  ],
};

export const CONTRIBUTION_CONFIG = {
  title: 'Contribution',
  description: 'Help build the future of evidence-based research. Submit papers, validate findings, and propose new sources for LENA to index.',
  feature: 'contribution',
  features: [
    { icon: '📄', title: 'Submit Papers', description: 'Contribute research papers to LENA\'s index' },
    { icon: '✅', title: 'Expert Validation', description: 'Help validate PULSE scoring accuracy' },
    { icon: '🔗', title: 'Propose Sources', description: 'Suggest new databases for LENA to integrate' },
    { icon: '💪', title: 'Fitness & Wellness', description: 'Expand evidence for exercise and nutrition' },
  ],
};
