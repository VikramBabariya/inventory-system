# ADR-006: Redis Caching Layer

- **Status:** Implemented
- **Date:** 2026-01-29
- **Implemented:** 2026-08-11

---

## Context

The application relies on PostgreSQL as its source of truth. As traffic increases,
two issues arise:

1. **Read Latency:** Repeated JOIN queries (products + categories) increase response times.
2. **Database Load:** High-frequency identical reads consume unnecessary PostgreSQL CPU/IOPS.

We need a mechanism to offload read-heavy traffic from the primary database.

---

## Decision

Implement a caching layer using **Redis** with the **Cache-Aside (Lazy Loading)** pattern.

### Technology Choice: Redis over Memcached

- Supports complex data structures (Lists, Sets, Hashes) useful for future features
- Industry standard for cloud-native and data-centric roles
- Official ARM64 image available — compatible with the OCI Ampere A1 deployment target

### Placement & Networking

- Redis container runs on the private `backend-tier` Docker network
- No ports exposed to the host or public internet
- Accessible only by the backend service via internal Docker DNS (`redis:6379`)

### Caching Pattern: Cache-Aside

```
Request arrives
    │
    ▼
Check Redis (cache_get)
    │
    ├── HIT  → return cached JSON immediately (no DB query)
    │
    └── MISS → query PostgreSQL → store result in Redis (cache_set) → return result
```

On writes (`POST /products/{id}/movements`):
- Write to PostgreSQL first (source of truth)
- On commit success, delete affected cache keys (cache invalidation)
- Next read repopulates the cache from fresh DB data

### Implementation

All caching logic lives in `backend/cache.py`:

| Symbol | Purpose |
|---|---|
| `get_cache()` | FastAPI dependency — injects Redis client into route handlers |
| `cache_get(cache, key)` | Read a JSON value from cache; returns `None` on MISS or error |
| `cache_set(cache, key, value)` | Write a JSON value with TTL; silent on error |
| `cache_delete(cache, *keys)` | Invalidate one or more keys; silent on error |
| `CACHE_TTL` | 3600 seconds (1 hour) — default TTL for all keys |
| `PRODUCTS_ALL_KEY` | `"products:all"` — full product list with categories |
| `movements_key(id)` | `"movements:{id}"` — movement history per product |

### Endpoints and Cache Behaviour

| Endpoint | Cache action | Key(s) affected |
|---|---|---|
| `GET /products` | Read → MISS → populate | `products:all` |
| `GET /products/{id}/movements` | Read → MISS → populate | `movements:{id}` |
| `POST /products/{id}/movements` | Invalidate on write | `products:all`, `movements:{id}` |
| `GET /health` | Reports Redis status | — |

### Graceful Degradation

If Redis is unavailable at any point, the application falls back to PostgreSQL
transparently. Cache errors are logged as warnings and never propagate as HTTP errors.
This is enforced in all three helpers (`cache_get`, `cache_set`, `cache_delete`) via
`try/except redis.RedisError`.

---

## Consequences

### Positive
- Repeated dashboard loads served from memory (~microseconds vs ~milliseconds)
- PostgreSQL query load reduced on read-heavy traffic
- Cache state visible via `redis-cli KEYS "*"` for easy debugging

### Negative
- **Eventual consistency:** Up to 1 hour of stale data if cache invalidation fails silently
- **Ephemeral cache:** Redis restart wipes all cached data (acceptable — cache is not source of truth)
- **Complexity:** One additional infrastructure component to operate and monitor
- **Memory:** All cached values live in RAM; large datasets require eviction policy tuning (current dataset is tiny)
