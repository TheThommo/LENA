# LENA Analytics Engine - Agent 3 Documentation

This document describes the analytics data collection engine built for LENA's business intelligence dashboard.

## Overview

The analytics engine is a non-blocking, fire-and-forget system that collects:
- **IP Geolocation** - where users are coming from (country, city, lat/lon)
- **UTM Tracking** - campaign attribution (utm_source, utm_medium, utm_campaign, utm_term, utm_content)
- **Referrer Classification** - traffic source categorization (organic_search, social, email, paid, direct, referral, unknown)
- **Session Tracking** - unique session IDs, timestamps, IP addresses
- **Search Events** - query topic, response time, sources used, results count, PULSE status
- **Usage Events** - user actions (button clicks, form submissions, conversions)
- **Funnel Progression** - tracking where users are in the freemium conversion funnel
- **Audit Trail** - admin actions and resource modifications

## Architecture

### File Structure
```
app/
├── middleware/
│   ├── __init__.py
│   └── analytics.py              # Core middleware (runs on every request)
├── services/
│   ├── geolocation.py            # IP geolocation (ip-api.com)
│   ├── tracking.py               # UTM & referrer parsing
│   ├── topic_classifier.py       # Query topic classification (MVP)
│   ├── analytics_writer.py       # Supabase write functions (async, fire-and-forget)
│   └── funnel_tracker.py         # Funnel stage tracking
└── main.py                       # (modified) middleware registration
```

### Request Flow

1. **Request arrives** → Middleware extracts IP, headers, query params
2. **Geolocation** (async) → IP → country/city/lat/lon
3. **Parse UTM** (sync) → Extract utm_source, utm_medium, utm_campaign, etc.
4. **Parse Referrer** (sync) → Classify into category (organic_search, social, etc.)
5. **Create Session** → Generate UUID, store in request.state
6. **Log to Supabase** (background task) → Fire-and-forget, never blocks
7. **Route handler executes** → Uses session/geo data from request.state
8. **Response sent** → Analytics tasks still running in background

### Key Design Principles

- **Non-blocking**: All Supabase writes are background tasks (asyncio.create_task)
- **Fire-and-forget**: Analytics failures NEVER crash the user experience
- **Graceful degradation**: Geolocation rate limits? Return None and continue
- **Efficient**: LRU cache for IP geolocation (prevents duplicate lookups)
- **Multi-tenant ready**: All data tagged with tenant_id

## Services

### 1. Geolocation Service (`geolocation.py`)

**Purpose**: Resolve IP → geographic coordinates

**Function**: `async def geolocate_ip(ip: str) -> Optional[dict]`

**Behavior**:
- Returns `{"country": "US", "city": "New York", "lat": 40.71, "lon": -74.00}` on success
- Returns `None` for private IPs (127.x, 192.168.x, etc.)
- Returns `None` on rate limit or network error (logs warning)
- Caches results in memory (max 1000 entries, LRU eviction)

**External API**: `http://ip-api.com/json/{ip}` (free, 45 req/min)

**Usage Example**:
```python
from app.services.geolocation import geolocate_ip

geo = await geolocate_ip("203.0.113.5")
# Returns: {"country": "US", "city": "San Francisco", "lat": 37.7749, "lon": -122.4194}
```

### 2. Tracking Service (`tracking.py`)

**Purpose**: Parse UTM parameters and classify referrer sources

**Functions**:

#### `parse_utm_params(query_params: dict) -> dict`
Extracts UTM parameters from query string.

**Returns**:
```python
{
    "utm_source": "google",
    "utm_medium": "cpc",
    "utm_campaign": "summer_2026",
    "utm_term": "clinical research",
    "utm_content": "ad_variant_a",
}
```

#### `classify_referrer(referrer: Optional[str]) -> dict`
Classifies referrer source into business-meaningful categories.

**Returns**:
```python
{
    "raw": "https://google.com/search?q=clinical+research",
    "domain": "google.com",
    "category": "organic_search",
}
```

**Categories**:
- `direct` - No referrer or empty
- `organic_search` - Google, Bing, DuckDuckGo, Yahoo, etc.
- `social` - Facebook, Twitter/X, LinkedIn, Instagram, Reddit, YouTube, TikTok, Pinterest
- `email` - Gmail, Outlook, Yahoo Mail, Mailchimp, Klaviyo, etc.
- `paid` - Ads platforms (Google Ads, Facebook Ads, LinkedIn Ads, etc.)
- `referral` - All other domains
- `unknown` - Could not parse domain

### 3. Topic Classifier Service (`topic_classifier.py`)

**Purpose**: Classify search queries into medical/wellness topics

**Function**: `def classify_query_topic(query: str) -> list[str]`

**Returns**: List of matching topic categories (can be multiple)

**Topics** (MVP, keyword-based):
- `cardiovascular` - heart, cardiac, hypertension, stroke, etc.
- `oncology` - cancer, tumor, chemotherapy, etc.
- `neurology` - brain, alzheimer, seizure, etc.
- `infectious_disease` - infection, bacteria, viral, vaccine, etc.
- `mental_health` - depression, anxiety, ptsd, etc.
- `pediatrics` - child, infant, vaccine, developmental, etc.
- `orthopedics` - bone, fracture, arthritis, joint, etc.
- `dermatology` - skin, rash, acne, melanoma, etc.
- `endocrinology` - diabetes, thyroid, hormone, insulin, etc.
- `respiratory` - lung, asthma, pneumonia, breathing, etc.
- `gastroenterology` - stomach, ulcer, ibs, crohn, liver, etc.
- `alternative_medicine` - herbal, acupuncture, homeopathy, etc.
- `fitness_wellness` - exercise, fitness, yoga, strength training, etc.
- `nutrition` - diet, vitamin, protein, supplement, etc.
- `general` - (default if no other matches)

**Usage Example**:
```python
from app.services.topic_classifier import classify_query_topic

topics = classify_query_topic("What are the best treatments for type 2 diabetes?")
# Returns: ["endocrinology", "nutrition"]

topics = classify_query_topic("My mom has heart problems")
# Returns: ["cardiovascular"]
```

### 4. Analytics Writer Service (`analytics_writer.py`)

**Purpose**: Write analytics events to Supabase (fire-and-forget)

**All functions are async and non-blocking. Errors are logged but never raised.**

#### `log_session_start(session_id, ip, geo_data, referrer_data, utm_data, tenant_id)`
Logs session creation to `sessions` table.

**Payload**:
```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "default_tenant",
    "ip_address": "203.0.113.5",
    "geo_city": "San Francisco",
    "geo_country": "US",
    "geo_lat": 37.7749,
    "geo_lon": -122.4194,
    "referrer": "https://google.com/search?q=...",
    "referrer_domain": "google.com",
    "referrer_category": "organic_search",
    "utm_source": None,
    "utm_medium": None,
    "utm_campaign": None,
    "utm_term": None,
    "utm_content": None,
    "started_at": "2026-04-08T15:30:45.123456",
}
```

#### `log_search_event(search_id, session_id, query, persona, tenant_id, response_time_ms, sources_queried, sources_succeeded, total_results, pulse_status)`
Logs completed search to `search_logs` table.

**Payload**:
```python
{
    "id": "search_001",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "tenant_id": "default_tenant",
    "query": "type 2 diabetes treatment",
    "persona": "patient",
    "response_time_ms": 1245.5,
    "sources_queried": ["pubmed", "clinical_trials", "who"],
    "sources_succeeded": ["pubmed", "clinical_trials"],
    "total_results": 142,
    "pulse_status": "valid",
    "created_at": "2026-04-08T15:31:30.123456",
}
```

#### `log_usage_event(tenant_id, user_id, action, metadata=None)`
Logs generic usage events to `usage_analytics` table.

**Common actions**:
- `button_click` - User clicked something
- `form_submit` - User submitted a form
- `disclaimer_accepted` - Medical disclaimer was accepted
- `funnel_stage` - Funnel progression (see funnel_tracker.py)
- `page_view` - Page visit
- `search_initiated` - Search started

**Payload**:
```python
{
    "tenant_id": "default_tenant",
    "user_id": None,  # Anonymous
    "action": "button_click",
    "metadata": {
        "button_id": "search_submit",
        "page": "/search",
    },
    "created_at": "2026-04-08T15:31:45.123456",
}
```

#### `log_audit_event(user_id, tenant_id, action, resource_type, resource_id, details, ip_address)`
Logs admin/security events to `audit_trail` table.

**Actions** (audit_action enum):
- `create` - Created a resource
- `read` - Accessed a resource
- `update` - Modified a resource
- `delete` - Deleted a resource
- `export` - Exported data
- `admin_override` - Admin action

**Payload**:
```python
{
    "user_id": "user_123",
    "tenant_id": "default_tenant",
    "action": "update",
    "resource_type": "search",
    "resource_id": "search_001",
    "details": {
        "fields_changed": ["pulse_status"],
        "old_value": "flagged",
        "new_value": "valid",
    },
    "ip_address": "203.0.113.5",
    "created_at": "2026-04-08T15:31:45.123456",
}
```

#### `schedule_analytics_task(coro)`
Internal helper to schedule async tasks without blocking.
Never raises exceptions.

### 5. Funnel Tracker Service (`funnel_tracker.py`)

**Purpose**: Track user progression through the freemium conversion funnel

**Funnel Stages**:
1. `landed` - User visits the site
2. `name_captured` - User enters their name
3. `disclaimer_accepted` - User accepts medical disclaimer
4. `first_search` - User performs their first search (free)
5. `email_captured` - User enters email (after 1st search)
6. `second_search` - User performs second search (final free)
7. `signup_cta_shown` - Signup call-to-action is shown
8. `registered` - User creates account

**Function**: `async def track_funnel_stage(session_id, tenant_id, stage, user_id=None, metadata=None) -> bool`

**Usage Example**:
```python
from app.services.funnel_tracker import track_funnel_stage

# User enters email after first search
success = await track_funnel_stage(
    session_id="session_123",
    tenant_id="default_tenant",
    stage="email_captured",
    user_id=None,  # Still anonymous
    metadata={"email": "user@example.com"},
)
```

**Returns**: `True` if stage is valid, `False` if invalid stage

### 6. Analytics Middleware (`middleware/analytics.py`)

**Purpose**: Run on every request to collect analytics data

**Automatically extracts**:
- Client IP (checks X-Forwarded-For header first, then request.client.host)
- Geolocation (country, city, lat, lon)
- Referrer header
- UTM parameters
- Creates session ID

**Stores in request.state**:
```python
request.state.session_id         # str: UUID
request.state.tenant_id          # str: tenant ID
request.state.ip_address         # str: client IP
request.state.geo_data           # dict or None: {country, city, lat, lon}
request.state.referrer_data      # dict: {raw, domain, category}
request.state.utm_data           # dict: {utm_source, medium, campaign, term, content}
request.state.request_started_at # datetime: request start time
```

**Route handlers can access this data**:
```python
@app.get("/api/search")
async def search(request: Request):
    session_id = request.state.session_id
    geo = request.state.geo_data
    utm = request.state.utm_data
    
    # ... perform search ...
    
    # Log search event
    await log_search_event(
        search_id=str(uuid.uuid4()),
        session_id=session_id,
        query=query,
        persona="patient",
        tenant_id=request.state.tenant_id,
        response_time_ms=elapsed_ms,
        sources_queried=["pubmed", "clinical_trials"],
        sources_succeeded=["pubmed", "clinical_trials"],
        total_results=len(results),
        pulse_status="valid",
    )
```

## Supabase Tables

All analytics data is stored in four main tables:

### 1. `sessions` table
Tracks individual user sessions.

**Columns**:
- `id` (uuid, primary)
- `user_id` (uuid, nullable) - Links to users table when authenticated
- `tenant_id` (uuid) - Multi-tenant isolation
- `ip_address` (text)
- `geo_city` (text)
- `geo_country` (text)
- `geo_lat` (numeric)
- `geo_lon` (numeric)
- `referrer` (text)
- `referrer_domain` (text)
- `referrer_category` (text)
- `utm_source` (text)
- `utm_medium` (text)
- `utm_campaign` (text)
- `utm_term` (text)
- `utm_content` (text)
- `started_at` (timestamp)
- `ended_at` (timestamp, nullable)

### 2. `search_logs` table
Tracks individual search queries and their performance.

**Columns**:
- `id` (uuid, primary)
- `session_id` (uuid) - Foreign key to sessions
- `user_id` (uuid, nullable)
- `tenant_id` (uuid)
- `query` (text) - The search query
- `persona` (text) - Detected persona (patient, provider, researcher)
- `response_time_ms` (numeric) - Milliseconds to complete
- `sources_queried` (text[]) - Array of source names
- `sources_succeeded` (text[]) - Array of successful sources
- `total_results` (integer)
- `pulse_status` (text) - PULSE validation result
- `created_at` (timestamp)

### 3. `usage_analytics` table
Generic event logging for all user interactions.

**Columns**:
- `id` (uuid, primary)
- `session_id` (uuid, nullable) - May not always have session
- `user_id` (uuid, nullable)
- `tenant_id` (uuid)
- `action` (text) - Action type (button_click, form_submit, etc.)
- `metadata` (jsonb) - Custom data for this event
- `created_at` (timestamp)

### 4. `audit_trail` table
Security and compliance logging.

**Columns**:
- `id` (uuid, primary)
- `user_id` (uuid, nullable)
- `tenant_id` (uuid)
- `action` (audit_action enum) - create, read, update, delete, export, admin_override
- `resource_type` (text) - Type of resource affected
- `resource_id` (text, nullable) - ID of resource
- `details` (jsonb) - Custom audit details
- `ip_address` (text)
- `created_at` (timestamp)

## Integration Patterns

### In a Route Handler

```python
from fastapi import APIRouter, Request
from app.services.analytics_writer import log_search_event, schedule_analytics_task
from app.services.funnel_tracker import track_funnel_stage
import time
import uuid

router = APIRouter()

@router.post("/api/search")
async def search(request: Request, query: str):
    start_time = time.time()
    session_id = request.state.session_id
    tenant_id = request.state.tenant_id
    
    # Perform search...
    results = await search_orchestrator.search(query)
    
    # Calculate metrics
    response_time_ms = (time.time() - start_time) * 1000
    
    # Log search event (background task, doesn't block)
    schedule_analytics_task(
        log_search_event(
            search_id=str(uuid.uuid4()),
            session_id=session_id,
            query=query,
            persona="patient",
            tenant_id=tenant_id,
            response_time_ms=response_time_ms,
            sources_queried=results["sources_queried"],
            sources_succeeded=results["sources_succeeded"],
            total_results=len(results["papers"]),
            pulse_status=results["pulse_status"],
        )
    )
    
    return results
```

### Tracking Funnel Progression

```python
from app.services.funnel_tracker import track_funnel_stage

# After user accepts disclaimer
success = await track_funnel_stage(
    session_id=request.state.session_id,
    tenant_id=request.state.tenant_id,
    stage="disclaimer_accepted",
    user_id=None,  # Still anonymous
)
```

## Configuration

Analytics is configured via environment variables (in `.env`):

```env
# Supabase (required for analytics)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJxxx...
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...
```

No additional dependencies were added beyond what was already in `requirements.txt`.

## Rate Limiting

**IP Geolocation**: ip-api.com free tier allows 45 requests per minute. If rate-limited:
- Returns `None` and logs warning
- Middleware continues normally
- Session is still tracked, just without geographic data

**Supabase**: Depends on project plan. If write fails:
- Error is logged
- Request continues normally
- User is not aware of analytics failure

## Testing

```bash
# Test analytics middleware
curl -v "http://localhost:8000/api/health?utm_source=test"

# Verify session was created in Supabase
# Check: supabase > SQL Editor > SELECT * FROM sessions LIMIT 1

# Test topic classifier
python -c "
from app.services.topic_classifier import classify_query_topic
topics = classify_query_topic('I have type 2 diabetes')
print(topics)  # Should include 'endocrinology'
"
```

## Future Enhancements

1. **Session persistence**: Store session ID in cookies for multi-request tracking
2. **User linking**: Merge anonymous session data with user_id after signup
3. **Real-time dashboards**: WebSocket updates for live metrics
4. **Advanced topic classification**: Use LLM (OpenAI API) for semantic classification
5. **Cohort analysis**: Track user journeys and conversion paths
6. **A/B testing**: Segment traffic by variant ID
7. **Performance profiling**: Track API latency per source, per persona
8. **Anomaly detection**: Alert on unusual traffic patterns

## Maintenance

- **Cache cleanup**: LRU cache in geolocation.py auto-evicts after 1000 entries
- **Database indexes**: Ensure these exist on `sessions.tenant_id`, `search_logs.session_id`, `usage_analytics.action`
- **Log rotation**: Review logs monthly (analytics errors should be rare)
- **API rate limits**: Monitor ip-api.com usage; consider caching strategy if hitting 45 req/min limit

## Known Limitations

1. **Session ID not persisted in cookies**: Each request gets a new session ID (will fix in Phase 4 with auth)
2. **No user linking yet**: Analytics doesn't connect anonymous sessions to registered users (requires auth/signup flow)
3. **Tenant ID hardcoded**: Currently "default_tenant" (will be dynamic with multi-tenancy)
4. **Topic classifier is MVP**: Keyword-based, not semantic (can enhance with LLM later)
5. **Geolocation disabled for localhost**: 127.x.x.x IPs return None (by design for dev)

## Questions & Support

For questions about the analytics engine, refer to:
- Agent 2's documentation on data models
- BI Dashboard requirements (BI_DASHBOARD.md)
- Main LENA architecture docs (lena-details.md)
