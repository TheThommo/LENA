-- =====================================================================
-- Migration 003: Add authentication columns to users table
-- Adds role, password_hash, and other missing columns for admin auth
-- =====================================================================

ALTER TABLE public.users ADD COLUMN IF NOT EXISTS name varchar(255);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS role varchar(50) DEFAULT 'public_user';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS persona_type varchar(50) DEFAULT 'general';
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS tenant_id uuid REFERENCES public.tenants(id);
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS last_login_at timestamptz;
ALTER TABLE public.users ADD COLUMN IF NOT EXISTS password_hash text;

-- Backfill name from full_name
UPDATE public.users SET name = full_name WHERE name IS NULL AND full_name IS NOT NULL;
