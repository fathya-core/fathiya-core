from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from typing import Any

from .config import RuntimeConfig
from .local_api import serve_local_control_plane
from .store import SQLiteTaskStore, SupabaseTaskStore, TaskStore, now_iso
from .tools import ToolExecutor
from .worker import AgentWorker


def build_store(config: RuntimeConfig) -> TaskStore:
    if config.store == "supabase":
        return SupabaseTaskStore(config.supabase_url, config.supabase_service_role_key)
    return SQLiteTaskStore(config.sqlite_path)


def main() -> None:
    _configure_console()
    parser = argparse.ArgumentParser(description="FATHIYA local agent runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")

    enqueue = sub.add_parser("enqueue")
    enqueue.add_argument("prompt")
    enqueue.add_argument("--title")
    enqueue.add_argument("--user-id", default="local-user")

    worker = sub.add_parser("worker")
    worker.add_argument("--once", action="store_true")
    worker.add_argument("--poll-seconds", type=float, default=3.0)

    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--poll-seconds", type=float, default=0.5)

    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)

    show = sub.add_parser("show")
    show.add_argument("task_id")

    approve = sub.add_parser("approve")
    approve.add_argument("task_id")

    cancel = sub.add_parser("cancel")
    cancel.add_argument("task_id")

    sub.add_parser("tools")

    args = parser.parse_args()
    config = RuntimeConfig.load()
    store = build_store(config)
    store.initialize()

    if args.command == "init":
        print(f"initialized {config.store} store")
    elif args.command == "enqueue":
        task = store.enqueue(args.title or args.prompt[:80], args.prompt, args.user_id)
        print(json.dumps(task, ensure_ascii=False, indent=2))
    elif args.command == "worker":
        count = AgentWorker(config, store).start(once=args.once, poll_seconds=args.poll_seconds)
        print(json.dumps({"processed": count}, ensure_ascii=False))
    elif args.command == "serve":
        serve_local_control_plane(
            config,
            store,
            host=args.host,
            port=args.port,
            poll_seconds=args.poll_seconds,
        )
    elif args.command == "list":
        print(json.dumps(store.list_tasks(args.limit), ensure_ascii=False, indent=2))
    elif args.command == "show":
        print(json.dumps(store.get_detail(args.task_id), ensure_ascii=False, indent=2))
    elif args.command == "approve":
        task = _require_task(store, args.task_id)
        if task["status"] != "awaiting_approval":
            raise SystemExit("task is not awaiting approval")
        store.update_task(
            task["id"],
            status="queued",
            approval_state="approved",
            current_step="تمت الموافقة، بانتظار المشغّل المحلي",
            error_message=None,
            last_heartbeat_at=now_iso(),
        )
        store.add_event(
            task,
            "approved",
            "وافق المشغل على خطة التنفيذ.",
            status="queued",
            step="approved",
            progress=task["progress"],
        )
        print(json.dumps(store.get_task(task["id"]), ensure_ascii=False, indent=2))
    elif args.command == "cancel":
        task = _require_task(store, args.task_id)
        if task["status"] not in {"queued", "running", "awaiting_approval", "stalled"}:
            raise SystemExit("task cannot be canceled")
        store.update_task(
            task["id"],
            status="canceled",
            current_step="ألغيت بواسطة المشغل",
            completed_at=datetime.now(UTC).isoformat(),
        )
        store.add_event(
            task,
            "canceled",
            "ألغى المشغل المهمة.",
            status="canceled",
            step="canceled",
            progress=task["progress"],
        )
        print(json.dumps(store.get_task(task["id"]), ensure_ascii=False, indent=2))
    elif args.command == "tools":
        print(json.dumps(ToolExecutor(config).catalog(), ensure_ascii=False, indent=2))


def _require_task(store: TaskStore, task_id: str) -> dict[str, Any]:
    task = store.get_task(task_id)
    if not task:
        raise SystemExit(f"task not found: {task_id}")
    return task


def _configure_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    main()
