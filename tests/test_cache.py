"""
Tests for the Redis cache wrapper (cache.py).

Redis is mocked so no live server is required.
"""

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# Stub config before importing cache
def _make_stub_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


_make_stub_module('config', REDIS_URL='redis://localhost:6379', ELASTICSEARCH_URL=None)


class TestCacheGetSet(unittest.TestCase):

    def setUp(self):
        # Reset the module-level _client so each test gets a fresh mock
        import cache
        cache._client = None

    @patch('cache.redis_lib.Redis.from_url')
    def test_cache_miss_returns_none(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_from_url.return_value = mock_redis

        import cache
        result = cache.get_cached_search(user_id=1, query='laptop')

        self.assertIsNone(result)
        mock_redis.get.assert_called_once_with('search:1:laptop')

    @patch('cache.redis_lib.Redis.from_url')
    def test_set_and_get_roundtrip(self, mock_from_url):
        stored = {}

        def fake_setex(key, ttl, value):
            stored[key] = value

        def fake_get(key):
            return stored.get(key)

        mock_redis = MagicMock()
        mock_redis.setex.side_effect = fake_setex
        mock_redis.get.side_effect = fake_get
        mock_from_url.return_value = mock_redis

        import cache
        lines = ['- Sony Laptop | 1 | хранение: office']
        cache.set_cached_search(1, 'sony', lines)
        result = cache.get_cached_search(1, 'sony')

        self.assertEqual(result, lines)

    @patch('cache.redis_lib.Redis.from_url')
    def test_key_is_lowercased_and_stripped(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_from_url.return_value = mock_redis

        import cache
        cache.get_cached_search(user_id=5, query='  Sony LAPTOP  ')

        mock_redis.get.assert_called_once_with('search:5:sony laptop')

    @patch('cache.redis_lib.Redis.from_url')
    def test_invalidate_deletes_matching_keys(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.scan_iter.return_value = ['search:7:laptop', 'search:7:sony']
        mock_from_url.return_value = mock_redis

        import cache
        cache.invalidate_user_cache(user_id=7)

        mock_redis.delete.assert_called_once_with('search:7:laptop', 'search:7:sony')

    @patch('cache.redis_lib.Redis.from_url')
    def test_invalidate_no_keys_does_not_call_delete(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.scan_iter.return_value = []
        mock_from_url.return_value = mock_redis

        import cache
        cache.invalidate_user_cache(user_id=99)

        mock_redis.delete.assert_not_called()


class TestCacheRedisUnavailable(unittest.TestCase):
    """All cache operations must be silent when Redis raises an exception."""

    def setUp(self):
        import cache
        cache._client = None

    @patch('cache.redis_lib.Redis.from_url')
    def test_get_returns_none_on_redis_error(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = Exception('connection refused')
        mock_from_url.return_value = mock_redis

        import cache
        result = cache.get_cached_search(1, 'test')

        self.assertIsNone(result)

    @patch('cache.redis_lib.Redis.from_url')
    def test_set_silently_ignores_redis_error(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.setex.side_effect = Exception('connection refused')
        mock_from_url.return_value = mock_redis

        import cache
        # Should not raise
        cache.set_cached_search(1, 'test', ['result'])

    @patch('cache.redis_lib.Redis.from_url')
    def test_invalidate_silently_ignores_redis_error(self, mock_from_url):
        mock_redis = MagicMock()
        mock_redis.scan_iter.side_effect = Exception('connection refused')
        mock_from_url.return_value = mock_redis

        import cache
        # Should not raise
        cache.invalidate_user_cache(1)

    @patch('cache.redis_lib.Redis.from_url')
    def test_from_url_failure_returns_none(self, mock_from_url):
        mock_from_url.side_effect = Exception('cannot connect')

        import cache
        cache._client = None
        result = cache.get_cached_search(1, 'query')

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
