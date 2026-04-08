# LENA Data Layer Documentation

## Overview

The LENA data layer provides a complete Pydantic model and Supabase CRUD repository system for the clinical research platform. All database operations go through this layer, which ensures type safety, consistent error handling, and clean separation of concerns.

## Architecture

```
app/
├── models/           # Pydantic models (input/output validation)
│   ├── enums.py     # All enum types (matching Supabase enums)
│   ├── tenant.py    # Tenant models
│   ├── user.py      # User & UserTenant models
│   ├── session.py   # Session models
│   ├── search.py    # Search & SearchResult models
│   ├── analytics.py # UsageAnalytics, SearchLog, AuditEntry models
│   ├── subscription.py  # Plan & Subscription models
│   └── __init__.py  # Re-exports all models
│
└── db/
    ├── supabase.py  # Client initialization & connection
    └── repositories/
        ├── tenant_repo.py      # Tenant CRUD
        ├── user_repo.py        # User & UserTenant CRUD
        ├── session_repo.py     # Session CRUD
        ├── search_repo.py      # Search & SearchResult CRUD
        ├── analytics_repo.py   # Analytics CRUD
        ├── subscription_repo.py # Plan & Subscription CRUD
        └── __init__.py         # Re-exports all repositories
```

## Pydantic Models

All models follow Pydantic v2 conventions with:
- `BaseModel` for all data classes
- `Optional[T]` for nullable fields
- `Field(...)` for validation and documentation
- `from_attributes = True` for database row conversion

### Model Patterns

**Create Models** (input):
```python
class TenantCreate(TenantBase):
    """Fields required to create a tenant."""
    pass
```

**Update Models** (input, all fields optional):
```python
class TenantUpdate(BaseModel):
    """Partial update (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    # ... other fields
```

**Response Models** (output):
```python
class Tenant(TenantBase):
    """Full record from database."""
    id: UUID
    created_at: datetime
    updated_at: datetime
```

**Public Models** (safe for external APIs):
```python
class UserPublic(BaseModel):
    """Safe info (no sensitive fields)."""
    id: UUID
    email: str
    name: str
    # ... no password, no auth tokens
```

## Enums

All enums match Supabase database constraints exactly. Enum values are lowercase strings:

- **UserRole**: `platform_admin`, `tenant_admin`, `practitioner`, `researcher`, `public_user`
- **PersonaType**: `medical_student`, `clinician`, `pharmacist`, `researcher`, `lecturer`, `physiotherapist`, `patient`, `general`
- **PlanType**: `free`, `starter`, `professional`, `enterprise`
- **SearchSource**: `pubmed`, `clinical_trials`, `cochrane`, `who_iris`, `cdc`
- **PulseStatus**: `validated`, `edge_case`, `insufficient_validation`, `pending`
- **SubscriptionStatus**: `active`, `past_due`, `cancelled`, `trialing`
- **AuditAction**: `login`, `logout`, `search`, `view_result`, `export`, `admin_action`, `settings_change`
- **TriggerType**: `row_insert`, `row_update`, `scheduled`, `manual`

## Repository Layer

Each repository handles CRUD operations for a specific table or related set of tables. All methods are async and return Pydantic model instances or lists.

### Error Handling

Repositories follow a consistent error handling pattern:
- Try/except blocks catch all exceptions
- Errors are logged to stdout
- Methods return `None` (for single items) or empty `[]` (for lists) on error
- No exceptions are raised - use return value checks instead

### Client Selection

- **Anon Client** (`get_supabase_client()`): Respects RLS policies. Use for user-facing operations.
- **Admin Client** (`get_supabase_admin_client()`): Bypasses RLS. Use for analytics writes, cross-tenant queries.

## Repository Methods

### Tenant Repository

```python
TenantRepository.create(tenant_create: TenantCreate) -> Optional[Tenant]
TenantRepository.get_by_id(tenant_id: UUID) -> Optional[Tenant]
TenantRepository.get_by_slug(slug: str) -> Optional[Tenant]
TenantRepository.get_by_domain(domain: str) -> Optional[Tenant]
TenantRepository.list_all() -> List[Tenant]
TenantRepository.update(tenant_id: UUID, tenant_update: TenantUpdate) -> Optional[Tenant]
TenantRepository.delete(tenant_id: UUID) -> bool
```

### User Repository

```python
UserRepository.create(user_create: UserCreate) -> Optional[User]
UserRepository.get_by_id(user_id: UUID) -> Optional[User]
UserRepository.get_by_email(email: str) -> Optional[User]
UserRepository.get_by_tenant_id(tenant_id: UUID) -> List[User]
UserRepository.update(user_id: UUID, user_update: UserUpdate) -> Optional[User]
UserRepository.update_last_login(user_id: UUID) -> Optional[User]
UserRepository.delete(user_id: UUID) -> bool
```

### UserTenant Repository

```python
UserTenantRepository.create(user_tenant_create: UserTenantCreate) -> Optional[UserTenant]
UserTenantRepository.get_by_user_and_tenant(user_id: UUID, tenant_id: UUID) -> Optional[UserTenant]
UserTenantRepository.get_by_user_id(user_id: UUID) -> List[UserTenant]
UserTenantRepository.get_by_tenant_id(tenant_id: UUID) -> List[UserTenant]
UserTenantRepository.delete(user_id: UUID, tenant_id: UUID) -> bool
```

### Session Repository

```python
SessionRepository.create(session_create: SessionCreate) -> Optional[Session]
SessionRepository.get_by_id(session_id: UUID) -> Optional[Session]
SessionRepository.get_by_user_id(user_id: UUID) -> List[Session]
SessionRepository.get_by_tenant_id(tenant_id: UUID, limit: int = 100) -> List[Session]
SessionRepository.update(session_id: UUID, session_update: SessionUpdate) -> Optional[Session]
SessionRepository.end_session(session_id: UUID) -> Optional[Session]
```

### Search Repository

```python
SearchRepository.create(search_create: SearchCreate) -> Optional[Search]
SearchRepository.get_by_id(search_id: UUID) -> Optional[Search]
SearchRepository.get_by_session_id(session_id: UUID) -> List[Search]
SearchRepository.get_by_user_id(user_id: UUID, limit: int = 50) -> List[Search]
SearchRepository.get_by_tenant_id(tenant_id: UUID, limit: int = 100) -> List[Search]
SearchRepository.get_with_results(search_id: UUID) -> Optional[SearchWithResults]
```

### SearchResult Repository

```python
SearchResultRepository.create(search_result_create: SearchResultCreate) -> Optional[SearchResult]
SearchResultRepository.create_batch(search_results: List[SearchResultCreate]) -> List[SearchResult]
SearchResultRepository.get_by_id(result_id: UUID) -> Optional[SearchResult]
SearchResultRepository.get_by_search_id(search_id: UUID) -> List[SearchResult]
SearchResultRepository.get_by_source(search_id: UUID, source_name: str) -> List[SearchResult]
SearchResultRepository.get_by_pmid(pmid: str) -> List[SearchResult]
SearchResultRepository.update_pulse_status(result_id: UUID, pulse_status: str) -> Optional[SearchResult]
```

### Analytics Repositories

#### UsageAnalyticsRepository
```python
UsageAnalyticsRepository.create(analytics_create: UsageAnalyticsCreate) -> Optional[UsageAnalytics]
UsageAnalyticsRepository.get_by_tenant_id(tenant_id: UUID, limit: int = 100) -> List[UsageAnalytics]
UsageAnalyticsRepository.get_by_user_id(user_id: UUID, limit: int = 50) -> List[UsageAnalytics]
```

#### SearchLogRepository
```python
SearchLogRepository.create(search_log_create: SearchLogCreate) -> Optional[SearchLog]
SearchLogRepository.get_by_search_id(search_id: UUID) -> Optional[SearchLog]
SearchLogRepository.get_recent(limit: int = 100) -> List[SearchLog]
```

#### AuditTrailRepository
```python
AuditTrailRepository.create(audit_create: AuditEntryCreate) -> Optional[AuditEntry]
AuditTrailRepository.get_by_user_id(user_id: UUID, limit: int = 50) -> List[AuditEntry]
AuditTrailRepository.get_by_tenant_id(tenant_id: UUID, limit: int = 100) -> List[AuditEntry]
AuditTrailRepository.get_by_action(action: str, limit: int = 50) -> List[AuditEntry]
```

### Subscription Repositories

#### PlanRepository
```python
PlanRepository.create(plan_create: PlanCreate) -> Optional[Plan]
PlanRepository.get_by_id(plan_id: UUID) -> Optional[Plan]
PlanRepository.get_by_slug(slug: str) -> Optional[Plan]
PlanRepository.list_active() -> List[Plan]
PlanRepository.list_all() -> List[Plan]
PlanRepository.update(plan_id: UUID, plan_update: PlanUpdate) -> Optional[Plan]
```

#### SubscriptionRepository
```python
SubscriptionRepository.create(subscription_create: SubscriptionCreate) -> Optional[Subscription]
SubscriptionRepository.get_by_id(subscription_id: UUID) -> Optional[Subscription]
SubscriptionRepository.get_by_tenant_id(tenant_id: UUID) -> Optional[Subscription]
SubscriptionRepository.get_with_plan(subscription_id: UUID) -> Optional[SubscriptionWithPlan]
SubscriptionRepository.update(subscription_id: UUID, subscription_update: SubscriptionUpdate) -> Optional[Subscription]
SubscriptionRepository.list_by_status(status: str, limit: int = 100) -> List[Subscription]
```

## Usage Examples

### Creating a Tenant

```python
from app.models import TenantCreate
from app.db.repositories import TenantRepository

# Create the tenant
tenant_create = TenantCreate(
    name="NYU Healthcare",
    slug="nyu-healthcare",
    domain="nyu.example.com",
    primary_color="#0066cc"
)
tenant = await TenantRepository.create(tenant_create)
if tenant:
    print(f"Created tenant: {tenant.id}")
else:
    print("Failed to create tenant")
```

### Searching for a User

```python
from app.db.repositories import UserRepository

# Get user by email
user = await UserRepository.get_by_email("researcher@nyu.edu")
if user:
    print(f"Found user: {user.name} ({user.role})")
else:
    print("User not found")
```

### Logging a Search

```python
from app.models import SearchCreate, SearchResultCreate, SearchLogCreate
from app.db.repositories import SearchRepository, SearchResultRepository, SearchLogRepository
from app.models import SearchSource, PulseStatus
import time

# Create the search
start_time = time.time()
search_create = SearchCreate(
    query="COVID-19 treatment guidelines",
    session_id=session_id,
    user_id=user_id,
    tenant_id=tenant_id,
    persona_type=PersonaType.CLINICIAN
)
search = await SearchRepository.create(search_create)

# Add results
results = []
for article in pubmed_results:
    result_create = SearchResultCreate(
        search_id=search.id,
        source_name=SearchSource.PUBMED,
        title=article['title'],
        authors=article.get('authors'),
        year=article.get('year'),
        pmid=article.get('pmid'),
        url=article.get('url'),
        abstract=article.get('abstract'),
        relevance_score=article.get('score'),
        pulse_status=PulseStatus.PENDING
    )
    results.append(result_create)

created_results = await SearchResultRepository.create_batch(results)

# Log the search
response_time_ms = int((time.time() - start_time) * 1000)
search_log = SearchLogCreate(
    search_id=search.id,
    response_time_ms=response_time_ms,
    sources_queried=1,
    sources_succeeded=1,
    total_results=len(created_results),
    pulse_status=PulseStatus.PENDING
)
await SearchLogRepository.create(search_log)
```

### Recording an Audit Event

```python
from app.models import AuditEntryCreate
from app.db.repositories import AuditTrailRepository
from app.models import AuditAction

# Log a login
audit = AuditEntryCreate(
    user_id=user_id,
    tenant_id=tenant_id,
    action=AuditAction.LOGIN,
    ip_address="192.168.1.1",
    details={"browser": "Chrome", "os": "macOS"}
)
await AuditTrailRepository.create(audit)
```

## Important Notes

1. **All methods are async**: Use `await` when calling repository methods.

2. **Enum values are lowercase**: When passing enums to Supabase, their `.value` property is used automatically in repositories.

3. **UUIDs are converted to strings**: Repositories handle UUID→string conversion for Supabase API calls.

4. **Timestamps are automatic**: `created_at`, `updated_at`, `started_at` are handled by Supabase triggers. Don't pass them.

5. **Batch operations**: Use `SearchResultRepository.create_batch()` for better performance when inserting multiple results.

6. **Error handling is graceful**: Repositories never raise exceptions. Always check return values.

7. **RLS is respected**: The anon client respects Row-Level Security policies. Use the admin client only for internal analytics.

## Future Enhancements

- [ ] pgvector integration for semantic search (`query_vector`, `full_text_vector`)
- [ ] Connection pooling for high-concurrency workloads
- [ ] Query caching layer
- [ ] Soft deletes support
- [ ] Audit triggers for automatic change tracking
- [ ] Full-text search integration

## Migration Notes

The database schema (31 tables) has already been deployed to Supabase. The data layer provides type-safe access to these tables through Pydantic models and repositories.

**pgvector not yet enabled**: To enable vector search:
1. Login to Supabase dashboard
2. Navigate to Database > Extensions
3. Enable the `vector` extension
4. Add vector columns to searches, search_results, and tenant_documents tables
5. Uncomment vector field handling in model classes
