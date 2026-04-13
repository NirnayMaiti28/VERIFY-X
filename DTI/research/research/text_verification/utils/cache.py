import hashlib
import json

import redis


CACHE_TTL_SECONDS = 3600


def _get_client():
    try:
        client = redis.Redis(
            host="localhost",
            port=6379,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        return client
    except redis.exceptions.RedisError:
        return None


def _normalize_claim_key(claim):
    normalized = " ".join((claim or "").strip().lower().split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"verify:{digest}"


def get_cached_result(claim):
    client = _get_client()
    if client is None:
        return None

    try:
        raw = client.get(_normalize_claim_key(claim))
        if not raw:
            return None
        return json.loads(raw)
    except (redis.exceptions.RedisError, ValueError, TypeError):
        return None


def set_cached_result(claim, result, ttl=CACHE_TTL_SECONDS):
    client = _get_client()
    if client is None:
        return False

    try:
        client.setex(_normalize_claim_key(claim), int(ttl), json.dumps(result))
        return True
    except (redis.exceptions.RedisError, TypeError, ValueError):
        return False


class RedisCache:
    """Backward-compatible wrapper for existing call sites."""

    def get(self, key):
        return get_cached_result(key)

    def set(self, key, value, ttl=CACHE_TTL_SECONDS):
        return set_cached_result(key, value, ttl=ttl)


__all__ = ["get_cached_result", "set_cached_result", "RedisCache"]
