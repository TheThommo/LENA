# LENA Launch Readiness Audit

**Date:** 2026-06-30  
**Target:** https://www.lenamd.com (production)  
**Branch:** `cursor/launch-readiness-88bc`

## Executive summary

The app is **functionally ready for a controlled public launch** once this branch is merged and deployed. Pre-deploy production has **2 smoke failures** (health endpoint path) and **unmerged fixes** (Lauren QA + HTTPS). This branch consolidates those fixes and adds automated gates.

| Gate | Status |
|------|--------|
| Frontend build | Pass |
| Backend pytest | 331 tests — health route fix restores route tests |
| Production smoke (pre-deploy) | 10/12 pass — health `/api/health` fails until deploy |
| Playwright E2E | Added — run after deploy |
| Lauren QA fixes | Included in this branch |
| lenamd.com API routing | Fixed — browser always uses `/api` |
| HTTPS / HSTS | Partially live; full headers after deploy |

---

## What was audited

### Code & config
- API routing (`config.ts`, `middleware.ts`, `next.config.js`, Dockerfile)
- Auth, search gate, billing, CORS defaults
- Lauren QA fixes (All mode, Cite, persona menu, projects, settings)
- Security: health probes, register rate limit, connection test exposure

### Production (live checks)
- Page availability: `/`, `/chat`, `/login`, `/register` — **200 OK**
- API proxy: `/api/discover/suggestions` — **200 OK**
- API health: `/api/health` — **404** (trailing-slash only on prod today)
- TLS: Valid Let's Encrypt cert for `www.lenamd.com`
- HSTS: Present on frontend responses

### Automated tests
- `scripts/smoke_test_production.sh` — expanded checklist
- `frontend/e2e/production.spec.ts` — Playwright suite
- `backend/tests/` — 23 test modules

---

## Fixes in this branch

1. **`/api/health` without trailing slash** — smoke tests and monitors expect this path
2. **Browser always uses same-origin `/api`** — works on any custom domain
3. **CORS / APP_URL defaults** include `www.lenamd.com`
4. **Register rate limit** — 5 attempts per 10 minutes
5. **Hide `/api/health/connections*` in production** — reduces info disclosure
6. **Merged:** Lauren QA (#25) + HTTPS/logo/3 searches (#24)
7. **Playwright E2E** + expanded smoke script

---

## Railway env checklist (verify before launch)

### Backend
```
APP_ENV=production
APP_DEBUG=false
JWT_SECRET_KEY=<strong-secret>
ANON_FINGERPRINT_SALT=<rotated-salt>
CORS_ORIGINS=https://www.lenamd.com,https://lenamd.com,https://lena-app.up.railway.app
APP_URL=https://www.lenamd.com
BILLING_SUCCESS_URL=https://www.lenamd.com/chat?billing=success
BILLING_CANCEL_URL=https://www.lenamd.com/chat?billing=cancelled
FREE_SEARCH_LIMIT_ANON=3
SUPABASE_* / OPENAI_API_KEY / RESEND_API_KEY / STRIPE_* (live keys)
```

### Frontend
```
BACKEND_URL=https://lena-production-health.up.railway.app
NEXT_PUBLIC_API_URL=/api
```

---

## Pre-launch commands

```bash
# Smoke test (production)
./scripts/smoke_test_production.sh

# Backend unit tests
cd backend && python3 -m pytest tests/ -q

# Frontend build
cd frontend && npm run build

# Playwright (against production)
cd frontend && npm ci && npx playwright install chromium && npm run test:e2e
```

---

## Known non-blockers (post-launch)

- Stripe live keys — billing falls back to mailto until configured
- `admin.html` / `hq.html` hardcoded backend URLs
- In-memory rate limiter (single worker OK for v1)
- Docs still reference Railway URLs in places
- `/api/ingest` unauthenticated — consider auth gate at scale

---

## Lauren retest checklist

After deploy, Lauren should verify:

- [ ] All filter search returns results (Vitamin D query)
- [ ] NIH DSLD shows once (strikethrough only if source failed)
- [ ] Persona dropdown shows all roles with Research panel open
- [ ] Cite copies citation text
- [ ] Project 3+ shows nested searches without re-login
- [ ] Settings: Share, Upgrade, Contact all work with visible feedback
- [ ] Padlock on https://www.lenamd.com (no strikethrough)
- [ ] 3 anonymous searches before signup prompt
