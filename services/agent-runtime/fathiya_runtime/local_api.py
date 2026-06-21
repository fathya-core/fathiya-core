from __future__ import annotations

import hmac
import json
import re
import shutil
import subprocess
import threading
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .config import RuntimeConfig
from .integrations import build_integration_readiness
from .knowledge_watcher import KnowledgeIntakeWatcher
from .knowledge_mission import operator_request
from .local_settings import LocalSettingsStore
from .store import TaskStore, now_iso
from .tools import ToolExecutionError, ToolExecutor
from .trading import PaperTradingAgent
from .worker import AgentWorker


LOCAL_ORIGIN = re.compile(r"^https?://(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?$")
TASK_PATH = re.compile(
    r"^/api/agent/tasks/(?P<task_id>[0-9a-f-]{36})(?:/(?P<action>approve|cancel))?$",
    re.IGNORECASE,
)
CONNECTOR_DISPATCH_PATH = "/api/agent/connector-dispatch"
TRADING_PATH = re.compile(
    r"^/api/agent/trading(?:/(?P<action>status|receipts|start|stop|tick|strategy-refresh))?$",
    re.IGNORECASE,
)
INTAKE_PATH = re.compile(
    r"^/api/agent/intake(?:/(?P<action>status|scan|start|stop))?$",
    re.IGNORECASE,
)
SETTINGS_PATH = re.compile(
    r"^/api/agent/settings(?:/(?P<group>[a-z0-9_-]+))?$",
    re.IGNORECASE,
)
INTEGRATION_PROBE_PATH = re.compile(
    r"^/api/agent/integrations/(?P<integration_id>[a-z0-9_-]+)/probe$",
    re.IGNORECASE,
)
COMMAND_CENTER_RUN_PATH = "/api/agent/command-center/run"
COMMAND_CENTER_CONNECTED_APP_PRIORITY = (
    "GitHub",
    "Gmail",
    "Microsoft Outlook",
    "Zapier Tables",
    "MCP Client by Zapier",
    "RSS by Zapier",
    "Web Parser by Zapier",
    "Zapier Manager",
    "Files By Zapier",
)

def _visible_connector_profile(profile: dict[str, Any]) -> bool:
    return bool(
        str(profile.get("name") or profile.get("provider") or profile.get("description") or "").strip()
    )


class LocalAgentHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        config: RuntimeConfig,
        store: TaskStore,
    ):
        if address[0] not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The local agent API must bind to a loopback address")
        super().__init__(address, LocalAgentRequestHandler)
        self.config = config
        self.store = store
        self.trading = PaperTradingAgent.from_config(config)
        self.tools = ToolExecutor(config, trading_agent=self.trading)
        self.intake = KnowledgeIntakeWatcher(config, store)
        self.settings = LocalSettingsStore(config.local_settings_path)
        self.worker: AgentWorker | None = None
        self.worker_thread: threading.Thread | None = None

    def reload_runtime_config(self) -> RuntimeConfig:
        config = RuntimeConfig.load()
        tools = ToolExecutor(config, trading_agent=self.trading)
        tools.zapier.oauth.pending = self.tools.zapier.oauth.pending
        if self.worker:
            self.worker.reload_config(config, tools)
        self.config = config
        self.tools = tools
        return config

    def server_close(self) -> None:
        self.intake.stop()
        self.trading.stop()
        super().server_close()


class LocalAgentRequestHandler(BaseHTTPRequestHandler):
    server: LocalAgentHTTPServer
    protocol_version = "HTTP/1.1"

    def do_OPTIONS(self) -> None:
        if not self._origin_allowed():
            return self._send_error(HTTPStatus.FORBIDDEN, "Origin is not allowed")
        self._send_json({}, HTTPStatus.NO_CONTENT)

    def do_GET(self) -> None:
        if not self._origin_allowed():
            return self._send_error(HTTPStatus.FORBIDDEN, "Origin is not allowed")
        parsed_request = urlparse(self.path)
        path = parsed_request.path.rstrip("/") or "/"
        if path == "/api/agent/oauth/zapier/status":
            return self._send_json({"zapier_mcp": self.server.tools.zapier.status()})
        if path == "/api/agent/oauth/zapier/diagnostics":
            query = parse_qs(parsed_request.query)
            return_to = _safe_operator_return_to(
                str(query.get("return_to", [""])[0])
                or str(self.headers.get("Referer") or ""),
                self.server.config,
            )
            return self._send_json(
                {
                    "zapier_mcp": _zapier_diagnostics_payload(
                        self.server,
                        return_to=return_to,
                    )
                }
            )
        if path == "/api/agent/oauth/github/codespaces/start":
            query = parse_qs(parsed_request.query)
            return_to = _safe_operator_return_to(
                str(query.get("return_to", [""])[0])
                or str(self.headers.get("Referer") or ""),
                self.server.config,
            )
            auth_result = _run_github_codespaces_scope_refresh()
            return self._send_redirect(
                _append_query(
                    return_to,
                    {
                        "integration": "github_codespaces",
                        "status": "connected" if auth_result["ok"] else "auth_failed",
                    },
                )
            )
        if path == "/api/agent/oauth/zapier/start":
            query = parse_qs(parsed_request.query)
            force_new = str(query.get("force", [""])[0]).casefold() in {
                "1",
                "true",
                "yes",
                "fresh",
            }
            return_to = _safe_operator_return_to(
                str(query.get("return_to", [""])[0])
                or str(self.headers.get("Referer") or ""),
                self.server.config,
            )
            callback_url = (
                f"http://127.0.0.1:{self.server.server_address[1]}"
                "/api/agent/oauth/zapier/callback"
            )
            try:
                authorization_url = self.server.tools.zapier.start_oauth(
                    callback_url,
                    return_to,
                    force_new=force_new,
                )
            except Exception as exc:
                return self._send_error(
                    HTTPStatus.BAD_GATEWAY,
                    f"Zapier OAuth start failed: {type(exc).__name__}",
                )
            return self._send_redirect(authorization_url)
        if path == "/api/agent/oauth/zapier/callback":
            query = parse_qs(parsed_request.query)
            code = str(query.get("code", [""])[0])
            state = str(query.get("state", [""])[0])
            if not code or not state:
                return self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Zapier OAuth callback requires code and state",
                )
            try:
                return_to = self.server.tools.zapier.complete_oauth(code, state)
            except Exception as exc:
                return self._send_error(
                    HTTPStatus.BAD_GATEWAY,
                    f"Zapier OAuth callback failed: {type(exc).__name__}",
                )
            return self._send_redirect(
                _append_query(return_to, {"integration": "zapier_mcp", "status": "connected"})
            )
        if path in {"/healthz", "/api/agent/health"}:
            return self._send_json(_runtime_health_payload(self.server))
        settings_match = SETTINGS_PATH.fullmatch(path)
        if settings_match:
            if settings_match.group("group"):
                return self._send_error(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    "Use POST to update a local settings group",
                )
            return self._send_json(
                {
                    **self.server.settings.status(),
                    "write_allowed": self._local_settings_write_allowed(),
                }
            )
        intake_match = INTAKE_PATH.fullmatch(path)
        if intake_match:
            action = intake_match.group("action") or "status"
            if action == "status":
                return self._send_json({"intake": self.server.intake.status()})
            return self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Use POST for this route")
        trading_match = TRADING_PATH.fullmatch(path)
        if trading_match:
            action = trading_match.group("action") or "status"
            if action == "receipts":
                return self._send_json({"receipts": self.server.trading.recent(50)})
            if action == "status":
                return self._send_json({"trading": self.server.trading.status()})
            return self._send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Use POST for this route")
        if path == "/api/agent/tools":
            return self._send_json({"tools": self.server.tools.catalog()})
        if path == "/api/agent/capabilities":
            return self._send_json(
                {
                    "capabilities": self.server.tools.execute(
                        "local_capability_inventory",
                        "افحص شبكة التنفيذ المحلية",
                    )
                }
            )
        if path == "/api/agent/zapier/catalog":
            query = parse_qs(parsed_request.query)
            app = str(query.get("app", [""])[0])
            refresh = str(query.get("refresh", [""])[0]).casefold() in {
                "1",
                "true",
                "yes",
            }
            return self._send_json(
                self.server.tools.execute(
                    "zapier_action_catalog",
                    "عرض كتالوج إجراءات Zapier MCP",
                    {"app": app, "refresh": refresh},
                )
            )
        if path == "/api/agent/zapier/action-details":
            query = parse_qs(parsed_request.query)
            app = str(query.get("app", [""])[0])
            action = str(query.get("action", [""])[0])
            if not app or not action:
                return self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "app and action query parameters are required",
                )
            return self._send_json(
                self.server.tools.execute(
                    "zapier_action_details",
                    "عرض حقول إجراء Zapier MCP",
                    {"app": app, "action": action},
                )
            )
        if path == "/api/agent/connectors":
            connectors = [
                connector
                for connector in self.server.tools.connector_catalog()
                if _visible_connector_profile(connector)
            ]
            bridge_profiles = [
                profile
                for profile in self.server.tools.bridge_dispatch_profiles()
                if _visible_connector_profile(profile)
            ]
            inventory = self.server.tools.execute(
                "connected_tool_inventory",
                "عرض مخزون الموصلات",
                {"quick": True},
            )
            return self._send_json(
                {
                    "connectors": connectors,
                    "configured_count": sum(
                        bool(connector.get("configured")) for connector in connectors
                    ),
                    "bridge": {
                        "configured": bool(
                            self.server.config.connector_dispatch_token
                        ),
                        "endpoint": CONNECTOR_DISPATCH_PATH,
                        "allowed_profile_count": len(bridge_profiles),
                        "ready_profile_count": sum(
                            bool(profile.get("configured")) for profile in bridge_profiles
                        ),
                        "allowed_profiles": [
                            profile["name"] for profile in bridge_profiles
                        ],
                    },
                    "inventory": inventory,
                }
            )
        if path == "/api/agent/integrations":
            readiness, _local_capabilities, _inventory = _build_readiness_snapshot(
                self.server,
            )
            return self._send_json(readiness)
        if path == "/api/agent/mesh/summary":
            readiness, local_capabilities, inventory = _build_readiness_snapshot(
                self.server,
            )
            return self._send_json(
                _build_agent_mesh_summary(
                    self.server,
                    readiness,
                    local_capabilities,
                    inventory,
                )
            )
        if path == "/api/agent/command-center":
            readiness, local_capabilities, inventory = _build_readiness_snapshot(
                self.server,
            )
            mesh = _build_agent_mesh_summary(
                self.server,
                readiness,
                local_capabilities,
                inventory,
            )
            return self._send_json(_build_command_center_payload(self.server, mesh))
        if path == "/api/agent/tasks":
            self.server.store.mark_stalled()
            return self._send_json({"tasks": self.server.store.list_tasks(50)})
        match = TASK_PATH.fullmatch(path)
        if match and not match.group("action"):
            self.server.store.mark_stalled()
            detail = self.server.store.get_detail(match.group("task_id"))
            if not detail:
                return self._send_error(HTTPStatus.NOT_FOUND, "Task not found")
            return self._send_json(detail)
        return self._send_error(HTTPStatus.NOT_FOUND, "Agent API route not found")

    def do_POST(self) -> None:
        if not self._origin_allowed():
            return self._send_error(HTTPStatus.FORBIDDEN, "Origin is not allowed")
        path = urlparse(self.path).path.rstrip("/") or "/"
        settings_match = SETTINGS_PATH.fullmatch(path)
        if settings_match and settings_match.group("group"):
            if not self._local_settings_write_allowed():
                return self._send_error(
                    HTTPStatus.FORBIDDEN,
                    "Local settings can only be changed from a loopback operator page",
                )
            try:
                body = self._json_body()
                result = self.server.settings.update_group(
                    settings_match.group("group"),
                    body.get("values", {}),
                    body.get("clear", []),
                )
                config = self.server.reload_runtime_config()
            except ValueError as exc:
                return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            except Exception as exc:
                return self._send_error(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    f"Local settings update failed: {type(exc).__name__}",
                )
            return self._send_json(
                {
                    **result,
                    "applied": True,
                    "active_store": config.store,
                    "write_allowed": True,
                }
            )
        intake_match = INTAKE_PATH.fullmatch(path)
        if intake_match and intake_match.group("action") in {"scan", "start", "stop"}:
            action = intake_match.group("action")
            if action == "scan":
                return self._send_json(self.server.intake.scan_once())
            if action == "start":
                return self._send_json({"intake": self.server.intake.start()})
            return self._send_json({"intake": self.server.intake.stop()})
        trading_match = TRADING_PATH.fullmatch(path)
        if trading_match and trading_match.group("action") in {
            "start",
            "stop",
            "tick",
            "strategy-refresh",
        }:
            try:
                action = trading_match.group("action")
                if action == "start":
                    return self._send_json({"trading": self.server.trading.start()})
                if action == "stop":
                    return self._send_json({"trading": self.server.trading.stop()})
                if action == "strategy-refresh":
                    result = self.server.tools.execute(
                        "trading_strategy_refresh",
                        "حدّث مستشار استراتيجية وكيل التداول",
                        {
                            "model_override": self.server.config.trading_advisory_model,
                            "model_timeout_seconds": (
                                self.server.config.trading_advisory_timeout_seconds
                            ),
                        },
                    )
                    return self._send_json(
                        {
                            "strategy": result,
                            "trading": self.server.trading.status(),
                        }
                    )
                return self._send_json({"cycle": self.server.trading.tick_once()})
            except RuntimeError as exc:
                return self._send_error(HTTPStatus.CONFLICT, str(exc))
            except Exception as exc:
                return self._send_error(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    f"Trading agent error: {type(exc).__name__}",
                )
        if path == CONNECTOR_DISPATCH_PATH:
            return self._dispatch_connector()
        if path == COMMAND_CENTER_RUN_PATH:
            return self._run_command_center_command()
        probe_match = INTEGRATION_PROBE_PATH.fullmatch(path)
        if probe_match:
            return self._probe_integration(probe_match.group("integration_id"))
        if path == "/api/agent/tasks":
            try:
                body = self._json_body()
            except ValueError as exc:
                return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            prompt = body.get("prompt")
            title = body.get("title")
            if not isinstance(prompt, str) or len(prompt.strip()) < 3:
                return self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Prompt must contain at least 3 characters",
                )
            prompt = prompt.strip()
            if len(prompt) > 20_000:
                return self._send_error(
                    HTTPStatus.BAD_REQUEST,
                    "Prompt exceeds 20,000 characters",
                )
            try:
                operator_prompt = operator_request(prompt)
                clean_title = (
                    title.strip()[:120]
                    if isinstance(title, str) and title.strip()
                    else " ".join(operator_prompt.split())[:120]
                )
                task = self.server.store.enqueue(clean_title, prompt, "local-operator")
            except ValueError as exc:
                return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
            return self._send_json({"task": task}, HTTPStatus.CREATED)

        match = TASK_PATH.fullmatch(path)
        if not match or not match.group("action"):
            return self._send_error(HTTPStatus.NOT_FOUND, "Agent API route not found")
        task = self.server.store.get_task(match.group("task_id"))
        if not task:
            return self._send_error(HTTPStatus.NOT_FOUND, "Task not found")
        if match.group("action") == "approve":
            if task["status"] != "awaiting_approval":
                return self._send_error(
                    HTTPStatus.CONFLICT,
                    "Task is not awaiting approval",
                )
            self.server.store.update_task(
                task["id"],
                status="queued",
                approval_state="approved",
                current_step="تمت الموافقة، بانتظار المشغّل المحلي",
                error_message=None,
                last_heartbeat_at=now_iso(),
            )
            self.server.store.add_event(
                task,
                "approved",
                "وافق المشغل المحلي على تنفيذ المهمة.",
                status="queued",
                step="approved",
                progress=task["progress"],
            )
            return self._send_json({"task": self.server.store.get_task(task["id"])})

        if task["status"] not in {"queued", "running", "awaiting_approval", "stalled"}:
            return self._send_error(HTTPStatus.CONFLICT, "Task cannot be canceled")
        self.server.store.update_task(
            task["id"],
            status="canceled",
            current_step="ألغيت بواسطة المشغل المحلي",
            completed_at=datetime.now(UTC).isoformat(),
        )
        self.server.store.add_event(
            task,
            "canceled",
            "ألغى المشغل المحلي المهمة.",
            status="canceled",
            step="canceled",
            progress=task["progress"],
        )
        return self._send_json({"task": self.server.store.get_task(task["id"])})

    def _run_command_center_command(self) -> None:
        try:
            body = self._json_body()
        except ValueError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
        command_id = str(body.get("command_id") or "").strip()
        if not command_id:
            return self._send_error(HTTPStatus.BAD_REQUEST, "command_id is required")
        readiness, local_capabilities, inventory = _build_readiness_snapshot(self.server)
        mesh = _build_agent_mesh_summary(
            self.server,
            readiness,
            local_capabilities,
            inventory,
        )
        center = _build_command_center_payload(self.server, mesh)
        command = next(
            (
                item
                for item in center.get("commands", [])
                if str(item.get("id") or "") == command_id
            ),
            None,
        )
        if not command:
            return self._send_error(HTTPStatus.NOT_FOUND, "Unknown command_id")
        prompt = str(command.get("prompt") or "").strip()
        if len(prompt) < 3:
            return self._send_error(
                HTTPStatus.CONFLICT,
                "Command is not executable because it has no prompt",
            )
        task = self.server.store.enqueue(
            str(command.get("title") or command.get("label") or command_id)[:120],
            prompt,
            "local-operator",
        )
        return self._send_json({"task": task, "command": command}, HTTPStatus.CREATED)

    def _probe_integration(self, integration_id: str) -> None:
        try:
            result = self.server.tools.integration_probe(integration_id)
        except ValueError:
            return self._send_error(HTTPStatus.NOT_FOUND, "Unknown integration probe")
        except Exception as exc:
            return self._send_json(
                {
                    "integration_id": integration_id,
                    "ok": False,
                    "status": "failed",
                    "summary": f"فشل اختبار الاتصال: {type(exc).__name__}",
                    "checked_at": now_iso(),
                    "secret_safe": True,
                    "action": "probe_failed",
                    "details": {"error_type": type(exc).__name__},
                },
                HTTPStatus.BAD_GATEWAY,
            )
        return self._send_json(result)

    def _dispatch_connector(self) -> None:
        expected_token = self.server.config.connector_dispatch_token
        if not expected_token:
            return self._send_error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "Connector dispatch bridge is not configured",
            )
        provided_token = self.headers.get("X-FATHIYA-Bridge-Token", "")
        if not provided_token or not hmac.compare_digest(provided_token, expected_token):
            return self._send_error(
                HTTPStatus.UNAUTHORIZED,
                "Connector dispatch authentication failed",
            )
        try:
            body = self._json_body()
        except ValueError as exc:
            return self._send_error(HTTPStatus.BAD_REQUEST, str(exc))

        task_id = str(body.get("task_id") or "").strip()
        profile_name = str(body.get("profile") or "").strip()
        if not TASK_PATH.fullmatch(f"/api/agent/tasks/{task_id}"):
            return self._send_error(HTTPStatus.BAD_REQUEST, "A valid task_id is required")
        task = self.server.store.get_task(task_id)
        if not task:
            return self._send_error(HTTPStatus.NOT_FOUND, "Task not found")
        upstream_receipt_id = str(body.get("receipt_id") or "")[:160]
        if not upstream_receipt_id:
            return self._send_error(
                HTTPStatus.BAD_REQUEST,
                "An upstream receipt_id is required for idempotent dispatch",
            )

        all_profiles = {
            profile["name"]: profile for profile in self.server.tools.connector_catalog()
        }
        profile = all_profiles.get(profile_name)
        if not profile:
            return self._send_error(HTTPStatus.BAD_REQUEST, "Unknown connector profile")
        if not profile.get("bridge_dispatch_allowed"):
            return self._send_error(
                HTTPStatus.FORBIDDEN,
                "Connector profile is not allowed through the n8n dispatch bridge",
            )
        if not profile.get("configured"):
            return self._send_error(
                HTTPStatus.CONFLICT,
                "Connector profile is not configured",
            )
        if body.get("dispatch_allowed") is not True or body.get("approval_state") != "approved":
            return self._send_error(
                HTTPStatus.CONFLICT,
                "Connector dispatch requires an approved n8n gate",
            )
        if profile.get("requires_approval") and task.get("approval_state") != "approved":
            return self._send_error(
                HTTPStatus.CONFLICT,
                "External connector dispatch requires task approval",
            )
        existing_receipt = _find_connector_dispatch_receipt(
            self.server.store.get_detail(task_id),
            profile_name,
            upstream_receipt_id,
        )
        if existing_receipt:
            evidence = existing_receipt.get("evidence")
            result = evidence.get("result", {}) if isinstance(evidence, dict) else {}
            duplicate_failed = existing_receipt.get("status") != "completed"
            return self._send_json(
                {
                    "accepted": not duplicate_failed,
                    "status": "duplicate_failed" if duplicate_failed else "duplicate",
                    "task_id": task_id,
                    "profile": profile_name,
                    "receipt_id": existing_receipt["receipt_id"],
                    "upstream_receipt_id": upstream_receipt_id,
                    "result": result,
                },
                HTTPStatus.BAD_GATEWAY if duplicate_failed else HTTPStatus.OK,
            )

        args: dict[str, Any] = {"profile": profile_name}
        if isinstance(body.get("payload"), dict):
            args["payload"] = body["payload"]
        if isinstance(body.get("query"), dict):
            args["query"] = body["query"]
        source = str(body.get("source") or "n8n-connector-gateway")[:120]

        try:
            result = self.server.tools.execute(
                "connector_profile",
                f"n8n approved dispatch for task {task_id}",
                args,
            )
            if not result.get("available") or result.get("executed") is False:
                raise ToolExecutionError("Connector dispatch did not complete", result)
            safe_result = _connector_result_evidence(result)
            receipt_id = self.server.store.add_receipt(
                task,
                "completed",
                f"اكتمل تسليم الموصل {profile_name} عبر جسر n8n.",
                {
                    "source": source,
                    "upstream_receipt_id": upstream_receipt_id,
                    "profile": profile_name,
                    "result": safe_result,
                },
            )
            self.server.store.add_event(
                task,
                "connector_dispatched",
                f"اكتمل تسليم الموصل {profile_name} عبر جسر n8n.",
                status=task["status"],
                step="connector_dispatch",
                progress=task["progress"],
                payload={
                    "profile": profile_name,
                    "receipt_id": receipt_id,
                    "upstream_receipt_id": upstream_receipt_id,
                    "result": safe_result,
                },
            )
            return self._send_json(
                {
                    "accepted": True,
                    "status": "dispatched",
                    "task_id": task_id,
                    "profile": profile_name,
                    "receipt_id": receipt_id,
                    "upstream_receipt_id": upstream_receipt_id,
                    "result": safe_result,
                }
            )
        except Exception as exc:
            raw_result = exc.result if isinstance(exc, ToolExecutionError) else {}
            safe_result = _connector_result_evidence(raw_result)
            receipt_id = self.server.store.add_receipt(
                task,
                "failed",
                f"فشل تسليم الموصل {profile_name} عبر جسر n8n.",
                {
                    "source": source,
                    "upstream_receipt_id": upstream_receipt_id,
                    "profile": profile_name,
                    "error_type": type(exc).__name__,
                    "result": safe_result,
                },
            )
            self.server.store.add_event(
                task,
                "connector_dispatch_failed",
                f"فشل تسليم الموصل {profile_name} عبر جسر n8n.",
                status=task["status"],
                step="connector_dispatch",
                progress=task["progress"],
                payload={
                    "profile": profile_name,
                    "receipt_id": receipt_id,
                    "upstream_receipt_id": upstream_receipt_id,
                    "error_type": type(exc).__name__,
                    "result": safe_result,
                },
            )
            return self._send_json(
                {
                    "accepted": False,
                    "status": "failed",
                    "task_id": task_id,
                    "profile": profile_name,
                    "receipt_id": receipt_id,
                    "upstream_receipt_id": upstream_receipt_id,
                    "result": safe_result,
                },
                HTTPStatus.BAD_GATEWAY,
            )

    def log_message(self, format: str, *args: Any) -> None:
        if (
            len(args) >= 2
            and str(args[0]).startswith(("GET ", "OPTIONS "))
            and str(args[1]) in {"200", "204"}
        ):
            return
        print(f"[local-api] {self.address_string()} {format % args}")

    def _origin_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return not origin or _operator_origin_allowed(origin, self.server.config)

    def _local_settings_write_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        return not origin or bool(LOCAL_ORIGIN.fullmatch(origin.rstrip("/")))

    def _json_body(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid Content-Length") from exc
        if length <= 0 or length > 64 * 1024:
            raise ValueError("JSON body must be between 1 byte and 64 KiB")
        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("Invalid JSON body") from exc
        if not isinstance(body, dict):
            raise ValueError("JSON body must be an object")
        return body

    def _send_error(self, status: HTTPStatus, message: str) -> None:
        self.close_connection = True
        self._send_json({"error": message}, status)

    def _send_json(
        self,
        payload: dict[str, Any],
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        body = b"" if status is HTTPStatus.NO_CONTENT else json.dumps(
            payload,
            ensure_ascii=False,
        ).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        if self.close_connection:
            self.send_header("Connection", "close")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, X-FATHIYA-Bridge-Token",
        )
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        origin = self.headers.get("Origin")
        if origin and _operator_origin_allowed(origin, self.server.config):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Vary", "Origin")
        self.end_headers()
        if body:
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass

    def _send_redirect(self, location: str) -> None:
        body = b""
        self.send_response(HTTPStatus.FOUND.value)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()


def _connector_result_evidence(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result.get(key)
        for key in (
            "tool",
            "profile",
            "provider",
            "method",
            "configured",
            "available",
            "executed",
            "execution_failed",
            "status_code",
            "error",
        )
        if key in result
    }


def _integration_probe(
    server: LocalAgentHTTPServer,
    integration_id: str,
) -> dict[str, Any]:
    checked_at = now_iso()
    if integration_id == "local_execution_mesh":
        result = server.tools.execute(
            "local_capability_inventory",
            "اختبر شبكة التنفيذ المحلية",
        )
        ready_count = int(result.get("ready_count") or 0)
        capability_count = int(result.get("capability_count") or 0)
        partial_count = int(result.get("partial_count") or 0)
        core_ready_count = int(result.get("core_ready_count") or ready_count)
        core_capability_count = int(result.get("core_capability_count") or capability_count)
        optional_attention_count = int(result.get("optional_attention_count") or 0)
        ok = bool(core_capability_count and core_ready_count == core_capability_count)
        return _probe_payload(
            integration_id,
            ok=ok,
            status="ready" if ok else "partial" if ready_count else "needs_setup",
            summary=(
                f"{core_ready_count} من {core_capability_count} بوابات التنفيذ الأساسية جاهزة"
                + (
                    f" و{optional_attention_count} اختيارية تحتاج انتباه."
                    if optional_attention_count
                    else "."
                )
            ),
            checked_at=checked_at,
            action="local_capability_inventory",
            details={
                "ready_count": ready_count,
                "partial_count": partial_count,
                "capability_count": capability_count,
                "core_ready_count": core_ready_count,
                "core_capability_count": core_capability_count,
                "optional_attention_count": optional_attention_count,
            },
        )
    if integration_id == "huggingface_local":
        retrieval = bool(server.config.enable_hf_retrieval)
        generation = bool(server.config.enable_local_generation)
        planning = bool(server.config.enable_local_planning)
        ok = retrieval or generation or planning
        return _probe_payload(
            integration_id,
            ok=ok,
            status="ready" if ok else "needs_setup",
            summary=(
                "النماذج المحلية مفعلة للاسترجاع أو التوليد أو التخطيط."
                if ok
                else "النماذج المحلية غير مفعلة في إعدادات المشغّل."
            ),
            checked_at=checked_at,
            action="configuration_check",
            details={
                "retrieval_enabled": retrieval,
                "generation_enabled": generation,
                "planning_enabled": planning,
                "retrieval_model": server.config.hf_model,
                "generation_model": server.config.local_model,
                "network_call": False,
            },
        )
    if integration_id == "openrouter":
        configured = bool(server.config.openrouter_api_key)
        return _probe_payload(
            integration_id,
            ok=configured,
            status="ready" if configured else "needs_setup",
            summary=(
                "مفتاح OpenRouter موجود محليًا؛ المكالمات الثقيلة جاهزة عند طلب الوكيل."
                if configured
                else "OpenRouter ينتظر مفتاحًا محليًا؛ لم تُجر مكالمة نموذج."
            ),
            checked_at=checked_at,
            action="configuration_check",
            details={
                "configured": configured,
                "model": server.config.openrouter_model,
                "model_candidates": list(server.config.openrouter_model_candidates),
                "research_model": server.config.openrouter_research_model,
                "safety_model": server.config.openrouter_safety_model,
                "trading_advisory_model": server.config.trading_advisory_model,
                "trading_advisory_model_candidates": list(
                    server.config.trading_advisory_model_candidates
                ),
                "fusion_policy": {
                    "invocation_modes": [
                        "direct_model_slug",
                        "server_tool_from_current_model",
                    ],
                    "enabled_for": [
                        "deep research",
                        "knowledge learning",
                        "source-grounded comparison",
                    ],
                    "not_default_for": ["coding agents", "general chat"],
                    "panel_limit": 8,
                    "web_search_default": True,
                },
                "free_model_routing": True,
                "network_call": False,
                "cost_incurred": False,
            },
        )
    if integration_id == "github_codespaces":
        result = server.tools.execute(
            "github_codespaces_inventory",
            "اختبر GitHub Codespaces المصادق",
            {"limit": 10},
        )
        available = bool(result.get("available"))
        installed = bool(result.get("installed"))
        codespace_count = int(result.get("codespace_count") or 0)
        active_count = int(result.get("active_codespace_count") or 0)
        return _probe_payload(
            integration_id,
            ok=available,
            status="ready" if available else "partial" if installed else "needs_setup",
            summary=(
                f"GitHub Codespaces متصل؛ {codespace_count} مساحة ظاهرة و{active_count} نشطة."
                if available
                else "GitHub CLI موجود ويحتاج scope codespace: gh auth refresh -h github.com -s codespace"
                if installed
                else "GitHub CLI غير مثبت أو غير ظاهر للمشغل المحلي."
            ),
            checked_at=checked_at,
            action="github_codespaces_inventory",
            details={
                "installed": installed,
                "authenticated": bool(result.get("authenticated")),
                "auth_state": result.get("auth_state"),
                "missing_scope": result.get("missing_scope"),
                "operator_action_required": bool(result.get("operator_action_required")),
                "codespace_count": codespace_count,
                "active_codespace_count": active_count,
                "execution_mode": result.get("execution_mode"),
                "required_scope": "codespace",
                "auth_command": result.get("auth_command")
                or "gh auth refresh -h github.com -s codespace",
                "requires_approval_for_remote_execution": True,
                "codespaces": result.get("codespaces", []),
                "error": result.get("error"),
            },
        )
    if integration_id == "supabase":
        configured = bool(
            server.config.supabase_url and server.config.supabase_service_role_key
        )
        active = configured and server.config.store == "supabase"
        return _probe_payload(
            integration_id,
            ok=active,
            status="ready" if active else "partial" if configured else "needs_setup",
            summary=(
                "Supabase مفعّل كقناة مهام حالية."
                if active
                else "بيانات Supabase موجودة، لكن المشغّل الحالي ما زال على SQLite."
                if configured
                else "Supabase ينتظر URL ومفتاح خدمة محلي."
            ),
            checked_at=checked_at,
            action="configuration_check",
            details={
                "configured": configured,
                "active_store": server.config.store,
                "network_call": False,
            },
        )
    if integration_id == "n8n_local":
        result = server.tools.execute(
            "connector_profile",
            "اختبر صحة خدمة n8n المحلية",
            {"profile": "n8n_health"},
        )
        ok = bool(result.get("available") and result.get("executed"))
        evidence = _connector_result_evidence(result)
        return _probe_payload(
            integration_id,
            ok=ok,
            status="ready" if ok else "partial",
            summary=(
                "n8n المحلي استجاب لفحص الصحة."
                if ok
                else "تعذر تأكيد استجابة n8n المحلي."
            ),
            checked_at=checked_at,
            action="connector_profile:n8n_health",
            details=evidence,
        )
    if integration_id == "kali_wsl":
        result = server.tools.execute(
            "kali_tool_inventory",
            "اختبر Kali WSL وأدوات الأمن المحلية",
        )
        found = result.get("found_commands")
        missing = result.get("missing_commands")
        found_commands = found if isinstance(found, list) else []
        missing_commands = missing if isinstance(missing, list) else []
        ok = bool(result.get("available") and not missing_commands)
        return _probe_payload(
            integration_id,
            ok=ok,
            status="ready" if ok else "partial" if result.get("available") else "needs_setup",
            summary=(
                f"Kali WSL جاهز وفيه {len(found_commands)} أدوات أمنية أساسية."
                if ok
                else f"Kali WSL متاح جزئيًا؛ الأدوات الناقصة: {', '.join(str(item) for item in missing_commands) or 'غير محددة'}."
                if result.get("available")
                else "تعذر الوصول إلى Kali WSL."
            ),
            checked_at=checked_at,
            action="kali_tool_inventory",
            details={
                "distro": result.get("distro"),
                "found_commands": found_commands,
                "missing_commands": missing_commands,
                "status": result.get("status"),
                "error": result.get("error"),
            },
        )
    if integration_id == "zapier_mcp":
        status = server.tools.zapier.status()
        inventory = server.tools.execute(
            "connected_tool_inventory",
            "اختبر مخزون Zapier MCP",
        )
        connected = bool(status.get("connected"))
        app_count = int(inventory.get("zapier_app_count") or 0)
        action_count = int(inventory.get("zapier_action_count") or 0)
        inventory_ready = bool(app_count > 0)
        ok = bool(connected and inventory_ready)
        return _probe_payload(
            integration_id,
            ok=ok,
            status=(
                "ready"
                if ok
                else "partial"
                if connected or inventory_ready
                else "needs_setup"
            ),
            summary=(
                f"Zapier OAuth المباشر جاهز، والمخزون يعرض {app_count} تطبيقًا و{action_count} إجراء."
                if ok
                else "Zapier OAuth المحلي متصل، لكن مخزون التطبيقات والإجراءات فارغ أو غير متزامن."
                if connected
                else f"مخزون Zapier يعرض {app_count} تطبيقًا و{action_count} إجراء، لكن OAuth المحلي المباشر لم يكتمل."
            ),
            checked_at=checked_at,
            action="oauth_status_and_inventory",
            details={
                "direct_oauth_connected": connected,
                "inventory_available": inventory_ready,
                "app_count": app_count,
                "action_count": action_count,
                "endpoint": status.get("endpoint"),
            },
        )
    if integration_id == "broker_testnet":
        status = server.tools.execute(
            "trading_testnet_status",
            "اختبر حالة وسيط التداول التجريبي",
            {},
        )["testnet"]
        configured = bool(status.get("configured"))
        probe = (
            server.tools.execute(
                "trading_testnet_status",
                "اختبر اتصال وسيط التداول التجريبي",
                {"probe": True},
            )["testnet"]
            if configured
            else status
        )
        authenticated = bool(probe.get("authenticated"))
        reachable = bool(probe.get("reachable")) if configured else False
        ok = configured and reachable and authenticated
        return _probe_payload(
            integration_id,
            ok=ok,
            status="ready" if ok else "partial" if configured else "needs_operator",
            summary=(
                "حساب Testnet استجاب وجرى التحقق من المصادقة."
                if ok
                else "مفاتيح Testnet موجودة لكن التحقق لم ينجح بعد."
                if configured
                else "Testnet ينتظر مفاتيح محلية؛ لم يُرسل أي طلب وساطة."
            ),
            checked_at=checked_at,
            action="testnet_status" if not configured else "testnet_probe",
            details={
                key: probe.get(key)
                for key in (
                    "provider",
                    "environment",
                    "configured",
                    "execution_enabled",
                    "symbol",
                    "reachable",
                    "authenticated",
                    "can_trade",
                    "base_host",
                    "error",
                )
                if key in probe
            },
        )
    raise KeyError(integration_id)


def _probe_payload(
    integration_id: str,
    *,
    ok: bool,
    status: str,
    summary: str,
    checked_at: str,
    action: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "integration_id": integration_id,
        "ok": ok,
        "status": status,
        "summary": summary,
        "checked_at": checked_at,
        "secret_safe": True,
        "action": action,
        "details": details,
    }


def _build_readiness_snapshot(
    server: LocalAgentHTTPServer,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    connectors = [
        connector
        for connector in server.tools.connector_catalog()
        if _visible_connector_profile(connector)
    ]
    inventory = server.tools.execute(
        "connected_tool_inventory",
        "عرض حالة الحسابات والاتصالات",
    )
    local_capabilities = server.tools.execute(
        "local_capability_inventory",
        "افحص شبكة التنفيذ المحلية",
    )
    readiness = build_integration_readiness(
        server.config,
        connectors,
        inventory,
        local_capabilities,
    )
    try:
        zapier_probe = server.tools.integration_probe("zapier_mcp")
    except Exception as exc:
        zapier_probe = {
            "integration_id": "zapier_mcp",
            "ok": False,
            "status": "partial",
            "summary": "تعذر فحص Zapier الحي؛ استخدم المخزون المحفوظ مؤقتًا.",
            "details": {
                "direct_live_available": False,
                "needs_reconnect": False,
                "error": f"{type(exc).__name__}: live probe failed",
            },
        }
    _apply_live_probe_to_readiness(readiness, zapier_probe)
    return readiness, local_capabilities, inventory


def _build_agent_mesh_summary(
    server: LocalAgentHTTPServer,
    readiness: dict[str, Any],
    local_capabilities: dict[str, Any],
    inventory: dict[str, Any],
) -> dict[str, Any]:
    integrations = [
        item
        for item in readiness.get("integrations", [])
        if isinstance(item, dict)
    ]
    by_id = {str(item.get("id")): item for item in integrations if item.get("id")}
    summary = readiness.get("summary") if isinstance(readiness.get("summary"), dict) else {}
    worker_online = bool(
        server.worker is not None
        and server.worker_thread is not None
        and server.worker_thread.is_alive()
    )
    ready_count = int(summary.get("ready") or 0)
    total_count = int(summary.get("total") or len(integrations))
    attention = [
        _mesh_blocker_payload(item)
        for item in integrations
        if item.get("status") != "ready"
    ]
    tool_count = len(server.tools.catalog())
    trading_status = server.trading.status()
    intake_status = server.intake.status()
    agent_providers = _mesh_agent_provider_summaries(inventory)
    zapier_apps = _mesh_zapier_app_summaries(inventory)

    lanes = [
        _mesh_lane(
            "execution",
            "محرك الوكلاء",
            "ready" if worker_online and ready_count >= 3 else "partial",
            f"{ready_count}/{total_count} تكاملات جاهزة · {tool_count} أداة",
            "شغّل الشبكة الآن",
            _mesh_execute_prompt(),
        ),
        _mesh_lane(
            "trading",
            "وكيل التداول",
            "ready" if trading_status.get("running") else "partial",
            (
                f"{trading_status.get('symbol', 'BTC-USD')} · "
                f"{trading_status.get('mode', 'paper')} · "
                f"{trading_status.get('cycle_target_seconds', 1)}s"
            ),
            "تشغيل/تحديث وكيل التداول",
            "شغّل وكيل التداول الورقي بنبض الثانية، حدّث مستشار OpenRouter، وسجل إيصالًا بالحالة والجودة.",
        ),
        _mesh_lane(
            "bug_bounty",
            "صيد الثغرات",
            "ready" if _mesh_status(by_id, "kali_wsl") == "ready" else "partial",
            (
                f"Kali {_mesh_short(by_id, 'kali_wsl')} · "
                f"Zapier {_mesh_short(by_id, 'zapier_mcp')} · Draft داخلي"
            ),
            "تشغيل صيد آمن",
            "شغّل مسار صيد الثغرات المصرح: اقرأ النطاق، استخدم المعرفة وKali/HexStrike عند اللزوم، وأنشئ تقرير Draft داخلي فقط.",
        ),
        _mesh_lane(
            "knowledge",
            "المعرفة والتقارير",
            "ready" if intake_status.get("running") and _mesh_status(by_id, "huggingface_local") == "ready" else "partial",
            (
                f"{intake_status.get('tracked_files', 0)} ملفات مراقبة · "
                f"HF {_mesh_short(by_id, 'huggingface_local')} · Fusion {_mesh_short(by_id, 'openrouter')}"
            ),
            "استيعاب وتشغيل",
            "استوعب ملفات وتقارير المعرفة الجديدة، اختبر الفهم بأسئلة تطبيقية، ثم شغّل الأدوات المناسبة بناءً على النتيجة.",
        ),
        _mesh_lane(
            "tool_bridge",
            "جسور الأدوات",
            "ready"
            if _mesh_status(by_id, "n8n_local") == "ready"
            and _mesh_status(by_id, "zapier_mcp") == "ready"
            else "partial",
            (
                f"n8n {_mesh_short(by_id, 'n8n_local')} · "
                f"Zapier {int(inventory.get('zapier_action_count') or 0)} إجراء · "
                f"{len(zapier_apps)} تطبيقات"
            ),
            "فحص وتفعيل الجسور",
            (
                "tool bridge sweep:\n"
                "FATHIYA_TOOL_BRIDGE_SWEEP_V1\n"
                "افحص Zapier MCP وn8n وCodespaces ووكلاء التطبيقات مثل Manus وCursor، "
                "نفذ ما هو آمن داخليًا، وأظهر أزرار التفعيل المطلوبة لما تبقى."
            ),
        ),
    ]
    quick_actions = [
        {
            "id": "agent_os_full_execute",
            "label": "تشغيل Agent OS كامل",
            "title": "تشغيل فتحية كوكلاء منفذين",
            "prompt": _agent_os_full_execute_prompt(),
            "mode": "execution",
        },
        {
            "id": "execute_mesh",
            "label": "تشغيل فتحية الآن",
            "title": "تشغيل شبكة فتحية",
            "prompt": _mesh_execute_prompt(),
            "mode": "execution",
        },
        {
            "id": "learn_and_execute",
            "label": "استيعاب وتشغيل",
            "title": "استيعاب معرفة وتشغيل أدوات",
            "prompt": _knowledge_execute_prompt(),
            "mode": "knowledge",
        },
        {
            "id": "activate_tools",
            "label": "تفعيل الناقص",
            "title": "تفعيل جسور فتحية",
            "prompt": _mesh_activation_sweep_prompt(),
            "mode": "tools",
        },
        {
            "id": "verify_production_site",
            "label": "إثبات الدومين",
            "title": "فحص fathya-core.com",
            "prompt": _production_site_audit_prompt(),
            "mode": "tools",
        },
        {
            "id": "verify_github_zapier_read",
            "label": "إثبات GitHub",
            "title": "قراءة GitHub عبر Zapier",
            "prompt": _zapier_github_repository_read_prompt(),
            "mode": "tools",
        },
        {
            "id": "verify_manus_zapier_read",
            "label": "إثبات Manus",
            "title": "قراءة مهام Manus عبر Zapier",
            "prompt": _zapier_manus_tasks_read_prompt(),
            "mode": "tools",
        },
        {
            "id": "verify_gmail_zapier_read",
            "label": "إثبات Gmail",
            "title": "قراءة Gmail عبر Zapier",
            "prompt": _zapier_gmail_openrouter_read_prompt(),
            "mode": "tools",
        },
        {
            "id": "prepare_cursor_zapier_read",
            "label": "تحضير Cursor",
            "title": "تحضير قراءة Cursor عبر Zapier",
            "prompt": _zapier_cursor_status_preflight_prompt(),
            "mode": "tools",
        },
    ]
    activation_overview = _mesh_activation_overview(
        lanes=lanes,
        attention=attention,
        tool_count=tool_count,
        local_capabilities=local_capabilities,
        inventory=inventory,
        agent_providers=agent_providers,
    )
    return {
        "mode": "agent_mesh_status_v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "ready_to_execute": worker_online and ready_count >= 3,
        "worker_online": worker_online,
        "headline": (
            "فتحية تعمل محليًا وتستطيع تنفيذ الأدوات الداخلية الآن."
            if worker_online and ready_count >= 3
            else "فتحية تعمل جزئيًا وتحتاج إكمال بعض الجسور."
        ),
        "summary": {
            "integration_total": total_count,
            "integration_ready": ready_count,
            "integration_attention": len(attention),
            "tool_count": tool_count,
            "capability_total": local_capabilities.get("capability_count"),
            "capability_ready": local_capabilities.get("ready_count"),
            "zapier_app_count": inventory.get("zapier_app_count"),
            "zapier_action_count": inventory.get("zapier_action_count"),
            "agent_provider_count": len(agent_providers),
            "agent_provider_ready_count": sum(
                1 for provider in agent_providers if provider.get("status") == "ready"
            ),
            "connected_app_count": len(zapier_apps),
            "connected_app_ready_count": sum(
                1 for app in zapier_apps if app.get("status") == "ready"
            ),
            "trading_running": trading_status.get("running"),
            "knowledge_intake_running": intake_status.get("running"),
        },
        "lanes": lanes,
        "agent_providers": agent_providers,
        "zapier_apps": zapier_apps,
        "attention": attention[:8],
        "quick_actions": quick_actions,
        "activation_overview": activation_overview,
        "policy": {
            "automatic_internal_execution": True,
            "local_direct_execution_default": True,
            "approval_gated_external_writes": True,
            "oauth_and_settings_are_followups": True,
            "external_impact_gate_does_not_block_internal_progress": True,
            "real_money_disabled_until_testnet_configured": True,
            "live_security_testing_requires_scope_confirmation": True,
        },
    }


def _build_command_center_payload(
    server: LocalAgentHTTPServer,
    mesh: dict[str, Any],
) -> dict[str, Any]:
    commands = _command_center_commands_from_mesh(mesh)
    command_groups = _command_center_command_groups(commands)
    activation = (
        mesh.get("activation_overview")
        if isinstance(mesh.get("activation_overview"), dict)
        else {}
    )
    operator_queue = [
        {
            "id": item.get("id"),
            "title": item.get("name") or item.get("id"),
            "status": item.get("status"),
            "action_type": item.get("action_type"),
            "action_tier": item.get("action_tier"),
            "blocks_local_execution": bool(item.get("blocks_local_execution")),
            "action_label": item.get("action_label"),
            "action_path": item.get("action_path"),
            "summary": item.get("summary"),
            "next_step": item.get("next_step"),
        }
        for item in activation.get("operator_actions", [])
        if isinstance(item, dict)
    ]
    summary = mesh.get("summary") if isinstance(mesh.get("summary"), dict) else {}
    api_base = f"http://127.0.0.1:{server.server_address[1]}"
    return {
        "mode": "fathiya_command_center_v1",
        "captured_at": datetime.now(UTC).isoformat(),
        "secret_safe": True,
        "ready_to_execute": bool(mesh.get("ready_to_execute")),
        "headline": mesh.get("headline"),
        "summary": {
            "command_count": len(commands),
            "ready_command_count": sum(
                1 for command in commands if command.get("status") == "ready"
            ),
            "command_group_count": len(command_groups),
            "operator_queue_count": len(operator_queue),
            "integration_ready": summary.get("integration_ready"),
            "integration_total": summary.get("integration_total"),
            "tool_count": summary.get("tool_count"),
            "zapier_action_count": summary.get("zapier_action_count"),
            "agent_provider_count": summary.get("agent_provider_count"),
            "connected_app_count": summary.get("connected_app_count"),
            "connected_app_ready_count": summary.get("connected_app_ready_count"),
            "trading_running": summary.get("trading_running"),
            "knowledge_intake_running": summary.get("knowledge_intake_running"),
        },
        "commands": commands,
        "command_groups": command_groups,
        "operator_queue": operator_queue,
        "lanes": mesh.get("lanes", []),
        "agent_providers": mesh.get("agent_providers", []),
        "zapier_apps": mesh.get("zapier_apps", []),
        "policy": mesh.get("policy", {}),
        "powershell": {
            "inspect": f"Invoke-RestMethod -Uri {api_base}/api/agent/command-center",
            "run_execute_mesh": (
                f"Invoke-RestMethod -Uri {api_base}/api/agent/command-center/run "
                "-Method Post -ContentType 'application/json' "
                "-Body '{\"command_id\":\"execute_mesh\"}'"
            ),
            "run_agent_os": (
                f"Invoke-RestMethod -Uri {api_base}/api/agent/command-center/run "
                "-Method Post -ContentType 'application/json' "
                "-Body '{\"command_id\":\"agent_os_full_execute\"}'"
            ),
            "run_trading": (
                f"Invoke-RestMethod -Uri {api_base}/api/agent/command-center/run "
                "-Method Post -ContentType 'application/json' "
                "-Body '{\"command_id\":\"lane_trading\"}'"
            ),
            "run_bug_bounty_draft": (
                f"Invoke-RestMethod -Uri {api_base}/api/agent/command-center/run "
                "-Method Post -ContentType 'application/json' "
                "-Body '{\"command_id\":\"lane_bug_bounty\"}'"
            ),
            "run_production_site_audit": (
                f"Invoke-RestMethod -Uri {api_base}/api/agent/command-center/run "
                "-Method Post -ContentType 'application/json' "
                "-Body '{\"command_id\":\"verify_production_site\"}'"
            ),
        },
    }


def _command_center_commands_from_mesh(mesh: dict[str, Any]) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(raw: dict[str, Any], *, source: str, command_id: str | None = None) -> None:
        prompt = str(raw.get("prompt") or "").strip()
        if not prompt:
            return
        item_id = command_id or str(raw.get("id") or "").strip()
        if not item_id or item_id in seen:
            return
        seen.add(item_id)
        lane = _command_center_lane(raw, source=source, command_id=item_id)
        commands.append(
            {
                "id": item_id,
                "label": raw.get("label") or raw.get("action_label") or raw.get("title"),
                "title": raw.get("title") or raw.get("label") or raw.get("action_label"),
                "lane": lane,
                "mode": lane,
                "group": _command_center_group_label(lane),
                "status": raw.get("status") or "ready",
                "prompt": prompt,
                "source": source,
                "ui_action": "task",
            }
        )

    quick_actions = mesh.get("quick_actions", [])
    if isinstance(quick_actions, list):
        for raw in quick_actions:
            if isinstance(raw, dict):
                add(raw, source="quick_action")

    lanes = mesh.get("lanes", [])
    if isinstance(lanes, list):
        for raw in lanes:
            if not isinstance(raw, dict):
                continue
            lane_id = str(raw.get("id") or "").strip()
            add(raw, source="lane", command_id=f"lane_{lane_id}" if lane_id else None)

    agent_providers = mesh.get("agent_providers", [])
    if isinstance(agent_providers, list):
        for provider in agent_providers[:8]:
            if not isinstance(provider, dict):
                continue
            provider_command = _command_center_agent_provider_command(provider)
            if provider_command:
                add(
                    provider_command,
                    source="agent_provider",
                    command_id=str(provider_command.get("id") or ""),
                )

    zapier_apps = mesh.get("zapier_apps", [])
    provider_names = {
        str(provider.get("app") or "").casefold()
        for provider in agent_providers
        if isinstance(provider, dict)
    }
    if isinstance(zapier_apps, list):
        for app in zapier_apps:
            if not isinstance(app, dict):
                continue
            if str(app.get("app") or "").casefold() in provider_names:
                continue
            app_command = _command_center_connected_app_command(app)
            if app_command:
                add(
                    app_command,
                    source="connected_app",
                    command_id=str(app_command.get("id") or ""),
                )

    return commands


COMMAND_CENTER_GROUP_ORDER = (
    "execution",
    "trading",
    "bug_bounty",
    "knowledge",
    "tools",
    "connected_apps",
)


COMMAND_CENTER_GROUP_LABELS = {
    "execution": "محرك الوكلاء",
    "trading": "التداول",
    "bug_bounty": "صيد الثغرات",
    "knowledge": "المعرفة والتقارير",
    "tools": "الأدوات والجسور",
    "connected_apps": "وكلاء التطبيقات",
}


def _command_center_lane(
    raw: dict[str, Any],
    *,
    source: str,
    command_id: str,
) -> str:
    explicit = str(raw.get("mode") or raw.get("lane") or "").strip()
    if explicit:
        return _normalize_command_center_lane(explicit)
    raw_id = str(raw.get("id") or command_id).strip()
    if source == "agent_provider" or source == "connected_app":
        return "connected_apps"
    if source == "lane":
        return _normalize_command_center_lane(raw_id.removeprefix("lane_"))
    if raw_id in {"activate_tools", "verify_production_site", "verify_github_zapier_read", "verify_manus_zapier_read", "verify_gmail_zapier_read", "prepare_cursor_zapier_read"}:
        return "tools"
    if raw_id == "learn_and_execute":
        return "knowledge"
    if raw_id in {"execute_mesh", "agent_os_full_execute"}:
        return "execution"
    return _normalize_command_center_lane(raw_id)


def _normalize_command_center_lane(value: str) -> str:
    lane = re.sub(r"[^a-z0-9_]+", "_", value.strip().casefold()).strip("_")
    aliases = {
        "bounty": "bug_bounty",
        "bug_bounty": "bug_bounty",
        "tool_bridge": "tools",
        "tool_bridges": "tools",
        "connected_app": "connected_apps",
        "connected_apps": "connected_apps",
        "agent_provider": "connected_apps",
        "agent_providers": "connected_apps",
    }
    return aliases.get(lane, lane or "execution")


def _command_center_group_label(lane: str) -> str:
    return COMMAND_CENTER_GROUP_LABELS.get(lane, "أوامر أخرى")


def _command_center_command_groups(commands: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for command in commands:
        lane = str(command.get("lane") or "execution")
        grouped.setdefault(lane, []).append(command)
    ordered_lanes = [
        *[lane for lane in COMMAND_CENTER_GROUP_ORDER if lane in grouped],
        *sorted(lane for lane in grouped if lane not in COMMAND_CENTER_GROUP_ORDER),
    ]
    groups: list[dict[str, Any]] = []
    for lane in ordered_lanes:
        items = grouped[lane]
        ready_count = sum(1 for item in items if item.get("status") == "ready")
        groups.append(
            {
                "id": lane,
                "label": _command_center_group_label(lane),
                "ready_count": ready_count,
                "command_count": len(items),
                "commands": [
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "label": item.get("label"),
                        "status": item.get("status"),
                        "source": item.get("source"),
                    }
                    for item in items[:6]
                ],
            }
        )
    return groups


def _command_center_connected_app_command(app_summary: dict[str, Any]) -> dict[str, Any] | None:
    app = str(app_summary.get("app") or "").strip()
    if not app:
        return None
    if app not in COMMAND_CENTER_CONNECTED_APP_PRIORITY:
        return None
    modes = [
        str(item)
        for item in app_summary.get("modes", [])
        if str(item).strip()
    ]
    status = str(app_summary.get("status") or "inventory_only")
    action_count = int(app_summary.get("action_count") or 0)
    read_capable = "read" in {mode.casefold() for mode in modes}
    prompt = "\n".join(
        [
            f"connected app catalog: {app}",
            "FATHIYA_CONNECTED_APP_COMMAND_V1",
            "Build a local-only catalog and parameter plan for this connected app.",
            "Use Zapier metadata only.",
            "Prefer read-type actions when present.",
            "For effect-capable actions, return approval queue only.",
            f"app_status: {status}",
            f"execution_mode: {app_summary.get('execution_mode') or 'inventory_only_until_oauth'}",
            f"action_count: {action_count}",
            f"read_capable: {str(read_capable).lower()}",
            f"mode_count: {len(modes)}",
        ]
    )
    return {
        "id": f"connected_app_{_command_center_slug(app)}",
        "label": app,
        "title": f"تطبيق {app}",
        "mode": "connected_apps",
        "status": "ready" if status == "ready" else "partial",
        "prompt": prompt,
    }


def _command_center_agent_provider_command(provider: dict[str, Any]) -> dict[str, Any] | None:
    app = str(provider.get("app") or "").strip()
    if not app:
        return None
    read_actions = [
        str(item)
        for item in provider.get("read_actions", [])
        if str(item).strip()
    ][:5]
    write_actions = [
        str(item)
        for item in provider.get("write_actions", [])
        if str(item).strip()
    ][:5]
    status = str(provider.get("status") or "inventory_only")
    launch_action = _command_center_agent_launch_action(app, write_actions)
    launch_params = _command_center_agent_launch_params(app)
    launch_objective = _command_center_agent_launch_objective(app)
    action_lines = (
        [
            f"action: {launch_action}",
            f"objective: {launch_objective}",
            f"params: {json.dumps(launch_params, ensure_ascii=False, separators=(',', ':'))}",
            "Prepare this provider launch as the primary command; do not execute the external write without the approval gate.",
        ]
        if launch_action
        else ["Choose the narrowest useful read action when available."]
    )
    prompt = "\n".join(
        [
            f"prepare provider action: {app}",
            "FATHIYA_AGENT_PROVIDER_COMMAND_V1",
            "Build a local-only provider action plan for FATHIYA.",
            "Use the Zapier catalog and local metadata only.",
            *action_lines,
            "For write-capable actions, return a parameter plan and approval queue only.",
            f"provider_status: {status}",
            f"execution_mode: {provider.get('execution_mode') or 'inventory_only_until_oauth'}",
            f"read_action_count: {len(read_actions)}",
            f"approval_gated_action_count: {len(write_actions)}",
        ]
    )
    return {
        "id": f"agent_provider_{_command_center_slug(app)}",
        "label": app,
        "title": f"وكيل {app}",
        "mode": "connected_apps",
        "status": "ready" if status == "ready" else "partial",
        "prompt": prompt,
    }


def _command_center_agent_launch_action(app: str, write_actions: list[str]) -> str:
    normalized = app.casefold()
    if "cursor" in normalized and any(action == "Launch Agent" for action in write_actions):
        return "Launch Agent"
    if "manus" in normalized:
        for action in ("Create Task", "Create Private Task", "Launch Agent"):
            if action in write_actions:
                return action
    return ""


def _command_center_agent_launch_objective(app: str) -> str:
    normalized = app.casefold()
    if "cursor" in normalized:
        return "راجع مسار فتحية التشغيلي وارجع بملاحظات تنفيذية فقط."
    if "manus" in normalized:
        return "نفذ مراجعة تشغيلية لفتحية وارجع بملاحظات عملية."
    return "حضّر تشغيل وكيل التطبيق داخل فتحية."


def _command_center_agent_launch_params(app: str) -> dict[str, Any]:
    normalized = app.casefold()
    if "cursor" in normalized:
        return {
            "repository_url": "https://github.com/fathya-core/fathiya-core",
            "prompt_text": _command_center_agent_launch_objective(app),
            "repository_ref": "main",
            "target_auto_create_pr": "false",
        }
    if "manus" in normalized:
        return {
            "prompt": _command_center_agent_launch_objective(app),
            "agent_profile": "manus-1.6",
            "share_visibility": "private",
        }
    return {}


def _command_center_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.strip().casefold())
    return slug.strip("_") or "app"


def _mesh_zapier_app_summaries(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    raw_apps = inventory.get("zapier_apps")
    if not isinstance(raw_apps, list):
        return []
    direct = inventory.get("direct_zapier_mcp")
    direct_live = bool(
        isinstance(direct, dict)
        and direct.get("connected")
        and direct.get("direct_execution")
        and not direct.get("expired")
        and not direct.get("needs_reconnect")
    )
    priority = {
        app.casefold(): index
        for index, app in enumerate(COMMAND_CENTER_CONNECTED_APP_PRIORITY)
    }
    apps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_apps:
        if not isinstance(item, dict):
            continue
        app = str(item.get("app") or "").strip()
        if not app or app.casefold() in seen:
            continue
        seen.add(app.casefold())
        modes = [
            str(mode)
            for mode in item.get("modes", [])
            if str(mode).strip()
        ]
        apps.append(
            {
                "app": app,
                "action_count": int(item.get("action_count") or 0),
                "modes": modes,
                "status": "ready" if direct_live else "inventory_only",
                "inventory_only": not direct_live,
                "execution_mode": (
                    "live_zapier_mcp"
                    if direct_live
                    else "inventory_only_until_oauth"
                ),
                "sources": item.get("sources", []),
            }
        )
    return sorted(
        apps,
        key=lambda item: (
            priority.get(str(item.get("app") or "").casefold(), 10_000),
            str(item.get("app") or "").casefold(),
        ),
    )


def _mesh_activation_overview(
    *,
    lanes: list[dict[str, Any]],
    attention: list[dict[str, Any]],
    tool_count: int,
    local_capabilities: dict[str, Any],
    inventory: dict[str, Any],
    agent_providers: list[dict[str, Any]],
) -> dict[str, Any]:
    ready_lanes = [
        str(lane.get("label") or lane.get("id"))
        for lane in lanes
        if lane.get("status") == "ready"
    ]
    operator_actions: list[dict[str, Any]] = []
    for item in attention[:8]:
        action_path = str(item.get("action_path") or "")
        if "/oauth/" in action_path:
            action_type = "oauth"
        elif "/settings/" in action_path:
            action_type = "settings"
        else:
            action_type = "probe"
        action_tier = _activation_action_tier(str(item.get("id") or ""))
        operator_actions.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "status": item.get("status"),
                "action_type": action_type,
                "action_tier": action_tier,
                "blocks_local_execution": action_tier == "blocking",
                "action_label": item.get("action_label") or "متابعة",
                "action_path": item.get("action_path"),
                "summary": item.get("summary"),
                "next_step": item.get("next_step"),
            }
        )
    lane_count = len(lanes)
    ready_lane_count = len(ready_lanes)
    ready_headline = (
        f"{ready_lane_count}/{lane_count} مسارات تعمل الآن"
        if lane_count
        else "مسارات فتحية قيد الفحص"
    )
    blocking_actions = [
        action for action in operator_actions if action.get("action_tier") == "blocking"
    ]
    upgrade_actions = [
        action for action in operator_actions if action.get("action_tier") == "upgrade"
    ]
    return {
        "mode": "agent_activation_overview_v1",
        "executable_now": ready_lane_count > 0 and not blocking_actions,
        "ready_headline": ready_headline,
        "primary_message": (
            "فتحية قابلة للتنفيذ محليًا الآن؛ النواقص المتبقية هي ربط حسابات أو مفاتيح اختيارية."
            if ready_lane_count and not blocking_actions
            else "فتحية تحتاج فحص تشغيل قبل تنفيذ الوكلاء."
        ),
        "ready_lane_count": ready_lane_count,
        "lane_count": lane_count,
        "ready_lane_labels": ready_lanes,
        "safe_tool_count": tool_count,
        "capability_ready": local_capabilities.get("ready_count"),
        "capability_total": local_capabilities.get("capability_count"),
        "zapier_app_count": inventory.get("zapier_app_count"),
        "zapier_action_count": inventory.get("zapier_action_count"),
        "agent_provider_count": len(agent_providers),
        "agent_provider_ready_count": sum(
            1 for provider in agent_providers if provider.get("status") == "ready"
        ),
        "agent_provider_write_action_count": sum(
            int(provider.get("write_count") or 0) for provider in agent_providers
        ),
        "agent_providers": agent_providers[:8],
        "operator_action_count": len(operator_actions),
        "blocking_action_count": len(blocking_actions),
        "upgrade_action_count": len(upgrade_actions),
        "operator_actions": operator_actions,
        "blocking_actions": blocking_actions,
        "upgrade_actions": upgrade_actions,
        "default_action": {
            "id": "execute_mesh",
            "label": "تشغيل فتحية الآن",
            "mode": "execution",
        },
    }


def _activation_action_tier(integration_id: str) -> str:
    if integration_id in {"zapier_mcp", "supabase", "broker_testnet"}:
        return "upgrade"
    return "blocking"


def _mesh_agent_provider_summaries(
    inventory: dict[str, Any],
    *,
    direct_live_override: bool | None = None,
) -> list[dict[str, Any]]:
    action_sets = inventory.get("agent_provider_actions")
    if not isinstance(action_sets, dict):
        return []
    direct = inventory.get("direct_zapier_mcp")
    direct_live = (
        bool(direct_live_override)
        if direct_live_override is not None
        else (
            isinstance(direct, dict)
            and bool(direct.get("connected"))
            and bool(direct.get("direct_execution"))
            and not bool(direct.get("expired"))
            and not bool(direct.get("needs_reconnect"))
            and bool(direct.get("live_available", True))
        )
    )
    providers: list[dict[str, Any]] = []
    for app, action_set in action_sets.items():
        if not isinstance(action_set, dict):
            continue
        raw_read_actions = action_set.get("read", [])
        raw_write_actions = action_set.get("approval_gated_write", [])
        read_actions = [
            str(action)
            for action in (raw_read_actions if isinstance(raw_read_actions, list) else [])
            if str(action).strip()
        ]
        write_actions = [
            str(action)
            for action in (raw_write_actions if isinstance(raw_write_actions, list) else [])
            if str(action).strip()
        ]
        total = len(read_actions) + len(write_actions)
        if total <= 0:
            continue
        app_name = str(app).strip()
        execution_mode = "live_zapier_mcp" if direct_live else "inventory_only_until_oauth"
        providers.append(
            {
                "app": app_name,
                "status": "ready" if direct_live else "inventory_only",
                "execution_mode": execution_mode,
                "inventory_only": not direct_live,
                "read_count": len(read_actions),
                "write_count": len(write_actions),
                "total_actions": total,
                "read_actions": read_actions[:6],
                "write_actions": write_actions[:6],
                "action_path": None if direct_live else "/api/agent/oauth/zapier/start",
                "action_label": "تشغيل عبر Zapier" if direct_live else "ربط Zapier OAuth",
                "next_step": (
                    f"{app_name} جاهز عبر Zapier MCP؛ اختر إجراء قراءة أو كتابة من كتالوج الأدوات."
                    if direct_live
                    else f"{app_name} ظاهر في المخزون، ويحتاج OAuth المحلي ليصبح قابلًا للتنفيذ الحي."
                ),
                "task_prompt": "\n".join(
                    [
                        f"Zapier agent provider: {app_name}",
                        "افحص هذا المزود كوكيل تطبيق داخل فتحية.",
                        "اعرض أفعال القراءة والكتابة المتاحة، ولا تنفذ كتابة خارجية بدون بوابة موافقة.",
                    ]
                ),
            }
        )
    return sorted(
        providers,
        key=lambda item: (
            0 if item.get("status") == "ready" else 1,
            -int(item.get("total_actions") or 0),
            str(item.get("app") or "").casefold(),
        ),
    )


def _zapier_diagnostics_payload(
    server: LocalAgentHTTPServer,
    *,
    return_to: str,
) -> dict[str, Any]:
    status = server.tools.zapier.status()
    try:
        inventory = server.tools.execute(
            "connected_tool_inventory",
            "diagnose Zapier MCP activation",
            {"quick": True},
        )
    except Exception as exc:
        inventory = {
            "available": False,
            "zapier_app_count": 0,
            "zapier_action_count": 0,
            "agent_provider_actions": {},
            "error": f"{type(exc).__name__}: connected inventory unavailable",
        }
    connected = bool(status.get("connected"))
    direct_execution = bool(status.get("direct_execution"))
    expired = bool(status.get("expired"))
    refresh_recommended = bool(status.get("refresh_recommended"))
    last_refresh_error = str(status.get("last_refresh_error") or "")
    has_refresh_token = bool(status.get("has_refresh_token"))
    needs_reconnect = bool(
        (
            connected
            and not (direct_execution and has_refresh_token and not expired)
            and (expired or refresh_recommended or last_refresh_error)
        )
        or (not connected and last_refresh_error)
    )
    live_candidate = connected and direct_execution and not needs_reconnect
    providers = _mesh_agent_provider_summaries(
        inventory if isinstance(inventory, dict) else {},
        direct_live_override=live_candidate,
    )
    if live_candidate:
        activation_state = "live"
        headline = "Zapier MCP متصل حيًا ويمكن تشغيل إجراءات القراءة مباشرة."
    elif needs_reconnect:
        activation_state = "reconnect_required"
        headline = "Zapier MCP يحتاج إعادة ربط أو تجديد قبل التنفيذ الحي."
    elif providers:
        activation_state = "inventory_only"
        headline = "Zapier MCP يملك مخزون أدوات محفوظ، لكن التنفيذ الحي ينتظر OAuth."
    else:
        activation_state = "not_connected"
        headline = "Zapier MCP غير متصل بعد."

    api_base = f"http://127.0.0.1:{server.server_address[1]}"
    start_path = "/api/agent/oauth/zapier/start"
    fresh_start_path = "/api/agent/oauth/zapier/start?force=1"
    start_url = _append_query(f"{api_base}{start_path}", {"return_to": return_to})
    fresh_start_url = _append_query(
        f"{api_base}{fresh_start_path}",
        {"return_to": return_to},
    )
    callback_url = f"{api_base}/api/agent/oauth/zapier/callback"
    next_actions: list[dict[str, Any]] = []
    if activation_state == "reconnect_required" and has_refresh_token:
        next_actions.append(
            {
                "id": "fresh_connect_zapier_oauth",
                "title": "إعادة ربط Zapier OAuth بالكامل",
                "action_type": "oauth",
                "action_label": "إعادة ربط كاملة",
                "action_path": fresh_start_path,
                "summary": "يمسح تسجيل OAuth المحلي القديم ويبدأ تسجيلًا جديدًا عندما يفشل refresh token.",
            }
        )
    if activation_state != "live":
        next_actions.append(
            {
                "id": "connect_zapier_oauth",
                "title": "ربط Zapier OAuth المحلي",
                "action_type": "oauth",
                "action_label": "ربط Zapier الآن",
                "action_path": start_path,
                "summary": "يفتح الربط التنفيذ الحي لمزودي الوكلاء الظاهرين في المخزون.",
            }
        )
    next_actions.append(
        {
            "id": "probe_zapier_after_oauth",
            "title": "فحص Zapier بعد الربط",
            "action_type": "task",
            "action_label": "فحص Zapier",
            "prompt": "integration probe: zapier_mcp\nافحص Zapier MCP بعد الربط، اعرض التطبيقات والإجراءات، وسجل إيصالًا بدون كشف أسرار.",
            "summary": "يشغل فحصًا داخليًا بعد الرجوع من OAuth أو عند تحديث المخزون.",
        }
    )
    return {
        "mode": "zapier_mcp_activation_diagnostics_v1",
        "activation_state": activation_state,
        "headline": headline,
        "connected": connected,
        "direct_execution": direct_execution,
        "expired": expired,
        "refresh_recommended": refresh_recommended,
        "needs_reconnect": needs_reconnect,
        "token_source": status.get("token_source"),
        "refresh_credential_saved": has_refresh_token,
        "last_refresh_error": status.get("last_refresh_error")
        if needs_reconnect or refresh_recommended
        else None,
        "last_refresh_status_code": status.get("last_refresh_status_code")
        if needs_reconnect or refresh_recommended
        else None,
        "last_refresh_at": status.get("last_refresh_at"),
        "endpoint": status.get("endpoint"),
        "inventory_available": bool(inventory.get("available")) if isinstance(inventory, dict) else False,
        "app_count": int(inventory.get("zapier_app_count") or 0) if isinstance(inventory, dict) else 0,
        "action_count": int(inventory.get("zapier_action_count") or 0) if isinstance(inventory, dict) else 0,
        "agent_provider_count": len(providers),
        "agent_provider_write_action_count": sum(
            int(provider.get("write_count") or 0) for provider in providers
        ),
        "agent_providers": providers[:8],
        "start_path": start_path,
        "start_url": start_url,
        "fresh_start_path": fresh_start_path,
        "fresh_start_url": fresh_start_url,
        "callback_url": callback_url,
        "return_to": return_to,
        "next_actions": next_actions,
        "secret_safe": True,
    }


def _agent_os_full_execute_prompt() -> str:
    return "\n".join(
        [
            "agent mesh execute:",
            "FATHIYA_AGENT_OS_FULL_EXECUTION_V1",
            "شغّل فتحية الآن كمحرك وكلاء منفذين لا كمحلل تقارير فقط.",
            "ابدأ من المعرفة المحلية: استرجع ما يلزم عبر Hugging Face، ثم استخدم OpenRouter للتخطيط والتقييم الثقيل عند الحاجة.",
            "نفذ كل ما هو داخلي أو قراءة أو Paper/Testnet متاح الآن عبر الأدوات المحلية: Zapier MCP inventory/live reads، n8n، Kali WSL، GitHub/Codespaces، ووكلاء التطبيقات مثل Manus وCursor وAI by Zapier عند توفر OAuth.",
            "افصل المسارات عمليًا: التداول الورقي بنبض الثانية أولًا، صيد الثغرات كمسودة مصرح بها مع dedupe، التقارير كإيصالات، والطلب المباشر كهدف واحد يتحول إلى أدوات.",
            "لا تتوقف عند نقص Supabase أو Testnet أو OAuth؛ نفذ المتاح الآن، وحوّل الناقص إلى next_action محدد.",
            "سجل إيصالًا يثبت الأدوات التي تحركت فعليًا، نتيجة كل مسار، وما بقي فقط بسبب إعداد خارجي أو أثر عالي.",
        ]
    )


def _mesh_execute_prompt() -> str:
    return "\n".join(
        [
            "agent mesh execute:",
            "شغّل شبكة فتحية المحلية الآن: المعرفة، Hugging Face المحلي، OpenRouter، Zapier MCP inventory، n8n، Kali، Codespaces، ووكيل التداول الورقي.",
            "نفذ الأدوات الداخلية الآمنة فقط، جهّز خطة تفعيل واضحة لما يحتاج OAuth أو حساب، وسجل إيصالًا بالأدوات التي عملت وما بقي.",
        ]
    )


def _knowledge_execute_prompt() -> str:
    return "\n".join(
        [
            "knowledge execution mission:",
            "FATHIYA_KNOWLEDGE_EXECUTION_V1",
            "استوعب ملفات وتقارير المعرفة الجديدة، اختبر الفهم بأسئلة تطبيقية، ثم اختر الأدوات والنماذج المناسبة.",
            "استخدم Hugging Face المحلي للاسترجاع/الفهم، OpenRouter للتوجيه، وZapier MCP inventory وn8n وKali وGitHub ووكيل التداول كقدرات تنفيذ.",
            "نفذ الأدوات الداخلية الآمنة وما هو قراءة أو Paper/Testnet جاهز، وسجل إيصالًا بما فُهم وما نُفذ وما ينتظر OAuth أو إعدادات.",
        ]
    )


def _mesh_activation_sweep_prompt() -> str:
    return "\n".join(
        [
            "agent mesh execute:",
            "FATHIYA_ACTIVATION_SWEEP_V1",
            "فعّل الناقص في فتحية كمسار تشغيل واحد لا كتنقل بين الإعدادات.",
            "افحص بوابات Zapier MCP وGitHub Codespaces وSupabase وn8n المحلي وKali WSL وOpenRouter وHugging Face وBroker Testnet.",
            "نفذ كل فحص أو قراءة أو تشغيل داخلي آمن متاح الآن، ولا توقف المهمة بسبب بوابات OAuth أو مفاتيح أو موافقة أثر.",
            "حوّل كل بوابة غير جاهزة إلى next_action واضح: ماذا أضغط، ماذا أربط، وأي إعداد محلي مطلوب بدون كشف أسرار.",
            "ابدأ أو تحقق من وكيل التداول الورقي، وأثبت أن مسار النماذج المحلي/OpenRouter جاهز، ثم سجل إيصالًا مرتبًا.",
        ]
    )


def _production_site_audit_prompt() -> str:
    return "\n".join(
        [
            "production site audit:",
            "base_url: https://fathya-core.com",
            "routes: /, /agent-tasks, /command-center, /ai-console",
            "افحص إنتاج فتحية قراءة فقط، وتأكد هل الدومين يعرض المنصة السيادية الذكية وصفحة agent-tasks الحالية.",
            "قارِن الإشارات العامة بالمحلي: الهوية، أقسام التداول، صيد الثغرات، المعرفة، والأدوات.",
            "لا تغيّر DNS ولا تنشر ولا تدخل بحسابات؛ سجّل إيصالًا واضحًا بما يعمل وما يحتاج نشر أو Supabase.",
        ]
    )


def _zapier_github_repository_read_prompt() -> str:
    return "\n".join(
        [
            "Zapier action: GitHub / Find Repository",
            "instructions: Execute a safe read against the FATHIYA GitHub repository through Zapier MCP, then record progress and a receipt without exposing secrets.",
            'params:{"owner":"fathya-core","repo":"fathiya-core"}',
        ]
    )


def _zapier_manus_tasks_read_prompt() -> str:
    return "\n".join(
        [
            "Zapier action: Manus / Get Tasks",
            "instructions: Execute a safe read of Manus task metadata through Zapier MCP, then record progress and a receipt without exposing task secrets.",
            "params:{}",
        ]
    )


def _zapier_gmail_openrouter_read_prompt() -> str:
    return "\n".join(
        [
            "Zapier action: Gmail / New Email Matching Search",
            "instructions: Execute a safe Gmail search for recent OpenRouter/Fusion-related mail, summarize only receipt-safe identifiers, and do not expose email bodies or secrets.",
            'params:{"query":"from:(openrouter.ai) OR subject:(OpenRouter) OR subject:(Fusion)"}',
        ]
    )


def _zapier_cursor_status_preflight_prompt() -> str:
    return "\n".join(
        [
            "Zapier action preflight: Cursor / Find Agent Status",
            "instructions: Prepare the safe Cursor agent-status read. Do not execute until agent_id is supplied; return required fields and a ready task prompt.",
            "params:{}",
        ]
    )


def _mesh_lane(
    lane_id: str,
    label: str,
    status: str,
    signal: str,
    action_label: str,
    prompt: str,
) -> dict[str, Any]:
    return {
        "id": lane_id,
        "label": label,
        "status": status,
        "signal": signal,
        "action_label": action_label,
        "prompt": prompt,
    }


def _mesh_status(by_id: dict[str, dict[str, Any]], integration_id: str) -> str:
    return str(by_id.get(integration_id, {}).get("status") or "unknown")


def _mesh_short(by_id: dict[str, dict[str, Any]], integration_id: str) -> str:
    status = _mesh_status(by_id, integration_id)
    return {
        "ready": "جاهز",
        "partial": "جزئي",
        "needs_setup": "إعداد",
        "needs_operator": "ينتظر",
    }.get(status, "تحقق")


def _mesh_blocker_payload(integration: dict[str, Any]) -> dict[str, Any]:
    action_path = integration.get("action_path") or integration.get("settings_path")
    action_label = integration.get("action_label") or integration.get("settings_label")
    action_tier = _activation_action_tier(str(integration.get("id") or ""))
    return {
        "id": integration.get("id"),
        "name": integration.get("name"),
        "status": integration.get("status"),
        "action_tier": action_tier,
        "blocks_local_execution": action_tier == "blocking",
        "summary": integration.get("summary"),
        "next_step": integration.get("next_step"),
        "action_path": action_path,
        "action_label": action_label,
    }


def _run_github_codespaces_scope_refresh() -> dict[str, Any]:
    gh = shutil.which("gh")
    if not gh:
        return {
            "ok": False,
            "error": "gh_not_found",
            "command": "gh auth login -h github.com -p https -s repo,workflow,read:org,gist,codespace -w",
        }
    login_command = [
        gh,
        "auth",
        "login",
        "-h",
        "github.com",
        "-p",
        "https",
        "-s",
        "repo,workflow,read:org,gist,codespace",
        "-w",
    ]
    refresh_command = [gh, "auth", "refresh", "-h", "github.com", "-s", "codespace"]
    try:
        auth_status = subprocess.run(
            [gh, "auth", "status", "-h", "github.com"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        auth_status = None
    command = (
        refresh_command
        if auth_status is not None and auth_status.returncode == 0
        else login_command
    )
    command_text = (
        "gh auth refresh -h github.com -s codespace"
        if command is refresh_command
        else "gh auth login -h github.com -p https -s repo,workflow,read:org,gist,codespace -w"
    )
    popen_kwargs: dict[str, Any] = {}
    if hasattr(subprocess, "CREATE_NEW_CONSOLE"):
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    try:
        process = subprocess.Popen(command, **popen_kwargs)
        return_code = process.wait(timeout=300)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except Exception:
            pass
        return {
            "ok": False,
            "error": "timeout",
            "command": command_text,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {str(exc)[:240]}",
            "command": command_text,
        }
    return {
        "ok": return_code == 0,
        "return_code": return_code,
        "command": command_text,
    }


def _apply_live_probe_to_readiness(
    readiness: dict[str, Any],
    probe: dict[str, Any],
) -> None:
    if probe.get("integration_id") != "zapier_mcp":
        return
    probe_details = probe.get("details") if isinstance(probe.get("details"), dict) else {}
    for integration in readiness.get("integrations", []):
        if not isinstance(integration, dict) or integration.get("id") != "zapier_mcp":
            continue
        details = integration.setdefault("details", {})
        if isinstance(details, dict):
            for key in (
                "direct_oauth_connected",
                "direct_live_available",
                "needs_reconnect",
                "auth_state",
                "refresh_recommended",
                "last_refresh_error",
                "last_refresh_status_code",
                "last_refresh_at",
                "app_count",
                "action_count",
                "endpoint",
                "error",
            ):
                if key in probe_details:
                    details[key] = probe_details[key]
        status = str(probe.get("status") or integration.get("status") or "partial")
        integration["status"] = status
        if probe.get("summary"):
            integration["summary"] = probe["summary"]
        needs_reconnect = bool(probe_details.get("needs_reconnect"))
        live_available = bool(probe_details.get("direct_live_available"))
        if status != "ready" or needs_reconnect or not live_available:
            integration["action_path"] = (
                "/api/agent/oauth/zapier/start?force=1"
                if needs_reconnect
                else "/api/agent/oauth/zapier/start"
            )
            integration["action_label"] = (
                "إعادة ربط كاملة"
                if needs_reconnect
                else "ربط Zapier MCP محليًا"
            )
            integration["next_step"] = (
                "أعد ربط Zapier MCP بالكامل؛ رمز OAuth المحلي منتهي أو فشل تجديده."
                if needs_reconnect
                else "اختبر أو اربط Zapier MCP عبر OAuth المحلي."
            )
        else:
            integration["action_path"] = None
            integration["action_label"] = None
            integration["next_step"] = "لا إجراء مطلوب."
        break

    summary = readiness.get("summary")
    integrations = [
        item
        for item in readiness.get("integrations", [])
        if isinstance(item, dict)
    ]
    if isinstance(summary, dict):
        summary["total"] = len(integrations)
        for status in ("ready", "partial", "needs_setup", "needs_operator"):
            summary[status] = sum(
                1 for item in integrations if item.get("status") == status
            )


def _operator_origin_allowed(origin: str, config: RuntimeConfig) -> bool:
    clean = origin.rstrip("/")
    return bool(LOCAL_ORIGIN.fullmatch(clean)) or clean in config.operator_origins


def _safe_operator_return_to(value: str, config: RuntimeConfig) -> str:
    parsed = urlparse(value)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else ""
    if not origin or not _operator_origin_allowed(origin, config):
        return "http://127.0.0.1:5180/agent-tasks"
    path = parsed.path if parsed.path.startswith("/") else "/agent-tasks"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def _append_query(value: str, fields: dict[str, str]) -> str:
    parsed = urlparse(value)
    query = parse_qs(parsed.query)
    for key, field_value in fields.items():
        query[key] = [field_value]
    flat = [(key, item) for key, values in query.items() for item in values]
    return urlunparse((*parsed[:4], urlencode(flat), ""))


def _runtime_health_payload(server: LocalAgentHTTPServer) -> dict[str, Any]:
    trading = server.trading.status()
    return {
        "status": "ok",
        "mode": "local_sqlite",
        "worker_id": server.config.worker_id,
        "worker_online": bool(server.worker_thread and server.worker_thread.is_alive()),
        "api": f"http://{server.server_address[0]}:{server.server_address[1]}",
        "agent_loop": {
            "max_rounds": server.config.max_agent_rounds,
            "max_tool_steps_per_round": server.config.max_tool_steps,
            "local_planning_enabled": server.config.enable_local_planning,
            "local_generation_enabled": server.config.enable_local_generation,
            "local_model": server.config.local_model,
            "local_max_new_tokens": server.config.local_max_new_tokens,
            "local_max_generation_seconds": server.config.local_max_generation_seconds,
            "openrouter_configured": bool(server.config.openrouter_api_key),
            "openrouter_model": server.config.openrouter_model,
            "openrouter_research_model": server.config.openrouter_research_model,
            "openrouter_safety_model": server.config.openrouter_safety_model,
            "planning_route": (
                "huggingface_local_then_openrouter_advisor"
                if server.config.enable_local_planning
                else "openrouter_then_deterministic_local"
            ),
        },
        "knowledge_intake": server.intake.status(),
        "trading": {
            "running": trading["running"],
            "autostart": server.config.trading_autostart,
            "mode": trading["mode"],
            "symbol": trading["symbol"],
            "cycle_target_seconds": trading["cycle_target_seconds"],
            "latest_receipt_id": trading["latest_receipt_id"],
        },
    }


def _find_connector_dispatch_receipt(
    detail: dict[str, Any] | None,
    profile: str,
    upstream_receipt_id: str,
) -> dict[str, Any] | None:
    for receipt in (detail or {}).get("receipts", []):
        evidence = receipt.get("evidence")
        if (
            isinstance(evidence, dict)
            and evidence.get("profile") == profile
            and evidence.get("upstream_receipt_id") == upstream_receipt_id
        ):
            return receipt
    return None


def create_local_server(
    config: RuntimeConfig,
    store: TaskStore,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
) -> LocalAgentHTTPServer:
    store.initialize()
    return LocalAgentHTTPServer((host, port), config, store)


def serve_local_control_plane(
    config: RuntimeConfig,
    store: TaskStore,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    poll_seconds: float = 0.5,
) -> None:
    server = create_local_server(config, store, host=host, port=port)
    worker = AgentWorker(config, store, tools=server.tools)
    server.worker = worker
    worker_thread = threading.Thread(
        target=worker.start,
        kwargs={"poll_seconds": poll_seconds},
        name="fathiya-local-worker",
        daemon=True,
    )
    server.worker_thread = worker_thread
    worker_thread.start()
    server.intake.start()
    if config.trading_autostart:
        server.trading.start()
    print(
        json.dumps(
            {
                "status": "online",
                "api": f"http://{host}:{server.server_address[1]}",
                "worker_id": config.worker_id,
                "store": config.store,
                "knowledge_intake": server.intake.status(),
            },
            ensure_ascii=False,
        )
    )
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
