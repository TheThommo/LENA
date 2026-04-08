-- LENA (Literature and Evidence Navigation Agent)
-- Multi-tenant Medical Research Platform
-- Initial Schema Migration
-- Created: 2026-04-08

-- =====================================================================
-- ENABLE EXTENSIONS
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "ltree";


-- =====================================================================
-- CUSTOM ENUM TYPES
-- =====================================================================

CREATE TYPE public.user_role AS ENUM (
  'platform_admin',
  'tenant_admin',
  'researcher',
  'student',
  'member'
);

CREATE TYPE public.persona_type AS ENUM (
  'medical_student',
  'clinician',
  'nurse_practitioner',
  'pharmacist',
  'researcher',
  'patient',
  'caregiver',
  'alternative_practitioner',
  'wellness_coach'
);

CREATE TYPE public.plan_type AS ENUM (
  'free',
  'starter',
  'professional',
  'enterprise'
);

CREATE TYPE public.search_source AS ENUM (
  'pubmed',
  'clinicaltrials',
  'cochrane',
  'who_iris',
  'cdc_open',
  'epistemonikos',
  'alternative_medicine_db',
  'internal_documents'
);

CREATE TYPE public.pulse_status AS ENUM (
  'consensus',
  'mixed_evidence',
  'conflicting',
  'inconclusive',
  'early_stage'
);

CREATE TYPE public.subscription_status AS ENUM (
  'trial',
  'active',
  'past_due',
  'cancelled',
  'suspended'
);

CREATE TYPE public.audit_action AS ENUM (
  'create',
  'read',
  'update',
  'delete',
  'search',
  'export',
  'share',
  'login',
  'settings_change',
  'role_change',
  'subscription_change'
);

CREATE TYPE public.trigger_type AS ENUM (
  'medical_advice',
  'drug_interaction',
  'contraindication',
  'dosage_concern',
  'pregnancy_warning',
  'allergy_alert',
  'other'
);


-- =====================================================================
-- UTILITY FUNCTIONS
-- =====================================================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Check if user is platform admin
CREATE OR REPLACE FUNCTION public.is_platform_admin(user_id uuid)
RETURNS BOOLEAN AS $$
DECLARE
  user_role public.user_role;
BEGIN
  SELECT role INTO user_role
  FROM public.user_tenants
  WHERE user_id = is_platform_admin.user_id
  LIMIT 1;
  RETURN user_role = 'platform_admin';
END;
$$ LANGUAGE plpgsql;

-- Check if user is tenant admin
CREATE OR REPLACE FUNCTION public.is_tenant_admin(user_id uuid, tenant_id uuid)
RETURNS BOOLEAN AS $$
DECLARE
  user_role public.user_role;
BEGIN
  SELECT role INTO user_role
  FROM public.user_tenants
  WHERE user_id = is_tenant_admin.user_id
    AND tenant_id = is_tenant_admin.tenant_id
  LIMIT 1;
  RETURN user_role IN ('tenant_admin', 'platform_admin');
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- 1. TENANTS - Multi-tenant Organizations
-- =====================================================================

CREATE TABLE public.tenants (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  slug text UNIQUE NOT NULL,
  name text NOT NULL,

  -- Branding
  logo_url text,
  primary_color text DEFAULT '#000000',
  secondary_color text DEFAULT '#666666',
  accent_color text DEFAULT '#0066cc',
  powered_by_text text DEFAULT 'Powered by LENA',
  domain text UNIQUE,

  -- Status
  is_active boolean DEFAULT true,
  is_demo boolean DEFAULT false,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.tenants IS 'Multi-tenant organizations (universities, hospitals, clinics). Each tenant can white-label LENA.';
COMMENT ON COLUMN public.tenants.slug IS 'URL-friendly identifier, e.g., "nyu", "mayo-clinic"';
COMMENT ON COLUMN public.tenants.domain IS 'Custom domain for white-label deployment';

CREATE INDEX idx_tenants_slug ON public.tenants(slug);
CREATE INDEX idx_tenants_is_active ON public.tenants(is_active);

ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenants_select ON public.tenants FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.user_tenants WHERE tenant_id = tenants.id
    ) OR is_platform_admin(auth.uid())
  );

CREATE TRIGGER tenants_update_updated_at BEFORE UPDATE ON public.tenants
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 2. TENANT CONFIG - Extended Tenant Settings
-- =====================================================================

CREATE TABLE public.tenant_config (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL UNIQUE REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Feature Flags
  alt_medicine_enabled boolean DEFAULT true,
  contribution_repo_enabled boolean DEFAULT false,
  community_enabled boolean DEFAULT false,
  external_publish_enabled boolean DEFAULT false,
  advanced_pulse_enabled boolean DEFAULT false,

  -- Limits
  max_searches_per_day integer DEFAULT 100,
  max_saved_results integer DEFAULT 1000,
  max_collections integer DEFAULT 50,
  max_storage_gb integer DEFAULT 10,

  -- Governance
  require_approval_for_share boolean DEFAULT false,
  enforce_disclaimer_daily boolean DEFAULT false,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.tenant_config IS 'Extended configuration per tenant including feature flags and usage limits.';

CREATE INDEX idx_tenant_config_tenant_id ON public.tenant_config(tenant_id);

ALTER TABLE public.tenant_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_config_select ON public.tenant_config FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.user_tenants WHERE tenant_id = tenant_id
    ) OR is_platform_admin(auth.uid())
  );

CREATE POLICY tenant_config_update ON public.tenant_config FOR UPDATE
  USING (is_tenant_admin(auth.uid(), tenant_id))
  WITH CHECK (is_tenant_admin(auth.uid(), tenant_id));

CREATE TRIGGER tenant_config_update_updated_at BEFORE UPDATE ON public.tenant_config
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 3. USERS - Platform Users (references auth.users)
-- =====================================================================

CREATE TABLE public.users (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email text NOT NULL UNIQUE,
  full_name text,
  avatar_url text,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.users IS 'LENA platform users, synced with auth.users from Supabase Auth.';

CREATE INDEX idx_users_email ON public.users(email);
CREATE INDEX idx_users_is_active ON public.users(is_active);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY users_select_self ON public.users FOR SELECT
  USING (auth.uid() = id OR is_platform_admin(auth.uid()));

CREATE POLICY users_update_self ON public.users FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

CREATE TRIGGER users_update_updated_at BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 4. ROLES - Platform Roles (RBAC)
-- =====================================================================

CREATE TABLE public.roles (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name public.user_role UNIQUE NOT NULL,
  description text,
  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.roles IS 'Predefined platform roles: platform_admin, tenant_admin, researcher, student, member.';

INSERT INTO public.roles (name, description) VALUES
  ('platform_admin', 'Full platform access, manages tenants and global settings'),
  ('tenant_admin', 'Manages tenant users, settings, and billing'),
  ('researcher', 'Full access to search, save, export, and share research'),
  ('student', 'Limited search and save capabilities'),
  ('member', 'Read-only access to shared results');

ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY roles_select ON public.roles FOR SELECT USING (true);


-- =====================================================================
-- 5. PERMISSIONS - Granular Permissions
-- =====================================================================

CREATE TABLE public.permissions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name text UNIQUE NOT NULL,
  description text,
  resource text,
  action text,
  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.permissions IS 'Granular permissions for RBAC (e.g., search:execute, results:export).';

INSERT INTO public.permissions (name, description, resource, action) VALUES
  ('search:execute', 'Execute search queries', 'search', 'execute'),
  ('results:view', 'View search results', 'results', 'view'),
  ('results:save', 'Save/bookmark results', 'results', 'save'),
  ('results:export', 'Export results (PDF, CSV)', 'results', 'export'),
  ('results:share', 'Share results with others', 'results', 'share'),
  ('collections:create', 'Create research collections', 'collections', 'create'),
  ('collections:manage', 'Edit/delete own collections', 'collections', 'manage'),
  ('documents:upload', 'Upload internal documents', 'documents', 'upload'),
  ('documents:manage', 'Manage all tenant documents', 'documents', 'manage'),
  ('users:manage', 'Manage tenant users', 'users', 'manage'),
  ('settings:edit', 'Edit tenant settings', 'settings', 'edit'),
  ('analytics:view', 'View tenant analytics', 'analytics', 'view'),
  ('billing:manage', 'Manage subscription/billing', 'billing', 'manage'),
  ('audit:view', 'View audit logs', 'audit', 'view');

ALTER TABLE public.permissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY permissions_select ON public.permissions FOR SELECT USING (true);


-- =====================================================================
-- 6. ROLE PERMISSIONS - Junction Table
-- =====================================================================

CREATE TABLE public.role_permissions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  role_id uuid NOT NULL REFERENCES public.roles(id) ON DELETE CASCADE,
  permission_id uuid NOT NULL REFERENCES public.permissions(id) ON DELETE CASCADE,
  created_at timestamptz DEFAULT now(),

  UNIQUE(role_id, permission_id)
);

COMMENT ON TABLE public.role_permissions IS 'Maps roles to permissions for RBAC.';

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.name = 'platform_admin';

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.name = 'tenant_admin' AND p.resource IN ('users', 'settings', 'analytics', 'billing', 'documents');

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.name = 'researcher' AND p.resource IN ('search', 'results', 'collections', 'documents');

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.name = 'student' AND p.action IN ('view', 'execute', 'save') AND p.resource IN ('search', 'results');

INSERT INTO public.role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM public.roles r, public.permissions p
WHERE r.name = 'member' AND p.action = 'view' AND p.resource IN ('results');

CREATE INDEX idx_role_permissions_role_id ON public.role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission_id ON public.role_permissions(permission_id);

ALTER TABLE public.role_permissions ENABLE ROW LEVEL SECURITY;

CREATE POLICY role_permissions_select ON public.role_permissions FOR SELECT USING (true);


-- =====================================================================
-- 7. USER TENANTS - User-Tenant Mapping with Roles
-- =====================================================================

CREATE TABLE public.user_tenants (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  role public.user_role NOT NULL DEFAULT 'member',
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),

  UNIQUE(user_id, tenant_id)
);

COMMENT ON TABLE public.user_tenants IS 'Maps users to tenants with roles. Users can belong to multiple tenants.';

CREATE INDEX idx_user_tenants_user_id ON public.user_tenants(user_id);
CREATE INDEX idx_user_tenants_tenant_id ON public.user_tenants(tenant_id);
CREATE INDEX idx_user_tenants_role ON public.user_tenants(role);

ALTER TABLE public.user_tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_tenants_select ON public.user_tenants FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY user_tenants_update ON public.user_tenants FOR UPDATE
  USING (is_tenant_admin(auth.uid(), tenant_id))
  WITH CHECK (is_tenant_admin(auth.uid(), tenant_id));

CREATE TRIGGER user_tenants_update_updated_at BEFORE UPDATE ON public.user_tenants
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 8. PLAN TIERS - Subscription Plans
-- =====================================================================

CREATE TABLE public.plan_tiers (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name public.plan_type UNIQUE NOT NULL,
  display_name text NOT NULL,
  description text,

  -- Limits
  searches_per_day integer NOT NULL,
  saved_results_limit integer NOT NULL,
  collections_limit integer NOT NULL,
  storage_gb integer NOT NULL,

  -- Features
  export_enabled boolean DEFAULT false,
  share_enabled boolean DEFAULT false,
  custom_domain_enabled boolean DEFAULT false,
  alt_medicine_enabled boolean DEFAULT false,
  advanced_pulse_enabled boolean DEFAULT false,
  community_enabled boolean DEFAULT false,
  sso_enabled boolean DEFAULT false,

  -- Pricing
  monthly_price_cents integer DEFAULT 0,
  annual_price_cents integer DEFAULT 0,
  stripe_product_id text,
  stripe_monthly_price_id text,
  stripe_annual_price_id text,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.plan_tiers IS 'Subscription plan tiers (Free, Starter, Professional, Enterprise) with feature limits.';

INSERT INTO public.plan_tiers (name, display_name, description, searches_per_day, saved_results_limit, collections_limit, storage_gb, export_enabled, share_enabled, monthly_price_cents, annual_price_cents) VALUES
  ('free', 'Free', 'Get started with LENA', 10, 50, 2, 1, false, false, 0, 0),
  ('starter', 'Starter', 'For individual researchers', 100, 500, 10, 10, true, true, 4900, 49000),
  ('professional', 'Professional', 'For research teams', 500, 5000, 50, 100, true, true, 14900, 149000),
  ('enterprise', 'Enterprise', 'Custom solution for institutions', 999999, 999999, 999999, 1000, true, true, NULL, NULL);

CREATE INDEX idx_plan_tiers_name ON public.plan_tiers(name);

ALTER TABLE public.plan_tiers ENABLE ROW LEVEL SECURITY;

CREATE POLICY plan_tiers_select ON public.plan_tiers FOR SELECT USING (true);

CREATE TRIGGER plan_tiers_update_updated_at BEFORE UPDATE ON public.plan_tiers
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 9. TENANT SUBSCRIPTIONS - Current Subscription per Tenant
-- =====================================================================

CREATE TABLE public.tenant_subscriptions (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL UNIQUE REFERENCES public.tenants(id) ON DELETE CASCADE,
  plan_id uuid NOT NULL REFERENCES public.plan_tiers(id),
  status public.subscription_status DEFAULT 'trial',

  -- Trial
  trial_starts_at timestamptz,
  trial_ends_at timestamptz,

  -- Billing
  stripe_customer_id text,
  stripe_subscription_id text,
  current_period_start timestamptz,
  current_period_end timestamptz,
  billing_email text,

  -- Metrics
  searches_used_this_month integer DEFAULT 0,
  storage_used_gb numeric(10, 2) DEFAULT 0,

  -- Override limits (for enterprise)
  override_max_searches_per_day integer,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.tenant_subscriptions IS 'Current subscription status and billing info per tenant.';

CREATE INDEX idx_tenant_subscriptions_tenant_id ON public.tenant_subscriptions(tenant_id);
CREATE INDEX idx_tenant_subscriptions_status ON public.tenant_subscriptions(status);
CREATE INDEX idx_tenant_subscriptions_plan_id ON public.tenant_subscriptions(plan_id);
CREATE INDEX idx_tenant_subscriptions_stripe_customer_id ON public.tenant_subscriptions(stripe_customer_id);

ALTER TABLE public.tenant_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_subscriptions_select ON public.tenant_subscriptions FOR SELECT
  USING (
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY tenant_subscriptions_update ON public.tenant_subscriptions FOR UPDATE
  USING (is_tenant_admin(auth.uid(), tenant_id) OR is_platform_admin(auth.uid()))
  WITH CHECK (is_tenant_admin(auth.uid(), tenant_id) OR is_platform_admin(auth.uid()));

CREATE TRIGGER tenant_subscriptions_update_updated_at BEFORE UPDATE ON public.tenant_subscriptions
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 10. TRIAL CONFIG - Trial Settings per Tenant
-- =====================================================================

CREATE TABLE public.trial_config (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL UNIQUE REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Trial Parameters
  trial_duration_days integer DEFAULT 14,
  trial_searches_limit integer DEFAULT 100,
  trial_results_limit integer DEFAULT 500,
  auto_downgrade_on_expiry boolean DEFAULT true,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.trial_config IS 'Trial period configuration per tenant.';

CREATE INDEX idx_trial_config_tenant_id ON public.trial_config(tenant_id);

ALTER TABLE public.trial_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY trial_config_select ON public.trial_config FOR SELECT
  USING (
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE TRIGGER trial_config_update_updated_at BEFORE UPDATE ON public.trial_config
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 11. DISCLAIMER ACCEPTANCES - MANDATORY Gate for Search Access
-- =====================================================================

CREATE TABLE public.disclaimer_acceptances (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Acceptance Tracking
  accepted_at timestamptz NOT NULL DEFAULT now(),
  disclaimer_version text NOT NULL DEFAULT '1.0',
  ip_address inet,
  user_agent text,

  -- Expiry (optional daily re-acceptance)
  expires_at timestamptz,

  created_at timestamptz DEFAULT now(),

  UNIQUE(user_id, tenant_id)
);

COMMENT ON TABLE public.disclaimer_acceptances IS 'MANDATORY: Tracks medical disclaimer acceptance. Users cannot search until accepted.';

CREATE INDEX idx_disclaimer_acceptances_user_id ON public.disclaimer_acceptances(user_id);
CREATE INDEX idx_disclaimer_acceptances_tenant_id ON public.disclaimer_acceptances(tenant_id);
CREATE INDEX idx_disclaimer_acceptances_accepted_at ON public.disclaimer_acceptances(accepted_at);

ALTER TABLE public.disclaimer_acceptances ENABLE ROW LEVEL SECURITY;

CREATE POLICY disclaimer_acceptances_select ON public.disclaimer_acceptances FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY disclaimer_acceptances_insert ON public.disclaimer_acceptances FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY disclaimer_acceptances_update ON public.disclaimer_acceptances FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);


-- =====================================================================
-- 12. USER PERSONAS - User Profile & Persona History
-- =====================================================================

CREATE TABLE public.user_personas (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Current Persona
  current_persona public.persona_type NOT NULL DEFAULT 'researcher',
  persona_updated_at timestamptz DEFAULT now(),

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),

  UNIQUE(user_id, tenant_id)
);

COMMENT ON TABLE public.user_personas IS 'Tracks user persona selection (medical_student, clinician, etc.) for personalized search results.';

CREATE INDEX idx_user_personas_user_id ON public.user_personas(user_id);
CREATE INDEX idx_user_personas_tenant_id ON public.user_personas(tenant_id);
CREATE INDEX idx_user_personas_current_persona ON public.user_personas(current_persona);

ALTER TABLE public.user_personas ENABLE ROW LEVEL SECURITY;

CREATE POLICY user_personas_select ON public.user_personas FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY user_personas_update ON public.user_personas FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER user_personas_update_updated_at BEFORE UPDATE ON public.user_personas
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 13. SEARCHES - Search Query Log
-- =====================================================================

CREATE TABLE public.searches (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,

  -- Query Details
  query_text text NOT NULL,
  query_vector vector(1536),

  -- Context
  persona_used public.persona_type DEFAULT 'researcher',
  alt_medicine_enabled boolean DEFAULT true,
  filters jsonb DEFAULT '{}',

  -- Results
  result_count integer DEFAULT 0,
  avg_pulse_score numeric(5, 2),
  avg_relevance_score numeric(5, 2),

  -- Performance
  duration_ms integer,

  -- Status
  status text DEFAULT 'completed',
  error_message text,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.searches IS 'Log of all search queries executed. Enables analytics and audit trail.';

CREATE INDEX idx_searches_tenant_id ON public.searches(tenant_id);
CREATE INDEX idx_searches_user_id ON public.searches(user_id);
CREATE INDEX idx_searches_created_at ON public.searches(created_at);
CREATE INDEX idx_searches_query_text_trgm ON public.searches USING GIN (query_text gin_trgm_ops);
CREATE INDEX idx_searches_status ON public.searches(status);
CREATE INDEX idx_searches_persona_used ON public.searches(persona_used);

ALTER TABLE public.searches ENABLE ROW LEVEL SECURITY;

CREATE POLICY searches_select ON public.searches FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY searches_insert ON public.searches FOR INSERT
  WITH CHECK (
    auth.uid() = user_id AND
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE TRIGGER searches_update_updated_at BEFORE UPDATE ON public.searches
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 14. SEARCH RESULTS - Individual Results per Search
-- =====================================================================

CREATE TABLE public.search_results (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  search_id uuid NOT NULL REFERENCES public.searches(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Source & Metadata
  source_database public.search_source NOT NULL,
  external_id text NOT NULL,

  -- Article Content
  paper_title text NOT NULL,
  authors text,
  year integer,
  doi text,
  pmid integer,
  url text,
  abstract text,

  -- Flags
  is_retracted boolean DEFAULT false,
  is_alternative_medicine boolean DEFAULT false,
  funding_source text,
  study_type text,

  -- Scoring
  pulse_score numeric(5, 2),
  relevance_score numeric(5, 2),
  cross_reference_count integer DEFAULT 0,

  -- Extraction (for future ML)
  full_text text,
  full_text_vector vector(1536),

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.search_results IS 'Individual search results from databases. One result per paper/study.';

CREATE INDEX idx_search_results_search_id ON public.search_results(search_id);
CREATE INDEX idx_search_results_tenant_id ON public.search_results(tenant_id);
CREATE INDEX idx_search_results_external_id ON public.search_results(external_id);
CREATE INDEX idx_search_results_source_database ON public.search_results(source_database);
CREATE INDEX idx_search_results_pmid ON public.search_results(pmid);
CREATE INDEX idx_search_results_doi ON public.search_results(doi);
CREATE INDEX idx_search_results_is_retracted ON public.search_results(is_retracted);
CREATE INDEX idx_search_results_pulse_score ON public.search_results(pulse_score);
CREATE INDEX idx_search_results_created_at ON public.search_results(created_at);

ALTER TABLE public.search_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY search_results_select ON public.search_results FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.searches WHERE id = search_id
    ) OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE TRIGGER search_results_update_updated_at BEFORE UPDATE ON public.search_results
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 15. PULSE SCORES - Detailed PULSE Scoring Breakdown
-- =====================================================================

CREATE TABLE public.pulse_scores (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  search_result_id uuid NOT NULL UNIQUE REFERENCES public.search_results(id) ON DELETE CASCADE,

  -- PULSE Scoring Breakdown
  consensus_status public.pulse_status DEFAULT 'inconclusive',
  cross_reference_count integer DEFAULT 0,
  source_consensus numeric(5, 2) DEFAULT 0.0,
  recency_weight numeric(5, 2) DEFAULT 0.0,
  study_type_weight numeric(5, 2) DEFAULT 0.0,
  funding_bias_weight numeric(5, 2) DEFAULT 0.0,

  -- Overall
  overall_score numeric(5, 2) NOT NULL,
  explanation text,

  -- Contradictions
  conflicting_studies_count integer DEFAULT 0,
  conflicting_study_ids text,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.pulse_scores IS 'Detailed PULSE cross-reference engine scoring. Validates consensus across sources.';

CREATE INDEX idx_pulse_scores_search_result_id ON public.pulse_scores(search_result_id);
CREATE INDEX idx_pulse_scores_consensus_status ON public.pulse_scores(consensus_status);
CREATE INDEX idx_pulse_scores_overall_score ON public.pulse_scores(overall_score);

ALTER TABLE public.pulse_scores ENABLE ROW LEVEL SECURITY;

CREATE POLICY pulse_scores_select ON public.pulse_scores FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.searches WHERE id = (
        SELECT search_id FROM public.search_results WHERE id = search_result_id
      )
    ) OR
    is_platform_admin(auth.uid())
  );

CREATE TRIGGER pulse_scores_update_updated_at BEFORE UPDATE ON public.pulse_scores
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 16. SAVED RESULTS - User Bookmarks/Favorites
-- =====================================================================

CREATE TABLE public.saved_results (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  search_result_id uuid NOT NULL REFERENCES public.search_results(id) ON DELETE CASCADE,

  -- User Annotation
  personal_notes text,
  importance_rating integer DEFAULT 3,
  is_flagged boolean DEFAULT false,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),

  UNIQUE(user_id, search_result_id)
);

COMMENT ON TABLE public.saved_results IS 'User-saved/bookmarked results with personal notes and ratings.';

CREATE INDEX idx_saved_results_user_id ON public.saved_results(user_id);
CREATE INDEX idx_saved_results_tenant_id ON public.saved_results(tenant_id);
CREATE INDEX idx_saved_results_search_result_id ON public.saved_results(search_result_id);
CREATE INDEX idx_saved_results_created_at ON public.saved_results(created_at);
CREATE INDEX idx_saved_results_is_flagged ON public.saved_results(is_flagged);

ALTER TABLE public.saved_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY saved_results_select ON public.saved_results FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY saved_results_insert ON public.saved_results FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY saved_results_update ON public.saved_results FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY saved_results_delete ON public.saved_results FOR DELETE
  USING (auth.uid() = user_id);

CREATE TRIGGER saved_results_update_updated_at BEFORE UPDATE ON public.saved_results
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 17. SEARCH FEEDBACK - User Feedback on Results
-- =====================================================================

CREATE TABLE public.search_feedback (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  search_result_id uuid NOT NULL REFERENCES public.search_results(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Feedback
  is_useful boolean,
  is_accurate boolean,
  accuracy_issue_description text,
  relevance_score integer,
  feedback_text text,

  created_at timestamptz DEFAULT now(),

  UNIQUE(search_result_id, user_id)
);

COMMENT ON TABLE public.search_feedback IS 'User feedback for improving result ranking and relevance.';

CREATE INDEX idx_search_feedback_search_result_id ON public.search_feedback(search_result_id);
CREATE INDEX idx_search_feedback_user_id ON public.search_feedback(user_id);
CREATE INDEX idx_search_feedback_tenant_id ON public.search_feedback(tenant_id);
CREATE INDEX idx_search_feedback_created_at ON public.search_feedback(created_at);

ALTER TABLE public.search_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY search_feedback_select ON public.search_feedback FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY search_feedback_insert ON public.search_feedback FOR INSERT
  WITH CHECK (auth.uid() = user_id);


-- =====================================================================
-- 18. COLLECTIONS - User-Created Research Collections
-- =====================================================================

CREATE TABLE public.collections (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Metadata
  name text NOT NULL,
  description text,
  color text DEFAULT '#0066cc',
  is_public boolean DEFAULT false,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.collections IS 'User-created research collections/folders for organizing papers.';

CREATE INDEX idx_collections_user_id ON public.collections(user_id);
CREATE INDEX idx_collections_tenant_id ON public.collections(tenant_id);
CREATE INDEX idx_collections_created_at ON public.collections(created_at);

ALTER TABLE public.collections ENABLE ROW LEVEL SECURITY;

CREATE POLICY collections_select ON public.collections FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_public = true OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY collections_insert ON public.collections FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY collections_update ON public.collections FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY collections_delete ON public.collections FOR DELETE
  USING (auth.uid() = user_id);

CREATE TRIGGER collections_update_updated_at BEFORE UPDATE ON public.collections
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 19. COLLECTION ITEMS - Papers in Collections
-- =====================================================================

CREATE TABLE public.collection_items (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  collection_id uuid NOT NULL REFERENCES public.collections(id) ON DELETE CASCADE,
  search_result_id uuid NOT NULL REFERENCES public.search_results(id) ON DELETE CASCADE,

  -- Position
  sort_order integer DEFAULT 0,

  created_at timestamptz DEFAULT now(),

  UNIQUE(collection_id, search_result_id)
);

COMMENT ON TABLE public.collection_items IS 'Junction table: papers within collections.';

CREATE INDEX idx_collection_items_collection_id ON public.collection_items(collection_id);
CREATE INDEX idx_collection_items_search_result_id ON public.collection_items(search_result_id);

ALTER TABLE public.collection_items ENABLE ROW LEVEL SECURITY;

CREATE POLICY collection_items_select ON public.collection_items FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.collections WHERE id = collection_id
    ) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY collection_items_insert ON public.collection_items FOR INSERT
  WITH CHECK (
    auth.uid() IN (
      SELECT user_id FROM public.collections WHERE id = collection_id
    )
  );

CREATE POLICY collection_items_delete ON public.collection_items FOR DELETE
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.collections WHERE id = collection_id
    )
  );


-- =====================================================================
-- 20. SHARED RESULTS - Sharing Research with Others
-- =====================================================================

CREATE TABLE public.shared_results (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  sharer_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Recipients
  recipient_user_id uuid REFERENCES public.users(id) ON DELETE CASCADE,
  recipient_email text,
  recipient_type text DEFAULT 'user',

  -- Content
  search_result_ids uuid[] NOT NULL,
  message text,

  -- Expiry
  expires_at timestamptz,
  is_revoked boolean DEFAULT false,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.shared_results IS 'Track sharing of research results with other users or external parties.';

CREATE INDEX idx_shared_results_sharer_id ON public.shared_results(sharer_id);
CREATE INDEX idx_shared_results_tenant_id ON public.shared_results(tenant_id);
CREATE INDEX idx_shared_results_recipient_user_id ON public.shared_results(recipient_user_id);
CREATE INDEX idx_shared_results_created_at ON public.shared_results(created_at);

ALTER TABLE public.shared_results ENABLE ROW LEVEL SECURITY;

CREATE POLICY shared_results_select ON public.shared_results FOR SELECT
  USING (
    auth.uid() = sharer_id OR
    auth.uid() = recipient_user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY shared_results_insert ON public.shared_results FOR INSERT
  WITH CHECK (auth.uid() = sharer_id);

CREATE POLICY shared_results_update ON public.shared_results FOR UPDATE
  USING (auth.uid() = sharer_id)
  WITH CHECK (auth.uid() = sharer_id);

CREATE TRIGGER shared_results_update_updated_at BEFORE UPDATE ON public.shared_results
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 21. TENANT DOCUMENTS - Internal Document Repository
-- =====================================================================

CREATE TABLE public.tenant_documents (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  uploaded_by uuid NOT NULL REFERENCES public.users(id) ON DELETE SET NULL,

  -- Document Metadata
  file_name text NOT NULL,
  file_size integer,
  file_type text,
  file_url text,
  storage_path text,

  -- Content
  title text NOT NULL,
  description text,
  document_vector vector(1536),

  -- Organization
  category text DEFAULT 'general',

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.tenant_documents IS 'Internal documents repository per tenant (guidelines, protocols, etc.).';

CREATE INDEX idx_tenant_documents_tenant_id ON public.tenant_documents(tenant_id);
CREATE INDEX idx_tenant_documents_uploaded_by ON public.tenant_documents(uploaded_by);
CREATE INDEX idx_tenant_documents_created_at ON public.tenant_documents(created_at);
CREATE INDEX idx_tenant_documents_category ON public.tenant_documents(category);

ALTER TABLE public.tenant_documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_documents_select ON public.tenant_documents FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.user_tenants WHERE tenant_id = tenant_id
    ) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY tenant_documents_insert ON public.tenant_documents FOR INSERT
  WITH CHECK (is_tenant_admin(auth.uid(), tenant_id));

CREATE POLICY tenant_documents_update ON public.tenant_documents FOR UPDATE
  USING (is_tenant_admin(auth.uid(), tenant_id))
  WITH CHECK (is_tenant_admin(auth.uid(), tenant_id));

CREATE POLICY tenant_documents_delete ON public.tenant_documents FOR DELETE
  USING (is_tenant_admin(auth.uid(), tenant_id));

CREATE TRIGGER tenant_documents_update_updated_at BEFORE UPDATE ON public.tenant_documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 22. DOCUMENT TAGS - Tags for Internal Documents
-- =====================================================================

CREATE TABLE public.document_tags (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  document_id uuid NOT NULL REFERENCES public.tenant_documents(id) ON DELETE CASCADE,

  -- Tag
  tag_name text NOT NULL,

  created_at timestamptz DEFAULT now(),

  UNIQUE(document_id, tag_name)
);

COMMENT ON TABLE public.document_tags IS 'Tags for organizing internal documents.';

CREATE INDEX idx_document_tags_tenant_id ON public.document_tags(tenant_id);
CREATE INDEX idx_document_tags_document_id ON public.document_tags(document_id);
CREATE INDEX idx_document_tags_tag_name ON public.document_tags(tag_name);

ALTER TABLE public.document_tags ENABLE ROW LEVEL SECURITY;

CREATE POLICY document_tags_select ON public.document_tags FOR SELECT
  USING (
    auth.uid() IN (
      SELECT user_id FROM public.user_tenants WHERE tenant_id = tenant_id
    ) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY document_tags_insert ON public.document_tags FOR INSERT
  WITH CHECK (is_tenant_admin(auth.uid(), tenant_id));

CREATE POLICY document_tags_delete ON public.document_tags FOR DELETE
  USING (is_tenant_admin(auth.uid(), tenant_id));


-- =====================================================================
-- 23. AGENT MEMORY - AI Conversation Context
-- =====================================================================

CREATE TABLE public.agent_memory (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Conversation
  session_id uuid NOT NULL DEFAULT uuid_generate_v4(),
  conversation_history jsonb NOT NULL DEFAULT '[]',

  -- Context
  last_search_id uuid REFERENCES public.searches(id) ON DELETE SET NULL,
  last_persona public.persona_type,
  preferences jsonb DEFAULT '{}',

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.agent_memory IS 'AI agent conversation context and memory per user session.';

CREATE INDEX idx_agent_memory_user_id ON public.agent_memory(user_id);
CREATE INDEX idx_agent_memory_tenant_id ON public.agent_memory(tenant_id);
CREATE INDEX idx_agent_memory_session_id ON public.agent_memory(session_id);
CREATE INDEX idx_agent_memory_updated_at ON public.agent_memory(updated_at);

ALTER TABLE public.agent_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_memory_select ON public.agent_memory FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY agent_memory_insert ON public.agent_memory FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY agent_memory_update ON public.agent_memory FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER agent_memory_update_updated_at BEFORE UPDATE ON public.agent_memory
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 24. AGENT GUARDRAIL TRIGGERS - Medical Advice Safety Logging
-- =====================================================================

CREATE TABLE public.agent_guardrail_triggers (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  search_id uuid REFERENCES public.searches(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Trigger Details
  trigger_type public.trigger_type NOT NULL,
  query_snippet text,
  response_given text,
  severity_level text DEFAULT 'info',

  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.agent_guardrail_triggers IS 'Log when medical advice guardrails are triggered (drug interactions, contraindications, etc.).';

CREATE INDEX idx_agent_guardrail_triggers_user_id ON public.agent_guardrail_triggers(user_id);
CREATE INDEX idx_agent_guardrail_triggers_tenant_id ON public.agent_guardrail_triggers(tenant_id);
CREATE INDEX idx_agent_guardrail_triggers_trigger_type ON public.agent_guardrail_triggers(trigger_type);
CREATE INDEX idx_agent_guardrail_triggers_created_at ON public.agent_guardrail_triggers(created_at);

ALTER TABLE public.agent_guardrail_triggers ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_guardrail_triggers_select ON public.agent_guardrail_triggers FOR SELECT
  USING (
    auth.uid() = user_id OR
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );


-- =====================================================================
-- 25. NOTIFICATIONS - In-App Notifications
-- =====================================================================

CREATE TABLE public.notifications (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Content
  title text NOT NULL,
  message text,
  notification_type text DEFAULT 'info',

  -- Linked Resources
  related_resource_type text,
  related_resource_id uuid,
  action_url text,

  -- Status
  is_read boolean DEFAULT false,
  read_at timestamptz,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.notifications IS 'In-app notifications (new features, shared results, system alerts).';

CREATE INDEX idx_notifications_user_id ON public.notifications(user_id);
CREATE INDEX idx_notifications_tenant_id ON public.notifications(tenant_id);
CREATE INDEX idx_notifications_is_read ON public.notifications(is_read);
CREATE INDEX idx_notifications_created_at ON public.notifications(created_at);

ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;

CREATE POLICY notifications_select ON public.notifications FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY notifications_update ON public.notifications FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER notifications_update_updated_at BEFORE UPDATE ON public.notifications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 26. NOTIFICATION PREFERENCES - Per-User Notification Settings
-- =====================================================================

CREATE TABLE public.notification_preferences (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL UNIQUE REFERENCES public.users(id) ON DELETE CASCADE,
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Notification Toggles
  email_on_shares boolean DEFAULT true,
  email_on_new_features boolean DEFAULT true,
  email_weekly_digest boolean DEFAULT true,
  in_app_notifications boolean DEFAULT true,

  -- Digest Frequency
  digest_frequency text DEFAULT 'weekly',

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.notification_preferences IS 'Per-user notification and digest preferences.';

CREATE INDEX idx_notification_preferences_user_id ON public.notification_preferences(user_id);
CREATE INDEX idx_notification_preferences_tenant_id ON public.notification_preferences(tenant_id);

ALTER TABLE public.notification_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY notification_preferences_select ON public.notification_preferences FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY notification_preferences_update ON public.notification_preferences FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE TRIGGER notification_preferences_update_updated_at BEFORE UPDATE ON public.notification_preferences
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 27. USAGE DAILY - Daily Aggregated Metrics per Tenant
-- =====================================================================

CREATE TABLE public.usage_daily (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Date
  metric_date date NOT NULL,

  -- Metrics
  searches_count integer DEFAULT 0,
  unique_users_count integer DEFAULT 0,
  avg_pulse_score numeric(5, 2),
  results_total integer DEFAULT 0,
  results_saved integer DEFAULT 0,
  results_shared integer DEFAULT 0,

  -- Top Queries (JSON)
  top_queries jsonb DEFAULT '[]',
  top_personas jsonb DEFAULT '[]',

  -- New Activity
  new_signups integer DEFAULT 0,
  new_collections integer DEFAULT 0,

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),

  UNIQUE(tenant_id, metric_date)
);

COMMENT ON TABLE public.usage_daily IS 'Daily aggregated usage metrics per tenant for analytics dashboard.';

CREATE INDEX idx_usage_daily_tenant_id ON public.usage_daily(tenant_id);
CREATE INDEX idx_usage_daily_metric_date ON public.usage_daily(metric_date);

ALTER TABLE public.usage_daily ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_daily_select ON public.usage_daily FOR SELECT
  USING (
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE TRIGGER usage_daily_update_updated_at BEFORE UPDATE ON public.usage_daily
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 28. USAGE MONTHLY - Monthly Rollup for Trend Analysis
-- =====================================================================

CREATE TABLE public.usage_monthly (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,

  -- Period
  year integer NOT NULL,
  month integer NOT NULL,

  -- Metrics
  searches_count integer DEFAULT 0,
  unique_users_count integer DEFAULT 0,
  avg_pulse_score numeric(5, 2),
  results_total integer DEFAULT 0,
  results_saved integer DEFAULT 0,
  results_shared integer DEFAULT 0,

  -- Trends
  searches_growth_pct numeric(8, 2),
  users_growth_pct numeric(8, 2),

  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),

  UNIQUE(tenant_id, year, month)
);

COMMENT ON TABLE public.usage_monthly IS 'Monthly rollup metrics for trend analysis and MRR calculations.';

CREATE INDEX idx_usage_monthly_tenant_id ON public.usage_monthly(tenant_id);
CREATE INDEX idx_usage_monthly_year_month ON public.usage_monthly(year, month);

ALTER TABLE public.usage_monthly ENABLE ROW LEVEL SECURITY;

CREATE POLICY usage_monthly_select ON public.usage_monthly FOR SELECT
  USING (
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE TRIGGER usage_monthly_update_updated_at BEFORE UPDATE ON public.usage_monthly
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 29. PLATFORM METRICS - Global Platform Metrics (Admin Only)
-- =====================================================================

CREATE TABLE public.platform_metrics (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),

  -- Global Counts
  total_tenants integer DEFAULT 0,
  total_users integer DEFAULT 0,
  total_searches integer DEFAULT 0,
  total_results integer DEFAULT 0,

  -- Financial
  mrr_cents integer DEFAULT 0,
  arr_cents integer DEFAULT 0,
  total_subscribers integer DEFAULT 0,

  -- Health
  avg_search_response_ms integer DEFAULT 0,
  churn_rate_pct numeric(5, 2),
  nps_score integer,

  -- Growth
  new_tenants_this_month integer DEFAULT 0,
  new_users_this_month integer DEFAULT 0,

  metric_date date UNIQUE NOT NULL,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.platform_metrics IS 'Global platform metrics for dashboard. Platform admins only.';

CREATE INDEX idx_platform_metrics_metric_date ON public.platform_metrics(metric_date);

ALTER TABLE public.platform_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY platform_metrics_select ON public.platform_metrics FOR SELECT
  USING (is_platform_admin(auth.uid()));

CREATE POLICY platform_metrics_insert ON public.platform_metrics FOR INSERT
  WITH CHECK (is_platform_admin(auth.uid()));

CREATE TRIGGER platform_metrics_update_updated_at BEFORE UPDATE ON public.platform_metrics
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();


-- =====================================================================
-- 30. AUDIT LOG - Comprehensive Audit Trail
-- =====================================================================

CREATE TABLE public.audit_log (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid REFERENCES public.tenants(id) ON DELETE SET NULL,
  user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,

  -- Action
  action public.audit_action NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid,

  -- Changes
  old_values jsonb,
  new_values jsonb,

  -- Metadata
  ip_address inet,
  user_agent text,
  session_id uuid,

  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.audit_log IS 'Comprehensive audit trail of all significant actions for compliance and troubleshooting.';

CREATE INDEX idx_audit_log_tenant_id ON public.audit_log(tenant_id);
CREATE INDEX idx_audit_log_user_id ON public.audit_log(user_id);
CREATE INDEX idx_audit_log_action ON public.audit_log(action);
CREATE INDEX idx_audit_log_resource_type ON public.audit_log(resource_type);
CREATE INDEX idx_audit_log_created_at ON public.audit_log(created_at);

ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY audit_log_select ON public.audit_log FOR SELECT
  USING (
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY audit_log_insert ON public.audit_log FOR INSERT
  WITH CHECK (true);


-- =====================================================================
-- 31. EVENT LOG - Granular Event Tracking for Analytics
-- =====================================================================

CREATE TABLE public.event_log (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  tenant_id uuid NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
  user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,

  -- Event
  event_type text NOT NULL,
  event_name text NOT NULL,

  -- Dimensions
  page_path text,
  feature_name text,
  persona public.persona_type,

  -- Metrics
  session_duration_ms integer,
  value numeric(10, 2),

  -- Context
  ip_address inet,
  user_agent text,
  session_id uuid,

  created_at timestamptz DEFAULT now()
);

COMMENT ON TABLE public.event_log IS 'Granular event tracking for analytics (page views, feature usage, session duration).';

CREATE INDEX idx_event_log_tenant_id ON public.event_log(tenant_id);
CREATE INDEX idx_event_log_user_id ON public.event_log(user_id);
CREATE INDEX idx_event_log_event_type ON public.event_log(event_type);
CREATE INDEX idx_event_log_event_name ON public.event_log(event_name);
CREATE INDEX idx_event_log_created_at ON public.event_log(created_at);

ALTER TABLE public.event_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY event_log_select ON public.event_log FOR SELECT
  USING (
    is_tenant_admin(auth.uid(), tenant_id) OR
    is_platform_admin(auth.uid())
  );

CREATE POLICY event_log_insert ON public.event_log FOR INSERT
  WITH CHECK (true);


-- =====================================================================
-- POST-CREATION SETUP
-- =====================================================================

-- Create default trial config for new tenants (trigger will handle this in production)
-- Create initial admin user (will be done via separate script in production)

-- Grant public access to read roles and permissions (for auth flows)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO anon;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO authenticated;

COMMIT;
