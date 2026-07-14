import Link from 'next/link';
import { BrandMark } from '@/components/brand/BrandMark';
import { branding, product } from '@/config/branding';

export const metadata = {
  title: `Terms of Service — ${branding.name}`,
  description: 'Terms of use for LENA, including research data capture for product improvement.',
};

export default function TermsPage() {
  return (
    <div className="min-h-dvh bg-gradient-to-b from-slate-50 to-white">
      <header className="border-b border-slate-200/80 bg-white/80 backdrop-blur-sm">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <Link href="/">
            <BrandMark height={36} />
          </Link>
          <Link href="/privacy" className="text-sm text-lena-700 hover:text-lena-800 font-medium">
            Privacy Policy
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-10">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Terms of Service</h1>
        <p className="text-slate-500 text-sm mb-8">Last updated: 14 July 2026</p>

        <section className="space-y-4 text-[15px] leading-relaxed text-slate-700">
          <p>
            By using LENA ({branding.name}) at lenamd.com you agree to these Terms.
            If you do not agree, do not use the service.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">1. Research tool — not medical advice</h2>
          <p>
            LENA aggregates and summarises peer-reviewed biomedical literature across{' '}
            {product.sourceCount} sources. Output is <strong>research evidence, not medical advice</strong>,
            diagnosis, or treatment. Always consult a qualified clinician for personal health decisions.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">2. Research data capture</h2>
          <p>
            To build a better product and understand users, personas, and search trends, we capture
            search queries, persona selections, and related usage metadata. This data is used{' '}
            <strong>for research purposes only</strong> — to improve LENA, measure demand, and tune
            evidence discovery. We do not sell this data. Details of anonymity, beta operator review,
            and your rights are in our{' '}
            <Link href="/privacy" className="text-lena-700 font-medium">
              Privacy Policy
            </Link>
            .
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">3. Accounts &amp; fair use</h2>
          <p>
            Free anonymous use, free registered limits, and paid Pro plans are subject to the limits
            shown in-product. You must not abuse the service (scraping at scale, sharing credentials
            for circumvention, or attempting to disrupt infrastructure). We may suspend accounts that
            violate these Terms.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">4. Intellectual property</h2>
          <p>
            LENA software, branding, and interface are owned by their respective rights holders.
            Source literature remains under the rights of its publishers and databases. You may use
            summaries for personal research subject to third-party source terms.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">5. Disclaimer of warranties</h2>
          <p>
            The service is provided “as is” during beta and ongoing operation. We do not warrant
            that results are complete, error-free, or suitable for any clinical decision.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">6. Limitation of liability</h2>
          <p>
            To the fullest extent permitted by law, LENA and its operators are not liable for
            decisions made in reliance on search results or summaries.
          </p>

          <h2 className="text-xl font-semibold text-slate-900 pt-4">7. Contact</h2>
          <p>
            Questions about these Terms:{' '}
            <a className="text-lena-700 font-medium" href="mailto:hello@lena-app.com">
              hello@lena-app.com
            </a>
          </p>
        </section>

        <p className="mt-10 text-sm text-slate-500">
          See also our{' '}
          <Link href="/privacy" className="text-lena-700 font-medium">
            Privacy Policy
          </Link>
          .
        </p>
      </main>
    </div>
  );
}
