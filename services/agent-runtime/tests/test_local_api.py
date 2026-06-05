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
        os.environ["FATHIYA_LOCAL_SETTINGS_PATH"] = str(
            Path(self.temp.name) / "operator-settings.json"
        )
        os.environ["FATHIYA_KNOWLEDGE_ROOT"] = str(Path(self.temp.name) / "knowledge")
        os.environ["FATHIYA_KNOWLEDGE_WATCH_ENABLED"] = "true"
        os.environ["FATHIYA_KNOWLEDGE_WATCH_ROOT"] = str(Path(self.temp.name) / "inbox")
        os.environ["FATHIYA_KNOWLEDGE_WATCH_STATE_PATH"] = str(
            Path(self.temp.name) / "knowledge-watcher.json"
        )
        os.environ["FATHIYA_TRADING_SQLITE_PATH"] = str(
            Path(self.temp.name) / "trading.db"
        )
        os.environ["FATHIYA_TRADING_TICK_SECONDS"] = "0.05"
        os.environ["FATHIYA_TRADING_MODE"] = "paper"
        os.environ["FATHIYA_TRADING_MARKET_PROVIDER"] = "synthetic_second_market"
        os.environ["FATHIYA_TRADING_SYMBOL"] = "SIM-USD"
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_GENERATION"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_PLANNING"] = "false"
        os.environ["FATHIYA_ZAPIER_MCP_TOKEN_PATH"] = str(
            Path(self.temp.name) / "zapier_oauth.json"
        )
        os.environ.pop("FATHIYA_ZAPIER_MCP_ACCESS_TOKEN", None)
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
        os.environ.pop("OPENROUTER_API_KEY", None)

    def test_local_api_vertical_slice_and_approval_controls(self) -> None:
        health = requests.get(f"{self.base_url}/healthz", headers=self.headers, timeout=5)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "local_sqlite")
        self.assertFalse(health.json()["worker_online"])
        self.assertEqual(health.json()["agent_loop"]["max_rounds"], 4)
        self.assertEqual(health.json()["agent_loop"]["max_tool_steps_per_round"], 6)
        self.assertFalse(health.json()["agent_loop"]["openrouter_configured"])
        self.assertTrue(health.json()["knowledge_intake"]["enabled"])
        self.assertFalse(health.json()["knowledge_intake"]["running"])
        self.assertEqual(health.json()["trading"]["mode"], "paper")
        self.assertTrue(health.json()["trading"]["autostart"])
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
        capabilities_response = requests.get(
            f"{self.base_url}/api/agent/capabilities",
            headers=self.headers,
            timeout=15,
        )
        self.assertEqual(capabilities_response.status_code, 200)
        capability_probe = capabilities_response.json()["capabilities"]
        self.assertEqual(capability_probe["capability_count"], 10)
        self.assertGreaterEqual(capability_probe["ready_count"], 1)

        integrations_response = requests.get(
            f"{self.base_url}/api/agent/integrations",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(integrations_response.status_code, 200)
        self.assertNotIn("local-api-test-bridge-token", integrations_response.text)
        integrations = integrations_response.json()
        integration_by_id = {
            item["id"]: item for item in integrations["integrations"]
        }
        self.assertFalse(integrations["security_policy"]["accept_passwords_in_chat"])
        self.assertIn(
            integration_by_id["local_execution_mesh"]["status"],
            {"ready", "partial"},
        )
        self.assertGreaterEqual(
            integration_by_id["local_execution_mesh"]["details"]["ready_count"],
            1,
        )
        self.assertEqual(integration_by_id["openrouter"]["status"], "needs_setup")
        self.assertIn(
            "OPENROUTER_API_KEY",
            integration_by_id["openrouter"]["missing_env"],
        )
        self.assertEqual(integration_by_id["zapier_mcp"]["status"], "partial")
        self.assertEqual(
            integration_by_id["zapier_mcp"]["action_path"],
            "/api/agent/oauth/zapier/start",
        )
        self.assertGreaterEqual(
            integration_by_id["zapier_mcp"]["details"]["app_count"],
            20,
        )
        self.assertEqual(
            integration_by_id["broker_testnet"]["status"],
            "needs_operator",
        )
        self.assertFalse(
            integration_by_id["broker_testnet"]["details"]["live_execution_enabled"]
        )
        openrouter_probe = requests.post(
            f"{self.base_url}/api/agent/integrations/openrouter/probe",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(openrouter_probe.status_code, 200)
        self.assertFalse(openrouter_probe.json()["ok"])
        self.assertEqual(openrouter_probe.json()["status"], "needs_setup")
        self.assertTrue(openrouter_probe.json()["secret_safe"])
        self.assertFalse(openrouter_probe.json()["details"]["network_call"])
        testnet_probe = requests.post(
            f"{self.base_url}/api/agent/integrations/broker_testnet/probe",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(testnet_probe.status_code, 200)
        self.assertFalse(testnet_probe.json()["ok"])
        self.assertEqual(testnet_probe.json()["status"], "needs_operator")
        self.assertNotIn("api_key", testnet_probe.text.lower())
        settings_response = requests.get(
            f"{self.base_url}/api/agent/settings",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(settings_response.status_code, 200)
        self.assertTrue(settings_response.json()["write_allowed"])
        self.assertFalse(settings_response.json()["security"]["values_returned"])
        self.assertNotIn("local-api-test-bridge-token", settings_response.text)

        remote_settings_write = requests.post(
            f"{self.base_url}/api/agent/settings/openrouter",
            headers={"Origin": "https://fathya-core.com"},
            json={"values": {"OPENROUTER_API_KEY": "remote-must-not-write"}, "clear": []},
            timeout=5,
        )
        self.assertEqual(remote_settings_write.status_code, 403)
        self.server.worker = AgentWorker(self.config, self.store, tools=self.server.tools)
        self.server.tools.zapier.oauth.pending["pending-test-state"] = {
            "expires_at": time.time() + 60
        }
        local_settings_write = requests.post(
            f"{self.base_url}/api/agent/settings/openrouter",
            headers=self.headers,
            json={"values": {"OPENROUTER_API_KEY": "local-openrouter-test-key"}, "clear": []},
            timeout=5,
        )
        self.assertEqual(local_settings_write.status_code, 200)
        self.assertTrue(local_settings_write.json()["applied"])
        self.assertNotIn("local-openrouter-test-key", local_settings_write.text)
        self.assertTrue(self.server.config.openrouter_api_key)
        self.assertTrue(self.server.worker.model.openrouter.available)
        self.assertIn("pending-test-state", self.server.tools.zapier.oauth.pending)
        self.assertTrue(
            requests.get(f"{self.base_url}/healthz", headers=self.headers, timeout=5)
            .json()["agent_loop"]["openrouter_configured"]
        )
        openrouter_probe_ready = requests.post(
            f"{self.base_url}/api/agent/integrations/openrouter/probe",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(openrouter_probe_ready.status_code, 200)
        self.assertTrue(openrouter_probe_ready.json()["ok"])
        self.assertEqual(openrouter_probe_ready.json()["status"], "ready")
        self.assertFalse(openrouter_probe_ready.json()["details"]["cost_incurred"])
        self.assertNotIn("local-openrouter-test-key", openrouter_probe_ready.text)
        unknown_probe = requests.post(
            f"{self.base_url}/api/agent/integrations/nope/probe",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(unknown_probe.status_code, 404)
        invalid_n8n_url = requests.post(
            f"{self.base_url}/api/agent/settings/n8n_local",
            headers=self.headers,
            json={"values": {"N8N_BASE_URL": "https://example.com"}, "clear": []},
            timeout=5,
        )
        self.assertEqual(invalid_n8n_url.status_code, 400)
        intake_status = requests.get(
            f"{self.base_url}/api/agent/intake/status",
            headers=self.headers,
            timeout=5,
        ).json()["intake"]
        self.assertTrue(intake_status["enabled"])
        self.assertFalse(intake_status["running"])
        intake_scan = requests.post(
            f"{self.base_url}/api/agent/intake/scan",
            headers=self.headers,
            timeout=5,
        ).json()
        self.assertEqual(intake_scan["enqueued"], [])

        zapier_status = requests.get(
            f"{self.base_url}/api/agent/oauth/zapier/status",
            headers=self.headers,
            timeout=5,
        ).json()["zapier_mcp"]
        self.assertFalse(zapier_status["connected"])
        with patch.object(
            self.server.tools.zapier,
            "start_oauth",
            return_value="https://mcp.zapier.com/oauth/authorize?test=1",
        ) as start_oauth:
            oauth_start = requests.get(
                f"{self.base_url}/api/agent/oauth/zapier/start",
                headers=self.headers,
                params={"return_to": f"{self.base_url}/agent-tasks"},
                allow_redirects=False,
                timeout=5,
            )
        self.assertEqual(oauth_start.status_code, 302)
        self.assertEqual(
            oauth_start.headers["Location"],
            "https://mcp.zapier.com/oauth/authorize?test=1",
        )
        self.assertEqual(
            start_oauth.call_args.args[1],
            f"{self.base_url}/agent-tasks",
        )

        denied = requests.get(
            f"{self.base_url}/healthz",
            headers={"Origin": "https://example.com"},
            timeout=5,
        )
        self.assertEqual(denied.status_code, 403)
        production_origin = requests.get(
            f"{self.base_url}/healthz",
            headers={"Origin": "https://fathya-core.com"},
            timeout=5,
        )
        self.assertEqual(production_origin.status_code, 200)
        self.assertEqual(
            production_origin.headers["Access-Control-Allow-Origin"],
            "https://fathya-core.com",
        )
        production_preflight = requests.options(
            f"{self.base_url}/api/agent/tasks",
            headers={
                "Origin": "https://fathya-core.com",
                "Access-Control-Request-Private-Network": "true",
            },
            timeout=5,
        )
        self.assertEqual(production_preflight.status_code, 204)
        self.assertEqual(
            production_preflight.headers["Access-Control-Allow-Private-Network"],
            "true",
        )

        created = requests.post(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            json={"prompt": "نفذ اختبار داخلي آمن"},
            timeout=5,
        )
        self.assertEqual(created.status_code, 201)
        task = created.json()["task"]
        self.assertEqual(task["status"], "queued")

        AgentWorker(self.config, self.store, tools=self.server.tools).start(once=True)
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

        task_started_trading = requests.post(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            json={"prompt": "شغّل وكيل التداول الورقي"},
            timeout=5,
        ).json()["task"]
        AgentWorker(self.config, self.store, tools=self.server.tools).start(once=True)
        task_started_detail = requests.get(
            f"{self.base_url}/api/agent/tasks/{task_started_trading['id']}",
            headers=self.headers,
            timeout=5,
        ).json()
        shared_trading_status = requests.get(
            f"{self.base_url}/api/agent/trading/status",
            headers=self.headers,
            timeout=5,
        ).json()["trading"]
        self.assertEqual(task_started_detail["task"]["status"], "completed")
        self.assertEqual(
            task_started_detail["task"]["result"]["tool_results"][0]["result"]["tool"],
            "trading_start",
        )
        self.assertTrue(shared_trading_status["running"])
        requests.post(
            f"{self.base_url}/api/agent/trading/stop",
            headers=self.headers,
            timeout=5,
        )

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
