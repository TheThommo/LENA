import Link from 'next/link';
import { BrandMark } from '@/components/brand/BrandMark';
import { branding } from '@/config/branding';

export const metadata = {
  title: `Privacy Policy — ${branding.name}`,
  description: 'How LENA collects and uses search queries, personas, and account data for research and product improvement.',
};

export default function PrivacyPage() {
  return (
    <div className="min-h-dvh bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/">
            <BrandMark height={36} />
          </Link>
          <Link href="/terms" className="text-sm text-lena-700 hover:text-lena-800 font-medium">
            Terms of Service
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10 prose prose-slate prose-sm sm:prose-base">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Privacy Policy</h1>
        <p className="text-slate-500 text-sm mb-8">Last updated: 14 July 2026</p>

        <section className="space-y-4 text-[15px] leading-relaxed text-slate-700">
          <p>
            LENA ({branding.name}) helps you find and validate biomedical research evidence.
            This policy explains what we collect, why we collect it, and how we use it.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">1. Data we collect for research</h2>
          <p>
            To understand users, personas, and search behaviour — and to fine-tune trends,
            ranking, and product quality — we capture:
          </p>
          <ul className="list-disc pl-5 space-y-1">
            <li>Search queries you submit</li>
            <li>Persona / role selections (e.g. clinician, researcher, student)</li>
            <li>Usage signals such as session counts, sources used, and PULSE outcomes</li>
            <li>Approximate location derived from IP (city / country) when available</li>
            <li>Account details you provide (name, email) when you register or leave a lead</li>
          </ul>
          <p>
            We use this information <strong>for research and product improvement purposes only</strong>.
            We do not sell search queries or personal data to third parties.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">2. Anonymity &amp; product disclaimers</h2>
          <p>
            In our product disclaimers and user-facing notices, we describe research analytics as{' '}
            <strong>anonymous</strong> — meaning we analyse search themes, persona mix, and trends
            in aggregate wherever practical, without publishing individual identity with queries.
          </p>
          <p>
            During the closed beta / early launch period, authorised LENA operators may review
            attributable session and account activity (including who searched what) solely to
            improve quality, support, and launch readiness. After beta hardens, research reporting
            remains aggregate and anonymised for day-to-day product work.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">3. How we use data</h2>
          <ul className="list-disc pl-5 space-y-1">
            <li>Operate and secure the service</li>
            <li>Personalise answers based on persona and profile preferences you set</li>
            <li>Measure funnel, conversion, and product-market fit</li>
            <li>Identify trending clinical and research topics across personas</li>
            <li>Send transactional email you requested (e.g. confirmation, password reset)</li>
          </ul>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">4. Legal bases &amp; rights</h2>
          <p>
            Where GDPR/CCPA or similar laws apply, we process data based on contract (to deliver
            the service), legitimate interests (product research and security), and/or consent
            (where we ask for it). You may request access, correction, or deletion by emailing{' '}
            <a className="text-lena-700 font-medium" href="mailto:privacy@lena-research.com">
              privacy@lena-research.com
            </a>
            .
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">5. Retention &amp; security</h2>
          <p>
            Analytics and search logs are retained only as long as needed for research, abuse
            prevention, and service operation. Data is stored with industry-standard access
            controls. Platform admin access is limited to authorised staff.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">6. Contact</h2>
          <p>
            Privacy questions: {' '}
            <a className="text-lena-700 font-medium" href="mailto:privacy@lena-research.com">
              privacy@lena-research.com
            </a>
          </p>
        </section>

        <p className="mt-10 text-sm text-slate-500">
          See also our{' '}
          <Link href="/terms" className="text-lena-700 font-medium">
            Terms of Service
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
