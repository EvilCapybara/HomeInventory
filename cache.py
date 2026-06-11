import json
import logging
import redis as redis_lib
from config import REDIS_URL

logger = logging.getLogger(__name__)

CACHE_TTL = 300  # seconds (5 minutes)

_client = None


def _get_client() -> redis_lib.Redis:
    global _client
    if _client is None:
        _client = redis_lib.Redis.from_url(REDIS_URL, decode_responses=True)
    return _client


def _key(user_id: int, query: str) -> str:
    return f"search:{user_id}:{query.strip().lower()}"


def get_cached_search(user_id: int, query: str):
    """Return cached search results list or None on miss / Redis unavailable."""
    try:
        raw = _get_client().get(_key(user_id, query))
        if raw:
            logger.debug('[cache] HIT  user=%s query="%s"', user_id, query)
            return json.loads(raw)
        logger.debug('[cache] MISS user=%s query="%s"', user_id, query)
        return None
    except Exception as e:
        logger.warning('[cache] get failed: %s', e)
        return None


def set_cached_search(user_id: int, query: str, results: list):
    """Store search results in Redis with TTL."""
    try:
        _get_client().setex(_key(user_id, query), CACHE_TTL, json.dumps(results))
        logger.debug('[cache] SET  user=%s query="%s" (%d results)', user_id, query, len(results))
    except Exception as e:
        logger.warning('[cache] set failed: %s', e)


def invalidate_user_cache(user_id: int):
    """Delete all search cache entries for a given user."""
    try:
        client = _get_client()
        keys = list(client.scan_iter(f"search:{user_id}:*"))
        if keys:
            client.delete(*keys)
            logger.debug('[cache] INVALIDATED %d keys for user=%s', len(keys), user_id)
    except Exception as e:
        logger.warning('[cache] invalidate failed: %s', e)
