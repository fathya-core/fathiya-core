from __future__ import annotations

import os
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from fathiya_runtime.config import RuntimeConfig
from fathiya_runtime.integrations import build_integration_readiness
from fathiya_runtime.local_api import (
    _mesh_activation_overview,
    _mesh_agent_provider_summaries,
    _run_github_codespaces_scope_refresh,
    create_local_server,
)
from fathiya_runtime.store import SQLiteTaskStore
from fathiya_runtime.worker import AgentWorker


class ZapierProviderSummaryTests(unittest.TestCase):
    def test_expired_zapier_oauth_does_not_mark_agent_providers_ready(self) -> None:
        inventory = {
            "direct_zapier_mcp": {
                "connected": True,
                "direct_execution": True,
                "expired": True,
                "needs_reconnect": True,
                "live_available": False,
            },
            "agent_provider_actions": {
                "Cursor": {
                    "read": ["Find Agent Status"],
                    "approval_gated_write": ["Launch Agent"],
                },
                "Manus": {
                    "read": ["Get Tasks"],
                    "approval_gated_write": ["Create Task"],
                },
            },
        }

        providers = _mesh_agent_provider_summaries(inventory)

        self.assertEqual({provider["app"] for provider in providers}, {"Cursor", "Manus"})
        self.assertTrue(all(provider["status"] == "inventory_only" for provider in providers))
        self.assertTrue(all(provider["inventory_only"] for provider in providers))
        self.assertTrue(
            all(provider["execution_mode"] == "inventory_only_until_oauth" for provider in providers)
        )
        self.assertTrue(all(provider["action_path"] == "/api/agent/oauth/zapier/start" for provider in providers))

    def test_live_zapier_oauth_marks_agent_providers_ready(self) -> None:
        inventory = {
            "direct_zapier_mcp": {
                "connected": True,
                "direct_execution": True,
                "expired": False,
                "needs_reconnect": False,
                "live_available": True,
            },
            "agent_provider_actions": {
                "Cursor": {
                    "read": ["Find Agent Status"],
                    "approval_gated_write": ["Launch Agent"],
                },
            },
        }

        providers = _mesh_agent_provider_summaries(inventory)

        self.assertEqual(providers[0]["app"], "Cursor")
        self.assertEqual(providers[0]["status"], "ready")
        self.assertFalse(providers[0]["inventory_only"])
        self.assertEqual(providers[0]["execution_mode"], "live_zapier_mcp")
        self.assertIsNone(providers[0]["action_path"])


class ActivationOverviewTests(unittest.TestCase):
    def test_upgrade_gates_do_not_block_local_execution(self) -> None:
        overview = _mesh_activation_overview(
            lanes=[
                {"id": "execution", "label": "محرك الوكلاء", "status": "ready"},
                {"id": "trading", "label": "وكيل التداول", "status": "ready"},
            ],
            attention=[
                {
                    "id": "zapier_mcp",
                    "name": "Zapier MCP",
                    "status": "partial",
                    "action_path": "/api/agent/oauth/zapier/start",
                },
                {
                    "id": "supabase",
                    "name": "Supabase",
                    "status": "needs_setup",
                    "action_path": "/api/agent/settings/supabase",
                },
                {
                    "id": "broker_testnet",
                    "name": "Broker Testnet",
                    "status": "needs_operator",
                    "action_path": "/api/agent/settings/broker_testnet",
                },
            ],
            tool_count=42,
            local_capabilities={"ready_count": 8, "capability_count": 10},
            inventory={"zapier_app_count": 22, "zapier_action_count": 126},
            agent_providers=[],
        )

        self.assertTrue(overview["executable_now"])
        self.assertEqual(overview["blocking_action_count"], 0)
        self.assertEqual(overview["upgrade_action_count"], 3)
        self.assertTrue(
            all(not action["blocks_local_execution"] for action in overview["upgrade_actions"])
        )

    def test_blocking_gate_disables_executable_now(self) -> None:
        overview = _mesh_activation_overview(
            lanes=[{"id": "execution", "label": "محرك الوكلاء", "status": "ready"}],
            attention=[
                {
                    "id": "openrouter",
                    "name": "OpenRouter",
                    "status": "needs_setup",
                    "action_path": "/api/agent/settings/openrouter",
                },
            ],
            tool_count=42,
            local_capabilities={"ready_count": 8, "capability_count": 10},
            inventory={"zapier_app_count": 22, "zapier_action_count": 126},
            agent_providers=[],
        )

        self.assertFalse(overview["executable_now"])
        self.assertEqual(overview["blocking_action_count"], 1)
        self.assertEqual(overview["blocking_actions"][0]["id"], "openrouter")
        self.assertTrue(overview["blocking_actions"][0]["blocks_local_execution"])


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

    def test_expired_zapier_readiness_uses_fresh_oauth_path(self) -> None:
        self.config.zapier_mcp_token_path.write_text(
            json.dumps(
                {
                    "access_token": "expired-access-token",
                    "refresh_token": "stale-refresh-token",
                    "expires_at": time.time() - 10,
                    "last_refresh_error": "http_400",
                    "last_refresh_status_code": 400,
                }
            ),
            encoding="utf-8",
        )
        readiness = build_integration_readiness(
            self.config,
            connectors=[],
            inventory={
                "available": True,
                "zapier_mcp_status": {"inventory": "active"},
                "zapier_apps": [{"app": "Gmail"}],
                "zapier_action_count": 3,
            },
            local_capabilities={"capabilities": []},
        )
        zapier = next(
            item for item in readiness["integrations"] if item["id"] == "zapier_mcp"
        )

        self.assertEqual(zapier["status"], "partial")
        self.assertEqual(zapier["action_path"], "/api/agent/oauth/zapier/start?force=1")
        self.assertEqual(zapier["action_label"], "إعادة ربط كاملة")
        self.assertTrue(zapier["details"]["needs_reconnect"])
        self.assertFalse(zapier["details"]["direct_live_available"])

    def test_local_api_vertical_slice_and_approval_controls(self) -> None:
        health = requests.get(f"{self.base_url}/healthz", headers=self.headers, timeout=5)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["mode"], "local_sqlite")
        api_health = requests.get(
            f"{self.base_url}/api/agent/health",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(api_health.status_code, 200)
        self.assertEqual(api_health.json()["worker_id"], health.json()["worker_id"])
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
        first_zapier_app = connectors["inventory"]["zapier_apps"][0]["app"]
        zapier_catalog_response = requests.get(
            f"{self.base_url}/api/agent/zapier/catalog?app={first_zapier_app}",
            headers=self.headers,
            timeout=15,
        )
        self.assertEqual(zapier_catalog_response.status_code, 200)
        self.assertNotIn("secret-token", zapier_catalog_response.text)
        zapier_catalog = zapier_catalog_response.json()
        self.assertEqual(zapier_catalog["provider"], "Zapier MCP")
        self.assertIn("action_count", zapier_catalog)
        capabilities_response = requests.get(
            f"{self.base_url}/api/agent/capabilities",
            headers=self.headers,
            timeout=15,
        )
        self.assertEqual(capabilities_response.status_code, 200)
        capability_probe = capabilities_response.json()["capabilities"]
        self.assertEqual(capability_probe["capability_count"], 10)
        self.assertGreaterEqual(capability_probe["ready_count"], 1)
        tools_response = requests.get(
            f"{self.base_url}/api/agent/tools",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(tools_response.status_code, 200)
        tools_by_name = {item["name"]: item for item in tools_response.json()["tools"]}
        self.assertIn("agent_mesh_audit", tools_by_name)
        self.assertEqual(tools_by_name["agent_mesh_audit"]["category"], "runtime")
        self.assertFalse(tools_by_name["agent_mesh_audit"]["requires_approval"])

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
        self.assertEqual(
            integration_by_id["local_execution_mesh"]["settings_path"],
            "/api/agent/settings/local_execution_mesh",
        )
        self.assertEqual(
            integration_by_id["local_execution_mesh"]["settings_label"],
            "إعداد جسور الوكلاء",
        )
        self.assertEqual(
            integration_by_id["huggingface_local"]["settings_path"],
            "/api/agent/settings/huggingface_local",
        )
        self.assertFalse(
            integration_by_id["huggingface_local"]["details"]["planning_enabled"]
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
        if integration_by_id["github_codespaces"]["status"] != "ready":
            self.assertEqual(
                integration_by_id["github_codespaces"]["action_path"],
                "/api/agent/oauth/github/codespaces/start",
            )
            self.assertEqual(
                integration_by_id["github_codespaces"]["action_label"],
                "تفويض GitHub Codespaces",
            )
        self.assertGreaterEqual(
            integration_by_id["zapier_mcp"]["details"]["app_count"],
            20,
        )
        self.assertEqual(
            integration_by_id["zapier_mcp"]["task_prompt"].splitlines()[0],
            "integration probe: zapier_mcp",
        )
        self.assertEqual(
            integration_by_id["openrouter"]["task_prompt"].splitlines()[0],
            "integration probe: openrouter",
        )
        self.assertEqual(
            integration_by_id["broker_testnet"]["status"],
            "needs_operator",
        )
        self.assertFalse(
            integration_by_id["broker_testnet"]["details"]["live_execution_enabled"]
        )
        mesh_response = requests.get(
            f"{self.base_url}/api/agent/mesh/summary",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(mesh_response.status_code, 200)
        self.assertNotIn("local-api-test-bridge-token", mesh_response.text)
        mesh_summary = mesh_response.json()
        self.assertEqual(mesh_summary["mode"], "agent_mesh_status_v1")
        self.assertIn("ready_to_execute", mesh_summary)
        self.assertGreaterEqual(mesh_summary["summary"]["tool_count"], 20)
        self.assertEqual(
            {lane["id"] for lane in mesh_summary["lanes"]},
            {"execution", "trading", "bug_bounty", "knowledge", "tool_bridge"},
        )
        self.assertIn(
            "agent mesh execute:",
            mesh_summary["quick_actions"][0]["prompt"],
        )
        quick_action_by_id = {
            action["id"]: action for action in mesh_summary["quick_actions"]
        }
        self.assertIn(
            "knowledge execution mission:",
            quick_action_by_id["learn_and_execute"]["prompt"],
        )
        self.assertIn(
            "FATHIYA_ACTIVATION_SWEEP_V1",
            quick_action_by_id["activate_tools"]["prompt"],
        )
        self.assertIn(
            "Zapier action: Manus / Get Tasks",
            quick_action_by_id["verify_manus_zapier_read"]["prompt"],
        )
        self.assertIn(
            "Zapier action: Gmail / New Email Matching Search",
            quick_action_by_id["verify_gmail_zapier_read"]["prompt"],
        )
        self.assertIn(
            "Zapier action preflight: Cursor / Find Agent Status",
            quick_action_by_id["prepare_cursor_zapier_read"]["prompt"],
        )
        self.assertIn(
            "agent mesh execute:",
            quick_action_by_id["activate_tools"]["prompt"],
        )
        activation_overview = mesh_summary["activation_overview"]
        self.assertEqual(activation_overview["mode"], "agent_activation_overview_v1")
        self.assertGreaterEqual(activation_overview["safe_tool_count"], 20)
        self.assertGreaterEqual(activation_overview["ready_lane_count"], 1)
        self.assertGreaterEqual(mesh_summary["summary"]["agent_provider_count"], 2)
        self.assertGreaterEqual(mesh_summary["summary"]["connected_app_count"], 5)
        provider_by_app = {
            provider["app"]: provider
            for provider in mesh_summary["agent_providers"]
        }
        zapier_app_names = {
            app["app"]
            for app in mesh_summary["zapier_apps"]
        }
        self.assertIn("GitHub", zapier_app_names)
        self.assertIn("Gmail", zapier_app_names)
        self.assertIn("Manus", provider_by_app)
        self.assertIn("Cursor", provider_by_app)
        self.assertEqual(provider_by_app["Manus"]["status"], "inventory_only")
        self.assertEqual(
            provider_by_app["Cursor"]["execution_mode"],
            "inventory_only_until_oauth",
        )
        self.assertGreaterEqual(
            activation_overview["agent_provider_write_action_count"],
            1,
        )
        self.assertIn(
            "Manus",
            {provider["app"] for provider in activation_overview["agent_providers"]},
        )
        self.assertIn("تشغيل فتحية الآن", activation_overview["default_action"]["label"])
        self.assertTrue(
            any(
                action["action_type"] in {"oauth", "settings"}
                for action in activation_overview["operator_actions"]
            )
        )
        self.assertTrue(mesh_summary["policy"]["automatic_internal_execution"])
        command_center_response = requests.get(
            f"{self.base_url}/api/agent/command-center",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(command_center_response.status_code, 200)
        self.assertNotIn("local-api-test-bridge-token", command_center_response.text)
        command_center = command_center_response.json()
        self.assertEqual(command_center["mode"], "fathiya_command_center_v1")
        self.assertTrue(command_center["secret_safe"])
        self.assertGreaterEqual(command_center["summary"]["command_count"], 5)
        self.assertGreaterEqual(command_center["summary"]["command_group_count"], 5)
        group_by_id = {
            group["id"]: group for group in command_center["command_groups"]
        }
        for group_id in {
            "execution",
            "trading",
            "bug_bounty",
            "knowledge",
            "tools",
            "connected_apps",
        }:
            self.assertIn(group_id, group_by_id)
            self.assertGreaterEqual(group_by_id[group_id]["command_count"], 1)
        command_by_id = {
            command["id"]: command for command in command_center["commands"]
        }
        self.assertIn("execute_mesh", command_by_id)
        self.assertIn("verify_production_site", command_by_id)
        self.assertIn("verify_github_zapier_read", command_by_id)
        self.assertIn("verify_manus_zapier_read", command_by_id)
        self.assertIn("verify_gmail_zapier_read", command_by_id)
        self.assertIn("prepare_cursor_zapier_read", command_by_id)
        self.assertIn("lane_trading", command_by_id)
        self.assertIn("lane_bug_bounty", command_by_id)
        self.assertIn("agent_provider_manus", command_by_id)
        self.assertIn("agent_provider_cursor", command_by_id)
        self.assertIn("connected_app_github", command_by_id)
        self.assertIn("connected_app_gmail", command_by_id)
        self.assertEqual(command_by_id["execute_mesh"]["mode"], "execution")
        self.assertEqual(command_by_id["execute_mesh"]["group"], "محرك الوكلاء")
        self.assertEqual(command_by_id["lane_trading"]["mode"], "trading")
        self.assertEqual(command_by_id["lane_bug_bounty"]["mode"], "bug_bounty")
        self.assertEqual(command_by_id["verify_production_site"]["mode"], "tools")
        self.assertEqual(command_by_id["verify_gmail_zapier_read"]["mode"], "tools")
        self.assertEqual(command_by_id["agent_provider_cursor"]["mode"], "connected_apps")
        self.assertEqual(command_by_id["connected_app_gmail"]["mode"], "connected_apps")
        self.assertIn(
            "agent mesh execute:",
            command_by_id["execute_mesh"]["prompt"],
        )
        self.assertIn(
            "production site audit:",
            command_by_id["verify_production_site"]["prompt"],
        )
        self.assertIn(
            "Zapier action: GitHub / Find Repository",
            command_by_id["verify_github_zapier_read"]["prompt"],
        )
        self.assertIn(
            '"owner":"fathya-core"',
            command_by_id["verify_github_zapier_read"]["prompt"],
        )
        self.assertIn(
            "Zapier action: Manus / Get Tasks",
            command_by_id["verify_manus_zapier_read"]["prompt"],
        )
        self.assertIn(
            '"query":"from:(openrouter.ai)',
            command_by_id["verify_gmail_zapier_read"]["prompt"],
        )
        self.assertIn(
            "Zapier action preflight: Cursor / Find Agent Status",
            command_by_id["prepare_cursor_zapier_read"]["prompt"],
        )
        self.assertEqual(command_by_id["agent_provider_manus"]["source"], "agent_provider")
        self.assertEqual(command_by_id["connected_app_github"]["source"], "connected_app")
        self.assertIn(
            "prepare provider action: Manus",
            command_by_id["agent_provider_manus"]["prompt"],
        )
        self.assertIn(
            "action: Create Task",
            command_by_id["agent_provider_manus"]["prompt"],
        )
        self.assertIn(
            "connected app catalog: GitHub",
            command_by_id["connected_app_github"]["prompt"],
        )
        self.assertIn(
            "FATHIYA_CONNECTED_APP_COMMAND_V1",
            command_by_id["connected_app_gmail"]["prompt"],
        )
        self.assertIn(
            "approval_gated_action_count:",
            command_by_id["agent_provider_cursor"]["prompt"],
        )
        self.assertIn(
            "action: Launch Agent",
            command_by_id["agent_provider_cursor"]["prompt"],
        )
        self.assertIn(
            "https://github.com/fathya-core/fathiya-core",
            command_by_id["agent_provider_cursor"]["prompt"],
        )
        self.assertIn(
            "/api/agent/command-center/run",
            command_center["powershell"]["run_execute_mesh"],
        )
        command_run = requests.post(
            f"{self.base_url}/api/agent/command-center/run",
            headers=self.headers,
            json={"command_id": "execute_mesh"},
            timeout=5,
        )
        self.assertEqual(command_run.status_code, 201)
        command_task = command_run.json()["task"]
        self.assertEqual(command_task["status"], "queued")
        self.assertEqual(command_run.json()["command"]["id"], "execute_mesh")
        cancel_command_task = requests.post(
            f"{self.base_url}/api/agent/tasks/{command_task['id']}/cancel",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(cancel_command_task.status_code, 200)
        self.assertEqual(cancel_command_task.json()["task"]["status"], "canceled")
        github_read_run = requests.post(
            f"{self.base_url}/api/agent/command-center/run",
            headers=self.headers,
            json={"command_id": "verify_github_zapier_read"},
            timeout=5,
        )
        self.assertEqual(github_read_run.status_code, 201)
        github_read_task = github_read_run.json()["task"]
        self.assertEqual(github_read_task["status"], "queued")
        self.assertEqual(github_read_run.json()["command"]["id"], "verify_github_zapier_read")
        self.assertIn(
            "Zapier action: GitHub / Find Repository",
            github_read_run.json()["command"]["prompt"],
        )
        cancel_github_read_task = requests.post(
            f"{self.base_url}/api/agent/tasks/{github_read_task['id']}/cancel",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(cancel_github_read_task.status_code, 200)
        self.assertEqual(cancel_github_read_task.json()["task"]["status"], "canceled")
        manus_read_run = requests.post(
            f"{self.base_url}/api/agent/command-center/run",
            headers=self.headers,
            json={"command_id": "verify_manus_zapier_read"},
            timeout=5,
        )
        self.assertEqual(manus_read_run.status_code, 201)
        manus_read_task = manus_read_run.json()["task"]
        self.assertEqual(manus_read_task["status"], "queued")
        self.assertEqual(manus_read_run.json()["command"]["id"], "verify_manus_zapier_read")
        self.assertIn(
            "Zapier action: Manus / Get Tasks",
            manus_read_run.json()["command"]["prompt"],
        )
        cancel_manus_read_task = requests.post(
            f"{self.base_url}/api/agent/tasks/{manus_read_task['id']}/cancel",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(cancel_manus_read_task.status_code, 200)
        self.assertEqual(cancel_manus_read_task.json()["task"]["status"], "canceled")
        connected_app_run = requests.post(
            f"{self.base_url}/api/agent/command-center/run",
            headers=self.headers,
            json={"command_id": "connected_app_github"},
            timeout=5,
        )
        self.assertEqual(connected_app_run.status_code, 201)
        connected_app_task = connected_app_run.json()["task"]
        self.assertEqual(connected_app_task["status"], "queued")
        self.assertEqual(connected_app_run.json()["command"]["id"], "connected_app_github")
        cancel_connected_app_task = requests.post(
            f"{self.base_url}/api/agent/tasks/{connected_app_task['id']}/cancel",
            headers=self.headers,
            timeout=5,
        )
        self.assertEqual(cancel_connected_app_task.status_code, 200)
        self.assertEqual(cancel_connected_app_task.json()["task"]["status"], "canceled")
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
        settings_by_id = {
            item["id"]: item for item in settings_response.json()["groups"]
        }
        self.assertIn("huggingface_local", settings_by_id)
        local_field_names = {
            field["name"] for field in settings_by_id["huggingface_local"]["fields"]
        }
        self.assertIn("FATHIYA_ENABLE_LOCAL_PLANNING", local_field_names)
        self.assertIn("local_execution_mesh", settings_by_id)
        mesh_setting_fields = {
            field["name"] for field in settings_by_id["local_execution_mesh"]["fields"]
        }
        self.assertEqual(
            {
                "FATHIYA_ZAPIER_WEBHOOK_URL",
                "FATHIYA_N8N_WEBHOOK_URL",
            },
            mesh_setting_fields,
        )

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
        zapier_diagnostics_response = requests.get(
            f"{self.base_url}/api/agent/oauth/zapier/diagnostics",
            headers=self.headers,
            timeout=15,
        )
        self.assertEqual(zapier_diagnostics_response.status_code, 200)
        self.assertNotIn("access_token", zapier_diagnostics_response.text)
        self.assertNotIn("refresh_token", zapier_diagnostics_response.text)
        self.assertNotIn("client_secret", zapier_diagnostics_response.text)
        zapier_diagnostics = zapier_diagnostics_response.json()["zapier_mcp"]
        self.assertEqual(
            zapier_diagnostics["mode"],
            "zapier_mcp_activation_diagnostics_v1",
        )
        self.assertTrue(zapier_diagnostics["secret_safe"])
        self.assertIn(
            zapier_diagnostics["activation_state"],
            {"inventory_only", "not_connected", "reconnect_required", "live"},
        )
        self.assertEqual(
            zapier_diagnostics["start_path"],
            "/api/agent/oauth/zapier/start",
        )
        self.assertEqual(
            zapier_diagnostics["fresh_start_path"],
            "/api/agent/oauth/zapier/start?force=1",
        )
        self.assertIn(
            "/api/agent/oauth/zapier/callback",
            zapier_diagnostics["callback_url"],
        )
        self.assertGreaterEqual(zapier_diagnostics["app_count"], 20)
        provider_names = {
            provider["app"] for provider in zapier_diagnostics["agent_providers"]
        }
        self.assertIn("Manus", provider_names)
        self.assertIn("Cursor", provider_names)
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
        self.assertFalse(start_oauth.call_args.kwargs.get("force_new", False))

        with patch.object(
            self.server.tools.zapier,
            "start_oauth",
            return_value="https://mcp.zapier.com/oauth/authorize?fresh=1",
        ) as fresh_start_oauth:
            fresh_oauth_start = requests.get(
                f"{self.base_url}/api/agent/oauth/zapier/start",
                headers=self.headers,
                params={"return_to": f"{self.base_url}/agent-tasks", "force": "1"},
                allow_redirects=False,
                timeout=5,
            )
        self.assertEqual(fresh_oauth_start.status_code, 302)
        self.assertEqual(
            fresh_oauth_start.headers["Location"],
            "https://mcp.zapier.com/oauth/authorize?fresh=1",
        )
        self.assertTrue(fresh_start_oauth.call_args.kwargs["force_new"])

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
        self.assertEqual(detail["task"]["receipt_count"], 1)
        self.assertEqual(
            detail["task"]["latest_receipt_id"],
            detail["receipts"][0]["receipt_id"],
        )
        task_list = requests.get(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            timeout=5,
        ).json()["tasks"]
        listed_task = next(item for item in task_list if item["id"] == task["id"])
        self.assertEqual(listed_task["latest_receipt_id"], detail["receipts"][0]["receipt_id"])

        integration_probe_task = requests.post(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            json={
                "title": "فحص اتصال: Zapier MCP",
                "prompt": integration_by_id["zapier_mcp"]["task_prompt"],
            },
            timeout=5,
        ).json()["task"]
        self.assertEqual(integration_probe_task["status"], "queued")
        AgentWorker(self.config, self.store, tools=self.server.tools).start(once=True)
        integration_probe_detail = requests.get(
            f"{self.base_url}/api/agent/tasks/{integration_probe_task['id']}",
            headers=self.headers,
            timeout=5,
        ).json()
        self.assertEqual(integration_probe_detail["task"]["status"], "completed")
        self.assertEqual(len(integration_probe_detail["receipts"]), 1)
        integration_probe_result = integration_probe_detail["task"]["result"]["tool_results"][0][
            "result"
        ]
        self.assertEqual(integration_probe_result["tool"], "integration_probe")
        self.assertEqual(integration_probe_result["integration_id"], "zapier_mcp")
        self.assertTrue(integration_probe_result["secret_safe"])
        self.assertNotIn("selected_api", str(integration_probe_detail))

        mesh_task = requests.post(
            f"{self.base_url}/api/agent/tasks",
            headers=self.headers,
            json={
                "title": "مسح شبكة الوكلاء",
                "prompt": (
                    "agent mesh audit:\n"
                    "استكشف كل الأدوات والوكلاء والحسابات محليًا، "
                    "وتحقق من وكيل التداول الأساسي ضمن المسح."
                ),
            },
            timeout=5,
        ).json()["task"]
        self.assertEqual(mesh_task["status"], "queued")
        AgentWorker(self.config, self.store, tools=self.server.tools).start(once=True)
        mesh_detail = requests.get(
            f"{self.base_url}/api/agent/tasks/{mesh_task['id']}",
            headers=self.headers,
            timeout=5,
        ).json()
        self.assertEqual(mesh_detail["task"]["status"], "completed")
        self.assertEqual(len(mesh_detail["receipts"]), 1)
        mesh_result = mesh_detail["task"]["result"]["tool_results"][0]["result"]
        self.assertEqual(mesh_result["tool"], "agent_mesh_audit")
        self.assertTrue(mesh_result["secret_safe"])
        self.assertGreaterEqual(mesh_result["summary"]["tool_count"], 20)
        self.assertGreaterEqual(mesh_result["summary"]["zapier_app_count"], 20)
        self.assertIn("trading_symbol", mesh_result["summary"])
        self.assertGreaterEqual(len(mesh_result["next_actions"]), 1)
        mesh_actions = {action["id"]: action for action in mesh_result["next_actions"]}
        self.assertEqual(
            mesh_actions["configure_agent_bridges"]["ui_action"],
            "settings",
        )
        self.assertEqual(
            mesh_actions["configure_agent_bridges"]["settings_group"],
            "local_execution_mesh",
        )
        self.assertIn("مسح شبكة الوكلاء", mesh_detail["task"]["result"]["synthesis"])
        self.assertNotIn("local-api-test-bridge-token", str(mesh_detail))

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

        strategy_refresh = requests.post(
            f"{self.base_url}/api/agent/trading/strategy-refresh",
            headers=self.headers,
            timeout=5,
        ).json()
        self.assertTrue(strategy_refresh["strategy"]["fallback"])
        self.assertEqual(strategy_refresh["strategy"]["advisory"]["action"], "hold")
        self.assertFalse(strategy_refresh["strategy"]["live_execution_enabled"])
        self.assertFalse(
            strategy_refresh["trading"]["strategy_advisory_policy"]["can_originate_orders"]
        )

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

    def test_github_codespaces_oauth_uses_login_when_gh_is_not_authenticated(self) -> None:
        process = Mock()
        process.wait.return_value = 0
        auth_status = Mock()
        auth_status.returncode = 1

        with (
            patch("fathiya_runtime.local_api.shutil.which", return_value="gh.cmd"),
            patch("fathiya_runtime.local_api.subprocess.run", return_value=auth_status),
            patch("fathiya_runtime.local_api.subprocess.Popen", return_value=process) as popen,
        ):
            result = _run_github_codespaces_scope_refresh()

        command = popen.call_args.args[0]
        self.assertTrue(result["ok"])
        self.assertEqual(
            result["command"],
            "gh auth login -h github.com -p https -s repo,workflow,read:org,gist,codespace -w",
        )
        self.assertIn("login", command)
        self.assertIn("codespace", command[-2])

    def test_github_codespaces_oauth_uses_refresh_when_gh_is_authenticated(self) -> None:
        process = Mock()
        process.wait.return_value = 0
        auth_status = Mock()
        auth_status.returncode = 0

        with (
            patch("fathiya_runtime.local_api.shutil.which", return_value="gh.cmd"),
            patch("fathiya_runtime.local_api.subprocess.run", return_value=auth_status),
            patch("fathiya_runtime.local_api.subprocess.Popen", return_value=process) as popen,
        ):
            result = _run_github_codespaces_scope_refresh()

        command = popen.call_args.args[0]
        self.assertTrue(result["ok"])
        self.assertEqual(result["command"], "gh auth refresh -h github.com -s codespace")
        self.assertIn("refresh", command)
        self.assertIn("codespace", command)


if __name__ == "__main__":
    unittest.main()
