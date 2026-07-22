'use client';

import type { SearchEnrichment } from '@/lib/api';

/**
 * Phase-3 enrichment panels — rendered BELOW the existing source card list.
 * Existing PULSE / SourceCard UI is untouched.
 */
export default function EnrichmentPanel({ enrichment }: { enrichment?: SearchEnrichment | null }) {
  if (!enrichment) return null;

  const chembl = enrichment.chembl || [];
  const targets = enrichment.opentargets || [];
  const synapse = enrichment.synapse || [];
  const figures = enrichment.biorender?.figures || [];
  const biorenderMeta = enrichment.biorender?.meta;
  const owkin = enrichment.owkin || [];

  const hasAnything =
    chembl.length > 0 ||
    targets.length > 0 ||
    synapse.length > 0 ||
    figures.length > 0 ||
    Boolean(biorenderMeta?.auth_required) ||
    owkin.length > 0;

  if (!hasAnything) return null;

  return (
    <div className="mt-4 space-y-4 border-t border-slate-200/80 pt-4" data-testid="enrichment-panel">
      {figures.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Related Scientific Figures
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {figures.map((fig) => (
              <a
                key={fig.id}
                href={fig.url || '#'}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg border border-slate-200 bg-white overflow-hidden hover:border-slate-300 transition-colors"
              >
                {fig.thumbnail_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={fig.thumbnail_url}
                    alt={fig.title}
                    className="w-full h-28 object-cover bg-slate-50"
                  />
                ) : (
                  <div className="w-full h-28 bg-slate-50 flex items-center justify-center text-[10px] text-slate-400">
                    BioRender
                  </div>
                )}
                <div className="px-2 py-1.5">
                  <p className="text-[11px] font-medium text-slate-800 line-clamp-2">{fig.title}</p>
                </div>
              </a>
            ))}
          </div>
        </section>
      )}

      {biorenderMeta?.auth_required && figures.length === 0 && (
        <p className="text-[11px] text-slate-500 italic">
          Related Scientific Figures available after BioRender sign-in.
        </p>
      )}

      {chembl.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Compound Data
          </h3>
          <div className="space-y-2">
            {chembl.map((c) => (
              <a
                key={c.chembl_id}
                href={c.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg border border-slate-200 bg-white px-3 py-2 hover:border-teal-300 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-800">{c.name}</span>
                  <span className="text-[10px] font-mono text-teal-700 bg-teal-50 px-1.5 py-0.5 rounded">
                    {c.chembl_id}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5">{c.summary}</p>
              </a>
            ))}
          </div>
        </section>
      )}

      {targets.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Target Evidence
          </h3>
          <div className="space-y-2">
            {targets.map((t) => (
              <a
                key={`${t.entity}-${t.id}`}
                href={t.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg border border-slate-200 bg-white px-3 py-2 hover:border-indigo-300 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <span className="text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-700">
                    {t.entity}
                  </span>
                  <span className="text-sm font-semibold text-slate-800">{t.name}</span>
                </div>
                {t.description && (
                  <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{t.description}</p>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      {synapse.length > 0 && (
        <section>
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Related Datasets
          </h3>
          <div className="space-y-2">
            {synapse.map((d) => (
              <a
                key={d.id}
                href={d.url}
                target="_blank"
                rel="noopener noreferrer"
                className="block rounded-lg border border-slate-200 bg-white px-3 py-2 hover:border-amber-300 transition-colors"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-800">{d.name}</span>
                  <span
                    className={`text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded ${
                      d.access_status === 'open'
                        ? 'bg-emerald-50 text-emerald-700'
                        : 'bg-amber-50 text-amber-800'
                    }`}
                  >
                    {d.access_status}
                  </span>
                </div>
                {d.description && (
                  <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{d.description}</p>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      {/* Owkin Pathology — Enterprise only; absent from DOM when empty / disabled */}
      {owkin.length > 0 && (
        <section data-testid="owkin-pathology-panel">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Pathology Analysis
          </h3>
          <div className="space-y-2">
            {owkin.map((o) => (
              <div
                key={o.id || o.title}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2"
              >
                <p className="text-sm font-semibold text-slate-800">{o.title}</p>
                <p className="text-[11px] text-slate-500 mt-0.5">{o.summary}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
