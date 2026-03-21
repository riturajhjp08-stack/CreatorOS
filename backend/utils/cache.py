import json
import time

try:
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None


class SimpleCache:
    def __init__(self, redis_url=None):
        self._redis = None
        if redis_url and redis:
            try:
                self._redis = redis.Redis.from_url(redis_url)
            except Exception:
                self._redis = None
        self._local = {}

    def get(self, key):
        if self._redis:
            try:
                value = self._redis.get(key)
                if value is None:
                    return None
                return json.loads(value)
            except Exception:
                return None
        entry = self._local.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at and expires_at < time.time():
            self._local.pop(key, None)
            return None
        return value

    def set(self, key, value, ttl_seconds=60):
        if self._redis:
            try:
                payload = json.dumps(value)
                self._redis.setex(key, ttl_seconds, payload)
                return
            except Exception:
                pass
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        self._local[key] = (expires_at, value)


_cache_instance = None


def get_cache(redis_url=None):
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = SimpleCache(redis_url=redis_url)
    return _cache_instance
