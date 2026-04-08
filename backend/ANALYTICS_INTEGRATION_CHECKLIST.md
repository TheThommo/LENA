# Analytics Engine Integration Checklist

## Files Created by Agent 3 (Analytics & Geo Tracking Engine)

### Services (New)
- [x] `/app/services/geolocation.py` - IP → geographic data via ip-api.com
- [x] `/app/services/tracking.py` - UTM & referrer parsing
- [x] `/app/services/topic_classifier.py` - Query topic classification (MVP, keyword-based)
- [x] `/app/services/analytics_writer.py` - Async Supabase write functions (fire-and-forget)
- [x] `/app/services/funnel_tracker.py` - Freemium funnel stage tracking

### Middleware (New)
- [x] `/app/middleware/__init__.py` - Middleware package init
- [x] `/app/middleware/analytics.py` - Core request-level analytics middleware

### Configuration (Modified)
- [x] `/app/main.py` - Surgical edits to import & register AnalyticsMiddleware

### Documentation (New)
- [x] `ANALYTICS_ENGINE.md` - Comprehensive service documentation
- [x] `ANALYTICS_INTEGRATION_CHECKLIST.md` - This file

## What the Analytics Engine Does

### On Every Request
1. Extracts client IP (checks X-Forwarded-For header)
2. Geolocates IP → country/city/lat/lon (cached, ip-api.com)
3. Parses UTM parameters (utm_source, utm_medium, utm_campaign, etc.)
4. Classifies referrer source (organic_search, social, email, paid, direct, referral)
5. Creates unique session ID
6. Stores context in `request.state` for route handlers to access
7. Logs session to `sessions` table (background task)

### Data Collection Points
- **Sessions table**: One row per unique session with geo + referrer + UTM data
- **Search logs table**: One row per search with query, response time, sources, results count
- **Usage analytics table**: Generic events (button clicks, form submissions, funnel progression)
- **Audit trail table**: Admin actions and resource modifications

### Key Features
- **Non-blocking**: All Supabase writes are background tasks (asyncio.create_task)
- **Fire-and-forget**: Analytics failures never crash the app
- **Caching**: IP geolocation results cached in memory (max 1000, LRU eviction)
- **Graceful degradation**: Rate limits, network errors handled gracefully
- **Multi-tenant ready**: All data tagged with tenant_id

## Integration Points for Agent 2 (Pydantic Models/Repos)

The analytics engine currently writes directly to Supabase using simple dicts:
```python
payload = {
    "id": session_id,
    "tenant_id": tenant_id,
    "ip_address": ip_address,
    "geo_city": geo_data.get("city") if geo_data else None,
    ...
}
client.table("sessions").insert(payload).execute()
```

When Agent 2 builds Pydantic models and repository layer, refactor these functions to use:
```python
from app.models.session import SessionModel
from app.repositories.session import SessionRepository

payload = SessionModel(
    id=session_id,
    tenant_id=tenant_id,
    ip_address=ip_address,
    geo_city=geo_data.get("city") if geo_data else None,
    ...
)
await SessionRepository.create(payload)
```

The analytics code is written to be easily refactorable to use the repo layer.

## Integration Points for Route Handlers

### Access Analytics Context
```python
@app.get("/api/search")
async def search(request: Request, query: str):
    session_id = request.state.session_id
    geo_data = request.state.geo_data  # {"country": "US", "city": "SF", "lat": 37.77, "lon": -122.41}
    utm_data = request.state.utm_data  # {"utm_source": "google", ...}
    referrer_data = request.state.referrer_data  # {"domain": "google.com", "category": "organic_search"}
    tenant_id = request.state.tenant_id
    
    # Use this data as needed
```

### Log Search Events
```python
from app.services.analytics_writer import log_search_event, schedule_analytics_task
import time

start = time.time()
results = await perform_search(query)
elapsed_ms = (time.time() - start) * 1000

# Log search (background task, doesn't block)
schedule_analytics_task(
    log_search_event(
        search_id="search_uuid",
        session_id=request.state.session_id,
        query=query,
        persona="patient",  # detected from query or user profile
        tenant_id=request.state.tenant_id,
        response_time_ms=elapsed_ms,
        sources_queried=["pubmed", "clinical_trials"],
        sources_succeeded=["pubmed"],
        total_results=len(results),
        pulse_status="valid",
    )
)
```

### Track Funnel Progression
```python
from app.services.funnel_tracker import track_funnel_stage

# After user accepts disclaimer
await track_funnel_stage(
    session_id=request.state.session_id,
    tenant_id=request.state.tenant_id,
    stage="disclaimer_accepted",
    user_id=None,  # Still anonymous
)

# After first search
await track_funnel_stage(
    session_id=request.state.session_id,
    tenant_id=request.state.tenant_id,
    stage="first_search",
    user_id=None,
)

# After email captured
await track_funnel_stage(
    session_id=request.state.session_id,
    tenant_id=request.state.tenant_id,
    stage="email_captured",
    user_id=None,
    metadata={"email": user_email},
)

# After user registers
await track_funnel_stage(
    session_id=request.state.session_id,
    tenant_id=request.state.tenant_id,
    stage="registered",
    user_id=newly_created_user_id,
)
```

### Log Generic Usage Events
```python
from app.services.analytics_writer import log_usage_event, schedule_analytics_task

# User clicked a button
schedule_analytics_task(
    log_usage_event(
        tenant_id=request.state.tenant_id,
        user_id=None,
        action="button_click",
        metadata={"button_id": "search_submit", "page": "/search"},
    )
)

# User submitted a form
schedule_analytics_task(
    log_usage_event(
        tenant_id=request.state.tenant_id,
        user_id=user_id,  # Now authenticated
        action="form_submit",
        metadata={"form_name": "signup", "fields": ["email", "password"]},
    )
)
```

### Log Audit Events
```python
from app.services.analytics_writer import log_audit_event, schedule_analytics_task

# Admin modified a search's pulse status
schedule_analytics_task(
    log_audit_event(
        user_id=admin_user_id,
        tenant_id=request.state.tenant_id,
        action="update",
        resource_type="search",
        resource_id=search_id,
        details={
            "field": "pulse_status",
            "old_value": "flagged",
            "new_value": "valid",
        },
        ip_address=request.state.ip_address,
    )
)
```

## Supabase Tables (Expected Schema)

These are the tables the analytics engine expects to exist. Schema should be created via Supabase migrations (Agent 1 likely already created these):

### sessions
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    ip_address TEXT,
    geo_city TEXT,
    geo_country TEXT,
    geo_lat NUMERIC,
    geo_lon NUMERIC,
    referrer TEXT,
    referrer_domain TEXT,
    referrer_category TEXT,
    utm_source TEXT,
    utm_medium TEXT,
    utm_campaign TEXT,
    utm_term TEXT,
    utm_content TEXT,
    started_at TIMESTAMP DEFAULT NOW(),
    ended_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### search_logs
```sql
CREATE TABLE search_logs (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    query TEXT,
    persona TEXT,
    response_time_ms NUMERIC,
    sources_queried TEXT[],
    sources_succeeded TEXT[],
    total_results INTEGER,
    pulse_status TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### usage_analytics
```sql
CREATE TABLE usage_analytics (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(id),
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    action TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### audit_trail
```sql
CREATE TABLE audit_trail (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    tenant_id UUID REFERENCES tenants(id),
    action audit_action,  -- enum: create, read, update, delete, export, admin_override
    resource_type TEXT,
    resource_id TEXT,
    details JSONB,
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Testing the Analytics Engine

### 1. Start the backend
```bash
cd /sessions/inspiring-sharp-pascal/mnt/HeathNet\ Rebuild/lena/backend
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Make a test request
```bash
curl -v "http://localhost:8000/?utm_source=test_google&utm_medium=organic"
# Should return 200 with LENA API info

# Check middleware is registered
curl -v "http://localhost:8000/docs"  # Should load Swagger docs normally
```

### 3. Verify session was logged in Supabase
```bash
# From Supabase dashboard:
# SQL Editor > SELECT * FROM sessions LIMIT 1;
# Should see one row with utm_source="test_google", utm_medium="organic"
```

### 4. Test topic classifier
```bash
python << 'EOF'
import sys
sys.path.insert(0, '/sessions/inspiring-sharp-pascal/mnt/HeathNet Rebuild/lena/backend')

from app.services.topic_classifier import classify_query_topic

test_queries = [
    "What are the best treatments for type 2 diabetes?",
    "My mom has heart problems",
    "COVID-19 vaccination",
    "Can yoga help my anxiety?",
]

for query in test_queries:
    topics = classify_query_topic(query)
    print(f"{query} → {topics}")
EOF
```

### 5. Test geolocation
```bash
python << 'EOF'
import asyncio
import sys
sys.path.insert(0, '/sessions/inspiring-sharp-pascal/mnt/HeathNet Rebuild/lena/backend')

from app.services.geolocation import geolocate_ip

async def test():
    # Test with a public IP
    geo = await geolocate_ip("8.8.8.8")
    print(f"8.8.8.8 → {geo}")
    
    # Test with localhost (should return None)
    geo = await geolocate_ip("127.0.0.1")
    print(f"127.0.0.1 → {geo}")

asyncio.run(test())
EOF
```

### 6. Test referrer classification
```bash
python << 'EOF'
import sys
sys.path.insert(0, '/sessions/inspiring-sharp-pascal/mnt/HeathNet Rebuild/lena/backend')

from app.services.tracking import classify_referrer, parse_utm_params

# Test referrer
refs = [
    "https://google.com/search?q=lena",
    "https://twitter.com/home",
    "https://mycompany.com/blog",
    None,
]

for ref in refs:
    result = classify_referrer(ref)
    print(f"{ref} → {result['category']}")

# Test UTM
params = {"utm_source": "linkedin", "utm_medium": "organic"}
utm = parse_utm_params(params)
print(f"\nUTM params: {utm}")
EOF
```

## Performance Expectations

- **Middleware latency**: < 1ms (mostly parsing)
- **Geolocation lookup**: ~100-300ms (cached after first lookup)
- **Supabase write**: ~50-200ms (async, doesn't block)
- **Total request overhead**: < 1ms on path (all writes are background tasks)

## Monitoring & Debugging

### Enable debug logging
In `.env`:
```env
LOGGING_LEVEL=DEBUG
```

### Check analytics logs
```bash
# From your backend container/shell:
tail -f logs/lena.log | grep analytics
```

### Monitor Supabase writes
```sql
-- Check latest sessions
SELECT id, ip_address, geo_country, utm_source, started_at
FROM sessions
ORDER BY started_at DESC
LIMIT 10;

-- Check latest searches
SELECT id, query, response_time_ms, total_results, created_at
FROM search_logs
ORDER BY created_at DESC
LIMIT 10;

-- Check funnel progression
SELECT action, metadata->>'stage' as funnel_stage, COUNT(*) as count
FROM usage_analytics
WHERE action = 'funnel_stage'
GROUP BY metadata->>'stage'
ORDER BY count DESC;
```

## Next Steps

1. **Agent 2**: Build Pydantic models & repository layer, refactor analytics writer to use them
2. **Route handlers**: Add calls to `log_search_event`, `track_funnel_stage`, `log_usage_event`
3. **Phase 4 (Auth)**: Link anonymous sessions to user_id after signup
4. **Phase 5 (BI Dashboard)**: Query these tables to build the business intelligence views
5. **Future**: Add real-time WebSocket updates, anomaly detection, ML-based cohort analysis

## Known Limitations & TODOs

- [ ] Session ID not persisted in cookies (needs auth/phase 4)
- [ ] Tenant ID hardcoded as "default_tenant" (needs multi-tenancy routing)
- [ ] No user session linking (anonymous → registered) yet
- [ ] Topic classifier is MVP (keyword-based, not semantic)
- [ ] Geolocation disabled for localhost (by design)
- [ ] No session end tracking yet (needs logout/session timeout)

## Questions?

Refer to:
- `ANALYTICS_ENGINE.md` for detailed service documentation
- Agent 1's Supabase schema docs for table definitions
- Agent 2's models documentation for Pydantic integration
- Route handler examples in this checklist
