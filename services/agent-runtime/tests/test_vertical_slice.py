from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fathiya_runtime.config import RuntimeConfig
from fathiya_runtime.models import OpenRouterClient
from fathiya_runtime.retrieval import KnowledgeRetriever
from fathiya_runtime.risk import classify_risk
from fathiya_runtime.store import SQLiteTaskStore
from fathiya_runtime.worker import AgentWorker


class AgentRuntimeVerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "runtime.db"
        os.environ["FATHIYA_STORE"] = "sqlite"
        os.environ["FATHIYA_SQLITE_PATH"] = str(self.db_path)
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ.pop("OPENROUTER_API_KEY", None)
        self.config = RuntimeConfig.load()
        self.store = SQLiteTaskStore(self.db_path)
        self.store.initialize()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_task_reaches_completed_with_receipt(self) -> None:
        task = self.store.enqueue("اختبار داخلي", "نفذ اختبار داخلي آمن")
        processed = AgentWorker(self.config, self.store).start(once=True)
        completed = self.store.get_task(task["id"])

        self.assertEqual(processed, 1)
        self.assertIsNotNone(completed)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(completed["progress"], 100)
        self.assertIn("tool_result", completed["result"])
        detail = self.store.get_detail(task["id"])
        self.assertIsNotNone(detail)
        self.assertGreater(len(detail["events"]), 1)
        self.assertEqual(len(detail["receipts"]), 1)

        with closing(sqlite3.connect(self.db_path)) as conn:
            receipt_count = conn.execute(
                "SELECT count(*) FROM receipts WHERE task_id=?", (task["id"],)
            ).fetchone()[0]
        self.assertEqual(receipt_count, 1)

    def test_old_running_task_becomes_stalled(self) -> None:
        task = self.store.enqueue("stalled", "اختبار توقف heartbeat")
        old = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        self.store.update_task(
            task["id"],
            status="running",
            last_heartbeat_at=old,
            current_step="waiting",
        )
        count = self.store.mark_stalled(age_seconds=120)
        stalled = self.store.get_task(task["id"])

        self.assertEqual(count, 1)
        self.assertEqual(stalled["status"], "stalled")

    def test_sensitive_task_waits_for_approval(self) -> None:
        task = self.store.enqueue("تداول", "نفذ صفقة شراء حقيقية")
        processed = AgentWorker(self.config, self.store).start(once=True)

        self.assertEqual(processed, 0)
        self.assertEqual(task["status"], "awaiting_approval")
        self.assertEqual(classify_risk(task["prompt"]).risk_class, "financial")

    def test_canceled_running_task_is_not_completed(self) -> None:
        task = self.store.enqueue("إلغاء", "نفذ اختبار داخلي آمن")
        worker = AgentWorker(self.config, self.store)

        def cancel_during_execution(_tool: str, _prompt: str) -> dict[str, bool]:
            self.store.update_task(
                task["id"],
                status="canceled",
                current_step="ألغيت أثناء التنفيذ",
                completed_at=datetime.now(UTC).isoformat(),
            )
            return {"executed": True}

        worker.tools.execute = cancel_during_execution
        worker.start(once=True)
        detail = self.store.get_detail(task["id"])

        self.assertIsNotNone(detail)
        self.assertEqual(detail["task"]["status"], "canceled")
        self.assertEqual(len(detail["receipts"]), 0)
        self.assertEqual(detail["events"][-1]["event_type"], "cancellation_observed")

    def test_retrieval_falls_back_when_hugging_face_is_unavailable(self) -> None:
        knowledge = Path(self.temp.name) / "knowledge"
        knowledge.mkdir()
        (knowledge / "runtime.md").write_text(
            "FATHIYA heartbeat progress receipt local worker",
            encoding="utf-8",
        )
        retriever = KnowledgeRetriever(
            knowledge,
            enable_hf=True,
            hf_model="not-used-without-sentence-transformers",
        )

        with patch.object(retriever, "_hf_search", return_value=None):
            results = retriever.search("heartbeat receipt")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].path, "runtime.md")
        self.assertEqual(retriever.last_mode, "keyword_fallback")

    def test_openrouter_evaluation_falls_back_on_provider_error(self) -> None:
        client = OpenRouterClient("configured-key", "test-model")

        def fail(*_args, **_kwargs):
            raise RuntimeError("provider unavailable")

        client.complete = fail
        evaluation = client.evaluate("test", {"evidence": True})

        self.assertTrue(evaluation["passed"])
        self.assertEqual(evaluation["mode"], "openrouter_error_fallback")
        self.assertEqual(evaluation["error_type"], "RuntimeError")

    def test_connected_tool_inventory_is_available(self) -> None:
        result = AgentWorker(self.config, self.store).tools.execute(
            "connected_tool_inventory",
            "اعرض أدوات Zapier",
        )

        self.assertTrue(result["available"])
        self.assertGreaterEqual(result["zapier_app_count"], 20)
        self.assertGreater(result["zapier_action_count"], result["zapier_app_count"])


if __name__ == "__main__":
    unittest.main()
