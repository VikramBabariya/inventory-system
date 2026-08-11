import json
import logging
import os
from typing import Any, Callable

import redis

logger = logging.getLogger(__name__)

# Read Redis URL from environment — defaults to the Docker Compose service name.
# Pattern mirrors database.py: fail fast on connect, not on import.
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

# Single client instance shared across requests (redis-py manages a connection pool
# internally, so this is safe and efficient).
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis | None:
    """
    Returns the shared Redis client, creating it on first call.
    Returns None if the connection cannot be established, allowing
    the application to degrade gracefully to direct DB reads.
    """
    global _redis_client
    if _redis_client is None:
        try:
            client = redis.from_url(REDIS_URL, decode_responses=True)
            # Ping to verify the connection is actually reachable at startup.
            client.ping()
            _redis_client = client
            logger.info("Redis connection established: %s", REDIS_URL)
        except redis.RedisError as e:
            logger.warning("Redis unavailable at startup — caching disabled: %s", e)
            return None
    return _redis_client


def get_cache() -> redis.Redis | None:
    """
    FastAPI dependency. Injects the Redis client into route handlers.
    Yields None if Redis is unreachable — handlers must check for None
    and fall back to PostgreSQL.

    Usage:
        @app.get("/example")
        def handler(cache: redis.Redis | None = Depends(get_cache)):
            ...
    """
    return get_redis_client()


# ---------------------------------------------------------------------------
# Cache key constants — centralised here to avoid string literals scattered
# across main.py and to make key changes a single-line edit.
# ---------------------------------------------------------------------------

CACHE_TTL = 3600  # 1 hour in seconds

PRODUCTS_ALL_KEY = "products:all"


def movements_key(product_id: int) -> str:
    """Returns the cache key for a specific product's movement history."""
    return f"movements:{product_id}"


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def cache_get(cache: redis.Redis | None, key: str) -> Any | None:
    """
    Reads a JSON value from cache.
    Returns the deserialised Python object on HIT, or None on MISS / error.
    """
    if cache is None:
        return None
    try:
        raw = cache.get(key)
        if raw is not None:
            logger.debug("Cache HIT: %s", key)
            return json.loads(raw)
        logger.debug("Cache MISS: %s", key)
        return None
    except redis.RedisError as e:
        logger.warning("Cache GET failed for key '%s': %s", key, e)
        return None


def cache_set(cache: redis.Redis | None, key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    """
    Serialises a Python object to JSON and stores it in cache with a TTL.
    Silently skips on error — a failed cache write must never break a response.
    """
    if cache is None:
        return
    try:
        cache.setex(key, ttl, json.dumps(value))
        logger.debug("Cache SET: %s (TTL=%ss)", key, ttl)
    except redis.RedisError as e:
        logger.warning("Cache SET failed for key '%s': %s", key, e)


def cache_delete(cache: redis.Redis | None, *keys: str) -> None:
    """
    Deletes one or more keys from cache (cache invalidation on write).
    Silently skips on error — a failed invalidation must never break a write.
    """
    if cache is None or not keys:
        return
    try:
        cache.delete(*keys)
        logger.debug("Cache DELETE: %s", keys)
    except redis.RedisError as e:
        logger.warning("Cache DELETE failed for keys %s: %s", keys, e)
