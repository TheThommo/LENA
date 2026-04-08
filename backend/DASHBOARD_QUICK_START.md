# BI Dashboard API - Quick Start Guide

## For Developers

### What Was Built
A complete two-tier analytics dashboard API with 23 endpoints for LENA platform:
- **11 platform endpoints** (platform_admin only) - see all tenant data
- **10 tenant endpoints** (tenant_admin + platform_admin) - see scoped tenant data
- **1 export endpoint** - JSON/CSV export for any metric

### Files You Need to Know About

1. **app/models/dashboard.py** (280 lines)
   - 47 Pydantic response models
   - All request/response types
   - Run: `from app.models.dashboard import DashboardOverview`

2. **app/services/dashboard_queries.py** (850 lines)
   - 12 async query functions
   - All the analytics logic
   - Usage: `await get_overview_stats(tenant_id=None, start_date=date, end_date=date)`

3. **app/api/routes/dashboard_platform.py** (200 lines)
   - 11 platform-only endpoints
   - Registered at `/api/dashboard/platform/*`

4. **app/api/routes/dashboard_tenant.py** (230 lines)
   - 10 tenant-scoped endpoints
   - Registered at `/api/dashboard/tenant/*`
   - Supports X-Tenant-ID header for platform admins

5. **app/api/routes/dashboard_export.py** (290 lines)
   - 1 flexible export endpoint
   - Registered at `/api/dashboard/export`
   - Supports JSON and CSV formats

6. **API_DASHBOARD.md** (500+ lines)
   - Complete API reference
   - Response examples for every endpoint
   - Security notes

### Common Tasks

#### Add a New Dashboard Metric
1. Create response model in `app/models/dashboard.py`
2. Implement query function in `app/services/dashboard_queries.py`
3. Add route in `app/api/routes/dashboard_platform.py` (and `dashboard_tenant.py` if tenant-scoped)
4. Update `API_DASHBOARD.md`

Example:
```python
# In dashboard_queries.py
async def get_new_metric(tenant_id=None, start_date=None, end_date=None):
    start_date, end_date = _get_date_range(start_date, end_date)
    try:
        client = get_supabase_admin_client()
        # Your query logic here
        return {"metric_data": [...], "period_start": start_date, "period_end": end_date}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"metric_data": [], ...}

# In dashboard_platform.py
@router.get("/new-metric", response_model=NewMetricResponse)
async def get_platform_new_metric(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    user=Depends(require_auth),
):
    data = await get_new_metric(tenant_id=None, start_date=start_date, end_date=end_date)
    return NewMetricResponse(**data)
```

#### Test an Endpoint Locally
```bash
# 1. Generate a test JWT token
# (See app/core/auth.py create_access_token())

# 2. Call the endpoint
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/dashboard/platform/overview?start_date=2024-03-01&end_date=2024-04-01"

# 3. For CSV export
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8000/api/dashboard/export?report_type=overview&format=csv" \
  > export.csv
```

#### Debug Query Issues
All query functions log errors:
```python
# In dashboard_queries.py - errors are logged but never raised
logger.error(f"Error getting overview stats: {e}")
# Returns empty dataset instead
```

Check logs with:
```bash
# In your deployment environment
journalctl -u lena-api -f
# or tail logs from Railway dashboard
```

### Key Concepts

#### Tenant Scoping
```python
# Platform admin sees all data (tenant_id=None)
await get_overview_stats(tenant_id=None)

# Tenant admin sees only their tenant
await get_overview_stats(tenant_id="nyu-uuid")

# API route enforces this
def get_scoped_tenant_id(request, user):
    # Tenant admins: always their own tenant
    # Platform admins: default their own, can override with X-Tenant-ID header
```

#### Date Range Filtering
```python
# All endpoints support optional date ranges
async def get_overview_stats(start_date=None, end_date=None):
    start_date, end_date = _get_date_range(start_date, end_date)
    # If both None, defaults to last 30 days
```

#### Error Handling Philosophy
- Query functions NEVER raise exceptions
- Errors are logged
- Empty datasets returned instead
- HTTP exceptions only raised at route level (auth/authorization)
- This means dashboards degrade gracefully under load

### Performance Tips

1. **Use date ranges** - Don't query all of time, that's slow
   ```bash
   # Good
   GET /api/dashboard/platform/overview?start_date=2024-03-01&end_date=2024-04-01
   
   # Bad - queries last 30 days by default, might be slow
   GET /api/dashboard/platform/overview
   ```

2. **Limit unbounded results**
   ```bash
   # Queries endpoint has limit parameter (default 20, max 100)
   GET /api/dashboard/platform/queries?limit=50
   ```

3. **Use CSV for large exports**
   - Streaming response, doesn't load entire result in memory
   ```bash
   GET /api/dashboard/export?report_type=searches&format=csv
   ```

4. **Cache dashboard UI renders**
   - Frontend should cache responses for 5-15 minutes
   - Don't refresh every second

### Common Issues & Solutions

#### Issue: "Insufficient permissions"
- **Check**: User role in JWT token
- **Solution**: Platform endpoints need `platform_admin`, tenant endpoints need `tenant_admin` or `platform_admin`

#### Issue: Tenant admin sees wrong data
- **Check**: Tenant ID enforcement in `get_scoped_tenant_id()`
- **Solution**: Code prevents override, tenant admins always see own tenant

#### Issue: Query returns empty dataset
- **Check**: Log file for query errors
- **Solution**: Empty datasets are by design (graceful degradation). Check:
  - Date range is correct
  - Tenant ID is valid
  - Tables have data in that date range

#### Issue: CSV export is slow
- **Check**: Date range size
- **Solution**: Narrow the date range or split into multiple requests

### Testing Checklist

Before deploying:
- [ ] All 6 Python files compile (no syntax errors)
- [ ] main.py imports new routers correctly
- [ ] At least one platform endpoint returns 401 without auth
- [ ] Platform endpoint returns 403 without platform_admin role
- [ ] Tenant endpoint respects X-Tenant-ID header scoping
- [ ] Date range filtering works (start_date/end_date params)
- [ ] CSV export downloads as .csv file
- [ ] JSON export returns valid JSON
- [ ] Empty tenant returns empty arrays (not errors)

### Helpful Commands

```bash
# Compile check all files
python3 -m py_compile app/models/dashboard.py
python3 -m py_compile app/services/dashboard_queries.py
python3 -m py_compile app/api/routes/dashboard_*.py

# Start the API locally
uvicorn app.main:app --reload

# View API docs
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)

# Check imports work
python3 -c "from app.models.dashboard import DashboardOverview; print('OK')"
python3 -c "from app.services.dashboard_queries import get_overview_stats; print('OK')"
```

### File Locations (Absolute Paths)

```
/sessions/inspiring-sharp-pascal/mnt/HeathNet Rebuild/lena/backend/
├── app/models/dashboard.py
├── app/services/dashboard_queries.py
├── app/api/routes/dashboard_platform.py
├── app/api/routes/dashboard_tenant.py
├── app/api/routes/dashboard_export.py
├── app/main.py (modified)
├── API_DASHBOARD.md
├── DASHBOARD_QUICK_START.md (this file)
└── DASHBOARD_IMPLEMENTATION_SUMMARY.md
```

### Next Steps

1. **Test locally**
   - Start the API: `uvicorn app.main:app --reload`
   - Create a test JWT token
   - Call `/api/dashboard/platform/overview`
   - Check Swagger UI at http://localhost:8000/docs

2. **Deploy to Railway**
   - Push code to GitHub
   - Railway auto-deploys from main branch
   - Check railway logs for any import errors

3. **Build frontend dashboard**
   - Frontend can now consume these 23 endpoints
   - Use Swagger UI for endpoint reference
   - Implement date range filters on UI
   - Add caching layer (don't refresh every second)

4. **Monitor in production**
   - Dashboard endpoints are read-only (safe to call frequently)
   - Check logs for slow queries
   - Track 401/403 errors (auth issues)
   - Monitor CSV export streaming performance

### Questions?
- See API_DASHBOARD.md for detailed endpoint reference
- See DASHBOARD_IMPLEMENTATION_SUMMARY.md for architecture overview
- Check app/core/auth.py for JWT structure
- Check app/core/tenant.py for tenant detection logic
