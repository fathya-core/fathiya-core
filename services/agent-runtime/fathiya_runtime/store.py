from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterator, Protocol
from urllib.parse import quote

import requests

from .risk import classify_risk


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class TaskStore(Protocol):
    def initialize(self) -> None: ...
    def register_worker(self, worker_id: str, name: str, capabilities: list[str]) -> None: ...
    def heartbeat_worker(self, worker_id: str, status: str) -> None: ...
    def enqueue(self, title: str, prompt: str, user_id: str = "local-user") -> dict[str, Any]: ...
    def claim_next(self, worker_id: str) -> dict[str, Any] | None: ...
    def update_task(self, task_id: str, **fields: Any) -> None: ...
    def add_event(
        self,
        task: dict[str, Any],
        event_type: str,
        message: str,
        *,
        status: str | None = None,
        step: str | None = None,
        progress: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None: ...
    def add_receipt(
        self,
        task: dict[str, Any],
        status: str,
        summary: str,
        evidence: dict[str, Any],
    ) -> str: ...
    def get_task(self, task_id: str) -> dict[str, Any] | None: ...
    def get_detail(self, task_id: str) -> dict[str, Any] | None: ...
    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]: ...
    def mark_stalled(self, age_seconds: int = 120) -> int: ...


def _attach_receipt_summary(
    task: dict[str, Any],
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    task["receipt_count"] = len(receipts)
    if receipts:
        latest = receipts[0]
        task["latest_receipt_id"] = latest.get("receipt_id")
        task["latest_receipt_status"] = latest.get("status")
        task["latest_receipt_at"] = latest.get("created_at")
        task["latest_receipt_summary"] = latest.get("summary")
    else:
        task["latest_receipt_id"] = None
        task["latest_receipt_status"] = None
        task["latest_receipt_at"] = None
        task["latest_receipt_summary"] = None
    return task


class SQLiteTaskStore:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS workers (
                  id TEXT PRIMARY KEY,
                  name TEXT NOT NULL,
                  status TEXT NOT NULL,
                  capabilities TEXT NOT NULL,
                  last_heartbeat_at TEXT,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS tasks (
                  id TEXT PRIMARY KEY,
                  user_id TEXT NOT NULL,
                  title TEXT NOT NULL,
                  prompt TEXT NOT NULL,
                  status TEXT NOT NULL,
                  progress INTEGER NOT NULL,
                  current_step TEXT,
                  risk_class TEXT NOT NULL,
                  requires_approval INTEGER NOT NULL,
                  approval_state TEXT NOT NULL,
                  worker_id TEXT,
                  plan TEXT NOT NULL,
                  result TEXT,
                  error_message TEXT,
                  last_heartbeat_at TEXT,
                  started_at TEXT,
                  completed_at TEXT,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  task_id TEXT NOT NULL,
                  user_id TEXT NOT NULL,
                  event_type TEXT NOT NULL,
                  status TEXT,
                  step TEXT,
                  message TEXT NOT NULL,
                  progress INTEGER,
                  payload TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS receipts (
                  id TEXT PRIMARY KEY,
                  receipt_id TEXT NOT NULL UNIQUE,
                  task_id TEXT NOT NULL,
                  user_id TEXT NOT NULL,
                  status TEXT NOT NULL,
                  summary TEXT NOT NULL,
                  evidence TEXT NOT NULL,
                  created_at TEXT NOT NULL
                );
                """
            )

    def register_worker(self, worker_id: str, name: str, capabilities: list[str]) -> None:
        timestamp = now_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO workers (id, name, status, capabilities, last_heartbeat_at, updated_at)
                VALUES (?, ?, 'online', ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  name=excluded.name,
                  status='online',
                  capabilities=excluded.capabilities,
                  last_heartbeat_at=excluded.last_heartbeat_at,
                  updated_at=excluded.updated_at
                """,
                (worker_id, name, json.dumps(capabilities), timestamp, timestamp),
            )

    def heartbeat_worker(self, worker_id: str, status: str) -> None:
        timestamp = now_iso()
        with self._connect() as conn:
            conn.execute(
                "UPDATE workers SET status=?, last_heartbeat_at=?, updated_at=? WHERE id=?",
                (status, timestamp, timestamp, worker_id),
            )

    def enqueue(self, title: str, prompt: str, user_id: str = "local-user") -> dict[str, Any]:
        task_id = str(uuid.uuid4())
        timestamp = now_iso()
        risk = classify_risk(prompt)
        status = "awaiting_approval" if risk.requires_approval else "queued"
        task = {
            "id": task_id,
            "user_id": user_id,
            "title": title,
            "prompt": prompt,
            "status": status,
            "progress": 0,
            "current_step": (
                "بانتظار موافقة المشغل"
                if risk.requires_approval
                else "بانتظار المشغّل المحلي"
            ),
            "risk_class": risk.risk_class,
            "requires_approval": risk.requires_approval,
            "approval_state": "pending" if risk.requires_approval else "not_required",
            "worker_id": None,
            "plan": [],
            "result": None,
            "error_message": None,
            "last_heartbeat_at": None,
            "started_at": None,
            "completed_at": None,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks VALUES (
                  :id, :user_id, :title, :prompt, :status, :progress, :current_step,
                  :risk_class, :requires_approval, :approval_state, :worker_id, :plan,
                  :result, :error_message, :last_heartbeat_at, :started_at, :completed_at,
                  :created_at, :updated_at
                )
                """,
                {
                    **task,
                    "requires_approval": int(risk.requires_approval),
                    "plan": "[]",
                },
            )
        self.add_event(
            task,
            "approval_required" if risk.requires_approval else "queued",
            (
                f"صُنفت المهمة {risk.risk_class} وتحتاج موافقة قبل التنفيذ."
                if risk.requires_approval
                else "تم إنشاء المهمة محليًا."
            ),
            status=status,
            progress=0,
            payload={"risk_class": risk.risk_class},
        )
        return task

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE status='queued' ORDER BY created_at LIMIT 1"
            ).fetchone()
            if not row:
                return None
            timestamp = now_iso()
            updated = conn.execute(
                """
                UPDATE tasks
                SET status='running', worker_id=?, started_at=COALESCE(started_at, ?),
                    last_heartbeat_at=?, updated_at=?
                WHERE id=? AND status='queued'
                """,
                (worker_id, timestamp, timestamp, timestamp, row["id"]),
            )
            if updated.rowcount != 1:
                return None
        return self.get_task(row["id"])

    def update_task(self, task_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields["updated_at"] = now_iso()
        for key in ("plan", "result"):
            if key in fields and fields[key] is not None:
                fields[key] = json.dumps(fields[key], ensure_ascii=False)
        fields["requires_approval"] = (
            int(fields["requires_approval"]) if "requires_approval" in fields else fields.get("requires_approval")
        )
        fields = {key: value for key, value in fields.items() if value is not None or key not in {"requires_approval"}}
        assignments = ", ".join(f"{key}=?" for key in fields)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE tasks SET {assignments} WHERE id=?",
                (*fields.values(), task_id),
            )

    def add_event(
        self,
        task: dict[str, Any],
        event_type: str,
        message: str,
        *,
        status: str | None = None,
        step: str | None = None,
        progress: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO events (
                  task_id, user_id, event_type, status, step, message, progress, payload, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["id"],
                    task["user_id"],
                    event_type,
                    status,
                    step,
                    message,
                    progress,
                    json.dumps(payload or {}, ensure_ascii=False),
                    now_iso(),
                ),
            )

    def add_receipt(
        self,
        task: dict[str, Any],
        status: str,
        summary: str,
        evidence: dict[str, Any],
    ) -> str:
        receipt_id = f"AR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}-{task['id'][:8]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO receipts (
                  id, receipt_id, task_id, user_id, status, summary, evidence, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    receipt_id,
                    task["id"],
                    task["user_id"],
                    status,
                    summary,
                    json.dumps(evidence, ensure_ascii=False),
                    now_iso(),
                ),
            )
        return receipt_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return self._decode_task(row) if row else None

    def get_detail(self, task_id: str) -> dict[str, Any] | None:
        task = self.get_task(task_id)
        if not task:
            return None
        with self._connect() as conn:
            event_rows = conn.execute(
                "SELECT * FROM events WHERE task_id=? ORDER BY created_at",
                (task_id,),
            ).fetchall()
            receipt_rows = conn.execute(
                "SELECT * FROM receipts WHERE task_id=? ORDER BY created_at DESC",
                (task_id,),
            ).fetchall()
        events = [dict(row) for row in event_rows]
        for event in events:
            event["payload"] = json.loads(event["payload"] or "{}")
        receipts = [dict(row) for row in receipt_rows]
        for receipt in receipts:
            receipt["evidence"] = json.loads(receipt["evidence"] or "{}")
        _attach_receipt_summary(task, receipts)
        return {"task": task, "events": events, "receipts": receipts}

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            tasks = [self._decode_task(row) for row in rows]
            if tasks:
                placeholders = ",".join("?" for _task in tasks)
                receipt_rows = conn.execute(
                    f"""
                    SELECT task_id, receipt_id, status, summary, created_at
                    FROM receipts
                    WHERE task_id IN ({placeholders})
                    ORDER BY created_at DESC
                    """,
                    tuple(task["id"] for task in tasks),
                ).fetchall()
            else:
                receipt_rows = []
        receipts_by_task: dict[str, list[dict[str, Any]]] = {}
        for row in receipt_rows:
            receipt = dict(row)
            receipts_by_task.setdefault(receipt["task_id"], []).append(receipt)
        for task in tasks:
            _attach_receipt_summary(task, receipts_by_task.get(task["id"], []))
        return tasks

    def mark_stalled(self, age_seconds: int = 120) -> int:
        threshold = (datetime.now(UTC) - timedelta(seconds=age_seconds)).isoformat()
        timestamp = now_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status='running' AND last_heartbeat_at IS NOT NULL AND last_heartbeat_at < ?
                """,
                (threshold,),
            ).fetchall()
            conn.execute(
                """
                UPDATE tasks SET status='stalled',
                  current_step='لم يصل heartbeat من المشغّل خلال دقيقتين',
                  updated_at=?
                WHERE status='running' AND last_heartbeat_at IS NOT NULL AND last_heartbeat_at < ?
                """,
                (timestamp, threshold),
            )
        for row in rows:
            task = self._decode_task(row)
            self.add_event(
                task,
                "stalled",
                "توقفت تحديثات المشغّل.",
                status="stalled",
                step="heartbeat_timeout",
            )
        return len(rows)

    @staticmethod
    def _decode_task(row: sqlite3.Row) -> dict[str, Any]:
        task = dict(row)
        task["requires_approval"] = bool(task["requires_approval"])
        task["plan"] = json.loads(task["plan"] or "[]")
        task["result"] = json.loads(task["result"]) if task["result"] else None
        return task


class SupabaseTaskStore:
    def __init__(self, url: str, service_role_key: str):
        if not url or not service_role_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
        self.url = f"{url.rstrip('/')}/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    def initialize(self) -> None:
        self._request("GET", "agent_tasks?select=id&limit=1")

    def register_worker(self, worker_id: str, name: str, capabilities: list[str]) -> None:
        self._request(
            "POST",
            "agent_workers?on_conflict=id",
            {
                "id": worker_id,
                "name": name,
                "status": "online",
                "capabilities": capabilities,
                "last_heartbeat_at": now_iso(),
            },
            prefer="resolution=merge-duplicates,return=minimal",
        )

    def heartbeat_worker(self, worker_id: str, status: str) -> None:
        self._request(
            "PATCH",
            f"agent_workers?id=eq.{worker_id}",
            {"status": status, "last_heartbeat_at": now_iso()},
            prefer="return=minimal",
        )

    def enqueue(self, title: str, prompt: str, user_id: str = "local-user") -> dict[str, Any]:
        risk = classify_risk(prompt)
        rows = self._request(
            "POST",
            "agent_tasks",
            {
                "user_id": user_id,
                "title": title,
                "prompt": prompt,
                "status": "awaiting_approval" if risk.requires_approval else "queued",
                "risk_class": risk.risk_class,
                "requires_approval": risk.requires_approval,
                "approval_state": "pending" if risk.requires_approval else "not_required",
                "current_step": (
                    "بانتظار موافقة المشغل"
                    if risk.requires_approval
                    else "بانتظار المشغّل المحلي"
                ),
            },
            prefer="return=representation",
        )
        return rows[0]

    def claim_next(self, worker_id: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            "agent_tasks?status=eq.queued&select=*&order=created_at.asc&limit=1",
        )
        if not rows:
            return None
        task = rows[0]
        timestamp = now_iso()
        claimed = self._request(
            "PATCH",
            f"agent_tasks?id=eq.{task['id']}&status=eq.queued",
            {
                "status": "running",
                "worker_id": worker_id,
                "started_at": task.get("started_at") or timestamp,
                "last_heartbeat_at": timestamp,
            },
            prefer="return=representation",
        )
        return claimed[0] if claimed else None

    def update_task(self, task_id: str, **fields: Any) -> None:
        self._request(
            "PATCH",
            f"agent_tasks?id=eq.{task_id}",
            fields,
            prefer="return=minimal",
        )

    def add_event(
        self,
        task: dict[str, Any],
        event_type: str,
        message: str,
        *,
        status: str | None = None,
        step: str | None = None,
        progress: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._request(
            "POST",
            "agent_task_events",
            {
                "task_id": task["id"],
                "user_id": task["user_id"],
                "event_type": event_type,
                "message": message,
                "status": status,
                "step": step,
                "progress": progress,
                "payload": payload or {},
            },
            prefer="return=minimal",
        )

    def add_receipt(
        self,
        task: dict[str, Any],
        status: str,
        summary: str,
        evidence: dict[str, Any],
    ) -> str:
        receipt_id = f"AR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}-{task['id'][:8]}"
        self._request(
            "POST",
            "agent_receipts",
            {
                "receipt_id": receipt_id,
                "task_id": task["id"],
                "user_id": task["user_id"],
                "status": status,
                "summary": summary,
                "evidence": evidence,
            },
            prefer="return=minimal",
        )
        return receipt_id

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        rows = self._request("GET", f"agent_tasks?id=eq.{task_id}&select=*&limit=1")
        return rows[0] if rows else None

    def get_detail(self, task_id: str) -> dict[str, Any] | None:
        task = self.get_task(task_id)
        if not task:
            return None
        events = self._request(
            "GET",
            f"agent_task_events?task_id=eq.{task_id}&select=*&order=created_at.asc",
        )
        receipts = self._request(
            "GET",
            f"agent_receipts?task_id=eq.{task_id}&select=*&order=created_at.desc",
        )
        _attach_receipt_summary(task, receipts)
        return {"task": task, "events": events, "receipts": receipts}

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        tasks = self._request(
            "GET",
            f"agent_tasks?select=*&order=created_at.desc&limit={int(limit)}",
        )
        if not tasks:
            return tasks
        task_ids = ",".join(str(task["id"]) for task in tasks)
        receipts = self._request(
            "GET",
            "agent_receipts"
            f"?task_id=in.({task_ids})"
            "&select=task_id,receipt_id,status,summary,created_at"
            "&order=created_at.desc",
        )
        receipts_by_task: dict[str, list[dict[str, Any]]] = {}
        for receipt in receipts:
            receipts_by_task.setdefault(receipt["task_id"], []).append(receipt)
        for task in tasks:
            _attach_receipt_summary(task, receipts_by_task.get(task["id"], []))
        return tasks

    def mark_stalled(self, age_seconds: int = 120) -> int:
        threshold = (datetime.now(UTC) - timedelta(seconds=age_seconds)).isoformat()
        encoded_threshold = quote(threshold, safe="")
        rows = self._request(
            "PATCH",
            f"agent_tasks?status=eq.running&last_heartbeat_at=lt.{encoded_threshold}",
            {
                "status": "stalled",
                "current_step": "لم يصل heartbeat من المشغّل خلال دقيقتين",
            },
            prefer="return=representation",
        )
        for task in rows:
            self.add_event(
                task,
                "stalled",
                "توقفت تحديثات المشغّل.",
                status="stalled",
                step="heartbeat_timeout",
            )
        return len(rows)

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        prefer: str | None = None,
    ) -> Any:
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        response = requests.request(
            method,
            f"{self.url}/{path}",
            headers=headers,
            json=body,
            timeout=30,
        )
        response.raise_for_status()
        if not response.content:
            return []
        return response.json()
