"""
Tests for main.py — the bot entry point.

All external dependencies are mocked; no live Telegram API, database,
Elasticsearch, or Redis connection is required.

Three groups of tests:
  - Module-level init: code that runs on every import (Bot creation, register_handlers)
  - main(): singleton initialisation
  - __main__ block: polling lifecycle and exception propagation (via runpy)
"""

import os
import sys
import types
import runpy
import unittest
from unittest.mock import MagicMock, patch

MAIN_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'main.py')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_stubs(api_token: str = 'test-token-123'):
    """Inject minimal stubs into sys.modules and return key mock objects.

    Returns (MockBot class, bot instance, MockHomeManager class, hm instance).
    Must be called before importing main so the module-level code sees the stubs.
    """
    config_mod = types.ModuleType('config')
    config_mod.API_TOKEN = api_token
    sys.modules['config'] = config_mod

    mock_bot_instance = MagicMock()
    MockBot = MagicMock(return_value=mock_bot_instance)
    api_mod = types.ModuleType('api')
    api_mod.Bot = MockBot
    sys.modules['api'] = api_mod

    mock_hm_instance = MagicMock()
    MockHomeManager = MagicMock(return_value=mock_hm_instance)
    hm_mod = types.ModuleType('homemanager')
    hm_mod.HomeManager = MockHomeManager
    sys.modules['homemanager'] = hm_mod

    return MockBot, mock_bot_instance, MockHomeManager, mock_hm_instance


def _purge_main():
    """Remove main from the module cache so the next import re-executes it."""
    sys.modules.pop('main', None)


# ---------------------------------------------------------------------------
# Module-level initialisation
# ---------------------------------------------------------------------------

class TestModuleLevelInit(unittest.TestCase):
    """Code at module scope runs the moment main is imported."""

    def tearDown(self):
        _purge_main()

    def test_bot_instantiated_with_api_token(self):
        MockBot, _, _, _ = _make_stubs(api_token='my-telegram-token')

        import main  # noqa: F401

        MockBot.assert_called_once_with(token='my-telegram-token')

    def test_register_handlers_called_on_import(self):
        _, mock_bot, _, _ = _make_stubs()

        import main  # noqa: F401

        mock_bot.register_handlers.assert_called_once()

    def test_bot_receives_none_token_when_env_not_set(self):
        # Current code has no validation — Bot() is still called with None.
        # This test documents the existing behaviour so a future guard is noticed.
        MockBot, _, _, _ = _make_stubs(api_token=None)

        import main  # noqa: F401

        MockBot.assert_called_once_with(token=None)

    def test_homemanager_not_called_at_import_time(self):
        # HomeManager() must only be called inside main(), never at module level.
        _, _, MockHomeManager, _ = _make_stubs()

        import main  # noqa: F401

        MockHomeManager.assert_not_called()


# ---------------------------------------------------------------------------
# main() function
# ---------------------------------------------------------------------------

class TestMainFunction(unittest.TestCase):
    """Unit tests for the main() callable."""

    def setUp(self):
        _purge_main()
        self.MockBot, self.mock_bot, self.MockHomeManager, self.mock_hm = _make_stubs()

    def tearDown(self):
        _purge_main()

    def test_main_initializes_homemanager(self):
        import main

        main.main()

        self.MockHomeManager.assert_called_once()

    def test_main_returns_none(self):
        import main

        result = main.main()

        self.assertIsNone(result)

    def test_main_can_be_called_multiple_times(self):
        # Singleton pattern means repeated calls are safe; no exception expected.
        import main

        main.main()
        main.main()

        self.assertEqual(self.MockHomeManager.call_count, 2)


# ---------------------------------------------------------------------------
# __main__ block  (executed via runpy to simulate `python main.py`)
# ---------------------------------------------------------------------------

class TestMainEntryPoint(unittest.TestCase):
    """Tests for the if __name__ == '__main__': block."""

    def tearDown(self):
        _purge_main()

    def test_infinity_polling_called_when_run_as_main(self):
        _, mock_bot, _, _ = _make_stubs()

        runpy.run_path(MAIN_PATH, run_name='__main__')

        mock_bot.infinity_polling.assert_called_once()

    def test_main_function_called_before_polling(self):
        _, mock_bot, MockHomeManager, _ = _make_stubs()
        call_order = []
        MockHomeManager.side_effect = lambda: call_order.append('hm') or MagicMock()
        mock_bot.infinity_polling.side_effect = lambda: call_order.append('poll')

        runpy.run_path(MAIN_PATH, run_name='__main__')

        self.assertEqual(call_order, ['hm', 'poll'])

    def test_exception_from_polling_propagates(self):
        _, mock_bot, _, _ = _make_stubs()
        mock_bot.infinity_polling.side_effect = RuntimeError('network error')

        with self.assertRaises(RuntimeError, msg='network error'):
            runpy.run_path(MAIN_PATH, run_name='__main__')

    def test_exception_from_main_propagates(self):
        _, _, MockHomeManager, _ = _make_stubs()
        MockHomeManager.side_effect = RuntimeError('db unavailable')

        with self.assertRaises(RuntimeError, msg='db unavailable'):
            runpy.run_path(MAIN_PATH, run_name='__main__')

    def test_polling_not_reached_when_main_raises(self):
        _, mock_bot, MockHomeManager, _ = _make_stubs()
        MockHomeManager.side_effect = RuntimeError('db unavailable')

        try:
            runpy.run_path(MAIN_PATH, run_name='__main__')
        except RuntimeError:
            pass

        mock_bot.infinity_polling.assert_not_called()

    def test_status_message_printed_before_polling(self):
        _, mock_bot, _, _ = _make_stubs()
        printed = []
        mock_bot.infinity_polling.side_effect = lambda: None

        with patch('builtins.print', side_effect=lambda *a: printed.append(a)):
            runpy.run_path(MAIN_PATH, run_name='__main__')

        self.assertTrue(any('waiting' in str(args).lower() or 'бот' in str(args).lower()
                            for args in printed),
                        msg=f'Expected a status print before polling, got: {printed}')


# ---------------------------------------------------------------------------
# Regular import must not trigger the __main__ block
# ---------------------------------------------------------------------------

class TestNotRunAsMain(unittest.TestCase):
    """Importing main as a library must not start the bot polling loop."""

    def tearDown(self):
        _purge_main()

    def test_import_does_not_call_infinity_polling(self):
        _, mock_bot, _, _ = _make_stubs()

        import main  # noqa: F401

        mock_bot.infinity_polling.assert_not_called()


if __name__ == '__main__':
    unittest.main()
