'use client';

import { useState, useEffect, useCallback } from 'react';

interface UserProfile {
  specialty: string;
  role: string;
  institution: string;
  focusAreas: string[];
  preferredSources: string[];
  yearsExperience: string;
  researchInterests: string;
  communicationStyle: 'clinical' | 'academic' | 'simplified' | 'default';
  notes: string;
}

const LS_KEY = 'lena_user_brain';

const DEFAULT_PROFILE: UserProfile = {
  specialty: '',
  role: '',
  institution: '',
  focusAreas: [],
  preferredSources: [],
  yearsExperience: '',
  researchInterests: '',
  communicationStyle: 'default',
  notes: '',
};

const AVAILABLE_SOURCES = [
  { key: 'pubmed', label: 'PubMed' },
  { key: 'clinical_trials', label: 'ClinicalTrials.gov' },
  { key: 'cochrane', label: 'Cochrane' },
  { key: 'who_iris', label: 'WHO IRIS' },
  { key: 'cdc', label: 'CDC' },
  { key: 'openalex', label: 'OpenAlex (250M+ papers)' },
];

const COMMUNICATION_STYLES = [
  { key: 'default' as const, label: 'Adaptive', desc: 'LENA adjusts based on your persona' },
  { key: 'clinical' as const, label: 'Clinical', desc: 'Direct, evidence-focused, minimal preamble' },
  { key: 'academic' as const, label: 'Academic', desc: 'Detailed methodology, citations-first' },
  { key: 'simplified' as const, label: 'Simplified', desc: 'Plain language, key takeaways first' },
];

const SPECIALTIES = [
  'Cardiology', 'Oncology', 'Neurology', 'Psychiatry', 'Endocrinology',
  'Pulmonology', 'Gastroenterology', 'Nephrology', 'Rheumatology', 'Dermatology',
  'Infectious Disease', 'Emergency Medicine', 'Critical Care', 'Paediatrics',
  'Obstetrics & Gynaecology', 'Orthopaedics', 'Radiology', 'Pathology',
  'Anaesthesiology', 'General Practice', 'Public Health', 'Pharmacology',
  'Physiotherapy', 'Nursing', 'Nutrition & Dietetics', 'Other',
];

export default function MyBrain() {
  const [profile, setProfile] = useState<UserProfile>(DEFAULT_PROFILE);
  const [saved, setSaved] = useState(false);
  const [focusInput, setFocusInput] = useState('');

  useEffect(() => {
    try {
      const stored = localStorage.getItem(LS_KEY);
      if (stored) setProfile(JSON.parse(stored));
    } catch {}
  }, []);

  const saveProfile = useCallback(() => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(profile));
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
  }, [profile]);

  const updateField = <K extends keyof UserProfile>(key: K, value: UserProfile[K]) => {
    setProfile(prev => ({ ...prev, [key]: value }));
  };

  const addFocusArea = () => {
    const trimmed = focusInput.trim();
    if (trimmed && !profile.focusAreas.includes(trimmed)) {
      updateField('focusAreas', [...profile.focusAreas, trimmed]);
      setFocusInput('');
    }
  };

  const removeFocusArea = (area: string) => {
    updateField('focusAreas', profile.focusAreas.filter(a => a !== area));
  };

  const toggleSource = (source: string) => {
    if (profile.preferredSources.includes(source)) {
      updateField('preferredSources', profile.preferredSources.filter(s => s !== source));
    } else {
      updateField('preferredSources', [...profile.preferredSources, source]);
    }
  };

  const clearAll = () => {
    setProfile(DEFAULT_PROFILE);
    localStorage.removeItem(LS_KEY);
  };

  const completeness = (() => {
    let filled = 0;
    let total = 7;
    if (profile.specialty) filled++;
    if (profile.role) filled++;
    if (profile.institution) filled++;
    if (profile.focusAreas.length > 0) filled++;
    if (profile.yearsExperience) filled++;
    if (profile.researchInterests) filled++;
    if (profile.communicationStyle !== 'default') filled++;
    return Math.round((filled / total) * 100);
  })();

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <div
              className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                <path d="M12 2C12 2 14.5 8.5 15.5 9.5C16.5 10.5 22 12 22 12C22 12 16.5 13.5 15.5 14.5C14.5 15.5 12 22 12 22C12 22 9.5 15.5 8.5 14.5C7.5 13.5 2 12 2 12C2 12 7.5 10.5 8.5 9.5C9.5 8.5 12 2 12 2Z" />
              </svg>
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-900">My Brain</h2>
              <p className="text-sm text-slate-500">Help LENA understand you better</p>
            </div>
          </div>
          <p className="text-sm text-slate-500 leading-relaxed mt-3">
            The more LENA knows about your background and research focus, the more relevant and precisely tailored your results will be. This information stays on your device and shapes how LENA interprets queries, prioritises sources, and frames findings.
          </p>
        </div>

        {/* Completeness indicator */}
        <div className="bg-slate-50 rounded-xl p-4 mb-6 border border-slate-100">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Profile Completeness</span>
            <span className={`text-sm font-bold ${completeness >= 70 ? 'text-emerald-600' : completeness >= 40 ? 'text-amber-600' : 'text-slate-400'}`}>
              {completeness}%
            </span>
          </div>
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: `${completeness}%`,
                background: completeness >= 70 ? '#059669' : completeness >= 40 ? '#D97706' : '#94A3B8',
              }}
            />
          </div>
          <p className="text-[11px] text-slate-400 mt-2">
            {completeness < 30 && 'Start by telling LENA your specialty and role.'}
            {completeness >= 30 && completeness < 70 && 'Good start. Adding focus areas and research interests will sharpen your results.'}
            {completeness >= 70 && 'LENA has strong context about your background. Results will be well-tailored.'}
          </p>
        </div>

        <div className="space-y-6">
          {/* Specialty & Role */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-4">Professional Background</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Specialty</label>
                <select
                  value={profile.specialty}
                  onChange={e => updateField('specialty', e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all"
                >
                  <option value="">Select specialty...</option>
                  {SPECIALTIES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Role</label>
                <input
                  type="text"
                  value={profile.role}
                  onChange={e => updateField('role', e.target.value)}
                  placeholder="e.g. Senior Registrar, PhD Candidate"
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Institution</label>
                <input
                  type="text"
                  value={profile.institution}
                  onChange={e => updateField('institution', e.target.value)}
                  placeholder="e.g. Royal Melbourne Hospital"
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Experience</label>
                <select
                  value={profile.yearsExperience}
                  onChange={e => updateField('yearsExperience', e.target.value)}
                  className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all"
                >
                  <option value="">Select...</option>
                  <option value="student">Student</option>
                  <option value="0-2">0-2 years</option>
                  <option value="3-5">3-5 years</option>
                  <option value="5-10">5-10 years</option>
                  <option value="10-20">10-20 years</option>
                  <option value="20+">20+ years</option>
                </select>
              </div>
            </div>
          </section>

          {/* Research Focus Areas */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Research Focus Areas</h3>
            <p className="text-xs text-slate-400 mb-3">Add topics LENA should prioritise when analysing results for you.</p>

            <div className="flex gap-2 mb-3">
              <input
                type="text"
                value={focusInput}
                onChange={e => setFocusInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addFocusArea(); } }}
                placeholder="e.g. Heart failure with preserved EF"
                className="flex-1 text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all"
              />
              <button
                onClick={addFocusArea}
                disabled={!focusInput.trim()}
                className="px-4 py-2 text-sm font-medium text-white rounded-lg disabled:opacity-40 transition-all"
                style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
              >
                Add
              </button>
            </div>

            {profile.focusAreas.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {profile.focusAreas.map(area => (
                  <span
                    key={area}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#1B6B93] bg-[#1B6B93]/5 border border-[#1B6B93]/15 rounded-full"
                  >
                    {area}
                    <button
                      onClick={() => removeFocusArea(area)}
                      className="text-[#1B6B93]/40 hover:text-red-500 transition-colors"
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 italic">No focus areas added yet. These help LENA weight results toward your specific interests.</p>
            )}
          </section>

          {/* Research Interests (free text) */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Research Context</h3>
            <p className="text-xs text-slate-400 mb-3">Tell LENA about your current research projects, interests, or what you are trying to accomplish.</p>
            <textarea
              value={profile.researchInterests}
              onChange={e => updateField('researchInterests', e.target.value)}
              placeholder="e.g. I'm currently working on a systematic review of SGLT2 inhibitors in heart failure with preserved ejection fraction. I'm particularly interested in real-world evidence and patient-reported outcomes..."
              rows={4}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all resize-none leading-relaxed"
            />
          </section>

          {/* Preferred Sources */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Preferred Sources</h3>
            <p className="text-xs text-slate-400 mb-3">Select databases LENA should prioritise. All sources are still searched, but preferred ones are weighted higher.</p>
            <div className="space-y-2">
              {AVAILABLE_SOURCES.map(src => {
                const isSelected = profile.preferredSources.includes(src.key);
                return (
                  <button
                    key={src.key}
                    onClick={() => toggleSource(src.key)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${
                      isSelected
                        ? 'border-[#1B6B93]/30 bg-[#1B6B93]/5'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <div className={`w-5 h-5 rounded border-2 flex items-center justify-center flex-shrink-0 transition-colors ${
                      isSelected ? 'border-[#1B6B93] bg-[#1B6B93]' : 'border-slate-300'
                    }`}>
                      {isSelected && (
                        <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                    <span className={`text-sm font-medium ${isSelected ? 'text-[#1B6B93]' : 'text-slate-700'}`}>
                      {src.label}
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Communication Style */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Communication Style</h3>
            <p className="text-xs text-slate-400 mb-3">How should LENA present findings to you?</p>
            <div className="grid grid-cols-2 gap-2">
              {COMMUNICATION_STYLES.map(style => {
                const isSelected = profile.communicationStyle === style.key;
                return (
                  <button
                    key={style.key}
                    onClick={() => updateField('communicationStyle', style.key)}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      isSelected
                        ? 'border-[#1B6B93]/30 bg-[#1B6B93]/5'
                        : 'border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    <p className={`text-sm font-medium mb-0.5 ${isSelected ? 'text-[#1B6B93]' : 'text-slate-700'}`}>
                      {style.label}
                    </p>
                    <p className="text-[11px] text-slate-400 leading-snug">{style.desc}</p>
                  </button>
                );
              })}
            </div>
          </section>

          {/* Additional Notes */}
          <section className="bg-white border border-slate-200 rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Additional Notes</h3>
            <p className="text-xs text-slate-400 mb-3">Anything else LENA should know about you or your work.</p>
            <textarea
              value={profile.notes}
              onChange={e => updateField('notes', e.target.value)}
              placeholder="e.g. I prefer Australian/UK spelling in reports. I often search for paediatric populations..."
              rows={3}
              className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:border-[#1B6B93] focus:ring-2 focus:ring-[#1B6B93]/10 transition-all resize-none leading-relaxed"
            />
          </section>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between mt-8 pb-8">
          <button
            onClick={clearAll}
            className="text-xs text-slate-400 hover:text-red-500 transition-colors"
          >
            Clear all data
          </button>
          <button
            onClick={saveProfile}
            className={`px-6 py-2.5 text-sm font-medium text-white rounded-xl transition-all ${
              saved ? 'bg-emerald-500' : 'hover:opacity-90'
            }`}
            style={saved ? undefined : { background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
          >
            {saved ? 'Profile Saved' : 'Save Profile'}
          </button>
        </div>

        {/* Privacy notice */}
        <div className="bg-slate-50 rounded-xl p-4 border border-slate-100 mb-8">
          <div className="flex items-start gap-2">
            <svg className="w-4 h-4 text-slate-400 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            <p className="text-xs text-slate-500 leading-relaxed">
              Your profile is stored locally on this device and is never sent to external servers. It is used only to personalise your LENA experience. When you sign in, this data will optionally sync to your encrypted account.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
