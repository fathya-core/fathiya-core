from __future__ import annotations

import json
import re
import threading
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .config import RuntimeConfig
from .store import TaskStore, now_iso
from .tools import ToolExecutor
from .worker import AgentWorker


LOCAL_ORIGIN = re.compile(r"^https?://(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?$")
TASK_PATH = re.compile(
    r"^/api/agent/tasks/(?P<task_id>[0-9a-f-]{36})(?:/(?P<action>approve|cancel))?$",
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
        self.tools = ToolExecutor(config)
        self.worker_thread: threading.Thread | None = None


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
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/healthz":
            return self._send_json(
                {
                    "status": "ok",
                    "mode": "local_sqlite",
                    "worker_id": self.server.config.worker_id,
                    "worker_online": bool(
                        self.server.worker_thread and self.server.worker_thread.is_alive()
                    ),
                    "api": f"http://{self.server.server_address[0]}:{self.server.server_address[1]}",
                }
            )
        if path == "/api/agent/tools":
            return self._send_json({"tools": self.server.tools.catalog()})
        if path == "/api/agent/connectors":
            connectors = self.server.tools.connector_catalog()
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
                    "inventory": inventory,
                }
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
            clean_title = (
                title.strip()[:120]
                if isinstance(title, str) and title.strip()
                else " ".join(prompt.split())[:120]
            )
            task = self.server.store.enqueue(clean_title, prompt, "local-operator")
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
        return not origin or bool(LOCAL_ORIGIN.fullmatch(origin))

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
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        origin = self.headers.get("Origin")
        if origin and LOCAL_ORIGIN.fullmatch(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.end_headers()
        if body:
            self.wfile.write(body)


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
    worker = AgentWorker(config, store)
    worker_thread = threading.Thread(
        target=worker.start,
        kwargs={"poll_seconds": poll_seconds},
        name="fathiya-local-worker",
        daemon=True,
    )
    server.worker_thread = worker_thread
    worker_thread.start()
    print(
        json.dumps(
            {
                "status": "online",
                "api": f"http://{host}:{server.server_address[1]}",
                "worker_id": config.worker_id,
                "store": config.store,
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
