# Authentication System Integration Checklist

## Overview
This checklist guides integration of the complete authentication and freemium funnel system into the LENA platform.

## Status: COMPLETE (Agent 1)

All authentication and freemium funnel code has been implemented. Below is the integration verification and next steps.

## Implementation Summary

### Code Files Created
- [x] `app/core/auth.py` - JWT token creation, verification, authentication dependencies
- [x] `app/core/tenant.py` - Multi-tenant detection from subdomain/header
- [x] `app/api/routes/session.py` - Anonymous session management (5 endpoints)
- [x] `app/api/routes/auth.py` - Registration and login (4 endpoints)
- [x] `app/middleware/search_gate.py` - Search limit enforcement middleware

### Code Files Modified
- [x] `requirements.txt` - Added PyJWT==2.9.0
- [x] `app/core/config.py` - Added JWT and freemium config
- [x] `app/models/session.py` - Added funnel tracking fields (name, email, disclaimer_accepted_at, search_count)
- [x] `app/models/__init__.py` - Exported SessionStatus model
- [x] `app/main.py` - Registered session and auth routers, registered search gate middleware

### Documentation
- [x] `AUTH_SYSTEM.md` - Complete system documentation with examples

## Pre-Deployment Checklist

### Backend Setup
- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Test imports: `python -c "from app.core.auth import create_access_token"`
- [ ] Verify database migrations are applied (sessions table must have: name, email, disclaimer_accepted_at, search_count fields)
- [ ] Run health check: `curl http://localhost:8000/api/health`

### Configuration
- [ ] Update `.env` with:
  ```
  JWT_SECRET_KEY=your-secure-random-key
  JWT_ALGORITHM=HS256
  JWT_EXPIRATION_MINUTES=1440
  FREE_SEARCH_LIMIT=2
  ```
- [ ] Verify Supabase credentials are set (SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY)
- [ ] Verify CORS origins: `CORS_ORIGINS=http://localhost:3000,https://your-frontend.com`

### Database Schema
- [ ] Verify `sessions` table has fields:
  - `id: uuid (pk)`
  - `user_id: uuid (fk, nullable)`
  - `tenant_id: uuid (fk)`
  - `ip_address: string`
  - `geo_city: string`
  - `geo_country: string`
  - `geo_lat: float`
  - `geo_lon: float`
  - `referrer: string`
  - `utm_source: string`
  - `utm_medium: string`
  - `utm_campaign: string`
  - `name: string (NEW)`
  - `email: string (NEW)`
  - `disclaimer_accepted_at: timestamp (NEW)`
  - `search_count: int (NEW, default 0)`
  - `started_at: timestamp (default now())`
  - `ended_at: timestamp (nullable)`

- [ ] Verify `users` table has fields:
  - `id: uuid (pk)`
  - `email: string (unique, indexed)`
  - `name: string`
  - `tenant_id: uuid (fk)`
  - `role: enum (default 'public_user')`
  - `persona_type: enum (default 'general')`
  - `created_at: timestamp (default now())`
  - `updated_at: timestamp (default now())`
  - `last_login_at: timestamp (nullable)`

- [ ] Verify `plans` table has "free" plan:
  - `slug: 'free'`
  - `name: 'Free'`
  - `price_monthly: 0.00`
  - `search_limit_monthly: 2` (optional, enforced by search gate)
  - `is_active: true`

- [ ] Verify `subscriptions` table has foreign keys to users, plans, tenants

### API Testing

#### Session Endpoints
- [ ] `POST /api/session/start` returns session_id and session_token
- [ ] `POST /api/session/{id}/name` stores name in session
- [ ] `POST /api/session/{id}/disclaimer` accepts disclaimer and returns authorized token
- [ ] `POST /api/session/{id}/email` stores email in session
- [ ] `GET /api/session/{id}/status` returns current funnel stage

**Test command:**
```bash
# Start session
curl -X POST http://localhost:8000/api/session/start

# Capture name
curl -X POST http://localhost:8000/api/session/{SESSION_ID}/name \
  -H "Content-Type: application/json" \
  -d '{"name": "Test User"}'

# Accept disclaimer
curl -X POST http://localhost:8000/api/session/{SESSION_ID}/disclaimer \
  -H "Content-Type: application/json" \
  -d '{"accepted": true}'

# Check status
curl http://localhost:8000/api/session/{SESSION_ID}/status
```

#### Auth Endpoints
- [ ] `POST /api/auth/register` creates user and returns JWT token
- [ ] `POST /api/auth/login` authenticates user and returns JWT token
- [ ] `GET /api/auth/me` returns user profile with valid token
- [ ] `POST /api/auth/logout` logs out user

**Test command:**
```bash
# Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepassword123",
    "name": "Test User",
    "session_id": "optional-uuid"
  }'

# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "securepassword123"}'

# Get profile (use token from register/login)
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Search Gate Middleware
- [ ] Anonymous user without session token gets 401 on `/api/search/`
- [ ] User without disclaimer acceptance gets 401 on `/api/search/`
- [ ] First search succeeds (search_count incremented to 1)
- [ ] Second search succeeds (search_count incremented to 2)
- [ ] Third search blocked with 403 and "signup required" message
- [ ] Registered users bypass the counter

**Test command:**
```bash
# Try search without session → 401
curl http://localhost:8000/api/search/?q=test

# Try search with session token but no disclaimer → 401
curl http://localhost:8000/api/search/?q=test \
  -H "Authorization: Bearer session_uuid"

# Try search with authorized session token
curl http://localhost:8000/api/search/?q=test \
  -H "Authorization: Bearer session_uuid_authorized"

# Try third search → 403
# (after 2 successful searches)
curl http://localhost:8000/api/search/?q=test \
  -H "Authorization: Bearer session_uuid_authorized"
```

### Frontend Integration

Frontend needs to implement the freemium funnel UI flow:

- [ ] Create `/api/session/start` on page load
- [ ] Store session_id in state/session storage
- [ ] Show name capture modal → `POST /api/session/{id}/name`
- [ ] Show medical disclaimer modal → `POST /api/session/{id}/disclaimer`
- [ ] Store session_token from disclaimer response in auth header
- [ ] Allow first search
- [ ] After first search, show email capture modal → `POST /api/session/{id}/email`
- [ ] Allow second search
- [ ] After second search, show signup modal
- [ ] Redirect to register flow or show login
- [ ] After registration/login, use JWT token for unlimited searches

### Analytics Integration

- [ ] Verify `usage_analytics` table receives funnel events
- [ ] Funnel stages logged: landed, name_captured, disclaimer_accepted, first_search, email_captured, second_search, signup_cta_shown, registered
- [ ] Set up analytics dashboard queries to track:
  - Funnel drop-off (% reaching each stage)
  - Time between stages
  - Signup conversion rate
  - Search counts per session

### Security Review

- [ ] JWT secret is not "change-me-in-production" in production
- [ ] CORS origins are restricted to your frontend domain(s)
- [ ] HTTPS enforced in production
- [ ] Rate limiting configured (optional but recommended)
- [ ] SQL injection protection verified (using Supabase parameterized queries)
- [ ] XSS protection in frontend (sanitize user inputs)
- [ ] CSRF tokens implemented if using cookie-based sessions
- [ ] Medical disclaimer acceptance is mandatory before any search

### Deployment Steps

1. **Update Requirements**
   ```bash
   pip install -r requirements.txt
   ```

2. **Apply Database Migrations** (if needed)
   - Run any pending migrations for new session fields
   - Ensure "free" plan exists in plans table

3. **Deploy Backend**
   ```bash
   git add .
   git commit -m "feat: Add auth system and freemium funnel (Agent 1)"
   git push origin main
   # Deploy to Railway / your chosen platform
   ```

4. **Test All Endpoints**
   - Run the test commands above
   - Verify error responses are correct
   - Check database records are created

5. **Deploy Frontend**
   - Implement UI components from wireframes
   - Integrate with backend endpoints
   - Test complete funnel flow

### Post-Deployment Verification

- [ ] Health check passes: `curl /api/health`
- [ ] Session endpoint responds: `POST /api/session/start`
- [ ] Search gate blocks unauthenticated: `GET /api/search/`
- [ ] JWT tokens work: `GET /api/auth/me` with valid token
- [ ] Funnel events logged in analytics
- [ ] Monitor error logs for any auth-related issues

## Known Limitations & TODO

### Password Management
Current implementation does NOT hash passwords. TODO before production:
- Integrate Supabase Auth (sign_up, sign_in_with_password)
- Implement password reset flow
- Consider two-factor authentication

### Session Linking
When anonymous session is converted to registered user:
- All previous searches and analytics are linked to user_id
- Plan-based limits apply on subsequent searches

### Token Refresh
JWT tokens don't auto-refresh. TODO:
- Implement refresh token flow
- Add token refresh endpoint
- Update frontend to refresh before expiration

### Plan Limits
Free search limit is hardcoded at 2. TODO:
- Implement plan-based search limits (from plans table)
- Handle monthly limit resets
- Add usage tracking per plan

## Support & Troubleshooting

### Common Issues

**"Session not found" on create**
- Likely Supabase connection issue
- Check SUPABASE_URL and SUPABASE_ANON_KEY in .env
- Verify sessions table exists and is accessible

**"401 Unauthorized" on search**
- Session token missing or invalid
- Check Authorization header format: "Bearer session_uuid"
- Ensure disclaimer was accepted

**"403 Forbidden" (intended)**
- User has exceeded free search limit
- Show signup modal to prompt registration
- This is correct behavior (not a bug)

**JWT verification fails**
- jwt_secret_key mismatch between token creation and verification
- Check JWT_SECRET_KEY is set consistently
- Verify token hasn't expired (exp claim)

### Monitoring

Key metrics to track:
- Auth endpoint response times
- Session creation rate
- Funnel drop-off by stage
- Search gate blocks (signup conversion point)
- JWT token expiration rate

## Next Steps (Agent 2+)

1. **Admin Console** - Build dashboard with:
   - User management (approve researchers, etc.)
   - Plan/subscription management
   - Analytics and funnel metrics
   - Tenant configuration

2. **Payment Integration** - Implement:
   - Stripe/payment processor integration
   - Subscription management
   - Billing portal for users

3. **Advanced Features**:
   - API key management for developers
   - Team/organization management
   - Audit logs for compliance
   - SSO/OAuth integration

## Questions?

Refer to `AUTH_SYSTEM.md` for complete technical documentation.
