'use client';

import React, { useState } from 'react';
import ModalOverlay from './ModalOverlay';

export interface EmailCaptureData {
  email: string;
  institution?: string;
  phone?: string;
  city?: string;
  country?: string;
  dataConsentAccepted: boolean;
}

interface EmailCaptureModalProps {
  isOpen: boolean;
  onSubmit: (data: EmailCaptureData) => void;
  onSkip: () => void;
}

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const COUNTRIES = [
  'Afghanistan', 'Albania', 'Algeria', 'Argentina', 'Australia', 'Austria',
  'Bahrain', 'Bangladesh', 'Belgium', 'Brazil', 'Canada', 'Chile', 'China',
  'Colombia', 'Croatia', 'Czech Republic', 'Denmark', 'Egypt', 'Estonia',
  'Ethiopia', 'Finland', 'France', 'Germany', 'Ghana', 'Greece', 'Hong Kong',
  'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland',
  'Israel', 'Italy', 'Japan', 'Jordan', 'Kazakhstan', 'Kenya', 'Kuwait',
  'Latvia', 'Lebanon', 'Libya', 'Lithuania', 'Luxembourg', 'Malaysia',
  'Mexico', 'Morocco', 'Nepal', 'Netherlands', 'New Zealand', 'Nigeria',
  'Norway', 'Oman', 'Pakistan', 'Peru', 'Philippines', 'Poland', 'Portugal',
  'Qatar', 'Romania', 'Russia', 'Saudi Arabia', 'Serbia', 'Singapore',
  'Slovakia', 'Slovenia', 'South Africa', 'South Korea', 'Spain', 'Sri Lanka',
  'Sweden', 'Switzerland', 'Taiwan', 'Thailand', 'Turkey', 'UAE',
  'Uganda', 'Ukraine', 'United Kingdom', 'United States', 'Uruguay',
  'Venezuela', 'Vietnam', 'Yemen', 'Zambia', 'Zimbabwe',
];

export default function EmailCaptureModal({
  isOpen,
  onSubmit,
  onSkip,
}: EmailCaptureModalProps) {
  const [email, setEmail] = useState('');
  const [institution, setInstitution] = useState('');
  const [phone, setPhone] = useState('');
  const [city, setCity] = useState('');
  const [country, setCountry] = useState('');
  const [dataConsent, setDataConsent] = useState(false);
  const [error, setError] = useState('');

  const isValidEmail = EMAIL_REGEX.test(email);

  const handleSubmit = () => {
    if (!isValidEmail) {
      setError('Please enter a valid email address');
      return;
    }
    if (!dataConsent) {
      setError('Please accept the data processing consent to continue');
      return;
    }
    onSubmit({
      email: email.trim(),
      institution: institution.trim() || undefined,
      phone: phone.trim() || undefined,
      city: city.trim() || undefined,
      country: country || undefined,
      dataConsentAccepted: true,
    });
    setEmail('');
    setInstitution('');
    setPhone('');
    setCity('');
    setCountry('');
    setDataConsent(false);
    setError('');
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && isValidEmail && dataConsent) {
      handleSubmit();
    }
  };

  const handleSkip = () => {
    setEmail('');
    setInstitution('');
    setPhone('');
    setCity('');
    setCountry('');
    setDataConsent(false);
    setError('');
    onSkip();
  };

  const inputClass =
    'w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-lena-500 focus:border-transparent text-slate-900 placeholder-slate-400 text-sm';

  return (
    <ModalOverlay isOpen={isOpen} onClose={handleSkip}>
      <div className="p-8 max-h-[85vh] overflow-y-auto">
        <h1 className="text-2xl font-semibold text-slate-900 mb-2">
          Save your research
        </h1>
        <p className="text-slate-600 mb-5 text-sm">
          Enter your details to save results and get personalized recommendations
        </p>

        <div className="space-y-3 mb-4">
          {/* Email — required */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Email <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => { setEmail(e.target.value); setError(''); }}
              onKeyPress={handleKeyPress}
              placeholder="your@email.com"
              className={inputClass}
              autoFocus
            />
          </div>

          {/* Institution / Company */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Institution / Organisation
            </label>
            <input
              type="text"
              value={institution}
              onChange={(e) => setInstitution(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="e.g. University of Sydney, NHS Trust"
              className={inputClass}
            />
          </div>

          {/* City + Country row */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                City
              </label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="e.g. London"
                className={inputClass}
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1">
                Country
              </label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                className={inputClass + ' bg-white'}
              >
                <option value="">Select country</option>
                {COUNTRIES.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Phone — optional */}
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">
              Phone <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="+61 400 000 000"
              className={inputClass}
            />
          </div>
        </div>

        {/* Data protection consent */}
        <div className="mb-4 bg-slate-50 border border-slate-200 rounded-lg p-3">
          <label className="flex items-start gap-2.5 cursor-pointer">
            <input
              type="checkbox"
              checked={dataConsent}
              onChange={(e) => { setDataConsent(e.target.checked); setError(''); }}
              className="mt-0.5 w-4 h-4 rounded border-slate-300 text-lena-500 focus:ring-lena-500"
            />
            <span className="text-xs text-slate-600 leading-relaxed">
              I consent to LENA processing my personal data to provide research services
              and improve the platform. My data will be handled in accordance with applicable
              data protection laws (GDPR, CCPA, PDPA, and regional equivalents).
              I can withdraw consent or request data deletion at any time by contacting{' '}
              <span className="text-lena-500 font-medium">privacy@lena-research.com</span>.
            </span>
          </label>
        </div>

        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

        <button
          onClick={handleSubmit}
          disabled={!isValidEmail || !dataConsent}
          className="w-full bg-lena-600 hover:bg-lena-700 disabled:bg-slate-300 text-white font-medium py-2 px-4 rounded-lg transition-colors duration-200 mb-3"
        >
          Continue
        </button>

        <button
          onClick={handleSkip}
          className="w-full text-slate-600 hover:text-slate-900 text-sm font-medium py-2 px-4 transition-colors duration-200"
        >
          Skip for now
        </button>

        <p className="text-[10px] text-slate-400 text-center mt-3 leading-relaxed">
          Your data is stored securely. We do not sell or share personal information with third parties.
          See our Privacy Policy for full details.
        </p>
      </div>
    </ModalOverlay>
  );
}
