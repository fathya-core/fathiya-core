"""
core/logger.py — نظام تسجيل منظم بصيغة JSON

يكتب سجلات منظمة في مجلد logs/ بصيغة JSON.
كل سطر في ملف السجل هو كائن JSON مستقل (JSON Lines).

أنواع السجلات:
- sessions.jsonl — سجل الجلسات
- errors.jsonl   — سجل الأخطاء
- runs.jsonl     — سجل التشغيل (pipeline runs)

كل سجل يحتوي:
- timestamp  — الطابع الزمني (ISO 8601)
- level      — مستوى السجل (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- component  — المكوّن المصدر (framer, solver, evaluator, router, إلخ)
- message    — الرسالة
- metadata   — بيانات إضافية (dict)

الاستخدام:
    from core.logger import fathiya_logger

    fathiya_logger.info("solver", "بدأ توليد الرد", {"user_input": "..."})
    fathiya_logger.error("evaluator", "فشل التقييم", {"error": str(e)})
    fathiya_logger.log_session(session_id=1, user_input="...", verdict="approve")
    fathiya_logger.log_run(run_id="abc", stages={"framer": 1.2, "solver": 3.5})
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class FathiyaLogger:
    """
    نظام تسجيل منظم — يكتب JSON Lines في مجلد logs/.

    ملفات السجل:
    - logs/sessions.jsonl — الجلسات
    - logs/errors.jsonl   — الأخطاء
    - logs/runs.jsonl     — التشغيل
    """

    def __init__(self, log_dir: str = "logs") -> None:
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)

        self._sessions_file = self._log_dir / "sessions.jsonl"
        self._errors_file = self._log_dir / "errors.jsonl"
        self._runs_file = self._log_dir / "runs.jsonl"
        self._last_write_error: Optional[Dict[str, Any]] = None

    def _now_iso(self) -> str:
        """الطابع الزمني الحالي بصيغة ISO 8601"""
        return datetime.now(timezone.utc).isoformat()

    def _write_entry(self, filepath: Path, entry: Dict[str, Any]) -> bool:
        """كتابة سجل واحد في ملف JSON Lines"""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self._last_write_error = None
            return True
        except OSError as exc:
            self._last_write_error = {
                "path": str(filepath),
                "error": str(exc),
                "timestamp": self._now_iso(),
            }
            fallback_entry = self._build_entry(
                "ERROR",
                "logger",
                "فشل في كتابة سجل",
                dict(self._last_write_error),
            )
            if filepath != self._errors_file:
                try:
                    with open(self._errors_file, "a", encoding="utf-8") as f:
                        f.write(json.dumps(fallback_entry, ensure_ascii=False, default=str) + "\n")
                    return False
                except OSError:
                    pass
            try:
                sys.stderr.write(json.dumps(fallback_entry, ensure_ascii=False, default=str) + "\n")
            except OSError:
                pass
            return False

    def _build_entry(
        self,
        level: str,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """بناء كائن سجل"""
        return {
            "timestamp": self._now_iso(),
            "level": level.upper(),
            "component": component,
            "message": message,
            "metadata": metadata or {},
        }

    @property
    def last_write_error(self) -> Optional[Dict[str, Any]]:
        return dict(self._last_write_error) if self._last_write_error else None

    # --- واجهة التسجيل العامة ---

    def debug(
        self,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل رسالة تشخيص"""
        entry = self._build_entry("DEBUG", component, message, metadata)
        return self._write_entry(self._runs_file, entry)

    def info(
        self,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل رسالة معلومات"""
        entry = self._build_entry("INFO", component, message, metadata)
        return self._write_entry(self._runs_file, entry)

    def warning(
        self,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل تحذير"""
        entry = self._build_entry("WARNING", component, message, metadata)
        return self._write_entry(self._runs_file, entry)

    def error(
        self,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل خطأ"""
        entry = self._build_entry("ERROR", component, message, metadata)
        return self._write_entry(self._errors_file, entry)

    def critical(
        self,
        component: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل خطأ حرج"""
        entry = self._build_entry("CRITICAL", component, message, metadata)
        return self._write_entry(self._errors_file, entry)

    # --- واجهات متخصصة ---

    def log_session(
        self,
        session_id: int,
        user_input: str,
        verdict: str,
        flow: str = "general",
        revised: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل جلسة كاملة"""
        entry = self._build_entry("INFO", "session", "جلسة مكتملة", {
            "session_id": session_id,
            "user_input_preview": user_input[:100],
            "verdict": verdict,
            "flow": flow,
            "revised": revised,
            **(metadata or {}),
        })
        return self._write_entry(self._sessions_file, entry)

    def log_run(
        self,
        run_id: str,
        stages: Dict[str, float],
        total_time: float = 0.0,
        retries: int = 0,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """تسجيل تشغيل pipeline كامل"""
        run_metadata = {
            "run_id": run_id,
            "stages": stages,
            "total_time_seconds": round(total_time, 3),
            "success": success,
            **(metadata or {}),
        }
        if retries > 0:
            run_metadata["retries"] = retries
        entry = self._build_entry("INFO", "pipeline", "تشغيل مكتمل", run_metadata)
        return self._write_entry(self._runs_file, entry)

    def log_api_call(
        self,
        component: str,
        model: str,
        latency: float,
        success: bool,
        attempt: int = 1,
        error: Optional[str] = None
    ) -> bool:
        """تسجيل استدعاء API"""
        entry = self._build_entry(
            "INFO" if success else "WARNING",
            component,
            "استدعاء API",
            {
                "model": model,
                "latency_seconds": round(latency, 3),
                "success": success,
                "attempt": attempt,
                "error": error,
            }
        )
        return self._write_entry(self._runs_file, entry)

    # --- أدوات مساعدة ---

    def read_log(self, log_type: str = "runs", limit: int = 50) -> list:
        """
        قراءة آخر السجلات من ملف محدد.

        المعاملات:
            log_type — نوع السجل: "sessions", "errors", "runs"
            limit    — عدد السجلات المطلوبة
        """
        file_map = {
            "sessions": self._sessions_file,
            "errors": self._errors_file,
            "runs": self._runs_file,
        }

        filepath = file_map.get(log_type)
        if not filepath or not filepath.exists():
            return []

        entries: list = []
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except OSError:
            return []

        return entries[-limit:]

    def clear_logs(self) -> None:
        """مسح جميع ملفات السجل"""
        for filepath in [self._sessions_file, self._errors_file, self._runs_file]:
            if filepath.exists():
                filepath.unlink()


# --- نسخة واحدة (Singleton) للاستخدام في كل المشروع ---
fathiya_logger = FathiyaLogger()
