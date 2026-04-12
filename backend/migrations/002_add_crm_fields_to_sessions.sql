-- =====================================================================
-- Migration 002: Add CRM fields to sessions table
-- Adds institution, phone, and data consent tracking for lead capture
-- =====================================================================

-- Add institution/organisation field
ALTER TABLE public.sessions
  ADD COLUMN IF NOT EXISTS institution text;

-- Add phone number field
ALTER TABLE public.sessions
  ADD COLUMN IF NOT EXISTS phone varchar(50);

-- Add data processing consent timestamp (GDPR/CCPA/PDPA compliance)
ALTER TABLE public.sessions
  ADD COLUMN IF NOT EXISTS data_consent_accepted_at timestamptz;

-- Index on institution for CRM lead filtering
CREATE INDEX IF NOT EXISTS idx_sessions_institution ON public.sessions(institution)
  WHERE institution IS NOT NULL;

-- Index on consent timestamp for compliance auditing
CREATE INDEX IF NOT EXISTS idx_sessions_data_consent ON public.sessions(data_consent_accepted_at)
  WHERE data_consent_accepted_at IS NOT NULL;
