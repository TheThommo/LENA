import Link from 'next/link';
import Image from 'next/image';
import { branding, product } from '@/config/branding';

const FEATURES = [
  {
    icon: '🔬',
    title: '11 databases, one question',
    body: `PubMed, Cochrane, OpenAlex, Semantic Scholar, Europe PMC, trials, WHO, CDC, DailyMed, DSLD, and openFDA — queried in parallel.`,
  },
  {
    icon: '✅',
    title: 'PULSE cross-validation',
    body: 'Claims are corroborated across independent sources. Confidence scores show agreement — not black-box AI guesses.',
  },
  {
    icon: '📋',
    title: 'Shareable evidence briefs',
    body: 'Export PDFs, copy full research summaries, or share a link. Built for clinicians, researchers, and health creators.',
  },
  {
    icon: '💊',
    title: 'Supplement & product research',
    body: 'Paste a product URL or label. LENA ingests context and searches regulatory and literature sources together.',
  },
];

const PRICING = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    highlight: false,
    features: [
      '1 search — no signup required',
      `${product.freeSearchLimit} searches/month with free account`,
      'PULSE validation & evidence briefs',
      'Saved history & project folders',
    ],
    cta: 'Try free search',
    href: '/chat',
  },
  {
    name: 'Pro',
    price: `$${product.proMonthlyUsd}`,
    period: '/month',
    highlight: true,
    features: [
      'Unlimited searches',
      'PDF export & full brief sharing',
      'All 11 databases + URL/label ingest',
      'Priority voice add-on coming soon (~$5/mo)',
    ],
    cta: 'Start with Pro',
    href: '/register',
    sub: `$${product.proAnnualUsd}/yr billed annually`,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    highlight: false,
    features: [
      'White-label / co-brand reskin',
      'Team seats & admin console',
      'Custom source integrations',
      'Dedicated support & SLA',
    ],
    cta: 'Contact us',
    href: 'mailto:hello@lena-app.com?subject=LENA%20Enterprise',
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-teal-50/30 text-slate-900">
      {/* Nav */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-white/80 border-b border-slate-200/60">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <Image
              src={branding.logoSrc}
              alt={branding.name}
              width={120}
              height={Math.round(120 / branding.logoAspect)}
              className="h-9 w-auto"
              priority
            />
          </Link>
          <nav className="hidden sm:flex items-center gap-6 text-sm font-medium text-slate-600">
            <a href="#features" className="hover:text-lena-700 transition-colors">Features</a>
            <a href="#pricing" className="hover:text-lena-700 transition-colors">Pricing</a>
            <Link href="/login" className="hover:text-lena-700 transition-colors">Sign in</Link>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/chat"
              className="hidden sm:inline-flex px-4 py-2 text-sm font-semibold text-lena-700 hover:text-lena-800 transition-colors"
            >
              Open app
            </Link>
            <Link
              href="/chat"
              className="inline-flex px-4 py-2 text-sm font-semibold text-white bg-lena-600 hover:bg-lena-700 rounded-lg transition-colors shadow-sm"
            >
              Try free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-lena-100/40 via-transparent to-transparent pointer-events-none" />
        <div className="max-w-6xl mx-auto px-4 sm:px-6 pt-16 pb-20 sm:pt-24 sm:pb-28 relative">
          <div className="max-w-3xl">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 mb-6 text-xs font-semibold rounded-full bg-lena-50 text-lena-700 border border-lena-200">
              {product.paperCount} papers · {product.sourceCount} live databases · PULSE validated
            </span>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-slate-900 leading-[1.1]">
              Health research,
              <span className="text-lena-600"> cross-validated in seconds</span>
            </h1>
            <p className="mt-6 text-lg sm:text-xl text-slate-600 leading-relaxed max-w-2xl">
              {product.description}
            </p>
            <div className="mt-8 flex flex-col sm:flex-row gap-3">
              <Link
                href="/chat"
                className="inline-flex items-center justify-center px-6 py-3.5 text-base font-semibold text-white rounded-xl shadow-lg hover:shadow-xl transition-all"
                style={{ background: 'linear-gradient(135deg, #1B6B93, #145372)' }}
              >
                Ask your first question — free
              </Link>
              <Link
                href="/register"
                className="inline-flex items-center justify-center px-6 py-3.5 text-base font-semibold text-lena-700 bg-white border border-lena-200 rounded-xl hover:bg-lena-50 transition-colors"
              >
                Create free account
              </Link>
            </div>
            <p className="mt-4 text-sm text-slate-500">
              No credit card · 1 search without signup · {product.freeSearchLimit}/month when registered
            </p>
          </div>

          {/* Source pills */}
          <div className="mt-14 flex flex-wrap gap-2">
            {product.sourceNames.map((name) => (
              <span
                key={name}
                className="px-3 py-1.5 text-xs font-medium rounded-full bg-white border border-slate-200 text-slate-600 shadow-sm"
              >
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 bg-white border-y border-slate-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900">
              Not another writing tool. An evidence navigator.
            </h2>
            <p className="mt-4 text-slate-600">
              Jenni writes papers. Vivli shares trial data. LENA finds, validates, and packages
              health evidence you can trust — across {product.sourceCount} sources at once.
            </p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className="p-6 rounded-2xl border border-slate-200/80 bg-slate-50/50 hover:bg-white hover:shadow-md transition-all"
              >
                <span className="text-2xl">{f.icon}</span>
                <h3 className="mt-3 text-lg font-semibold text-slate-900">{f.title}</h3>
                <p className="mt-2 text-sm text-slate-600 leading-relaxed">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="py-20">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-slate-900">Simple, honest pricing</h2>
            <p className="mt-3 text-slate-600">Start free. Upgrade when research is part of your workflow.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {PRICING.map((tier) => (
              <div
                key={tier.name}
                className={`relative p-6 rounded-2xl border flex flex-col ${
                  tier.highlight
                    ? 'border-lena-300 bg-gradient-to-b from-lena-50/80 to-white shadow-lg ring-1 ring-lena-200'
                    : 'border-slate-200 bg-white'
                }`}
              >
                {tier.highlight && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 text-xs font-bold uppercase tracking-wide bg-lena-600 text-white rounded-full">
                    Most popular
                  </span>
                )}
                <h3 className="text-lg font-semibold text-slate-900">{tier.name}</h3>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-slate-900">{tier.price}</span>
                  {tier.period && <span className="text-sm text-slate-500">{tier.period}</span>}
                </div>
                {'sub' in tier && tier.sub && (
                  <p className="text-xs text-slate-500 mt-1">{tier.sub}</p>
                )}
                <ul className="mt-6 space-y-2.5 flex-1">
                  {tier.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2 text-sm text-slate-600">
                      <svg className="w-4 h-4 text-lena-600 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                      {feat}
                    </li>
                  ))}
                </ul>
                <Link
                  href={tier.href}
                  className={`mt-6 block text-center py-2.5 px-4 rounded-lg text-sm font-semibold transition-colors ${
                    tier.highlight
                      ? 'bg-lena-600 text-white hover:bg-lena-700'
                      : 'bg-slate-100 text-slate-800 hover:bg-slate-200'
                  }`}
                >
                  {tier.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16 bg-gradient-to-r from-lena-700 to-lena-900 text-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold">Ready to validate your next question?</h2>
          <p className="mt-3 text-lena-100 max-w-xl mx-auto">
            Your first search is on us. No signup, no credit card — just evidence.
          </p>
          <Link
            href="/chat"
            className="inline-flex mt-8 px-8 py-3.5 bg-white text-lena-800 font-semibold rounded-xl hover:bg-lena-50 transition-colors shadow-lg"
          >
            Start researching →
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 border-t border-slate-200 bg-white">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
          <p>© {new Date().getFullYear()} {branding.name} — {branding.subtitle}</p>
          <div className="flex gap-6">
            <Link href="/chat" className="hover:text-lena-700">App</Link>
            <Link href="/login" className="hover:text-lena-700">Sign in</Link>
            <a href="mailto:hello@lena-app.com" className="hover:text-lena-700">Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
