from __future__ import annotations

import argparse
import json
from typing import Any

from .config import RuntimeConfig
from .store import SQLiteTaskStore, SupabaseTaskStore, TaskStore
from .worker import AgentWorker


def build_store(config: RuntimeConfig) -> TaskStore:
    if config.store == "supabase":
        return SupabaseTaskStore(config.supabase_url, config.supabase_service_role_key)
    return SQLiteTaskStore(config.sqlite_path)


def main() -> None:
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

    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=20)

    show = sub.add_parser("show")
    show.add_argument("task_id")

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
    elif args.command == "list":
        print(json.dumps(store.list_tasks(args.limit), ensure_ascii=False, indent=2))
    elif args.command == "show":
        print(json.dumps(store.get_detail(args.task_id), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
