-- Per-user Pro subscriptions on a shared tenant.
-- Previously UNIQUE(tenant_id) meant only one Stripe sub could exist for the
-- default "lena" tenant — second paid user overwrote the first.

ALTER TABLE public.tenant_subscriptions
  ADD COLUMN IF NOT EXISTS user_id uuid REFERENCES public.users(id) ON DELETE SET NULL;

-- Drop one-sub-per-tenant constraint when present
ALTER TABLE public.tenant_subscriptions
  DROP CONSTRAINT IF EXISTS tenant_subscriptions_tenant_id_key;

CREATE UNIQUE INDEX IF NOT EXISTS idx_tenant_subscriptions_user_id_unique
  ON public.tenant_subscriptions(user_id)
  WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tenant_subscriptions_billing_email
  ON public.tenant_subscriptions(lower(billing_email));
