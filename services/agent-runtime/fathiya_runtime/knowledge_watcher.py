from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from io import BytesIO
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader

from .config import RuntimeConfig
from .knowledge_mission import build_knowledge_mission_prompt
from .store import TaskStore


TEXT_SUFFIXES = {".md", ".txt", ".json", ".csv"}
ARCHIVE_MEMBER_SUFFIXES = TEXT_SUFFIXES | {".pdf"}
SUPPORTED_SUFFIXES = TEXT_SUFFIXES | {".pdf", ".zip"}
MAX_BINARY_SOURCE_BYTES = 25 * 1024 * 1024
MAX_PDF_PAGES = 80
MAX_ZIP_MEMBERS = 40
MAX_ZIP_MEMBER_BYTES = 2 * 1024 * 1024
MAX_ZIP_TOTAL_BYTES = 8 * 1024 * 1024
REDACTION_MARKER = "[REDACTED_SECRET_LIKE_VALUE]"
SENSITIVE_TEXT_PATTERNS = [
    re.compile(r"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"),
]


class KnowledgeSourceError(ValueError):
    """Raised when a local knowledge source cannot be safely converted."""


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
        suffix = path.suffix.lower()
        max_source_bytes = (
            self.config.knowledge_watch_max_characters * 4
            if suffix in TEXT_SUFFIXES
            else MAX_BINARY_SOURCE_BYTES
        )
        if stat.st_size > max_source_bytes:
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

        source_name = key
        objective = self.config.knowledge_watch_objective
        try:
            content = self._content_from_source(path, raw, key)
        except KnowledgeSourceError as exc:
            self._remember_ignored(files, key, digest, str(exc))
            return None
        if len(content) < 3:
            self._remember_ignored(files, key, digest, "empty_or_too_short")
            return None

        if path.name.lower().endswith(".mission.json"):
            try:
                payload = json.loads(content)
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
            content = self._redact_sensitive_text(content)
            if len(content) > self.config.knowledge_watch_max_characters:
                self._remember_ignored(files, key, digest, "report_too_large")
                return None

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

    def _content_from_source(self, path: Path, raw: bytes, key: str) -> str:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return self._extract_pdf_content(raw, key)
        if suffix == ".zip":
            return self._extract_zip_content(raw, key)

        text = raw.decode("utf-8", errors="replace").strip()
        if len(text) > self.config.knowledge_watch_max_characters:
            raise KnowledgeSourceError("report_too_large")
        return self._redact_sensitive_text(text)

    def _extract_pdf_content(self, raw: bytes, source_name: str) -> str:
        try:
            reader = PdfReader(BytesIO(raw))
        except Exception as exc:
            raise KnowledgeSourceError(f"invalid_pdf:{type(exc).__name__}") from exc

        try:
            page_count = len(reader.pages)
        except Exception as exc:
            raise KnowledgeSourceError(f"invalid_pdf_pages:{type(exc).__name__}") from exc

        sections = [
            f"# PDF: {source_name}",
            "",
            f"Pages parsed: {min(page_count, MAX_PDF_PAGES)} of {page_count}.",
        ]
        extracted_pages = 0
        for page_index in range(min(page_count, MAX_PDF_PAGES)):
            try:
                page_text = reader.pages[page_index].extract_text() or ""
            except Exception as exc:
                page_text = f"[page extraction failed: {type(exc).__name__}]"
            page_text = page_text.strip()
            if not page_text:
                continue
            extracted_pages += 1
            sections.extend(("", f"## Page {page_index + 1}", "", page_text))
            if len("\n".join(sections)) >= self.config.knowledge_watch_max_characters:
                break

        if extracted_pages == 0:
            raise KnowledgeSourceError("pdf_text_empty")
        if page_count > MAX_PDF_PAGES:
            sections.extend(
                (
                    "",
                    (
                        f"[TRUNCATED: parsed first {MAX_PDF_PAGES} pages "
                        f"of {page_count}.]"
                    ),
                )
            )
        return self._limit_content("\n".join(sections))

    def _extract_zip_content(self, raw: bytes, source_name: str) -> str:
        try:
            archive = ZipFile(BytesIO(raw))
        except BadZipFile as exc:
            raise KnowledgeSourceError("invalid_zip") from exc

        with archive:
            sections = [
                f"# ZIP: {source_name}",
                "",
                "Extracted supported knowledge files from the archive.",
            ]
            skipped: list[str] = []
            included = 0
            total_bytes = 0
            for info in sorted(archive.infolist(), key=lambda item: item.filename.lower()):
                if info.is_dir():
                    continue
                member_name = self._safe_zip_member_name(info.filename)
                if not member_name:
                    skipped.append(f"{info.filename}: unsafe_name")
                    continue
                suffix = Path(member_name).suffix.lower()
                if suffix not in ARCHIVE_MEMBER_SUFFIXES:
                    skipped.append(f"{member_name}: unsupported_extension")
                    continue
                if included >= MAX_ZIP_MEMBERS:
                    skipped.append("remaining_entries: member_limit")
                    break
                if info.flag_bits & 0x1:
                    skipped.append(f"{member_name}: encrypted")
                    continue
                if info.file_size > MAX_ZIP_MEMBER_BYTES:
                    skipped.append(f"{member_name}: member_too_large")
                    continue
                if total_bytes + info.file_size > MAX_ZIP_TOTAL_BYTES:
                    skipped.append("remaining_entries: archive_byte_limit")
                    break

                try:
                    member_raw = archive.read(info)
                except RuntimeError as exc:
                    skipped.append(f"{member_name}: read_failed_{type(exc).__name__}")
                    continue

                total_bytes += len(member_raw)
                if suffix == ".pdf":
                    try:
                        member_text = self._extract_pdf_content(member_raw, member_name)
                    except KnowledgeSourceError as exc:
                        skipped.append(f"{member_name}: {exc}")
                        continue
                else:
                    member_text = member_raw.decode("utf-8", errors="replace").strip()

                if len(member_text) < 3:
                    skipped.append(f"{member_name}: empty_or_too_short")
                    continue
                included += 1
                sections.extend(("", f"## {member_name}", "", member_text))
                if len("\n".join(sections)) >= self.config.knowledge_watch_max_characters:
                    skipped.append("remaining_entries: content_limit")
                    break

        if included == 0:
            raise KnowledgeSourceError("zip_has_no_supported_knowledge_files")
        if skipped:
            sections.extend(("", "## Skipped archive entries", "", "\n".join(skipped[:12])))
            if len(skipped) > 12:
                sections.append(f"... {len(skipped) - 12} more skipped entries")
        return self._limit_content("\n".join(sections))

    def _limit_content(self, content: str) -> str:
        clean = self._redact_sensitive_text(content).strip()
        limit = self.config.knowledge_watch_max_characters
        if len(clean) <= limit:
            return clean
        marker = (
            "\n\n[TRUNCATED: source exceeded "
            "FATHIYA_KNOWLEDGE_WATCH_MAX_CHARACTERS.]"
        )
        return f"{clean[: max(0, limit - len(marker))].rstrip()}{marker}"

    @staticmethod
    def _redact_sensitive_text(content: str) -> str:
        redacted = content
        for pattern in SENSITIVE_TEXT_PATTERNS:
            redacted = pattern.sub(REDACTION_MARKER, redacted)
        return redacted

    @staticmethod
    def _safe_zip_member_name(name: str) -> str | None:
        normalized = name.replace("\\", "/").strip()
        if not normalized or normalized.startswith("/"):
            return None
        parts = [part for part in normalized.split("/") if part not in {"", "."}]
        if not parts or any(part == ".." for part in parts):
            return None
        return "/".join(parts)

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
