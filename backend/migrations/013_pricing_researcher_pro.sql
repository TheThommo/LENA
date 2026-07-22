-- Phase 4 pricing: Researcher ($19) + Pro ($49); founding unchanged.
-- Existing paid `pro` subscribers are remapped to `researcher` (nobody worse off).
-- Then `pro` is redefined as $49/$490.

ALTER TYPE public.plan_type ADD VALUE IF NOT EXISTS 'researcher';

-- Seed Researcher tier ($19 / $190)
INSERT INTO public.plan_tiers
  (name, display_name, description, searches_per_day, saved_results_limit,
   collections_limit, storage_gb, export_enabled, share_enabled,
   alt_medicine_enabled, advanced_pulse_enabled, community_enabled,
   monthly_price_cents, annual_price_cents)
VALUES
  ('researcher', 'Researcher', 'Unlimited search + bioRxiv, Consensus, ChEMBL, Open Targets, BioRender, Synapse open datasets',
   999999, 999999, 999999, 25, true, true, true, true, true, 1900, 19000)
ON CONFLICT (name) DO UPDATE SET
  display_name = EXCLUDED.display_name,
  description = EXCLUDED.description,
  monthly_price_cents = EXCLUDED.monthly_price_cents,
  annual_price_cents = EXCLUDED.annual_price_cents,
  export_enabled = true,
  share_enabled = true,
  updated_at = now();

-- Remap existing Pro ($19 / legacy) subscriptions → Researcher
UPDATE public.tenant_subscriptions
SET plan_id = (SELECT id FROM public.plan_tiers WHERE name = 'researcher' LIMIT 1),
    updated_at = now()
WHERE plan_id = (SELECT id FROM public.plan_tiers WHERE name = 'pro' LIMIT 1);

-- Redefine Pro as $49 / $490
UPDATE public.plan_tiers
SET
  display_name = 'Pro',
  description = 'Researcher plus Synapse restricted, Benchling, priority support, team seats, custom My Brain',
  monthly_price_cents = 4900,
  annual_price_cents = 49000,
  updated_at = now()
WHERE name = 'pro';

-- Ensure Pro row exists if somehow missing
INSERT INTO public.plan_tiers
  (name, display_name, description, searches_per_day, saved_results_limit,
   collections_limit, storage_gb, export_enabled, share_enabled,
   alt_medicine_enabled, advanced_pulse_enabled, community_enabled,
   monthly_price_cents, annual_price_cents)
VALUES
  ('pro', 'Pro', 'Researcher plus Synapse restricted, Benchling, priority support, team seats, custom My Brain',
   999999, 999999, 999999, 50, true, true, true, true, true, 4900, 49000)
ON CONFLICT (name) DO NOTHING;

-- Founding stays $50/yr
UPDATE public.plan_tiers
SET display_name = 'Pro (Founding 10)',
    annual_price_cents = COALESCE(annual_price_cents, 5000),
    updated_at = now()
WHERE name = 'pro_founding';
