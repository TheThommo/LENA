-- Migration 008: search_logs.user_id (+ indexes)
--
-- search_logs did not carry user_id, which broke three things:
--   1. analytics_writer.log_search_event always failed with
--      "column user_id does not exist" for authed users, dropping the
--      whole row
--   2. SearchGateMiddleware's registered 24h quota count returned 0
--      because .eq("user_id", ...) matched nothing
--   3. projects.assign_search_to_project ownership check returned 404
--      even when the user did own the search
--
-- Adding the column + indexes. Backfill is a no-op since historic
-- rows never had ownership attributed anyway.

ALTER TABLE public.search_logs
  ADD COLUMN IF NOT EXISTS user_id uuid
  REFERENCES public.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_search_logs_user_id
  ON public.search_logs(user_id);

CREATE INDEX IF NOT EXISTS idx_search_logs_project_id
  ON public.search_logs(project_id);
