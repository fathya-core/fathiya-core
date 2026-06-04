from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from fathiya_runtime.config import RuntimeConfig
from fathiya_runtime.models import AgentModelRouter, OpenRouterClient
from fathiya_runtime.planner import build_plan
from fathiya_runtime.retrieval import KnowledgeRetriever
from fathiya_runtime.risk import classify_risk
from fathiya_runtime.store import SQLiteTaskStore
from fathiya_runtime.tools import ToolExecutionError, ToolExecutor
from fathiya_runtime.worker import AgentWorker, _deterministic_synthesis, _is_useful_synthesis


class AgentRuntimeVerticalSliceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "runtime.db"
        os.environ["FATHIYA_STORE"] = "sqlite"
        os.environ["FATHIYA_SQLITE_PATH"] = str(self.db_path)
        os.environ["FATHIYA_TRADING_SQLITE_PATH"] = str(
            Path(self.temp.name) / "trading.db"
        )
        os.environ["FATHIYA_TRADING_MARKET_PROVIDER"] = "synthetic_second_market"
        os.environ["FATHIYA_TRADING_SYMBOL"] = "TEST-USD"
        os.environ["FATHIYA_TRADING_TICK_SECONDS"] = "0.05"
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_GENERATION"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_PLANNING"] = "false"
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
        self.assertIn(
            "synthesis_started",
            {event["event_type"] for event in detail["events"]},
        )
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

    def test_local_model_planning_is_opt_in(self) -> None:
        router = AgentModelRouter(
            "",
            "remote-model",
            enable_local_generation=True,
            local_model="local-model",
            local_max_new_tokens=64,
        )
        with patch.object(router.local, "complete") as local_complete:
            plan = build_plan(
                {"prompt": "inspect repo"},
                [],
                router,
                ToolExecutor(self.config).catalog(),
                max_tool_steps=4,
            )

        tools = [step["tool"] for step in plan if step.get("kind") == "tool"]
        self.assertEqual(tools, ["repo_status"])
        self.assertEqual(plan[0]["planner_mode"], "local_fallback")
        self.assertIn("local planning disabled", plan[0]["planner_error"])
        local_complete.assert_not_called()

    def test_local_evaluation_uses_fast_deterministic_gate(self) -> None:
        router = AgentModelRouter(
            "",
            "remote-model",
            enable_local_generation=True,
            local_model="local-model",
            local_max_new_tokens=64,
        )
        with patch.object(router.local, "complete") as local_complete:
            evaluation = router.evaluate("inspect repo", {"tool_results": [{"ok": True}]})

        self.assertTrue(evaluation["passed"])
        self.assertEqual(evaluation["mode"], "local_deterministic_evaluation")
        local_complete.assert_not_called()

    def test_short_model_synthesis_is_rejected_for_evidence_summary(self) -> None:
        self.assertFalse(_is_useful_synthesis("###"))
        kali_results = [
            {
                "result": {
                    "tool": "kali_tool_inventory",
                    "available": True,
                    "found_commands": ["nmap", "python3"],
                }
            }
        ]
        self.assertFalse(
            _is_useful_synthesis(
                "اكتمل العمل بنجاح وتم عرض الأدوات المتاحة في النظام المحلي.",
                kali_results,
            )
        )
        self.assertTrue(
            _is_useful_synthesis(
                "Kali متاحة وتم التحقق من وجود nmap وpython3 داخل WSL بنجاح.",
                kali_results,
            )
        )
        summary = _deterministic_synthesis(
            [
                {
                    "result": {
                        "tool": "n8n_status",
                        "available": True,
                        "version": "2.23.2",
                    }
                },
                {
                    "result": {
                        "tool": "n8n_workflows",
                        "available": False,
                        "status_code": 401,
                    }
                },
            ],
            5,
        )

        self.assertIn("n8n المحلية متاحة بإصدار 2.23.2", summary)
        self.assertIn("N8N_API_KEY", summary)
        self.assertIn("5 مصادر", summary)

    def test_connected_tool_inventory_is_available(self) -> None:
        result = AgentWorker(self.config, self.store).tools.execute(
            "connected_tool_inventory",
            "اعرض أدوات Zapier",
        )

        self.assertTrue(result["available"])
        self.assertGreaterEqual(result["zapier_app_count"], 20)
        self.assertGreater(result["zapier_action_count"], result["zapier_app_count"])

    def test_fallback_plan_controls_primary_paper_trading_agent(self) -> None:
        catalog = ToolExecutor(self.config).catalog()
        model = AgentModelRouter(
            "",
            "remote-model",
            enable_local_generation=False,
            local_model="local-model",
            local_max_new_tokens=64,
        )

        status_plan = build_plan(
            {"prompt": "اعرض حالة وكيل التداول وجودة التنبؤ"},
            [],
            model,
            catalog,
            max_tool_steps=4,
        )
        start_plan = build_plan(
            {"prompt": "شغّل وكيل التداول الورقي"},
            [],
            model,
            catalog,
            max_tool_steps=4,
        )

        self.assertEqual(
            [step["tool"] for step in status_plan if step.get("kind") == "tool"],
            ["trading_status"],
        )
        self.assertEqual(
            [step["tool"] for step in start_plan if step.get("kind") == "tool"],
            ["trading_start"],
        )
        research_plan = build_plan(
            {"prompt": "ابحث عن استراتيجيات التداول الحديثة"},
            [],
            model,
            catalog,
            max_tool_steps=4,
        )
        self.assertNotIn(
            "trading_status",
            [step["tool"] for step in research_plan if step.get("kind") == "tool"],
        )
        stop_loss_plan = build_plan(
            {"prompt": "اشرح وقف الخسارة في التداول"},
            [],
            model,
            catalog,
            max_tool_steps=4,
        )
        self.assertNotIn(
            "trading_stop",
            [step["tool"] for step in stop_loss_plan if step.get("kind") == "tool"],
        )
        refresh_plan = build_plan(
            {"prompt": "حدّث مستشار استراتيجية وكيل التداول"},
            [],
            model,
            catalog,
            max_tool_steps=4,
        )
        self.assertEqual(
            [step["tool"] for step in refresh_plan if step.get("kind") == "tool"],
            ["trading_strategy_refresh"],
        )

    def test_trading_tools_share_one_paper_agent(self) -> None:
        executor = ToolExecutor(self.config)
        started = executor.execute("trading_start", "شغّل وكيل التداول الورقي")
        try:
            status = executor.execute("trading_status", "اعرض حالة وكيل التداول")
            self.assertTrue(started["trading"]["running"])
            self.assertTrue(status["trading"]["running"])
            self.assertEqual(status["trading"]["symbol"], "TEST-USD")
            self.assertFalse(status["trading"]["live_execution_enabled"])
        finally:
            stopped = executor.execute("trading_stop", "أوقف وكيل التداول الورقي")
        self.assertFalse(stopped["trading"]["running"])

    def test_trading_status_task_completes_with_receipt(self) -> None:
        task = self.store.enqueue(
            "حالة وكيل التداول",
            "اعرض حالة وكيل التداول وجودة التنبؤ",
        )

        worker = AgentWorker(self.config, self.store)
        with (
            patch.object(worker.retriever, "search") as retrieve,
            patch.object(worker, "_synthesize") as synthesize,
        ):
            processed = worker.start(once=True)
        detail = self.store.get_detail(task["id"])

        retrieve.assert_not_called()
        synthesize.assert_not_called()
        self.assertEqual(processed, 1)
        self.assertEqual(detail["task"]["status"], "completed")
        self.assertEqual(
            detail["task"]["result"]["tool_results"][0]["result"]["tool"],
            "trading_status",
        )
        self.assertIn("وكيل التداول Paper", detail["task"]["result"]["synthesis"])
        self.assertEqual(
            detail["task"]["result"]["model_trace"]["planner_provider"],
            "local_fast_control",
        )
        self.assertEqual(
            detail["task"]["result"]["model_trace"]["synthesis_provider"],
            "local_deterministic_fast_control",
        )
        self.assertEqual(len(detail["receipts"]), 1)

    def test_trading_strategy_refresh_uses_model_and_validates_advisory(self) -> None:
        executor = ToolExecutor(self.config)
        model = Mock()
        model.available = True
        model.last_provider = "openrouter"
        model.complete.return_value = (
            '{"action":"sell","confidence":0.82,"rationale":"measured downside risk"}'
        )
        executor.set_model_router(model)

        result = executor.execute(
            "trading_strategy_refresh",
            "حدّث مستشار استراتيجية وكيل التداول",
        )
        status = executor.execute("trading_status", "اعرض حالة وكيل التداول")

        self.assertFalse(result["fallback"])
        self.assertEqual(result["model_provider"], "openrouter")
        self.assertEqual(result["advisory"]["action"], "sell")
        self.assertEqual(result["advisory"]["confidence"], 0.82)
        self.assertTrue(status["trading"]["strategy_advisory"]["active"])
        self.assertEqual(
            status["trading"]["strategy_advisory_policy"]["mode"],
            "veto_only",
        )
        model.complete.assert_called_once()

    def test_trading_strategy_refresh_falls_back_without_model(self) -> None:
        result = ToolExecutor(self.config).execute(
            "trading_strategy_refresh",
            "حدّث مستشار استراتيجية وكيل التداول",
        )

        self.assertTrue(result["fallback"])
        self.assertEqual(result["model_provider"], "deterministic_fallback")
        self.assertEqual(result["advisory"]["action"], "hold")
        self.assertEqual(result["advisory"]["confidence"], 0.0)

    def test_trading_strategy_refresh_task_completes_with_safe_fallback(self) -> None:
        task = self.store.enqueue(
            "تحديث مستشار التداول",
            "حدّث مستشار استراتيجية وكيل التداول",
        )

        processed = AgentWorker(self.config, self.store).start(once=True)
        detail = self.store.get_detail(task["id"])
        result = detail["task"]["result"]["tool_results"][0]["result"]

        self.assertEqual(processed, 1)
        self.assertEqual(detail["task"]["status"], "completed")
        self.assertEqual(result["tool"], "trading_strategy_refresh")
        self.assertTrue(result["fallback"])
        self.assertEqual(result["advisory"]["confidence"], 0.0)
        self.assertFalse(result["policy"]["can_originate_orders"])
        self.assertFalse(result["live_execution_enabled"])
        self.assertEqual(
            detail["task"]["result"]["model_trace"]["synthesis_provider"],
            "local_deterministic_tool_summary",
        )

    def test_kali_inventory_uses_wsl_safe_explicit_commands(self) -> None:
        executor = ToolExecutor(self.config)
        paths = "\n".join(
            [
                "/usr/bin/nmap",
                "/usr/bin/nuclei",
                "/usr/bin/httpx",
                "/usr/bin/subfinder",
                "/usr/bin/git",
                "/usr/bin/python3",
            ]
        )
        run_result = {
            "command": [],
            "return_code": 0,
            "stdout": f"{paths}\n",
            "stderr": "",
        }

        with patch.object(executor, "_run", return_value=run_result) as run:
            result = executor.execute("kali_tool_inventory", "اعرض أدوات كالي")

        script = run.call_args.args[0][-1]
        self.assertNotIn("$cmd", script)
        self.assertIn("command -v nmap", script)
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["missing_commands"], [])
        self.assertEqual(len(result["found_commands"]), 6)

    def test_kali_inventory_synthesis_reports_real_availability(self) -> None:
        summary = _deterministic_synthesis(
            [
                {
                    "result": {
                        "tool": "kali_tool_inventory",
                        "available": True,
                        "found_commands": ["nmap", "git", "python3"],
                        "missing_commands": ["nuclei", "httpx", "subfinder"],
                    }
                }
            ],
            0,
        )

        self.assertIn("تم العثور على 3 أدوات", summary)
        self.assertIn("أدوات Kali غير المتاحة", summary)

    def test_connector_catalog_exposes_readiness_and_dynamic_approval(self) -> None:
        executor = ToolExecutor(self.config)
        connectors = {item["name"]: item for item in executor.connector_catalog()}

        self.assertTrue(connectors["n8n_health"]["configured"])
        self.assertFalse(connectors["n8n_health"]["requires_approval"])
        self.assertTrue(connectors["n8n_health"]["bridge_dispatch_allowed"])
        self.assertFalse(connectors["n8n_fathiya_webhook"]["bridge_dispatch_allowed"])
        self.assertEqual(
            {profile["name"] for profile in executor.bridge_dispatch_profiles()},
            {
                "n8n_health",
                "n8n_workflows",
                "zapier_fathiya_webhook",
                "cursor_agent_bridge",
                "manus_agent_bridge",
            },
        )
        self.assertTrue(connectors["zapier_fathiya_webhook"]["requires_approval"])
        requirement = executor.approval_requirement(
            "connector_profile",
            {"profile": "zapier_fathiya_webhook"},
        )
        self.assertTrue(requirement.required)
        self.assertEqual(requirement.risk_class, "external")

    def test_connector_profile_executes_configured_read_connector(self) -> None:
        executor = ToolExecutor(self.config)
        response = Mock(ok=True, status_code=200, text='{"status":"ok"}')

        with patch("fathiya_runtime.tools.requests.request", return_value=response) as request:
            result = executor.execute(
                "connector_profile",
                "افحص n8n",
                {"profile": "n8n_health"},
            )

        self.assertTrue(result["available"])
        self.assertEqual(result["response"], {"status": "ok"})
        self.assertEqual(result["profile"], "n8n_health")
        self.assertEqual(request.call_args.args[0], "GET")
        self.assertEqual(request.call_args.args[1], "http://127.0.0.1:5678/healthz")

    def test_connector_network_error_does_not_leak_webhook_url(self) -> None:
        previous = os.environ.get("FATHIYA_ZAPIER_WEBHOOK_URL")
        os.environ["FATHIYA_ZAPIER_WEBHOOK_URL"] = (
            "https://example.invalid/zapier/secret-token"
        )
        try:
            executor = ToolExecutor(RuntimeConfig.load())
            with patch(
                "fathiya_runtime.tools.requests.request",
                side_effect=requests.ConnectionError(
                    "failed https://example.invalid/zapier/secret-token"
                ),
            ):
                with self.assertRaises(ToolExecutionError) as raised:
                    executor.execute(
                        "connector_profile",
                        "send proof",
                        {"profile": "zapier_fathiya_webhook", "payload": {"ok": True}},
                    )
            self.assertNotIn("secret-token", raised.exception.result["error"])
            self.assertEqual(
                raised.exception.result["error"],
                "ConnectionError: connector request failed",
            )
        finally:
            if previous is None:
                os.environ.pop("FATHIYA_ZAPIER_WEBHOOK_URL", None)
            else:
                os.environ["FATHIYA_ZAPIER_WEBHOOK_URL"] = previous

    def test_fallback_plan_selects_generic_connector_gateway(self) -> None:
        plan = build_plan(
            {"prompt": "اعرض حالة n8n عبر بوابة الموصلات"},
            [],
            AgentModelRouter(
                "",
                "remote-model",
                enable_local_generation=False,
                local_model="local-model",
                local_max_new_tokens=64,
            ),
            ToolExecutor(self.config).catalog(),
            max_tool_steps=6,
        )
        connector_steps = [
            step
            for step in plan
            if step.get("tool") == "connector_profile"
        ]

        self.assertEqual(len(connector_steps), 1)
        self.assertEqual(connector_steps[0]["args"]["profile"], "n8n_health")

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

    def test_connector_profile_plan_waits_for_dynamic_approval(self) -> None:
        task = self.store.enqueue("بوابة Zapier", "نفذ مهمة داخلية")
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
                "tool": "connector_profile",
                "description": "external connector",
                "args": {
                    "profile": "zapier_fathiya_webhook",
                    "payload": {"test": True},
                },
            },
        ]

        with patch("fathiya_runtime.worker.build_plan", return_value=plan):
            worker.start(once=True)

        gated = self.store.get_detail(task["id"])
        self.assertEqual(gated["task"]["status"], "awaiting_approval")
        self.assertEqual(gated["task"]["risk_class"], "external")
        self.assertEqual(gated["events"][-1]["payload"]["gated_steps"][0]["tool"], "connector_profile")

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

    def test_openrouter_plan_rejects_unconfigured_connector_profile(self) -> None:
        model = OpenRouterClient("configured-key", "test-model")
        model.complete = lambda *_args, **_kwargs: (
            '{"steps": [{"tool": "connector_profile", "description": "send", '
            '"args": {"profile": "zapier_fathiya_webhook"}}]}'
        )
        plan = build_plan(
            {"prompt": "نفذ طلبا داخليا"},
            [],
            model,
            ToolExecutor(self.config).catalog(),
            max_tool_steps=4,
        )
        tools = [step["tool"] for step in plan if step.get("kind") == "tool"]

        self.assertNotIn("connector_profile", tools)
        self.assertEqual(tools, ["internal_echo"])

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
        self.assertIn("connector_catalog", by_name)
        self.assertIn("connector_profile", by_name)
        self.assertTrue(by_name["n8n_webhook"]["requires_approval"])
        profiles = {profile["name"] for profile in by_name["command_profile"]["profiles"]}
        self.assertIn("runtime_tests", profiles)
        self.assertIn("repo_build", profiles)
        connector_profiles = {
            profile["name"] for profile in by_name["connector_profile"]["profiles"]
        }
        self.assertIn("n8n_health", connector_profiles)
        self.assertIn("zapier_fathiya_webhook", connector_profiles)

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
