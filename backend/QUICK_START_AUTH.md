# Quick Start: Authentication & Freemium Funnel

## Installation

```bash
cd backend
pip install -r requirements.txt
```

## Running the Backend

```bash
# Development
python -m uvicorn app.main:app --reload --port 8000

# Production (Railway)
# See Dockerfile and railway.toml
```

## Testing the Freemium Flow

### 1. Start Session
```bash
curl -X POST http://localhost:8000/api/session/start \
  -H "Content-Type: application/json"
```

Response:
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "session_token": "session_550e8400-e29b-41d4-a716-446655440000"
}
```

Save `session_id` and `session_token` for next calls.

### 2. Capture Name
```bash
curl -X POST http://localhost:8000/api/session/{SESSION_ID}/name \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe"}'
```

### 3. Accept Disclaimer
```bash
curl -X POST http://localhost:8000/api/session/{SESSION_ID}/disclaimer \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {SESSION_TOKEN}" \
  -d '{"accepted": true}'
```

Response includes:
```json
{
  "session_token": "session_550e8400-e29b-41d4-a716-446655440000_authorized",
  "message": "Disclaimer accepted. You can now search."
}
```

Save the new `session_token` for search calls.

### 4. First Search
```bash
curl http://localhost:8000/api/search/?q=diabetes \
  -H "Authorization: Bearer session_550e8400-e29b-41d4-a716-446655440000_authorized"
```

Success! Search count is now 1.

### 5. Capture Email
```bash
curl -X POST http://localhost:8000/api/session/{SESSION_ID}/email \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com"}'
```

### 6. Second Search
```bash
curl http://localhost:8000/api/search/?q=treatment \
  -H "Authorization: Bearer session_550e8400-e29b-41d4-a716-446655440000_authorized"
```

Success! Search count is now 2.

### 7. Third Search (Blocked)
```bash
curl http://localhost:8000/api/search/?q=prevention \
  -H "Authorization: Bearer session_550e8400-e29b-41d4-a716-446655440000_authorized"
```

Response: **403 Forbidden**
```json
{
  "detail": "You've used your 2 free searches. Sign up to continue."
}
```

### 8. Register
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123",
    "name": "John Doe",
    "session_id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

Response:
```json
{
  "user": {
    "id": "...",
    "email": "john@example.com",
    "name": "John Doe",
    "role": "public_user",
    "persona_type": "general",
    "tenant_id": "...",
    "created_at": "2026-04-08T15:30:00"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

Save the `access_token`.

### 9. Unlimited Searches
```bash
curl http://localhost:8000/api/search/?q=clinical+trials \
  -H "Authorization: Bearer {ACCESS_TOKEN}"
```

Now unlimited! (Plan limits apply, not the 2-search limit)

## Common Commands

### Get Session Status
```bash
curl http://localhost:8000/api/session/{SESSION_ID}/status
```

### Check User Profile
```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

### Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "securepassword123"
  }'
```

### Logout
```bash
curl -X POST http://localhost:8000/api/auth/logout \
  -H "Authorization: Bearer {JWT_TOKEN}"
```

## Environment Setup

Create `.env` file:

```
# App
APP_ENV=development
APP_DEBUG=true
PORT=8000
CORS_ORIGINS=http://localhost:3000,localhost:3000

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# JWT
JWT_SECRET_KEY=your-super-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440

# Freemium
FREE_SEARCH_LIMIT=2

# OpenAI
OPENAI_API_KEY=sk-...

# NCBI
NCBI_API_KEY=your-ncbi-key
NCBI_EMAIL=your-email@example.com
```

## Key Files

| File | Purpose |
|------|---------|
| `app/core/auth.py` | JWT token creation/verification |
| `app/core/tenant.py` | Multi-tenant detection |
| `app/api/routes/session.py` | Anonymous session endpoints |
| `app/api/routes/auth.py` | Registration/login endpoints |
| `app/middleware/search_gate.py` | Search limit enforcement |
| `AUTH_SYSTEM.md` | Full technical documentation |
| `AUTH_INTEGRATION_CHECKLIST.md` | Deployment checklist |

## API Reference

### Session Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/session/start` | Create anonymous session |
| POST | `/api/session/{id}/name` | Capture name |
| POST | `/api/session/{id}/disclaimer` | Accept disclaimer |
| POST | `/api/session/{id}/email` | Capture email |
| GET | `/api/session/{id}/status` | Get status |

### Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Get profile |
| POST | `/api/auth/logout` | Logout |

### Protected Endpoints

| Path | Auth Required | Description |
|------|---------------|-------------|
| `/api/search/` | Yes | Search across all sources |
| `/api/auth/me` | Yes | Get user profile |
| Most admin endpoints | Yes | Tenant/admin operations |

## Troubleshooting

### "Session not found"
- Check session_id is valid UUID
- Verify session was created via `/api/session/start`
- Check Supabase connection

### "Invalid token" on search
- Include full Authorization header: `Bearer {token}`
- Token must have "authorized" suffix after disclaimer acceptance
- Check token hasn't expired (24 hours)

### "403 Forbidden" on 3rd search
- This is expected! Show signup modal
- User has hit the 2-free-search limit
- Redirect to registration

### JWT verification fails
- Check JWT_SECRET_KEY is set consistently
- Verify token structure (3 parts separated by dots)
- Ensure token hasn't expired

## Frontend Integration

Include in your app:

```javascript
// Start funnel
const res = await fetch('/api/session/start', { method: 'POST' });
const { session_id, session_token } = await res.json();

// Store in state
setSessionId(session_id);
setSessionToken(session_token);

// Make searches
const searchRes = await fetch(`/api/search/?q=${query}`, {
  headers: { Authorization: `Bearer ${sessionToken}` }
});

if (searchRes.status === 403) {
  // Show signup modal
  showSignupModal();
}
```

## Performance Notes

- JWT tokens are stateless (no database lookup)
- Search gate middleware runs before each search
- Session increments are lightweight updates
- Analytics writes are async (non-blocking)
- Geoip lookups are cached

## Security Checklist

- [ ] JWT_SECRET_KEY is unique and secure (>32 characters)
- [ ] CORS_ORIGINS matches frontend domain(s)
- [ ] Supabase RLS policies are enabled
- [ ] HTTPS enforced in production
- [ ] Rate limiting configured (optional)
- [ ] Medical disclaimer is non-negotiable

## Support

- Full documentation: `AUTH_SYSTEM.md`
- Integration guide: `AUTH_INTEGRATION_CHECKLIST.md`
- Questions? Check the docs first!

---

**Created by**: Agent 1 (Freemium Funnel & Auth)
**Last Updated**: 2026-04-08
