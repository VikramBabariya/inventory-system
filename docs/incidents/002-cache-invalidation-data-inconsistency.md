# Incident Report: Cache Invalidation Data Inconsistency

**Incident ID:** INC-003  
**Date:** 2026-08-11  
**Environment:** Development (Docker Compose)  
**Severity:** Medium  
**Status:** Resolved  

## Summary

Manual database edits bypassed Redis cache invalidation mechanism, causing data inconsistency between PostgreSQL database state and API responses. Issue revealed cache architecture understanding gap and lack of clear guidance for database debugging procedures.

## Timeline

| Time | Event |
|------|-------|
| Morning | Developer noticed incorrect stock values in API responses |
| 10:00 | Connected to PostgreSQL directly to investigate |
| 10:15 | Manually updated product stock values in database |
| 10:20 | API still returning old values despite database update |
| 10:30 | Investigated caching layer behavior |
| 10:45 | Identified Redis cache serving stale data |
| 11:00 | Manual cache flush resolved immediate issue |
| 11:15 | Root cause analysis and prevention planning |

## Impact Assessment

- **Environment**: Development environment  
- **Duration**: ~1 hour of debugging time
- **Data Consistency**: Temporary inconsistency between database and API layer
- **Developer Confusion**: Understanding gap in cache architecture
- **Debugging Workflow**: Inefficient manual database editing approach

## Root Cause Analysis

### Problem Description
The application uses a **Redis caching layer** with the following architecture:

```
API Request → Redis Check → Cache HIT: Return cached data
                        → Cache MISS: Query PostgreSQL → Cache result (1hr TTL)
```

**Cache invalidation strategy:**
- Cache is invalidated **only** on write operations through API endpoints
- Direct database edits **bypass** the API layer entirely
- Result: Database updated, cache unchanged

### Technical Root Cause

1. **Manual Database Edit**: Developer executed direct SQL: `UPDATE products SET current_stock = 99 WHERE id = 1`
2. **Cache Bypass**: Update did not go through API layer (`POST /products/{id}/movements`)  
3. **Stale Cache**: Redis still contained old value with remaining TTL
4. **API Response**: Served cached data instead of fresh database value
5. **Data Inconsistency**: Database showed 99, API returned cached value (e.g., 45)

### Data Flow Comparison

| Update Method | Path | Cache Invalidation | Result |
|---------------|------|-------------------|---------|
| **API Endpoint** | `POST /products/1/movements` → DB → Cache Clear | ✅ Automatic | Consistent |
| **Direct SQL** | `psql` → DB (cache unaware) | ❌ None | Inconsistent |

### Architecture Gap
```python
# What should happen:
def update_stock(product_id, new_stock):
    # 1. Update database
    db.execute(f"UPDATE products SET current_stock = {new_stock} WHERE id = {product_id}")
    # 2. Invalidate cache
    redis.delete(f"products:all")
    redis.delete(f"movements:{product_id}")

# What actually happened:
# Manual SQL update → Cache never notified
```

## Evidence

### Database State
```sql
SELECT id, current_stock FROM products WHERE id = 1;
-- id | current_stock
-- 1  | 99           ← Updated value
```

### API Response  
```bash
curl http://localhost:8000/products
# {"id": 1, "current_stock": 45, ...}  ← Stale cached value
```

### Cache Investigation
```bash
docker exec -it inventory-system-redis-1 redis-cli TTL "products:all"
# 2847  ← Still had ~47 minutes remaining on 1-hour TTL

docker exec -it inventory-system-redis-1 redis-cli GET "products:all"
# [{"id": 1, "current_stock": 45, ...}]  ← Cached stale data
```

## Resolution

### Immediate Fix
```bash
# Manual cache flush to restore consistency
docker exec -it inventory-system-redis-1 redis-cli FLUSHALL
```

### Verification
```bash
# Confirmed fresh data retrieval
curl http://localhost:8000/products
# {"id": 1, "current_stock": 99, ...}  ← Now consistent with database
```

## Lessons Learned

### Architecture Understanding Gaps
1. **Cache Layer Visibility**: Developers unaware of Redis caching impact
2. **Data Flow**: Manual database edits bypass application logic
3. **Debugging Approach**: Direct SQL modification creates more problems  
4. **Invalidation Strategy**: Cache management tied to API endpoints only

### Development Workflow Issues
1. **Debugging Process**: No clear guidance for investigating data issues
2. **Cache Awareness**: Developers need visibility into cached vs live data
3. **Data Modification**: All changes should go through API layer
4. **Investigation Tools**: Need better debugging procedures

## Prevention Actions

### Immediate Actions (Completed)
- ✅ Documented cache invalidation behavior  
- ✅ Added Redis inspection commands to troubleshooting guide
- ✅ Established "API-only" data modification policy

### Long-term Actions (Recommended)

| Action | Owner | Due Date | Priority |
|--------|-------|----------|----------|
| Create data debugging runbook | Development | 2026-08-18 | High |
| Add cache inspection to health endpoint | Backend | 2026-08-20 | Medium |
| Implement cache monitoring dashboard | DevOps | 2026-08-25 | Medium |
| Add cache invalidation logging | Backend | 2026-08-22 | Low |

### Development Process Improvements

#### **Data Investigation Protocol**
1. **First**: Check API responses (`curl /products`)
2. **Second**: Check cache state (`redis-cli KEYS "*"`)  
3. **Third**: Check database directly if needed
4. **Never**: Modify database directly for debugging

#### **Cache Visibility Tools**
```bash
# Add to health endpoint response:
{
  "status": "healthy",
  "database": "connected", 
  "cache": "connected",
  "cache_keys": 3,           ← New: Number of cached keys
  "cache_hit_ratio": 0.85    ← New: Cache effectiveness
}
```

## Architecture Documentation Needs

### Cache Strategy Documentation
- **TTL Policy**: 1-hour expiration for product data
- **Invalidation Triggers**: API write operations only
- **Fallback Behavior**: Graceful degradation to database on cache miss
- **Monitoring**: Cache hit ratios and key counts

### Developer Guidelines  
- **Data Debugging**: Always use API endpoints for investigation
- **Cache Inspection**: Redis CLI commands for troubleshooting
- **Manual Overrides**: When cache flush is appropriate
- **Production Considerations**: Cache behavior in different environments

## Broader Implications

### Performance vs Consistency Trade-offs
- **Cache Benefits**: 1-hour TTL provides significant performance improvement
- **Consistency Risk**: Manual database edits create inconsistency windows
- **Debugging Challenge**: Cache layer adds complexity to data investigation

### Production Considerations
- **Cache Monitoring**: Need alerting on cache failures or inconsistencies
- **Data Validation**: Periodic consistency checks between cache and database
- **Invalidation Strategy**: Consider more granular cache invalidation
- **Emergency Procedures**: Clear cache flush procedures for production issues

## References

- **Cache Implementation**: `backend/cache.py` - Redis integration code
- **API Endpoints**: `backend/main.py` - Cache invalidation triggers  
- **Troubleshooting Commands**: Redis CLI reference guide
- **Architecture Decision**: ADR on caching strategy implementation

---

**Incident Closed:** 2026-08-11  
**Next Review Date:** 2026-08-18 (Data debugging runbook creation)