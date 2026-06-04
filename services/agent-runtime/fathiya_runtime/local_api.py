from __future__ import annotations

import hmac
import json
import re
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
    r"^/api/agent/trading(?:/(?P<action>status|receipts|start|stop|tick))?$",
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
        if path == "/api/agent/oauth/zapier/start":
            query = parse_qs(parsed_request.query)
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
        if path == "/healthz":
            trading = self.server.trading.status()
            return self._send_json(
                {
                    "status": "ok",
                    "mode": "local_sqlite",
                    "worker_id": self.server.config.worker_id,
                    "worker_online": bool(
                        self.server.worker_thread and self.server.worker_thread.is_alive()
                    ),
                    "api": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}",
                    "agent_loop": {
                        "max_rounds": self.server.config.max_agent_rounds,
                        "max_tool_steps_per_round": self.server.config.max_tool_steps,
                        "local_planning_enabled": self.server.config.enable_local_planning,
                        "openrouter_configured": bool(
                            self.server.config.openrouter_api_key
                        ),
                    },
                    "knowledge_intake": self.server.intake.status(),
                    "trading": {
                        "running": trading["running"],
                        "autostart": self.server.config.trading_autostart,
                        "mode": trading["mode"],
                        "symbol": trading["symbol"],
                        "cycle_target_seconds": trading["cycle_target_seconds"],
                        "latest_receipt_id": trading["latest_receipt_id"],
                    },
                }
            )
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
        if path == "/api/agent/connectors":
            connectors = self.server.tools.connector_catalog()
            bridge_profiles = self.server.tools.bridge_dispatch_profiles()
            inventory = self.server.tools.execute(
                "connected_tool_inventory",
                "عرض مخزون الموصلات",
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
            connectors = self.server.tools.connector_catalog()
            inventory = self.server.tools.execute(
                "connected_tool_inventory",
                "عرض حالة الحسابات والاتصالات",
            )
            local_capabilities = self.server.tools.execute(
                "local_capability_inventory",
                "افحص شبكة التنفيذ المحلية",
            )
            return self._send_json(
                build_integration_readiness(
                    self.server.config,
                    connectors,
                    inventory,
                    local_capabilities,
                )
            )
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
        if trading_match and trading_match.group("action") in {"start", "stop", "tick"}:
            try:
                action = trading_match.group("action")
                if action == "start":
                    return self._send_json({"trading": self.server.trading.start()})
                if action == "stop":
                    return self._send_json({"trading": self.server.trading.stop()})
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
