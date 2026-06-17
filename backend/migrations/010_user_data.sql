-- Migration 010: User-owned profile prefs, saved documents, interest waitlist, share events

CREATE TABLE IF NOT EXISTS public.user_profiles (
  user_id uuid PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
  preferences jsonb NOT NULL DEFAULT '{}',
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.saved_documents (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
  doc_key text NOT NULL,
  payload jsonb NOT NULL,
  saved_at timestamptz DEFAULT now(),
  UNIQUE(user_id, doc_key)
);

CREATE INDEX IF NOT EXISTS idx_saved_documents_user_saved
  ON public.saved_documents (user_id, saved_at DESC);

CREATE TABLE IF NOT EXISTS public.feature_interest (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email text NOT NULL,
  feature text NOT NULL,
  user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
  created_at timestamptz DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feature_interest_feature
  ON public.feature_interest (feature, created_at DESC);

CREATE TABLE IF NOT EXISTS public.share_events (
  id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id uuid REFERENCES public.users(id) ON DELETE SET NULL,
  search_id uuid,
  recipient_type text NOT NULL,
  recipient_email text,
  note text,
  result_title text,
  created_at timestamptz DEFAULT now()
);

ALTER TABLE public.user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.saved_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.feature_interest ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.share_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on user_profiles"
  ON public.user_profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on saved_documents"
  ON public.saved_documents FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on feature_interest"
  ON public.feature_interest FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "Service role full access on share_events"
  ON public.share_events FOR ALL USING (true) WITH CHECK (true);
