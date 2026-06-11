"""
Tests for Elasticsearch search and PostgreSQL fallback behaviour.

All external dependencies (ES client, database session) are mocked so the
tests run without a live Elasticsearch instance or PostgreSQL connection.
"""

import sys
import types
import unittest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Minimal stubs so we can import homemanager without a real DB / bot
# ---------------------------------------------------------------------------

def _make_stub_module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


def _stub_config():
    mod = _make_stub_module('config')
    mod.SQLALCHEMY_DATABASE_URI = 'postgresql://test'
    mod.ELASTICSEARCH_URL = 'http://localhost:9200'
    mod.REDIS_URL = 'redis://'
    mod.API_TOKEN = 'fake-token'
    return mod


def _stub_telebot():
    mod = _make_stub_module('telebot')
    mod.TeleBot = object
    types_mod = _make_stub_module('telebot.types')
    types_mod.User = object
    types_mod.Message = object
    mod.types = types_mod  # so `telebot.types.User` resolves correctly
    return mod


def _build_item(id_, name, brand, model, category, storage_place, owner_id, quantity=1):
    item = MagicMock()
    item.id = id_
    item.name = name
    item.brand = brand
    item.model = model
    item.category = category
    item.storage_place = storage_place
    item.owner_id = owner_id
    item.quantity = quantity
    return item


# Register stubs before importing project modules
_stub_config()
_stub_telebot()
_make_stub_module('api').Bot = object
_make_stub_module('gui')
_make_stub_module('notifications')

# rq stubs — need rq.exceptions and rq.job submodules
_rq = _make_stub_module('rq')
_rq_exc = _make_stub_module('rq.exceptions')
_rq_exc.NoSuchJobError = Exception
_rq.exceptions = _rq_exc
_rq_job = _make_stub_module('rq.job')
_rq.job = _rq_job
_rq.Queue = MagicMock
_rq.get_current_job = MagicMock(return_value=None)

_tasks = _make_stub_module('tasks')
_tasks.redis_conn = MagicMock()
_tasks.task_queue = MagicMock()
_tasks.export_inventory_table = MagicMock()


class TestElasticQueryIndex(unittest.TestCase):
    """elastic.query_index builds the right ES query and parses results."""

    def test_returns_ids_in_relevance_order(self):
        import elastic
        mock_es = MagicMock()
        mock_es.search.return_value = {
            'hits': {
                'hits': [
                    {'_id': '3', '_score': 1.8},
                    {'_id': '1', '_score': 1.2},
                ],
                'total': {'value': 2},
            }
        }
        elastic.es = mock_es

        ids, total = elastic.query_index('ноутбук', owner_id=42)

        self.assertEqual(ids, [3, 1])
        self.assertEqual(total, 2)
        mock_es.search.assert_called_once()
        call_kwargs = mock_es.search.call_args
        query_body = call_kwargs.kwargs.get('query') or call_kwargs[1].get('query')
        self.assertIn('bool', query_body)
        self.assertEqual(query_body['bool']['filter']['term']['owner_id'], 42)

    def test_returns_empty_on_es_exception(self):
        import elastic
        mock_es = MagicMock()
        mock_es.search.side_effect = Exception('connection refused')
        elastic.es = mock_es

        ids, total = elastic.query_index('test')

        self.assertEqual(ids, [])
        self.assertEqual(total, 0)

    def test_returns_empty_when_es_is_none(self):
        import elastic
        elastic.es = None

        ids, total = elastic.query_index('anything')

        self.assertEqual(ids, [])
        self.assertEqual(total, 0)


class TestHomeManagerSearch(unittest.TestCase):
    """HomeManager.search() uses ES → cache, falls back to PostgreSQL ILIKE."""

    def _make_manager(self):
        """Return a HomeManager instance with mocked conn.

        HomeManager is wrapped by @singleton so hm.HomeManager is the
        get_instance function.  We extract the actual class from its closure.
        """
        import homemanager as hm

        # Extract the actual HomeManager class from the singleton closure
        actual_class = None
        for cell in hm.HomeManager.__closure__:
            try:
                obj = cell.cell_contents
                if isinstance(obj, type) and obj.__name__ == 'HomeManager':
                    actual_class = obj
                    break
            except ValueError:
                pass

        if actual_class is None:
            raise RuntimeError('Could not find HomeManager class in singleton closure')

        manager = object.__new__(actual_class)
        manager.conn = MagicMock()

        db_user = MagicMock()
        db_user.user_id = 10
        manager.conn.session.query.return_value.filter_by.return_value.one_or_none.return_value = db_user

        return manager

    @patch('homemanager.cache')
    @patch('homemanager.elastic')
    def test_es_hit_returns_formatted_results(self, mock_elastic, mock_cache):
        manager = self._make_manager()
        mock_cache.get_cached_search.return_value = None  # cache miss

        item = _build_item(3, 'Sony Laptop', 'Sony', 'VAIO', 'electronics', 'office', owner_id=10)
        mock_elastic.query_index.return_value = ([3], 1)

        # session.query(...).filter(...) returns our item
        manager.conn.session.query.return_value.filter.return_value = [item]

        result = manager.search('sony', user_id=99)

        self.assertIn('Sony Laptop', result)
        mock_cache.set_cached_search.assert_called_once()

    @patch('homemanager.cache')
    @patch('homemanager.elastic')
    def test_cache_hit_skips_es_and_db(self, mock_elastic, mock_cache):
        manager = self._make_manager()
        mock_cache.get_cached_search.return_value = ['- Sony Laptop | 1 | хранение: office']

        result = manager.search('sony', user_id=99)

        mock_elastic.query_index.assert_not_called()
        manager.conn.session.query.assert_not_called()
        self.assertIn('Sony Laptop', result)

    @patch('homemanager.cache')
    @patch('homemanager.elastic')
    def test_fallback_to_postgres_when_es_returns_empty(self, mock_elastic, mock_cache):
        manager = self._make_manager()
        mock_cache.get_cached_search.return_value = None
        mock_elastic.query_index.return_value = ([], 0)  # ES down / no results

        item = _build_item(5, 'Kitchen Mixer', 'Bosch', '', 'appliances', 'kitchen', owner_id=10)

        # The fallback path goes through a chained .filter().all() call
        filter_mock = MagicMock()
        filter_mock.all.return_value = [item]
        manager.conn.session.query.return_value.filter.return_value = filter_mock

        result = manager.search('mixer', user_id=99)

        self.assertIn('Kitchen Mixer', result)

    @patch('homemanager.cache')
    @patch('homemanager.elastic')
    def test_empty_query_returns_prompt(self, mock_elastic, mock_cache):
        manager = self._make_manager()

        result = manager.search('   ', user_id=99)

        self.assertIn('Введите', result)
        mock_elastic.query_index.assert_not_called()

    @patch('homemanager.cache')
    @patch('homemanager.elastic')
    def test_no_results_returns_not_found_message(self, mock_elastic, mock_cache):
        manager = self._make_manager()
        mock_cache.get_cached_search.return_value = None
        mock_elastic.query_index.return_value = ([], 0)

        filter_mock = MagicMock()
        filter_mock.all.return_value = []
        manager.conn.session.query.return_value.filter.return_value = filter_mock

        result = manager.search('xyzzy', user_id=99)

        self.assertIn('Ничего не найдено', result)
        mock_cache.set_cached_search.assert_called_once_with(99, 'xyzzy', [])


if __name__ == '__main__':
    unittest.main()
