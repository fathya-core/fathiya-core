from __future__ import annotations

import os
import tempfile
import threading
import unittest
from pathlib import Path

import requests

from fathiya_runtime.config import RuntimeConfig
from fathiya_runtime.local_api import create_local_server
from fathiya_runtime.store import SQLiteTaskStore
from fathiya_runtime.worker import AgentWorker


class LocalAgentApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "runtime.db"
        os.environ["FATHIYA_STORE"] = "sqlite"
        os.environ["FATHIYA_SQLITE_PATH"] = str(self.db_path)
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_GENERATION"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_PLANNING"] = "false"
        os.environ.pop("OPENROUTER_API_KEY", None)
        self.config = RuntimeConfig.load()
        self.store = SQLiteTaskStore(self.db_path)
        self.server = create_local_server(self.config, self.store, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.headers = {"Origin": "http://127.0.0.1:5173"}

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def test_local_api_vertical_slice_and_approval_controls(self) -> None:
        health = requests.get(f"{self.base_url}/healthz", headers=self.headers, timeout=5)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "local_sqlite")
        self.assertFalse(health.json()["worker_online"])
        self.assertEqual(
            health.headers["Access-Control-Allow-Origin"],
            "http://127.0.0.1:5173",
        )
        previous_zapier_url = os.environ.get("FATHIYA_ZAPIER_WEBHOOK_URL")
        os.environ["FATHIYA_ZAPIER_WEBHOOK_URL"] = (
            "https://example.invalid/zapier/secret-token"
        )
        try:
            connector_response = requests.get(
                f"{self.base_url}/api/agent/connectors",
                headers=self.headers,
                timeout=5,
            )
        finally:
            if previous_zapier_url is None:
                os.environ.pop("FATHIYA_ZAPIER_WEBHOOK_URL", None)
            else:
                os.environ["FATHIYA_ZAPIER_WEBHOOK_URL"] = previous_zapier_url
        self.assertNotIn("secret-token", connector_response.text)
        connectors = connector_response.json()
        by_name = {item["name"]: item for item in connectors["connectors"]}
        self.assertTrue(by_name["n8n_health"]["configured"])
        self.assertGreaterEqual(connectors["inventory"]["zapier_app_count"], 20)

        denied = requests.get(
            f"{self.base_url}/healthz",
            headers={"Origin": "https://example.com"},
            timeout=5,
        )
        self.assertEqual(denied.status_code, 403)

        created = requests.post(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            json={"prompt": "نفذ اختبار داخلي آمن"},
            timeout=5,
        )
        self.assertEqual(created.status_code, 201)
        task = created.json()["task"]
        self.assertEqual(task["status"], "queued")

        AgentWorker(self.config, self.store).start(once=True)
        detail = requests.get(
            f"{self.base_url}/api/agent/tasks/{task['id']}",
            headers=self.headers,
            timeout=5,
        ).json()
        self.assertEqual(detail["task"]["status"], "completed")
        self.assertEqual(detail["task"]["progress"], 100)
        self.assertEqual(len(detail["receipts"]), 1)

        sensitive = requests.post(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            json={"prompt": "نفذ صفقة شراء حقيقية"},
            timeout=5,
        ).json()["task"]
        self.assertEqual(sensitive["status"], "awaiting_approval")

        approved = requests.post(
            f"{self.base_url}/api/agent/tasks/{sensitive['id']}/approve",
            headers=self.headers,
            timeout=5,
        ).json()["task"]
        self.assertEqual(approved["status"], "queued")
        self.assertEqual(approved["approval_state"], "approved")

        canceled = requests.post(
            f"{self.base_url}/api/agent/tasks/{sensitive['id']}/cancel",
            headers=self.headers,
            timeout=5,
        ).json()["task"]
        self.assertEqual(canceled["status"], "canceled")


if __name__ == "__main__":
    unittest.main()
