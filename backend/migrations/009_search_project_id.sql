-- Migration 009: project_id on search_logs + searches (required for Projects filing)

ALTER TABLE public.search_logs
  ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES public.projects(id) ON DELETE SET NULL;

ALTER TABLE public.searches
  ADD COLUMN IF NOT EXISTS project_id uuid REFERENCES public.projects(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_searches_project_id
  ON public.searches(project_id);

COMMENT ON COLUMN public.search_logs.project_id IS 'Optional project folder this search is filed under.';
COMMENT ON COLUMN public.searches.project_id IS 'Optional project folder this search is filed under.';
