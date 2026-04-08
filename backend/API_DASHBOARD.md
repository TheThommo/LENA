# LENA BI Dashboard API

Complete API documentation for the two-tier business intelligence dashboard.

## Architecture Overview

The dashboard API provides analytics read-only access with two distinct scopes:

1. **Platform Dashboard** (`/api/dashboard/platform/*`) - Requires `platform_admin` role
   - View metrics across ALL tenants
   - See platform-wide trends, revenue, and tenant comparisons
   - Access to data like total MRR, all user registrations, etc.

2. **Tenant Dashboard** (`/api/dashboard/tenant/*`) - Requires `tenant_admin` or `platform_admin` role
   - Tenant admins see ONLY their tenant's data
   - Platform admins can view any tenant (default their own, override with `X-Tenant-ID` header)
   - Scoped to individual tenant's searches, users, and metrics

3. **Export** (`/api/dashboard/export`) - Requires authentication (any role)
   - Export any dashboard metric in JSON or CSV format
   - Respects the same scoping rules as dashboards

## Authentication

All dashboard endpoints require JWT Bearer token in `Authorization` header:

```
Authorization: Bearer <jwt_token>
```

The JWT payload must contain:
- `user_id`: UUID of the user
- `tenant_id`: UUID of the user's tenant
- `role`: One of `platform_admin`, `tenant_admin`, `practitioner`, `researcher`, `public_user`

## Response Format

All endpoints return JSON with consistent structure:

```json
{
  "metric_name": value,
  "period_start": "2024-04-01",
  "period_end": "2024-05-01",
  "...": "..."
}
```

Time series data uses arrays of objects:
```json
{
  "activity_data": [
    {"date": "2024-04-01", "total_searches": 42, "avg_per_user": 1.5},
    {"date": "2024-04-02", "total_searches": 38, "avg_per_user": 1.3}
  ]
}
```

## Date Range Filtering

Most endpoints support optional date range filtering:

```
GET /api/dashboard/platform/overview?start_date=2024-03-01&end_date=2024-04-01
```

- Query params: `start_date` and `end_date` (YYYY-MM-DD format)
- If omitted, defaults to last 30 days
- End date defaults to today if not specified

## Platform Dashboard Endpoints

All require `Authorization` header with `platform_admin` role.

### GET /api/dashboard/platform/overview
Top-level summary statistics across all tenants.

**Response:**
```json
{
  "total_users": 1250,
  "total_searches": 8430,
  "active_sessions": 156,
  "avg_response_time_ms": 245.5,
  "new_users_this_period": 89,
  "mrr": 12450.50,
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/traffic
Traffic source breakdown by UTM parameters and referrer categories.

**Response:**
```json
{
  "total_sessions": 4500,
  "sources": [
    {"source": "google", "count": 1200, "percentage": 26.67},
    {"source": "direct", "count": 980, "percentage": 21.78},
    {"source": "referral", "count": 750, "percentage": 16.67}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/geo
Geographic distribution of visitors.

**Response:**
```json
{
  "total_locations": 87,
  "locations": [
    {"country": "United States", "city": "New York", "count": 450},
    {"country": "United States", "city": "San Francisco", "count": 380},
    {"country": "United Kingdom", "city": "London", "count": 290}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/topics
Top 20 trending search topics.

**Response:**
```json
{
  "total_unique_topics": 234,
  "topics": [
    {"topic": "diabetes management", "count": 234},
    {"topic": "hypertension treatment", "count": 198},
    {"topic": "cardiovascular disease", "count": 156}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/funnel
Conversion funnel metrics with stage-by-stage conversion rates.

**Stages:**
1. landed
2. name_captured
3. disclaimer_accepted
4. first_search
5. email_captured
6. second_search
7. signup_cta_shown
8. registered

**Response:**
```json
{
  "stages": [
    {"stage_name": "landed", "session_count": 5000, "conversion_rate": null},
    {"stage_name": "name_captured", "session_count": 3200, "conversion_rate": 64.0},
    {"stage_name": "disclaimer_accepted", "session_count": 2800, "conversion_rate": 87.5},
    {"stage_name": "first_search", "session_count": 2400, "conversion_rate": 85.7},
    {"stage_name": "email_captured", "session_count": 1800, "conversion_rate": 75.0},
    {"stage_name": "second_search", "session_count": 1200, "conversion_rate": 66.7},
    {"stage_name": "signup_cta_shown", "session_count": 1100, "conversion_rate": 91.7},
    {"stage_name": "registered", "session_count": 450, "conversion_rate": 40.9}
  ],
  "overall_conversion_rate": 9.0,
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/users
User registration growth over time.

**Response:**
```json
{
  "total_users": 1250,
  "growth_data": [
    {"date": "2024-03-01", "new_users": 15, "cumulative_users": 1135},
    {"date": "2024-03-02", "new_users": 12, "cumulative_users": 1147},
    {"date": "2024-03-03", "new_users": 18, "cumulative_users": 1165}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/searches
Search activity trends over time.

**Response:**
```json
{
  "total_searches": 8430,
  "avg_searches_per_user": 6.74,
  "activity_data": [
    {"date": "2024-03-01", "total_searches": 180, "avg_per_user": 6.2},
    {"date": "2024-03-02", "total_searches": 210, "avg_per_user": 7.1},
    {"date": "2024-03-03", "total_searches": 195, "avg_per_user": 6.8}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/revenue
Current revenue and subscription metrics.

**Note:** This endpoint returns current snapshot (does not support date range filtering).

**Response:**
```json
{
  "mrr": 12450.50,
  "active_subscriptions": 156,
  "cancelled_last_period": 12,
  "plan_distribution": [
    {"plan_name": "Professional", "count": 78, "mrr": 7800.00, "percentage": 50.0},
    {"plan_name": "Enterprise", "count": 45, "mrr": 4500.00, "percentage": 28.8},
    {"plan_name": "Starter", "count": 33, "mrr": 150.50, "percentage": 21.2}
  ],
  "period_start": "2024-04-08",
  "period_end": "2024-04-08"
}
```

### GET /api/dashboard/platform/tenants
Per-tenant comparison view (platform admins only).

**Response:**
```json
{
  "total_tenants": 3,
  "tenants": [
    {
      "tenant_name": "NYU Medical",
      "tenant_slug": "nyu",
      "user_count": 450,
      "search_count": 3200,
      "mrr": 8500.00,
      "active_subscriptions": 85,
      "avg_response_time_ms": 234.5
    },
    {
      "tenant_name": "Johns Hopkins",
      "tenant_slug": "jhu",
      "user_count": 380,
      "search_count": 2890,
      "mrr": 5200.00,
      "active_subscriptions": 48,
      "avg_response_time_ms": 256.3
    }
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/queries
Most popular search queries across the platform.

**Query params:**
- `limit`: Number of top queries to return (default 20, max 100)

**Response:**
```json
{
  "total_searches": 8430,
  "queries": [
    {"query": "diabetes management", "count": 234, "avg_response_time_ms": 240.5},
    {"query": "hypertension treatment", "count": 198, "avg_response_time_ms": 235.2},
    {"query": "cardiovascular disease", "count": 156, "avg_response_time_ms": 248.9}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/personas
User breakdown by persona type.

**Persona types:** medical_student, clinician, pharmacist, researcher, lecturer, physiotherapist, patient, general

**Response:**
```json
{
  "total_users": 1250,
  "personas": [
    {"persona": "clinician", "count": 450, "percentage": 36.0},
    {"persona": "researcher", "count": 380, "percentage": 30.4},
    {"persona": "medical_student", "count": 250, "percentage": 20.0},
    {"persona": "patient", "count": 170, "percentage": 13.6}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

### GET /api/dashboard/platform/pulse-accuracy
PULSE validation accuracy metrics.

**PULSE statuses:** validated, edge_case, insufficient_validation, pending

**Response:**
```json
{
  "total_results_validated": 42500,
  "accuracy_metrics": [
    {"status": "validated", "count": 38250, "percentage": 90.0},
    {"status": "edge_case", "count": 2975, "percentage": 7.0},
    {"status": "insufficient_validation", "count": 1275, "percentage": 3.0}
  ],
  "period_start": "2024-03-01",
  "period_end": "2024-04-01"
}
```

## Tenant Dashboard Endpoints

All require `Authorization` header with `tenant_admin` or `platform_admin` role.

**Endpoints:**
- GET /api/dashboard/tenant/overview
- GET /api/dashboard/tenant/traffic
- GET /api/dashboard/tenant/geo
- GET /api/dashboard/tenant/topics
- GET /api/dashboard/tenant/funnel
- GET /api/dashboard/tenant/users
- GET /api/dashboard/tenant/searches
- GET /api/dashboard/tenant/queries
- GET /api/dashboard/tenant/personas
- GET /api/dashboard/tenant/pulse-accuracy

**Behavior:**
- Tenant admins automatically see their own tenant's data
- Platform admins see their tenant by default, or override with `X-Tenant-ID` header
- Response format identical to platform endpoints, scoped to single tenant

### Tenant Scoping Example

```bash
# Tenant admin sees their own data
curl -H "Authorization: Bearer <token>" \
  https://api.lena-research.com/api/dashboard/tenant/overview

# Platform admin sees their own tenant (same as tenant admin)
curl -H "Authorization: Bearer <token>" \
  https://api.lena-research.com/api/dashboard/tenant/overview

# Platform admin views another tenant (NYU)
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: nyu" \
  https://api.lena-research.com/api/dashboard/tenant/overview

# Error: Tenant admin cannot override their scope
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: other-tenant" \
  https://api.lena-research.com/api/dashboard/tenant/overview
# Returns 403 Forbidden
```

## Export Endpoints

All require authentication (any authenticated role).

### GET /api/dashboard/export

Export dashboard data in JSON or CSV format.

**Query params:**
- `report_type` (required): Type of report
  - `overview` - Overview statistics
  - `traffic` - Traffic sources
  - `geo` - Geographic distribution
  - `topics` - Topic trends
  - `funnel` - Conversion funnel
  - `users` - User growth
  - `searches` - Search activity
- `format` (optional): Export format
  - `json` (default) - JSON object
  - `csv` - CSV file
- `start_date` (optional): Start date (YYYY-MM-DD)
- `end_date` (optional): End date (YYYY-MM-DD)
- `X-Tenant-ID` (optional header): (platform admins only) Specify tenant

**Examples:**

```bash
# Export overview as JSON (default)
curl -H "Authorization: Bearer <token>" \
  "https://api.lena-research.com/api/dashboard/export?report_type=overview"

# Export traffic as CSV
curl -H "Authorization: Bearer <token>" \
  "https://api.lena-research.com/api/dashboard/export?report_type=traffic&format=csv" \
  > traffic_report.csv

# Export with date range
curl -H "Authorization: Bearer <token>" \
  "https://api.lena-research.com/api/dashboard/export?report_type=users&start_date=2024-03-01&end_date=2024-04-01&format=csv" \
  > user_growth.csv

# Platform admin exports another tenant's data
curl -H "Authorization: Bearer <token>" \
  -H "X-Tenant-ID: nyu" \
  "https://api.lena-research.com/api/dashboard/export?report_type=overview&format=json"
```

**CSV Format Example (Overview):**
```csv
Metric,Value
Total Users,1250
Total Searches,8430
Active Sessions,156
Avg Response Time (ms),245.5
New Users This Period,89
MRR,12450.50
Period Start,2024-03-01
Period End,2024-04-01
```

## Error Handling

All endpoints return standard HTTP status codes:

- **200 OK** - Request successful
- **401 Unauthorized** - Missing or invalid JWT token
- **403 Forbidden** - Insufficient permissions (not platform_admin for platform endpoints, or tenant_admin trying to access another tenant)
- **400 Bad Request** - Invalid query parameters or request format

**Error Response Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

**Examples:**
```json
{
  "detail": "Not authenticated. Provide a valid Bearer token."
}
```

```json
{
  "detail": "Insufficient permissions. Required roles: platform_admin"
}
```

```json
{
  "detail": "Invalid report_type. Must be one of: overview, traffic, geo, topics, funnel, users, searches"
}
```

## Query Performance Notes

- All queries use the admin Supabase client (bypasses RLS) for performance
- Date range filtering defaults to last 30 days if not specified
- Large date ranges (>1 year) may be slow; recommend pagination or filtering
- Results are computed on-demand; consider caching for dashboard UI
- CSV exports stream data and should not timeout even for large datasets

## Implementation Details

### Query Service (dashboard_queries.py)

- All functions are async and safe for FastAPI
- Return dicts/lists suitable for Pydantic model serialization
- Date parsing handles both string and datetime objects
- Errors are logged and return empty datasets (never raise exceptions)

### Response Models (models/dashboard.py)

- All models inherit from Pydantic BaseModel
- Use `Field()` for validation and constraints (ge=0, le=100, etc.)
- Date fields use Python `date` type (YYYY-MM-DD format)
- Percentage fields always 0-100

### Route Handlers (dashboard_platform.py, dashboard_tenant.py)

- All routes use async/await pattern
- Dependencies enforce authentication and role-based access control
- Return Pydantic models (FastAPI auto-serializes to JSON)
- Query params are Optional[date] with sensible defaults

### Export Handler (dashboard_export.py)

- JSON export uses `json_serializer` helper for date/time serialization
- CSV export uses Python stdlib csv module (no new dependencies)
- Streaming responses for large datasets
- Content-disposition headers for file downloads

## Development Notes

- No new dependencies required (uses stdlib csv module)
- Tested with Supabase SDK v2.x
- Compatible with FastAPI 0.100+
- All endpoints are read-only (no write operations)
- RLS is bypassed for dashboard reads (using admin client)

## Security Considerations

1. **Role-Based Access Control**
   - Platform endpoints strictly require `platform_admin` role
   - Tenant endpoints allow both `tenant_admin` and `platform_admin`
   - Tenant admins cannot override their scope

2. **Audit Trail**
   - Dashboard reads are not logged to audit_trail (read-only, no mutations)
   - Consider adding access logging at middleware level if needed

3. **Rate Limiting**
   - No rate limiting implemented in dashboard endpoints
   - Recommend adding rate limits at API gateway for export endpoints
   - Dashboard UI should implement sensible refresh intervals (not sub-second)

4. **Data Scoping**
   - Tenant data is strictly scoped by tenant_id in queries
   - Platform admin cannot accidentally access cross-tenant PII
   - All dates filtered server-side before returning to client
