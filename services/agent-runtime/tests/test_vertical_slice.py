from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fathiya_runtime.config import RuntimeConfig
from fathiya_runtime.models import AgentModelRouter, OpenRouterClient
from fathiya_runtime.planner import build_plan
from fathiya_runtime.retrieval import KnowledgeRetriever
from fathiya_runtime.risk import classify_risk
from fathiya_runtime.store import SQLiteTaskStore
from fathiya_runtime.tools import ToolExecutionError, ToolExecutor
from fathiya_runtime.worker import AgentWorker


class AgentRuntimeVerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "runtime.db"
        os.environ["FATHIYA_STORE"] = "sqlite"
        os.environ["FATHIYA_SQLITE_PATH"] = str(self.db_path)
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_GENERATION"] = "false"
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

        def cancel_during_execution(
            _tool: str,
            _prompt: str,
            _args: dict | None = None,
            _context: list | None = None,
        ) -> dict[str, bool]:
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

    def test_model_router_falls_back_to_local_huggingface(self) -> None:
        router = AgentModelRouter(
            "configured-key",
            "remote-model",
            enable_local_generation=True,
            local_model="local-model",
            local_max_new_tokens=64,
        )
        router.openrouter.complete = lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("remote failed")
        )
        router.local.complete = lambda *_args, **_kwargs: '{"steps":[]}'

        result = router.complete("system", "user", json_mode=True)

        self.assertEqual(result, '{"steps":[]}')
        self.assertEqual(router.last_provider, "huggingface_local")
        self.assertIn("remote failed", router.last_error)

    def test_connected_tool_inventory_is_available(self) -> None:
        result = AgentWorker(self.config, self.store).tools.execute(
            "connected_tool_inventory",
            "اعرض أدوات Zapier",
        )

        self.assertTrue(result["available"])
        self.assertGreaterEqual(result["zapier_app_count"], 20)
        self.assertGreater(result["zapier_action_count"], result["zapier_app_count"])

    def test_fallback_plan_executes_multiple_connected_tools(self) -> None:
        task = self.store.enqueue(
            "تشغيل متعدد",
            "اعرض أدوات Zapier وحالة مستودع GitHub",
        )
        worker = AgentWorker(self.config, self.store)
        calls: list[dict] = []

        def execute(
            tool: str,
            _prompt: str,
            args: dict | None = None,
            context: list | None = None,
        ) -> dict:
            calls.append(
                {
                    "tool": tool,
                    "args": args or {},
                    "prior_result_count": len(context or []),
                }
            )
            return {"tool": tool, "executed": True}

        worker.tools.execute = execute
        worker.start(once=True)
        completed = self.store.get_task(task["id"])

        self.assertEqual(completed["status"], "completed")
        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(calls[0]["prior_result_count"], 0)
        self.assertEqual(calls[-1]["prior_result_count"], len(calls) - 1)
        self.assertEqual(len(completed["result"]["tool_results"]), len(calls))

    def test_plan_selected_sensitive_tool_waits_for_approval(self) -> None:
        task = self.store.enqueue("بوابة ديناميكية", "نفذ مهمة داخلية")
        worker = AgentWorker(self.config, self.store)
        plan = [
            {
                "id": "retrieve",
                "kind": "retrieval",
                "tool": "knowledge_search",
                "description": "retrieve",
            },
            {
                "id": "execute-1",
                "kind": "tool",
                "tool": "n8n_webhook",
                "description": "external action",
                "args": {"payload": {"test": True}},
            },
        ]

        with patch("fathiya_runtime.worker.build_plan", return_value=plan):
            worker.start(once=True)

        gated = self.store.get_detail(task["id"])
        self.assertEqual(gated["task"]["status"], "awaiting_approval")
        self.assertEqual(gated["task"]["risk_class"], "external")
        self.assertEqual(gated["task"]["approval_state"], "pending")
        self.assertEqual(len(gated["receipts"]), 0)
        self.assertEqual(gated["events"][-1]["event_type"], "approval_required")

    def test_openrouter_plan_uses_only_registered_tools(self) -> None:
        model = OpenRouterClient("configured-key", "test-model")
        model.complete = lambda *_args, **_kwargs: (
            '{"steps": ['
            '{"tool": "repo_status", "description": "status", "args": {}},'
            '{"tool": "invented_tool", "description": "bad", "args": {}}'
            "]} trailing model text"
        )
        catalog = ToolExecutor(self.config).catalog()
        plan = build_plan(
            {"prompt": "inspect repo"},
            [],
            model,
            catalog,
            max_tool_steps=4,
        )
        tools = [step["tool"] for step in plan if step.get("kind") == "tool"]

        self.assertEqual(tools, ["repo_status"])
        self.assertEqual(plan[0]["planner_mode"], "openrouter")

    def test_model_plan_accepts_direct_json_array(self) -> None:
        model = OpenRouterClient("configured-key", "test-model")
        model.complete = lambda *_args, **_kwargs: (
            '```json\n[{"tool":"github_repo_info","description":"inspect","args":{}}]\n```'
        )
        plan = build_plan(
            {"prompt": "inspect repo"},
            [],
            model,
            ToolExecutor(self.config).catalog(),
            max_tool_steps=4,
        )
        tools = [step["tool"] for step in plan if step.get("kind") == "tool"]

        self.assertEqual(tools, ["github_repo_info"])
        self.assertEqual(plan[0]["planner_mode"], "openrouter")

    def test_tool_catalog_exposes_extensible_execution_profiles(self) -> None:
        catalog = ToolExecutor(self.config).catalog()
        by_name = {tool["name"]: tool for tool in catalog}

        self.assertIn("knowledge_ingest_url", by_name)
        self.assertIn("n8n_webhook", by_name)
        self.assertTrue(by_name["n8n_webhook"]["requires_approval"])
        profiles = {profile["name"] for profile in by_name["command_profile"]["profiles"]}
        self.assertIn("runtime_tests", profiles)
        self.assertIn("repo_build", profiles)

    def test_command_profile_uses_runtime_python_interpreter(self) -> None:
        executor = ToolExecutor(self.config)
        with patch.object(
            executor,
            "_run",
            return_value={"return_code": 0, "stdout": "ok", "stderr": "", "command": []},
        ) as run:
            result = executor.execute(
                "command_profile",
                "run tests",
                {"profile": "runtime_tests"},
            )

        self.assertEqual(run.call_args.args[0][0], sys.executable)
        self.assertEqual(result["return_code"], 0)

    def test_failed_tool_emits_failed_receipt(self) -> None:
        task = self.store.enqueue("فشل أداة", "نفذ اختبار داخلي آمن")
        worker = AgentWorker(self.config, self.store)

        def fail_tool(*_args, **_kwargs):
            raise ToolExecutionError(
                "profile failed",
                {"tool": "command_profile", "profile": "test", "return_code": 1},
            )

        worker.tools.execute = fail_tool
        worker.start(once=True)
        detail = self.store.get_detail(task["id"])

        self.assertEqual(detail["task"]["status"], "failed")
        self.assertEqual(detail["task"]["result"]["error_type"], "ToolExecutionError")
        self.assertEqual(len(detail["receipts"]), 1)
        self.assertEqual(detail["receipts"][0]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
