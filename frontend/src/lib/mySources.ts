/**
 * @deprecated Use `@/lib/savedDocuments` — kept for backward compatibility.
 */
export {
  type SavedDocument as SavedSource,
  makeDocumentId as makeSourceId,
  listDocuments as listSources,
  isDocumentSaved as isSaved,
  saveDocument as saveSource,
  removeDocument as removeSource,
  toggleDocumentFavourite as toggleFavourite,
  DOCUMENTS_CHANGED_EVENT,
} from '@/lib/savedDocuments';
