-- Migration 007: Stripe billing wiring
--
-- 1. Extend plan_type enum with 'pro' and 'pro_founding' (the live SKUs
--    for demo-era + founding cohort — see project_pricing_strategy memory).
-- 2. Add stripe_price_id column to tenant_subscriptions so webhooks record
--    which price (monthly / annual / founding) the tenant is on.
-- 3. Seed plan_tiers rows (prices in cents). Stripe product / price IDs are
--    filled in by UPDATE after creating them in Stripe (MCP or dashboard).
--
-- Run in Supabase SQL Editor. Enum ALTERs cannot run inside a transaction
-- in older PG versions, so each ALTER TYPE is its own statement.

ALTER TYPE public.plan_type ADD VALUE IF NOT EXISTS 'pro';
ALTER TYPE public.plan_type ADD VALUE IF NOT EXISTS 'pro_founding';

ALTER TABLE public.tenant_subscriptions
  ADD COLUMN IF NOT EXISTS stripe_price_id text;

CREATE INDEX IF NOT EXISTS idx_tenant_subscriptions_stripe_price_id
  ON public.tenant_subscriptions(stripe_price_id);

INSERT INTO public.plan_tiers
  (name, display_name, description, searches_per_day, saved_results_limit,
   collections_limit, storage_gb, export_enabled, share_enabled,
   alt_medicine_enabled, advanced_pulse_enabled, community_enabled,
   monthly_price_cents, annual_price_cents)
VALUES
  ('pro', 'Pro', 'Unlimited research + projects + export',
   999999, 999999, 999999, 25, true, true, true, true, true, 3000, 30000),
  ('pro_founding', 'Pro (Founding 50)', 'First-50 lifetime founding rate',
   999999, 999999, 999999, 25, true, true, true, true, true, 0, 5000)
ON CONFLICT (name) DO NOTHING;
