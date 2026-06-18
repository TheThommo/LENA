-- Affiliation & co-branding for B2B (universities, hospitals, clinics, pharmacies)
-- and B2C users arriving via partner codes.

-- Partner organisation types (hierarchy sales)
CREATE TYPE public.partner_segment AS ENUM (
  'university',
  'hospital',
  'clinic',
  'pharmacy',
  'doctors_room',
  'corporate',
  'individual'
);

CREATE TYPE public.affiliation_benefit_type AS ENUM (
  'percent_discount',
  'free_months',
  'trial_extension',
  'custom'
);

-- Canonical partner record (B2B tenant may link here)
CREATE TABLE public.partner_organizations (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug text UNIQUE NOT NULL,
  name text NOT NULL,
  segment public.partner_segment NOT NULL DEFAULT 'corporate',
  logo_url text,
  website_url text,
  tenant_id uuid REFERENCES public.tenants(id) ON DELETE SET NULL,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE public.partner_organizations IS
  'B2B partners for co-branded LENA (universities, hospitals, clinics, pharmacies).';

CREATE INDEX idx_partner_organizations_slug ON public.partner_organizations(slug);
CREATE INDEX idx_partner_organizations_segment ON public.partner_organizations(segment);

-- Shareable affiliation / referral codes
CREATE TABLE public.affiliation_codes (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  code text UNIQUE NOT NULL,
  partner_id uuid NOT NULL REFERENCES public.partner_organizations(id) ON DELETE CASCADE,
  label text,
  benefit_type public.affiliation_benefit_type NOT NULL DEFAULT 'percent_discount',
  benefit_value numeric NOT NULL DEFAULT 0,
  benefit_description text,
  max_redemptions integer,
  redemption_count integer NOT NULL DEFAULT 0,
  valid_from timestamptz NOT NULL DEFAULT now(),
  valid_until timestamptz,
  co_brand_duration_days integer,
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT affiliation_codes_code_format CHECK (code ~ '^[A-Za-z0-9_-]{3,32}$')
);

COMMENT ON TABLE public.affiliation_codes IS
  'Codes partners share (e.g. UNSW-STUDENT) for discounts and co-branding.';

CREATE INDEX idx_affiliation_codes_partner ON public.affiliation_codes(partner_id);
CREATE INDEX idx_affiliation_codes_active ON public.affiliation_codes(is_active) WHERE is_active = true;

-- User redemption — co-brand persists for subscription duration
CREATE TABLE public.user_affiliations (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  affiliation_code_id uuid NOT NULL REFERENCES public.affiliation_codes(id) ON DELETE RESTRICT,
  partner_id uuid NOT NULL REFERENCES public.partner_organizations(id) ON DELETE RESTRICT,
  code_used text NOT NULL,
  co_brand_until timestamptz,
  benefit_applied jsonb NOT NULL DEFAULT '{}',
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, affiliation_code_id)
);

COMMENT ON TABLE public.user_affiliations IS
  'Tracks which users signed up via a partner code; drives co-brand header until co_brand_until.';

CREATE INDEX idx_user_affiliations_user ON public.user_affiliations(user_id);
CREATE INDEX idx_user_affiliations_partner ON public.user_affiliations(partner_id);

ALTER TABLE public.partner_organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.affiliation_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_affiliations ENABLE ROW LEVEL SECURITY;

-- Public read of active partners/codes for validation (via service role in API)
CREATE POLICY partner_orgs_public_read ON public.partner_organizations
  FOR SELECT USING (is_active = true);

CREATE POLICY affiliation_codes_public_read ON public.affiliation_codes
  FOR SELECT USING (is_active = true);

CREATE POLICY user_affiliations_own_read ON public.user_affiliations
  FOR SELECT USING (auth.uid() = user_id);

CREATE TRIGGER partner_organizations_updated_at
  BEFORE UPDATE ON public.partner_organizations
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER affiliation_codes_updated_at
  BEFORE UPDATE ON public.affiliation_codes
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Demo partners for development / investor demos (safe to delete in prod)
INSERT INTO public.partner_organizations (slug, name, segment, logo_url, website_url)
VALUES
  (
    'demo-university',
    'Demo University',
    'university',
    NULL,
    'https://example.edu'
  ),
  (
    'demo-hospital',
    'Demo Health System',
    'hospital',
    NULL,
    'https://example.health'
  )
ON CONFLICT (slug) DO NOTHING;

INSERT INTO public.affiliation_codes (code, partner_id, label, benefit_type, benefit_value, benefit_description, co_brand_duration_days)
SELECT
  'DEMO-UNI',
  p.id,
  'Student access',
  'free_months',
  1,
  '1 month free on annual subscription',
  365
FROM public.partner_organizations p
WHERE p.slug = 'demo-university'
ON CONFLICT (code) DO NOTHING;

INSERT INTO public.affiliation_codes (code, partner_id, label, benefit_type, benefit_value, benefit_description, co_brand_duration_days)
SELECT
  'DEMO-HOSP',
  p.id,
  'Clinical staff',
  'percent_discount',
  20,
  '20% off Pro subscription',
  365
FROM public.partner_organizations p
WHERE p.slug = 'demo-hospital'
ON CONFLICT (code) DO NOTHING;
