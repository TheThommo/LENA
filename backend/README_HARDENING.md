# LENA Search Pipeline Hardening - Complete Documentation Index

## Overview

This directory contains the hardened LENA search pipeline, made production-grade by Agent 4 with structured logging, retry logic, alternative medicine filtering, PULSE scoring rules, response time tracking, result caching, and analytics integration.

**Status**: ✓ Complete and verified  
**Date**: April 8, 2026  
**Backward Compatibility**: 100%  
**Production Ready**: YES

---

## Quick Links

### For Project Managers
- **PIPELINE_HARDENING_SUMMARY.md** - High-level overview of what was built
- **HARDENING_VERIFICATION.md** - Verification checklist and readiness assessment

### For Developers
- **HARDENING_DEVELOPER_GUIDE.md** - Code examples, testing, debugging
- This file (README_HARDENING.md) - Navigation and architecture

### For DevOps/Operations
- **HARDENING_VERIFICATION.md** - Deployment notes and configuration
- **HARDENING_DEVELOPER_GUIDE.md** - Monitoring and observability section

---

## What Was Built

### 1. Structured Logging (`app/core/logging.py`)
Centralized logging system with named loggers for different subsystems.

```python
from app.core.logging import get_logger
logger = get_logger("lena.search")
logger.info("Search completed", extra={"results": 42})
```

**Named Loggers Available**:
- `lena.search` - Main search pipeline
- `lena.pulse` - PULSE validation engine
- `lena.sources` - Data source operations
- `lena.guardrails` - Medical advice guardrails
- `lena.analytics` - Analytics events

---

### 2. Retry Logic (`tenacity` decorators on all data sources)
Automatic retry with exponential backoff on all 5 data sources.

**Configuration**:
- 3 attempts per request
- Wait: 1s → 2s → 4s
- Retries only on transient failures (timeouts, connection errors)
- No retry on 4xx client errors

**Protected Sources**:
- PubMed/NCBI (pubmed.py)
- ClinicalTrials.gov (clinical_trials.py)
- Cochrane (cochrane.py)
- WHO IRIS (who_iris.py)
- CDC Open Data (cdc.py)

---

### 3. Alternative Medicine Toggle (`include_alt_medicine` parameter)
User-facing parameter to filter out alternative medicine results.

**Usage**:
```
GET /search/?q=diabetes&include_alt_medicine=false
```

**Filtered Keywords**: herbal, acupuncture, homeopathy, naturopathy, yoga, chiropractic, etc.

**Behavior**: Filters only validated results (never affects PULSE computation)

---

### 4. PULSE Scoring Rules (4 enforced rules)
Automatic enforcement of evidence hierarchy and quality standards.

**Rule 1**: Single-Source Cap
- If only ONE source has results, max relevance_score = 0.60
- Prevents over-weighting of singleton sources

**Rule 2**: Systematic Reviews Weighted
- Cochrane results (systematic reviews) get 1.25x multiplier
- Reflects evidence hierarchy: meta-analyses > RCTs > observational
- Capped at 1.0 to prevent overflow

**Rule 3**: Conflicting Evidence Penalty
- If edge_cases exist, confidence_ratio penalized by up to 25%
- Alerts downstream that consensus is weaker

**Rule 4**: Retracted Papers Excluded
- Results with `is_retracted=True` skipped from PULSE scoring
- Still shown to users with warning flag if desired

---

### 5. Response Time Tracking
Millisecond-precision timing for all searches.

**Included in All Responses**:
```json
{
  "response_time_ms": 145.3,
  "from_cache": false,
  ...
}
```

**Uses**: SLA monitoring, performance regression detection, analytics dashboards

---

### 6. Result Caching (`app/services/result_cache.py`)
In-memory cache with 5-minute TTL and 500-entry limit.

**Configuration**:
- TTL: 5 minutes
- Max entries: 500
- Eviction: LRU (least recently used)
- Key: hash(query + sources + include_alt_medicine_flag)

**Cache Hits**: Returned as-is with `from_cache: true` flag

**Cache Misses**: Computed normally, then cached for next request

---

### 7. Analytics Integration
Fire-and-forget logging of search events.

**Logged Data**:
- search_id (unique per search)
- session_id (user session tracking)
- query text
- persona (patient/provider/researcher)
- tenant_id (multi-tenant support)
- response_time_ms
- sources_queried and sources_succeeded
- total_results count
- pulse_status (validated/insufficient/edge_case/pending)

**Never Blocks**: Uses asyncio.create_task() - exceptions logged but never raised

---

## Architecture

### Request Flow
```
Client Request
    ↓
Check Guardrail (medical advice)
    ↓
Check Cache (5-min TTL)
    ├─ HIT → Return cached result + timing
    └─ MISS ↓
Query All Sources (parallel)
    ├─ PubMed (with retry)
    ├─ ClinicalTrials.gov (with retry)
    ├─ Cochrane (with retry)
    ├─ WHO IRIS (with retry)
    └─ CDC (with retry)
    ↓
PULSE Validation
    ├─ Extract keywords
    ├─ Build consensus
    ├─ Score sources
    ├─ Apply Rules 1-4
    └─ Generate confidence ratio
    ↓
Filter by Alt Medicine (if requested)
    ↓
Cache Result
    ↓
Log Analytics (async, fire-and-forget)
    ↓
Return Response + Timing
```

### Logging Flow
```
Search starts → log to lena.search
    ↓
Sources queried → log to lena.sources
    ↓
PULSE validation → log to lena.pulse
    ├─ Rule 1 applied → debug log
    ├─ Rule 2 applied → debug log
    ├─ Rule 3 applied → debug log
    └─ Rule 4 applied → debug log
    ↓
Analytics logged → async, fire-and-forget
```

---

## File Changes Summary

### New Files (2)
| File | Lines | Purpose |
|------|-------|---------|
| `app/core/logging.py` | 111 | Structured logging configuration |
| `app/services/result_cache.py` | 132 | In-memory result caching |

### Modified Files (8)
| File | Changes | Type |
|------|---------|------|
| `app/services/search_orchestrator.py` | 95 lines | Core pipeline modifications |
| `app/services/pubmed.py` | 6 lines | Retry + logging |
| `app/services/clinical_trials.py` | 7 lines | Retry + logging |
| `app/services/cochrane.py` | 8 lines | Retry + logging |
| `app/services/who_iris.py` | 6 lines | Retry + logging |
| `app/services/cdc.py` | 8 lines | Retry + logging |
| `app/core/pulse_engine.py` | 35 lines | Scoring rules |
| `app/api/routes/search.py` | 45 lines | Analytics wiring |

---

## API Changes

### New Query Parameters
```
GET /search/
  ?q=<query>
  &include_alt_medicine=<true|false>  (default: true)
  &session_id=<uuid>                   (optional, auto-generated)
  &tenant_id=<string>                  (default: "default")
```

### New Response Fields
```json
{
  "search_id": "uuid",                    // Unique per search
  "session_id": "uuid",                   // User session
  "response_time_ms": 145.3,              // Milliseconds
  "from_cache": false,                    // Was this cached?
  "include_alt_medicine": true,           // Was filter applied?
  "sources_queried": [...],               // Which sources queried
  "total_results": 42,                    // Total papers returned
  "pulse_report": {...}                   // Validation results
}
```

### Backward Compatibility
**FULL** - All new fields are additive and optional. Existing code continues to work unchanged.

---

## Deployment Guide

### Pre-Deployment Checklist
- [ ] Verify `tenacity==9.0.0` in requirements.txt
- [ ] Ensure Supabase tables exist: `search_logs`, `usage_analytics`
- [ ] Set `ENV=production` for production logging format (optional)

### Deployment Steps
1. Pull latest code with hardening changes
2. Run test suite to verify no regressions
3. Deploy to staging
4. Monitor response times and cache hit rates
5. Deploy to production

### Post-Deployment Monitoring
- Monitor `response_time_ms` for SLA compliance
- Track `from_cache` flag for cache hit rate (target 30-50%)
- Watch `lena.sources` logs for retry activity
- Check `pulse_report.status` distribution

---

## Configuration

### Environment Variables
```bash
ENV=development    # "development" or "production"
                  # Controls logging format (readable vs concise)
```

### Tunable Parameters (in source code)
See individual module docstrings:

- `app/services/result_cache.py`:
  - `_CACHE_MAX_ENTRIES = 500`
  - `_CACHE_TTL_SECONDS = 300`

- `app/core/pulse_engine.py`:
  - `edge_case_threshold = 0.15`
  - `single_source_cap = 0.60`
  - `cochrane_multiplier = 1.25`

---

## Documentation Files

### 1. PIPELINE_HARDENING_SUMMARY.md
**Audience**: Project managers, team leads  
**Content**: Feature overview, file-by-file changes, API contract, configuration notes

### 2. HARDENING_VERIFICATION.md
**Audience**: QA, DevOps, deployment teams  
**Content**: Implementation checklist, functional tests, production readiness, next steps

### 3. HARDENING_DEVELOPER_GUIDE.md
**Audience**: Developers, engineers  
**Content**: Code examples, testing, debugging, monitoring, performance tuning, FAQs

### 4. README_HARDENING.md (this file)
**Audience**: Everyone  
**Content**: Navigation, architecture overview, quick reference

---

## Testing

### Unit Tests
Run individual component tests:
```bash
pytest tests/test_logging.py
pytest tests/test_cache.py
pytest tests/test_pulse_rules.py
```

### Integration Tests
Test the full pipeline:
```bash
pytest tests/test_search_pipeline.py
```

### Load Tests
Test retry logic and caching under load:
```bash
pytest tests/test_search_load.py
```

See HARDENING_DEVELOPER_GUIDE.md for detailed testing examples.

---

## Monitoring & Observability

### Key Metrics
- `response_time_ms` - Search latency
- `from_cache` - Cache hit detection
- `sources_succeeded` / `sources_queried` - Source reliability
- `pulse_report.confidence_ratio` - Result quality

### Log Queries
```bash
# Find all search operations
grep -r "lena.search" /var/log/app

# Find retry attempts
grep -r "Attempt" /var/log/app

# Find PULSE rule applications
grep -r "lena.pulse" /var/log/app
```

---

## Troubleshooting

### Slow Searches
1. Check `response_time_ms` - if > 2s, likely retries happening
2. Look for timeout entries in `lena.sources` logs
3. Verify network connectivity to data sources

### Low Cache Hit Rate
1. Check if same queries are being repeated
2. Verify cache isn't full (use `get_cache_stats()`)
3. Consider warming cache with popular queries

### Missing Alternative Medicine Results
1. Verify `include_alt_medicine=true` in request
2. Check if query keywords match alt medicine list
3. Review filtered results in `pulse_report`

---

## Future Enhancements

### Phase 1: Multi-Process Scaling
- Replace in-memory cache with Redis
- Share cache across worker processes
- Implement cache warming

### Phase 2: Advanced Monitoring
- Build metrics dashboard from `response_time_ms`
- Alert on response time regression
- Track cache hit rate trends

### Phase 3: ML Integration
- Calibrate PULSE confidence with real query feedback
- Learn optimal alt medicine keywords from user behavior
- Predict cache hits

### Phase 4: Alternative Medicine Knowledge Base
- Expand keyword list with domain expert input
- Integrate traditional medicine references
- Add practitioner reputation scoring

---

## Support & Questions

### Key Contacts
- **Logging Issues**: Check `app/core/logging.py` and HARDENING_DEVELOPER_GUIDE.md
- **Retry Issues**: Review `@retry` decorators and tenacity documentation
- **Cache Issues**: See `app/services/result_cache.py` API reference
- **PULSE Rules**: Review `app/core/pulse_engine.py` rule implementations

### Common Questions
See HARDENING_DEVELOPER_GUIDE.md section "FAQs"

---

## Summary

The LENA search pipeline is now **production-grade** with:

✓ Structured logging for debugging and monitoring  
✓ Automatic retry logic protecting all 5 data sources  
✓ User-facing alternative medicine filtering  
✓ 4 enforced PULSE validation rules  
✓ Response time tracking for performance monitoring  
✓ Smart result caching reducing redundant queries  
✓ Fire-and-forget analytics integration  
✓ Complete backward compatibility  

**Ready for immediate deployment.**

---

*Generated April 8, 2026 by Agent 4 (Search Pipeline Hardening)*
