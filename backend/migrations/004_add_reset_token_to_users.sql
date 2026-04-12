-- =====================================================================
-- Migration 004: Add password reset token columns to users table
-- =====================================================================

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS reset_token_hash text;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS reset_token_expires_at timestamptz;
