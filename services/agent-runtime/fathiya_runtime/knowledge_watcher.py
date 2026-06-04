from __future__ import annotations

import hashlib
import json
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .knowledge_mission import build_knowledge_mission_prompt
from .store import TaskStore


SUPPORTED_SUFFIXES = {".md", ".txt", ".json", ".csv"}


class KnowledgeIntakeWatcher:
    """Turns new local inbox reports into receipt-backed knowledge missions."""

    def __init__(self, config: RuntimeConfig, store: TaskStore):
        self.config = config
        self.store = store
        self.root = config.knowledge_watch_root.resolve()
        self.state_path = config.knowledge_watch_state_path.resolve()
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._state = self._load_state()
        self._last_scan_at: str | None = None
        self._last_error: str | None = None
        self._last_enqueued = self._latest_enqueued_record()
        self._enqueued_count = int(self._state.get("enqueued_count") or 0)
        self._ignored_count = 0

    def start(self) -> dict[str, Any]:
        with self._lock:
            if not self.config.knowledge_watch_enabled:
                return self.status()
            if self._thread and self._thread.is_alive():
                return self.status()
            self.root.mkdir(parents=True, exist_ok=True)
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="fathiya-knowledge-intake-watcher",
                daemon=True,
            )
            self._thread.start()
            return self.status()

    def stop(self) -> dict[str, Any]:
        self._stop.set()
        with self._lock:
            thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self.config.knowledge_watch_seconds * 2))
        return self.status()

    def status(self) -> dict[str, Any]:
        with self._lock:
            files = self._state.get("files", {})
            last_enqueued = dict(self._last_enqueued) if self._last_enqueued else None
            if last_enqueued and last_enqueued.get("task_id"):
                task = self.store.get_task(str(last_enqueued["task_id"]))
                if task:
                    last_enqueued.update(
                        {
                            "task_status": task["status"],
                            "task_progress": task["progress"],
                            "task_current_step": task["current_step"],
                        }
                    )
            return {
                "enabled": self.config.knowledge_watch_enabled,
                "running": bool(self._thread and self._thread.is_alive()),
                "watch_root": str(self.root),
                "scan_interval_seconds": self.config.knowledge_watch_seconds,
                "max_report_characters": self.config.knowledge_watch_max_characters,
                "supported_extensions": sorted(SUPPORTED_SUFFIXES),
                "tracked_files": len(files) if isinstance(files, dict) else 0,
                "enqueued_count": self._enqueued_count,
                "ignored_count": self._ignored_count,
                "last_scan_at": self._last_scan_at,
                "last_error": self._last_error,
                "last_enqueued": last_enqueued,
            }

    def scan_once(self) -> dict[str, Any]:
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            enqueued: list[dict[str, Any]] = []
            ignored = 0
            try:
                for path in sorted(self.root.rglob("*")):
                    if not path.is_file() or path.is_symlink():
                        continue
                    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                        ignored += 1
                        continue
                    result = self._ingest_file(path)
                    if result:
                        enqueued.append(result)
                self._ignored_count = ignored
                self._last_error = None
            except Exception as exc:
                self._last_error = f"{type(exc).__name__}: {str(exc)[:300]}"
            self._last_scan_at = datetime.now(UTC).isoformat()
            self._save_state()
            return {
                "status": self.status(),
                "enqueued": enqueued,
            }

    def _run(self) -> None:
        while not self._stop.is_set():
            self.scan_once()
            self._stop.wait(self.config.knowledge_watch_seconds)

    def _ingest_file(self, path: Path) -> dict[str, Any] | None:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError:
            return None
        key = relative.as_posix()
        files = self._state.setdefault("files", {})
        stat = resolved.stat()
        if stat.st_size > self.config.knowledge_watch_max_characters * 4:
            marker = hashlib.sha256(
                f"{stat.st_size}:{stat.st_mtime_ns}".encode("ascii")
            ).hexdigest()
            previous = files.get(key) if isinstance(files, dict) else None
            if not isinstance(previous, dict) or previous.get("sha256") != marker:
                self._remember_ignored(files, key, marker, "report_too_large")
            return None
        raw = resolved.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        previous = files.get(key) if isinstance(files, dict) else None
        if isinstance(previous, dict) and previous.get("sha256") == digest:
            return None
        text = raw.decode("utf-8", errors="replace").strip()
        if len(text) < 3:
            self._remember_ignored(files, key, digest, "empty_or_too_short")
            return None
        if len(text) > self.config.knowledge_watch_max_characters:
            self._remember_ignored(files, key, digest, "report_too_large")
            return None

        source_name = key
        objective = self.config.knowledge_watch_objective
        content = text
        if path.name.lower().endswith(".mission.json"):
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                self._remember_ignored(files, key, digest, f"invalid_mission_json:{exc.msg}")
                return None
            if not isinstance(payload, dict):
                self._remember_ignored(files, key, digest, "mission_payload_not_object")
                return None
            source_name = str(payload.get("source_name") or key)
            objective = str(payload.get("objective") or objective)
            report_content = payload.get("content")
            content = (
                report_content
                if isinstance(report_content, str)
                else json.dumps(report_content, ensure_ascii=False)
            )

        try:
            prompt = build_knowledge_mission_prompt(source_name, objective, content)
        except ValueError as exc:
            self._remember_ignored(files, key, digest, f"invalid_mission:{exc}")
            return None
        title = f"استيعاب تلقائي: {source_name}"[:120]
        task = self.store.enqueue(title, prompt, "local-knowledge-watcher")
        captured_at = datetime.now(UTC).isoformat()
        record = {
            "path": key,
            "source_name": source_name,
            "sha256": digest,
            "task_id": task["id"],
            "task_status": task["status"],
            "captured_at": captured_at,
        }
        files[key] = record
        self._enqueued_count += 1
        self._state["enqueued_count"] = self._enqueued_count
        self._last_enqueued = record
        return record

    @staticmethod
    def _remember_ignored(
        files: dict[str, Any],
        key: str,
        digest: str,
        reason: str,
    ) -> None:
        files[key] = {
            "path": key,
            "sha256": digest,
            "ignored": True,
            "reason": reason[:300],
            "captured_at": datetime.now(UTC).isoformat(),
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema_version": 1, "files": {}, "enqueued_count": 0}
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"schema_version": 1, "files": {}, "enqueued_count": 0}
        if not isinstance(payload, dict) or not isinstance(payload.get("files"), dict):
            return {"schema_version": 1, "files": {}, "enqueued_count": 0}
        return payload

    def _latest_enqueued_record(self) -> dict[str, Any] | None:
        files = self._state.get("files", {})
        if not isinstance(files, dict):
            return None
        records = [
            value
            for value in files.values()
            if isinstance(value, dict) and value.get("task_id")
        ]
        if not records:
            return None
        return max(records, key=lambda value: str(value.get("captured_at") or ""))

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            **self._state,
            "schema_version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.state_path)
