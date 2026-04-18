-- Migration 006: anonymous visitor fingerprint table
--
-- Purpose: IP/UA-based backstop so anonymous visitors can't game the
-- "1 free search before signup" gate by clearing localStorage or opening
-- incognito. The session cookie + fingerprint are ANDed, so even if the
-- visitor drops their session token we still recognise the combo.
--
-- Privacy: stores SHA256(ip + user_agent + server_salt) only. Raw IP +
-- UA are persisted for admin debugging / suspicious-actor review, but
-- the hash is what the gate reads. A fingerprint row that converts
-- (signs up) records the resulting user_id so we can measure anon -> user
-- funnel without needing email.

CREATE TABLE IF NOT EXISTS anon_fingerprints (
    fingerprint_hash   text PRIMARY KEY,
    first_seen_at      timestamptz NOT NULL DEFAULT now(),
    last_seen_at       timestamptz NOT NULL DEFAULT now(),
    search_count       int NOT NULL DEFAULT 0,
    disclaimer_accepted_at timestamptz,
    converted_user_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    ip_address         text,
    user_agent         text
);

CREATE INDEX IF NOT EXISTS idx_anon_fp_last_seen ON anon_fingerprints (last_seen_at);
CREATE INDEX IF NOT EXISTS idx_anon_fp_converted ON anon_fingerprints (converted_user_id) WHERE converted_user_id IS NOT NULL;

-- RLS: admin client only (service role bypasses RLS). No user-scoped access.
ALTER TABLE anon_fingerprints ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE anon_fingerprints IS
  'IP+UA hashed backstop for the 1-free-search gate. Not a privacy store; the hash is the PK and raw IP/UA are for admin review only.';
