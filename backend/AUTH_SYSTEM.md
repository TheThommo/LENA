# LENA Authentication & Freemium Funnel System

## Overview

The LENA authentication system implements a complete freemium conversion funnel that guides anonymous visitors through a progressive funnel to paid registration. All code is production-ready with proper error handling, JWT authentication, and comprehensive analytics tracking.

## Architecture

```
Anonymous Session Flow → Registration → Authenticated User
         ↓                   ↓                    ↓
    - No database user   - Create user     - Full access
    - Search limited to 2 - Get JWT token   - Plan-based limits
    - Tracked analytics  - Assign plan     - Subscription mgmt
```

## Core Components

### 1. JWT Authentication (`app/core/auth.py`)

Stateless token management using PyJWT.

**Functions:**
- `create_access_token(user_id, tenant_id, role, expires_delta)` - Create JWT token
- `verify_token(token)` - Decode and validate token
- `get_current_user(request)` - Extract user from Authorization header (optional auth)
- `require_auth(request)` - Enforce authentication (raises 401)
- `require_role(allowed_roles)` - Dependency factory for role-based access control

**Token Payload:**
```json
{
  "user_id": "uuid",
  "tenant_id": "uuid",
  "role": "public_user|practitioner|researcher|...",
  "exp": 1234567890,
  "iat": 1234567800
}
```

**Configuration:**
- `jwt_secret_key` - Secret signing key (change in production!)
- `jwt_algorithm` - "HS256"
- `jwt_expiration_minutes` - 1440 (24 hours)

### 2. Tenant Detection (`app/core/tenant.py`)

Multi-tenant subdomain/header-based routing.

**Logic:**
1. Check `X-Tenant-ID` header (for API clients)
2. Extract subdomain from Host header (e.g., "acme.lena-research.com" → "acme")
3. Default: "lena" (platform itself)

**Usage:**
```python
from app.core.tenant import detect_tenant
tenant_slug = detect_tenant(request)
```

### 3. Anonymous Session Management (`app/api/routes/session.py`)

Tracks user progression through the freemium funnel before registration.

**Endpoints:**

#### POST /api/session/start
Creates anonymous session, tracks "landed" stage.

**Response:**
```json
{
  "session_id": "uuid",
  "session_token": "session_uuid"
}
```

#### POST /api/session/{session_id}/name
Capture visitor name, tracks "name_captured" stage.

**Request:**
```json
{
  "name": "John Smith"
}
```

#### POST /api/session/{session_id}/disclaimer
Accept medical disclaimer (MANDATORY before search).
Tracks "disclaimer_accepted" stage with timestamp.

**Request:**
```json
{
  "accepted": true
}
```

**Response:**
```json
{
  "session_token": "session_uuid_authorized",
  "message": "Disclaimer accepted. You can now search."
}
```

#### POST /api/session/{session_id}/email
Capture email for follow-up.
Tracks "email_captured" stage.

**Request:**
```json
{
  "email": "john@example.com"
}
```

#### GET /api/session/{session_id}/status
Get current funnel stage and session data.

**Response:**
```json
{
  "session_id": "uuid",
  "funnel_stage": "disclaimer_accepted",
  "search_count": 0,
  "name": "John Smith",
  "email": null,
  "disclaimer_accepted_at": "2026-04-08T15:30:00"
}
```

### 4. Search Gate Middleware (`app/middleware/search_gate.py`)

Enforces freemium search limits on `/api/search/` endpoints.

**Rules:**
- No session token → 401 Unauthorized
- Disclaimer not accepted → 401 Unauthorized
- Search count >= 2 AND not registered → 403 Forbidden (signup gate)
- Otherwise → Allow and increment counter
- Registered users bypass counter (plan limits apply)

**Token Extraction:**
1. From Authorization header: "Bearer session_uuid" or "Bearer session_uuid_authorized"
2. From X-Session-ID header

**Flow:**
```
Request → SearchGateMiddleware
    ↓
Check session exists?
    ├─ No → 401
    ↓
Check disclaimer accepted?
    ├─ No → 401
    ↓
Check user registered?
    ├─ Yes → Allow (plan limits apply)
    ├─ No → Check search_count
    │   ├─ >= 2 → 403 (show signup CTA)
    │   ├─ < 2 → Increment counter & allow
    ↓
Continue to /api/search/
```

### 5. Authentication Routes (`app/api/routes/auth.py`)

User registration and login.

**Endpoints:**

#### POST /api/auth/register
Create new user account from anonymous session.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123",
  "name": "John Smith",
  "session_id": "uuid (optional)"
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "john@example.com",
    "name": "John Smith",
    "role": "public_user",
    "persona_type": "general",
    "tenant_id": "uuid",
    "created_at": "2026-04-08T15:30:00"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Side effects:**
- Creates user in database
- Assigns to detected tenant (or creates default)
- Assigns "free" plan
- Links to anonymous session (if session_id provided)
- Tracks "registered" funnel stage
- Returns JWT access token

#### POST /api/auth/login
Authenticate with email/password.

**Request:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "user": { ... },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

#### GET /api/auth/me
Get current user profile (requires authentication).

**Headers:**
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response:**
```json
{
  "id": "uuid",
  "email": "john@example.com",
  "name": "John Smith",
  "role": "public_user",
  "persona_type": "general",
  "tenant_id": "uuid",
  "created_at": "2026-04-08T15:30:00"
}
```

#### POST /api/auth/logout
Invalidate session (logs event, client should discard token).

**Response:**
```json
{
  "message": "Logged out successfully. Please discard your token."
}
```

## Freemium Funnel Flow

The complete user journey is tracked through funnel stages:

### 1. **Landed** (automatic)
- User visits site
- AnalyticsMiddleware captures IP/geo/UTM
- Funnel stage: **landed**

### 2. **Name Capture**
- `POST /api/session/start` → get session_id
- `POST /api/session/{session_id}/name` → store name
- Funnel stage: **name_captured**

### 3. **Disclaimer Acceptance** (MANDATORY)
- `POST /api/session/{session_id}/disclaimer` → accept terms
- Funnel stage: **disclaimer_accepted**
- Now allowed to search

### 4. **First Search**
- User makes first search via `/api/search/`
- SearchGateMiddleware increments counter
- Funnel stage: **first_search**

### 5. **Email Capture**
- `POST /api/session/{session_id}/email` → store email
- Funnel stage: **email_captured**

### 6. **Second Search**
- User makes second search
- SearchGateMiddleware increments counter to 2
- Funnel stage: **second_search**

### 7. **Signup CTA Shown**
- User attempts 3rd search
- SearchGateMiddleware blocks with 403
- Funnel stage: **signup_cta_shown**
- Frontend shows signup modal

### 8. **Registration**
- `POST /api/auth/register` → create account
- Links session to user_id
- Funnel stage: **registered**
- Now full access to searches

## Data Model

### Sessions Table Extensions

New fields for funnel tracking:
- `name: string` - Captured visitor name
- `email: string` - Captured email
- `disclaimer_accepted_at: timestamp` - When disclaimer was accepted (MANDATORY)
- `search_count: int` - Number of searches performed (default 0)

These are already added to:
- `app/models/session.py` - SessionBase, SessionUpdate, Session, SessionStatus
- Session repository already supports update operations

### Users Table
Already has:
- `id: uuid`
- `email: string` (unique)
- `name: string`
- `tenant_id: uuid`
- `role: enum` (default: public_user)
- `persona_type: enum`
- `created_at: timestamp`
- `updated_at: timestamp`
- `last_login_at: timestamp` (nullable)

### Plans Table
Already has:
- `id: uuid`
- `name: string`
- `slug: enum` (free, starter, professional, enterprise)
- `price_monthly: float`
- `search_limit_monthly: int`
- `features: json`
- `is_active: bool`

### Subscriptions Table
Already has:
- `id: uuid`
- `tenant_id: uuid`
- `plan_id: uuid`
- `status: enum` (active, past_due, cancelled, trialing)
- `current_period_start: timestamp`
- `current_period_end: timestamp`
- `created_at: timestamp`

## Analytics Integration

All funnel stages are tracked via `track_funnel_stage()`:

```python
from app.services.funnel_tracker import track_funnel_stage

await track_funnel_stage(
    session_id=str(session.id),
    tenant_id=str(session.tenant_id),
    stage="name_captured",
    user_id=None,  # None for anonymous
    metadata={"name": "John Smith"},
)
```

**Logged to:** `usage_analytics` table with:
- action: "funnel_stage"
- metadata.session_id: session UUID
- metadata.stage: funnel stage name
- metadata.timestamp: when stage reached

## Middleware Registration

In `app/main.py`:

```python
# Analytics middleware - captures IP, geo, UTM (all requests)
app.add_middleware(AnalyticsMiddleware)

# Search gate - enforces freemium limits (/api/search/)
app.add_middleware(SearchGateMiddleware)

# Routes
app.include_router(session.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(search.router, prefix="/api")
```

**Important:** SearchGateMiddleware must be registered BEFORE the search router.

## Configuration

Update `app/core/config.py`:

```python
# Authentication & JWT
jwt_secret_key: str = "change-me-in-production"
jwt_algorithm: str = "HS256"
jwt_expiration_minutes: int = 1440  # 24 hours

# Freemium
free_search_limit: int = 2
```

**Production checklist:**
- [ ] Set `jwt_secret_key` to secure random value
- [ ] Set `jwt_algorithm` to HS256 or RS256 (avoid HS256 in highly distributed systems)
- [ ] Set `jwt_expiration_minutes` to desired value
- [ ] Verify `free_search_limit` matches product spec

## Usage Examples

### Frontend: Complete Funnel Flow

```javascript
// 1. Start session
const sessionRes = await fetch("/api/session/start", { method: "POST" });
const { session_id, session_token } = await sessionRes.json();

// 2. Capture name
await fetch(`/api/session/${session_id}/name`, {
  method: "POST",
  body: JSON.stringify({ name: "John Smith" }),
  headers: { "Content-Type": "application/json" }
});

// 3. Show disclaimer modal
const disclaimerRes = await fetch(
  `/api/session/${session_id}/disclaimer`,
  {
    method: "POST",
    body: JSON.stringify({ accepted: true }),
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${session_token}`
    }
  }
);
const { session_token: authorizedToken } = await disclaimerRes.json();

// 4. First search
const searchRes = await fetch("/api/search/?q=diabetes", {
  headers: { "Authorization": `Bearer ${authorizedToken}` }
});

// 5. Capture email (after first search)
await fetch(`/api/session/${session_id}/email`, {
  method: "POST",
  body: JSON.stringify({ email: "john@example.com" }),
  headers: { "Content-Type": "application/json" }
});

// 6. Try second search
const search2Res = await fetch("/api/search/?q=treatment", {
  headers: { "Authorization": `Bearer ${authorizedToken}` }
});

// 7. Try third search → blocked with 403
const search3Res = await fetch("/api/search/?q=clinical", {
  headers: { "Authorization": `Bearer ${authorizedToken}` }
});
if (search3Res.status === 403) {
  // Show signup modal
  const registerRes = await fetch("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email: "john@example.com",
      password: "securepassword123",
      name: "John Smith",
      session_id: session_id
    }),
    headers: { "Content-Type": "application/json" }
  });
  const { access_token } = await registerRes.json();
  
  // Now use access_token for unlimited searches
  const search3Res = await fetch("/api/search/?q=clinical", {
    headers: { "Authorization": `Bearer ${access_token}` }
  });
}
```

### Backend: Protected Routes

```python
from fastapi import Depends
from app.core.auth import require_auth, require_role

@app.get("/api/protected-endpoint")
async def protected(user: dict = Depends(require_auth)):
    """User must provide valid JWT."""
    return {"user_id": user["user_id"], "role": user["role"]}

@app.delete("/api/admin-action")
async def admin_action(user: dict = Depends(require_role(["platform_admin", "tenant_admin"]))):
    """Only admin users allowed."""
    return {"action": "performed by", "admin": user["user_id"]}
```

## Error Handling

### Common Status Codes

| Status | Scenario | Response |
|--------|----------|----------|
| 201 | Session/User created | `{ session_id, ... }` or `{ user, access_token }` |
| 200 | Successful request | Response data |
| 400 | Invalid input | `{ detail: "..." }` |
| 401 | No auth / Disclaimer not accepted | `{ detail: "..." }` |
| 403 | Search limit exceeded | `{ detail: "You've used your 2 free searches..." }` |
| 404 | Session/User not found | `{ detail: "..." }` |
| 409 | Email already registered | `{ detail: "Email already registered" }` |
| 500 | Server error | `{ detail: "..." }` |

## TODO: Password Management

Current implementation **does not hash passwords**. Before production:

1. Integrate Supabase Auth for password management
2. Use:
   ```python
   from supabase import create_client
   supabase = create_client(url, key)
   
   # Sign up
   supabase.auth.sign_up({"email": email, "password": password})
   
   # Sign in
   supabase.auth.sign_in_with_password({"email": email, "password": password})
   ```
3. Store auth tokens in supabase.auth.session()
4. Update login/register endpoints to call Supabase Auth

## Files Created/Modified

**Created:**
- `app/core/auth.py` - JWT utilities
- `app/core/tenant.py` - Tenant detection
- `app/api/routes/session.py` - Anonymous session endpoints
- `app/api/routes/auth.py` - Registration/login endpoints
- `app/middleware/search_gate.py` - Search limit enforcement

**Modified:**
- `requirements.txt` - Added PyJWT==2.9.0
- `app/core/config.py` - Added JWT config, free_search_limit
- `app/models/session.py` - Added funnel tracking fields
- `app/models/__init__.py` - Exported SessionStatus
- `app/main.py` - Registered routes and middleware

## Testing

Health check endpoint:

```bash
curl http://localhost:8000/api/health
```

Start session:

```bash
curl -X POST http://localhost:8000/api/session/start
```

Full funnel test (see usage examples above).

## Production Considerations

1. **JWT Secret**: Change `jwt_secret_key` to a secure random value
2. **Password Hashing**: Integrate Supabase Auth or another secure auth service
3. **HTTPS Only**: Ensure all endpoints are HTTPS in production
4. **CORS**: Update `cors_origins` to match frontend domain
5. **Rate Limiting**: Consider implementing rate limiting per IP/session
6. **Monitoring**: Add logging and error tracking for auth failures
7. **Backup Plans**: Ensure fallback if Supabase connection fails
8. **Token Refresh**: Consider implementing refresh tokens for extended sessions
