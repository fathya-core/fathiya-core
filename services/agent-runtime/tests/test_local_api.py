from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

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
        os.environ["FATHIYA_TRADING_SQLITE_PATH"] = str(
            Path(self.temp.name) / "trading.db"
        )
        os.environ["FATHIYA_TRADING_TICK_SECONDS"] = "0.05"
        os.environ["FATHIYA_TRADING_MODE"] = "paper"
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_GENERATION"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_PLANNING"] = "false"
        os.environ.pop("OPENROUTER_API_KEY", None)
        self.previous_dispatch_token = os.environ.get("FATHIYA_CONNECTOR_DISPATCH_TOKEN")
        os.environ["FATHIYA_CONNECTOR_DISPATCH_TOKEN"] = "local-api-test-bridge-token"
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
        if self.previous_dispatch_token is None:
            os.environ.pop("FATHIYA_CONNECTOR_DISPATCH_TOKEN", None)
        else:
            os.environ["FATHIYA_CONNECTOR_DISPATCH_TOKEN"] = self.previous_dispatch_token

    def test_local_api_vertical_slice_and_approval_controls(self) -> None:
        health = requests.get(f"{self.base_url}/healthz", headers=self.headers, timeout=5)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "local_sqlite")
        self.assertFalse(health.json()["worker_online"])
        self.assertEqual(health.json()["trading"]["mode"], "paper")
        self.assertEqual(health.json()["trading"]["cycle_target_seconds"], 0.05)
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
        self.assertTrue(by_name["n8n_health"]["bridge_dispatch_allowed"])
        self.assertFalse(by_name["n8n_fathiya_webhook"]["bridge_dispatch_allowed"])
        self.assertTrue(connectors["bridge"]["configured"])
        self.assertIn("n8n_health", connectors["bridge"]["allowed_profiles"])
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

        trading_status = requests.get(
            f"{self.base_url}/api/agent/trading/status",
            headers=self.headers,
            timeout=5,
        ).json()["trading"]
        self.assertFalse(trading_status["running"])
        self.assertFalse(trading_status["live_execution_enabled"])

        paper_cycle = requests.post(
            f"{self.base_url}/api/agent/trading/tick",
            headers=self.headers,
            timeout=5,
        ).json()["cycle"]
        self.assertTrue(paper_cycle["receipt_id"].startswith("TR-"))
        self.assertEqual(paper_cycle["mode"], "paper")

        started_trading = requests.post(
            f"{self.base_url}/api/agent/trading/start",
            headers=self.headers,
            timeout=5,
        ).json()["trading"]
        self.assertTrue(started_trading["running"])
        tick_while_running = requests.post(
            f"{self.base_url}/api/agent/trading/tick",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(tick_while_running.status_code, 409)
        time.sleep(0.12)
        stopped_trading = requests.post(
            f"{self.base_url}/api/agent/trading/stop",
            headers=self.headers,
            timeout=5,
        ).json()["trading"]
        self.assertFalse(stopped_trading["running"])
        trading_receipts = requests.get(
            f"{self.base_url}/api/agent/trading/receipts",
            headers=self.headers,
            timeout=5,
        ).json()["receipts"]
        self.assertGreaterEqual(len(trading_receipts), 2)

        dispatch_body = {
            "task_id": task["id"],
            "profile": "n8n_health",
            "approval_state": "approved",
            "dispatch_allowed": True,
            "receipt_id": "N8N-STAGE-TEST",
            "source": "n8n-connector-gateway",
        }
        unauthorized = requests.post(
            f"{self.base_url}/api/agent/connector-dispatch",
            headers=self.headers,
            json=dispatch_body,
            timeout=5,
        )
        self.assertEqual(unauthorized.status_code, 401)

        bridge_headers = {
            **self.headers,
            "X-FATHIYA-Bridge-Token": "local-api-test-bridge-token",
        }
        denied_gate = requests.post(
            f"{self.base_url}/api/agent/connector-dispatch",
            headers=bridge_headers,
            json={**dispatch_body, "dispatch_allowed": False},
            timeout=5,
        )
        self.assertEqual(denied_gate.status_code, 409)

        loop_profile = requests.post(
            f"{self.base_url}/api/agent/connector-dispatch",
            headers=bridge_headers,
            json={**dispatch_body, "profile": "n8n_fathiya_webhook"},
            timeout=5,
        )
        self.assertEqual(loop_profile.status_code, 403)

        previous_zapier_url = os.environ.get("FATHIYA_ZAPIER_WEBHOOK_URL")
        os.environ["FATHIYA_ZAPIER_WEBHOOK_URL"] = "https://example.invalid/approved-only"
        try:
            unapproved_external = requests.post(
                f"{self.base_url}/api/agent/connector-dispatch",
                headers=bridge_headers,
                json={**dispatch_body, "profile": "zapier_fathiya_webhook"},
                timeout=5,
            )
        finally:
            if previous_zapier_url is None:
                os.environ.pop("FATHIYA_ZAPIER_WEBHOOK_URL", None)
            else:
                os.environ["FATHIYA_ZAPIER_WEBHOOK_URL"] = previous_zapier_url
        self.assertEqual(unapproved_external.status_code, 409)

        with patch.object(
            self.server.tools,
            "execute",
            return_value={
                "tool": "connector_profile",
                "profile": "n8n_health",
                "provider": "n8n",
                "method": "GET",
                "configured": True,
                "available": True,
                "executed": True,
                "status_code": 200,
                "response": {"secret_response_field": "not stored"},
            },
        ) as execute:
            dispatched = requests.post(
                f"{self.base_url}/api/agent/connector-dispatch",
                headers=bridge_headers,
                json=dispatch_body,
                timeout=5,
            )
            duplicate = requests.post(
                f"{self.base_url}/api/agent/connector-dispatch",
                headers=bridge_headers,
                json=dispatch_body,
                timeout=5,
            )
        self.assertEqual(dispatched.status_code, 200)
        self.assertEqual(dispatched.json()["status"], "dispatched")
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(duplicate.json()["status"], "duplicate")
        self.assertEqual(
            duplicate.json()["receipt_id"],
            dispatched.json()["receipt_id"],
        )
        execute.assert_called_once()
        self.assertNotIn("secret_response_field", dispatched.text)
        dispatched_detail = self.store.get_detail(task["id"])
        self.assertEqual(len(dispatched_detail["receipts"]), 2)
        self.assertEqual(
            dispatched_detail["events"][-1]["event_type"],
            "connector_dispatched",
        )
        self.assertNotIn(
            "secret_response_field",
            str(dispatched_detail["receipts"][0]["evidence"]),
        )

        failed_dispatch_body = {
            **dispatch_body,
            "receipt_id": "N8N-STAGE-FAILED-TEST",
        }
        with patch.object(
            self.server.tools,
            "execute",
            return_value={
                "tool": "connector_profile",
                "profile": "n8n_health",
                "provider": "n8n",
                "configured": True,
                "available": False,
                "executed": False,
                "error": "connection failed",
            },
        ) as execute:
            failed = requests.post(
                f"{self.base_url}/api/agent/connector-dispatch",
                headers=bridge_headers,
                json=failed_dispatch_body,
                timeout=5,
            )
            duplicate_failed = requests.post(
                f"{self.base_url}/api/agent/connector-dispatch",
                headers=bridge_headers,
                json=failed_dispatch_body,
                timeout=5,
            )
        self.assertEqual(failed.status_code, 502)
        self.assertFalse(failed.json()["accepted"])
        self.assertEqual(duplicate_failed.status_code, 502)
        self.assertFalse(duplicate_failed.json()["accepted"])
        self.assertEqual(duplicate_failed.json()["status"], "duplicate_failed")
        self.assertEqual(
            duplicate_failed.json()["receipt_id"],
            failed.json()["receipt_id"],
        )
        execute.assert_called_once()


if __name__ == "__main__":
    unittest.main()
