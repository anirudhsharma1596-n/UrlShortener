# app/cache.py
import redis
import json
from app.config import settings

# Create a connection pool — reuses connections instead of 
# opening a new one on every request (expensive)
pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=0,                    # Redis has 16 databases (0-15), we use 0
    decode_responses=True    # Return strings instead of bytes
)

def get_redis():
    """Get a Redis client from the connection pool"""
    return redis.Redis(connection_pool=pool)


# ── Key naming convention ──────────────────────────────────────
# Always use a consistent pattern for keys so you can identify
# them easily in RedisInsight and avoid accidental collisions
#
# url:{short_code}     → stores the URL data
# rate:{ip_address}    → stores request count (Phase 6)

def make_url_key(short_code: str) -> str:
    return f"url:{short_code}"


# ── Cache operations ───────────────────────────────────────────

def cache_url(short_code: str, url_data: dict, ttl_seconds: int = 3600):
    """
    Store URL data in Redis.
    ttl = time to live — key auto-deletes after this many seconds.
    3600 seconds = 1 hour. After that, next request goes to PostgreSQL
    and refreshes the cache.
    """
    r = get_redis()
    key = make_url_key(short_code)
    # Redis can only store strings — we serialize our dict to JSON
    r.setex(key, ttl_seconds, json.dumps(url_data))


def get_cached_url(short_code: str) -> dict | None:
    """
    Try to get URL data from Redis.
    Returns the dict if found, None if not cached.
    """
    r = get_redis()
    key = make_url_key(short_code)
    data = r.get(key)

    if data is None:
        return None

    return json.loads(data)   # deserialize JSON string back to dict


def invalidate_url_cache(short_code: str):
    """
    Delete a URL from cache.
    Called when a URL is deactivated — we don't want Redis
    serving stale data for a deleted URL.
    """
    r = get_redis()
    r.delete(make_url_key(short_code))