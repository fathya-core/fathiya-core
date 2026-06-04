from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from fathiya_runtime.local_settings import LocalSettingsStore


class LocalSettingsStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "operator-settings.json"
        self.store = LocalSettingsStore(self.path)
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("N8N_BASE_URL", None)

    def tearDown(self) -> None:
        os.environ.pop("OPENROUTER_API_KEY", None)
        os.environ.pop("N8N_BASE_URL", None)
        self.temp.cleanup()

    def test_secret_is_persisted_but_never_returned(self) -> None:
        secret = "openrouter-secret-test-value"
        result = self.store.update_group(
            "openrouter",
            {"OPENROUTER_API_KEY": secret},
            [],
        )

        self.assertTrue(self.path.exists())
        self.assertEqual(os.environ["OPENROUTER_API_KEY"], secret)
        self.assertNotIn(secret, json.dumps(result))
        status = self.store.status()
        openrouter = next(group for group in status["groups"] if group["id"] == "openrouter")
        key_field = next(
            field for field in openrouter["fields"] if field["name"] == "OPENROUTER_API_KEY"
        )
        self.assertTrue(key_field["configured"])
        self.assertEqual(key_field["source"], "local_store")
        self.assertTrue(key_field["clearable"])

    def test_local_store_loads_into_environment_and_can_clear_its_value(self) -> None:
        self.store.update_group("openrouter", {"OPENROUTER_API_KEY": "saved-key"}, [])
        os.environ.pop("OPENROUTER_API_KEY", None)

        self.store.load_into_environment()
        cleared = self.store.update_group("openrouter", {}, ["OPENROUTER_API_KEY"])

        self.assertEqual(os.environ.get("OPENROUTER_API_KEY"), None)
        self.assertEqual(cleared["cleared_fields"], ["OPENROUTER_API_KEY"])

    def test_rejects_unknown_fields_and_non_loopback_n8n_url(self) -> None:
        with self.assertRaises(ValueError):
            self.store.update_group("openrouter", {"PASSWORD": "not-allowed"}, [])
        with self.assertRaises(ValueError):
            self.store.update_group(
                "n8n_local",
                {"N8N_BASE_URL": "https://example.com"},
                [],
            )
