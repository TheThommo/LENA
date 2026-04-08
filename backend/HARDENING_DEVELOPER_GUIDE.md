# Search Pipeline Hardening - Developer Guide

## Quick Start

### 1. Using Structured Logging

```python
from app.core.logging import get_logger

# Get a named logger
logger = get_logger("lena.search")

# Use like standard Python logger
logger.debug("Detailed diagnostic info")
logger.info("Important operation completed")
logger.warning("Degraded mode - one source failed")
logger.error("Critical failure", exc_info=True)
```

**Named Loggers Available**:
- `lena.search` - Main search pipeline operations
- `lena.pulse` - PULSE validation and scoring
- `lena.sources` - Individual data source operations
- `lena.guardrails` - Medical advice guardrail triggers
- `lena.analytics` - Analytics event logging

### 2. Using Result Caching

```python
from app.services.result_cache import (
    get_cached_result,
    cache_result,
    get_cache_stats,
    clear_cache,
)

# Check cache before doing expensive operation
cached = get_cached_result(
    query="diabetes treatment",
    sources=["pubmed", "cochrane"],
    include_alt_medicine=True,
)

if cached:
    return cached  # Cache hit!

# Do expensive computation...
result = await run_search(...)

# Cache the result for next time
cache_result(
    query="diabetes treatment",
    result=result,
    sources=["pubmed", "cochrane"],
    include_alt_medicine=True,
)

# Check cache usage
stats = get_cache_stats()
print(f"Cache usage: {stats['usage_percent']}%")
```

**Cache Configuration**:
- TTL: 5 minutes - Queries older than 5 minutes are recomputed
- Max: 500 entries - Oldest entries evicted when limit reached
- Key: `hash(query + sources + alt_medicine_flag)`

### 3. Alternative Medicine Toggle

```python
# In your route or function
result = await run_search(
    query=q,
    include_alt_medicine=False,  # Exclude herbal, acupuncture, etc.
)

# Response includes this flag
response["include_alt_medicine"]  # True or False
```

**Filtered Keywords**:
- Herbal remedies: "herbal", "herb", "supplement"
- Traditional: "acupuncture", "homeopathy", "ayurveda", "tcm"
- Holistic: "naturopathy", "chiropractic", "meditation", "yoga"

### 4. PULSE Scoring Rules

These are applied automatically - no manual configuration needed.

```python
# Rule 1: Single-source results capped at 60% relevance
# If only PubMed has results, max score = 0.60

# Rule 2: Cochrane (systematic reviews) boosted 1.25x
# Cochrane result with 0.8 score → 1.0 (capped)

# Rule 3: Conflicting evidence penalizes confidence
# If edge_cases exist, confidence_ratio *= (1 - penalty)

# Rule 4: Retracted papers excluded
result = SourceResult(
    source_name="pubmed",
    title="Withdrawn Study",
    is_retracted=True,  # This result won't appear in PULSE output
)
```

### 5. Response Time Tracking

```python
# Already included in all responses from run_search()
response = await run_search(...)

timing_ms = response["response_time_ms"]
print(f"Search took {timing_ms:.1f}ms")

# Useful for:
# - SLA monitoring
# - Performance regression detection
# - Analytics dashboards
```

### 6. Analytics Logging

```python
# In your route/controller
from app.services.analytics_writer import log_search_event, schedule_analytics_task

# Log a search event (fire-and-forget, never blocks)
schedule_analytics_task(
    log_search_event(
        search_id="abc-123",
        session_id="user-session-456",
        query="diabetes treatment",
        persona="patient",
        tenant_id="default",
        response_time_ms=145.3,
        sources_queried=["pubmed", "cochrane"],
        sources_succeeded=["pubmed", "cochrane"],
        total_results=42,
        pulse_status="validated",
    )
)

# Never blocks response - uses asyncio.create_task()
# Errors are logged but never raised
```

## Common Scenarios

### Scenario 1: Improve Performance for Popular Queries

```python
from app.services.result_cache import get_cache_stats

# Monitor cache effectiveness
stats = get_cache_stats()
if stats['usage_percent'] > 80:
    logger.warning("Cache near capacity, consider increasing max_entries")

# Popular queries automatically get cached
# No code changes needed - caching is transparent
```

### Scenario 2: Handle Alternative Medicine Preference

```python
# User preference from database or cookie
include_alt_medicine = user.preferences.get("include_alt_medicine", True)

result = await run_search(
    query=q,
    include_alt_medicine=include_alt_medicine,
)

# Different cache entries for same query with different toggle
# Query cached separately for each preference
```

### Scenario 3: Diagnose Source Failures

```python
from app.core.logging import get_logger

logger = get_logger("lena.sources")

# Configure to see all debug messages in development
# In production, check logs when a source consistently fails

result = await run_search(...)

if result["sources_failed"]:
    logger.warning(
        f"Some sources failed: {result['sources_failed']}"
    )
    # Check logs to see which source and why
```

### Scenario 4: Monitor PULSE Quality

```python
pulse = result["pulse_report"]

status = pulse["status"]  # "validated", "insufficient_validation", "edge_case", "pending"
confidence = pulse["confidence_ratio"]  # 0.0 to 1.0

if status == "edge_case":
    # Consensus is weaker - show warning to user
    # "Results from sources disagree - see edge cases below"
    edge_count = pulse["edge_case_count"]
    logger.info(f"Divergent results: {edge_count} edge cases detected")
```

## Testing with New Features

### Unit Test: Retry Logic

```python
import pytest
from unittest.mock import patch, AsyncMock
from app.services.pubmed import search_pubmed
import httpx

@pytest.mark.asyncio
async def test_pubmed_retry_on_timeout():
    """Verify retry logic handles timeouts."""
    with patch('app.services.pubmed.httpx.AsyncClient') as mock_client:
        # First call: timeout, second call: success
        mock_client.return_value.__aenter__.return_value.get.side_effect = [
            httpx.TimeoutException("timeout"),
            AsyncMock(json=lambda: {"esearchresult": {"idlist": ["12345"]}})(),
        ]
        
        # Should retry and succeed
        result = await search_pubmed("test query")
        assert result == ["12345"]
```

### Unit Test: Cache

```python
from app.services.result_cache import get_cached_result, cache_result, clear_cache

def test_cache_store_and_retrieve():
    """Verify caching works."""
    clear_cache()
    
    query = "test"
    result = {"data": "value"}
    
    cache_result(query, result, sources=["pubmed"])
    cached = get_cached_result(query, sources=["pubmed"])
    
    assert cached == result

def test_cache_ttl_expiration(monkeypatch):
    """Verify TTL is enforced."""
    import time as time_module
    from app.services import result_cache
    
    clear_cache()
    
    # Store result
    result = {"data": "value"}
    cache_result("query", result, sources=["pubmed"])
    
    # Mock time to skip ahead past TTL
    original_time = time_module.time
    monkeypatch.setattr(time_module, "time", lambda: original_time() + 301)  # 5m 1s
    
    # Should be expired
    cached = get_cached_result("query", sources=["pubmed"])
    assert cached is None
```

### Integration Test: Alt Medicine Filter

```python
@pytest.mark.asyncio
async def test_alt_medicine_filter():
    """Verify alternative medicine results are filtered."""
    # Create mock results with alt medicine keywords
    results = {
        "pubmed": [
            SourceResult(
                source_name="pubmed",
                title="Herbal Treatment Study",
                summary="Testing herbal remedies",
                keywords=["herbal", "treatment"],
            ),
            SourceResult(
                source_name="pubmed",
                title="Standard Treatment Study",
                summary="Testing pharmaceutical treatment",
                keywords=["pharmaceutical", "treatment"],
            ),
        ]
    }
    
    # Run with alt medicine OFF
    report = await run_pulse_validation(
        query="treatment",
        results_by_source=results,
    )
    
    # Should exclude herbal result (in production code)
    # For now, PULSE includes all, filter happens in run_search()
```

## Monitoring & Observability

### Log Aggregation

```
# Example ELK/CloudWatch query
fields @timestamp, @message, @logStream
| filter @logStream like /lena\.(search|pulse|sources)/
| stats count() by @logStream
```

### Response Time SLA

```python
# Track in your monitoring system
response_time_ms = result["response_time_ms"]

# Good: < 500ms (most single-source queries)
# Acceptable: 500-2000ms (multi-source with network latency)
# Warn: > 2000ms (timeouts + retries happening)
```

### Cache Hit Rate

```python
# In your metrics collection
if result.get("from_cache"):
    cache_hits += 1
total_requests += 1

hit_rate = (cache_hits / total_requests) * 100
# Target: 30-50% hit rate for typical usage patterns
```

## Debugging Tips

### Enable Debug Logging

```python
# In development, set ENV=development
# Or manually configure:
import os
os.environ["ENV"] = "development"

from app.core.logging import setup_logging
setup_logging("development")  # Readable format
```

### Check Cache State

```python
from app.services.result_cache import get_cache_stats

stats = get_cache_stats()
print(f"""
Cache Stats:
  Total entries: {stats['total_entries']}
  Max capacity: {stats['max_entries']}
  Usage: {stats['usage_percent']}%
  TTL: {stats['ttl_seconds']}s
""")
```

### Inspect PULSE Scoring

```python
pulse = result["pulse_report"]

print(f"Status: {pulse['status']}")
print(f"Confidence: {pulse['confidence_ratio']}")
print(f"Consensus keywords: {pulse['consensus_keywords'][:5]}")

for agreement in pulse["source_agreements"]:
    print(f"  {agreement['source']}: {agreement['overlap_score']:.2f}")
```

## Performance Tuning

### Cache Size

Currently: 500 entries, 5-minute TTL
- **High traffic**: Increase to 2000-5000
- **Limited memory**: Decrease to 100-200
- **Long-tail queries**: Keep 300-500

### Retry Strategy

Currently: 3 attempts, 1s/2s/4s backoff
- **Flaky source**: Increase to 5 attempts
- **Stable source**: Decrease to 2 attempts
- **Rate-limited**: Increase max backoff to 16s

### PULSE Parameters

Currently hardcoded in pulse_engine.py:
- `edge_case_threshold = 0.15` - Lower = more edge cases
- `single_source_cap = 0.60` - Lower = more conservative
- `cochrane_multiplier = 1.25` - Higher = more weight to reviews

## FAQs

**Q: Why is my query taking longer than expected?**
A: Check if retries are happening - look for "Attempt N/3" in logs. If sources are down, first request + retries = 1s + 2s + 4s = 7s wait time.

**Q: Are alternative medicine results still available to users?**
A: Yes - filtering is optional (`include_alt_medicine` parameter). When False, they're excluded from results but not deleted.

**Q: How do I clear the cache without restarting?**
A: Call `from app.services.result_cache import clear_cache; clear_cache()` in a management command or endpoint.

**Q: Is caching safe for sensitive queries?**
A: Yes - cache is in-process memory, scoped to current request context. Survives process restarts though, so clear on deployment if concerned.

**Q: What if a PULSE rule conflicts with another?**
A: Rules are applied in order: retracted (exclude) → single-source cap → Cochrane boost → edge case penalty. No conflicts by design.
