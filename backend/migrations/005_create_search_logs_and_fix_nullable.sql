-- Migration 005: Create search_logs table + make searches.user_id nullable
--
-- Root cause: analytics_writer.py writes to search_logs (which was never
-- created in any migration) and searches.user_id NOT NULL blocks anonymous
-- search logging. Both silently fail inside try/except, leaving the
-- dashboard empty.

-- 1. Allow anonymous searches (user_id NULL = not yet registered)
ALTER TABLE public.searches
  ALTER COLUMN user_id DROP NOT NULL;

-- 2. Create search_logs (the detailed analytics table analytics_writer.py
--    and dashboard_queries.py both rely on). Column set matches the payload
--    in analytics_writer.log_search_event().
CREATE TABLE IF NOT EXISTS public.search_logs (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  session_id uuid REFERENCES public.sessions(id) ON DELETE SET NULL,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
  query text NOT NULL,
  persona text,
  response_time_ms numeric(10, 2),
  sources_queried jsonb DEFAULT '[]',
  sources_succeeded jsonb DEFAULT '[]',
  total_results integer DEFAULT 0,
  pulse_status text,
  created_at timestamptz DEFAULT now()
);

-- Indexes for dashboard_queries.py reads
CREATE INDEX IF NOT EXISTS idx_search_logs_tenant_created
  ON public.search_logs (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_search_logs_session
  ON public.search_logs (session_id);

-- Enable RLS but allow service-role full access (analytics_writer uses admin client)
ALTER TABLE public.search_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on search_logs"
  ON public.search_logs FOR ALL
  USING (true)
  WITH CHECK (true);

COMMENT ON TABLE public.search_logs IS 'Per-search analytics: response time, sources, PULSE status. Written by analytics_writer.log_search_event().';
