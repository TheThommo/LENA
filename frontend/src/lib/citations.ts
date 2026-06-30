import type { ValidatedResult } from '@/lib/api';

/** Vancouver-style citation for clipboard / export. */
export function formatVancouverCitation(result: Pick<ValidatedResult, 'authors' | 'title' | 'year' | 'url' | 'doi'>): string {
  const authors = result.authors?.length
    ? result.authors.slice(0, 6).join(', ') + (result.authors.length > 6 ? ', et al' : '')
    : '[Author unknown]';
  const year = result.year > 0 ? `${result.year}. ` : '';
  const doi = result.doi ? ` doi:${result.doi}` : '';
  return `${authors}. ${result.title}. ${year}${result.url}${doi}`.trim();
}
