# Admin Leads & Visitors — How to Use

Production URLs (use these after deploy):

| Console | URL |
|---------|-----|
| **Admin (Leads / Visitors)** | https://www.lenamd.com/admin.html |
| **HQ Console** | https://www.lenamd.com/hq.html |

Sign in with a **platform_admin** account.

## Who appears where

### Visitors (`Admin → Visitors`)
Every analytics session — including anonymous free chats — with:
- Geo (city / country)
- Search count
- Cohort: **Anon 3 free** or **Free 10/mo**
- Status: Landed / Disclaimer OK / Lead captured / Registered

Sessions are created when someone opens `/chat` (geo attached via IP).

### Leads (`Admin → Leads`)
Emails captured from sessions + all registered users, with:
- Location, source (UTM/referrer), searches
- Plan column: **Anon 3 free** | **Free 10/mo** | **Pro**

### Subscriptions (`HQ → Subscriptions`)
Paid Stripe Pro clients (status, price, billing email, period).

## Cohorts (must match product limits)

| Cohort | Product limit | How we identify |
|--------|---------------|-----------------|
| Anon free chat | 3 searches | `anon_fingerprints` + `sessions` (no user_id) |
| Free registered | 10 / calendar month | `users` + `search_logs.user_id` |
| Pro paid | Unlimited | `tenant_subscriptions` active/trialing for that user |

## One-time Supabase migration

Run in Supabase SQL editor (or Railway-linked DB):

```sql
-- file: backend/migrations/012_subscription_user_id.sql
```

This allows **per-user** Pro rows on the shared tenant (required for multiple paid customers).

## Create a platform admin

```bash
railway run python backend/scripts/create_platform_admin.py \
  --email you@yourdomain.com --password 'StrongPasswordHere'
```
