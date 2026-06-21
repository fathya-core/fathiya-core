from __future__ import annotations

import json
import re
import threading
import time
from datetime import UTC, datetime
from typing import Any

from .config import RuntimeConfig
from .knowledge_mission import parse_knowledge_mission, persist_knowledge_mission
from .models import AgentModelRouter
from .planner import (
    DETERMINISTIC_SYNTHESIS_TOOLS,
    FAST_CONTROL_TOOLS,
    build_follow_up_decision,
    build_plan,
    fast_control_steps,
    knowledge_only_requested,
    step_signature,
)
from .retrieval import KnowledgeRetriever
from .retrieval import RetrievedSource
from .store import TaskStore, now_iso
from .tools import ToolExecutionError, ToolExecutor


class TaskCanceledError(RuntimeError):
    pass


class AgentWorker:
    def __init__(
        self,
        config: RuntimeConfig,
        store: TaskStore,
        *,
        tools: ToolExecutor | None = None,
    ):
        self.store = store
        self._runtime_lock = threading.RLock()
        self.synthesis_mode = "not_run"
        self._configure_runtime(config, tools or ToolExecutor(config))

    def reload_config(self, config: RuntimeConfig, tools: ToolExecutor) -> None:
        with self._runtime_lock:
            self._configure_runtime(config, tools)

    def _configure_runtime(self, config: RuntimeConfig, tools: ToolExecutor) -> None:
        self.config = config
        self.model = AgentModelRouter(
            config.openrouter_api_key,
            config.openrouter_model,
            config.openrouter_model_candidates,
            enable_local_generation=config.enable_local_generation,
            local_model=config.local_model,
            local_max_new_tokens=config.local_max_new_tokens,
            enable_local_planning=config.enable_local_planning,
            local_max_generation_seconds=config.local_max_generation_seconds,
        )
        self.retriever = KnowledgeRetriever(
            config.knowledge_root,
            enable_hf=config.enable_hf_retrieval,
            hf_model=config.hf_model,
        )
        self.tools = tools
        self.tools.set_model_router(self.model)
        self.capabilities = [
            "knowledge_search",
            "openrouter_planning",
            "openrouter_synthesis",
            "openrouter_evaluation",
            "huggingface_local_generation",
            *[tool["name"] for tool in self.tools.catalog()],
        ]

    def start(self, *, once: bool = False, poll_seconds: float = 3.0) -> int:
        self.store.initialize()
        self.store.register_worker(
            self.config.worker_id,
            self.config.worker_name,
            self.capabilities,
        )
        processed = 0
        while True:
            self.store.mark_stalled()
            self.store.heartbeat_worker(self.config.worker_id, "online")
            task = self.store.claim_next(self.config.worker_id)
            if task:
                processed += 1
                with self._runtime_lock:
                    self._process(task)
            if once:
                self.store.heartbeat_worker(self.config.worker_id, "online")
                return processed
            time.sleep(poll_seconds)

    def _process(self, task: dict[str, Any]) -> None:
        heartbeat_stop = threading.Event()
        heartbeat_thread = threading.Thread(
            target=self._task_heartbeat_loop,
            args=(task["id"], heartbeat_stop),
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            self.store.heartbeat_worker(self.config.worker_id, "busy")
            checkpoint = _execution_checkpoint(task)
            self._progress(
                task,
                5,
                "استئناف التنفيذ" if checkpoint else "بدء التنفيذ",
                "resumed" if checkpoint else "started",
                (
                    "استأنف المشغّل المهمة من الجولة المحفوظة بعد الموافقة."
                    if checkpoint
                    else "بدأ المشغّل المحلي المهمة."
                ),
            )

            tool_catalog = self.tools.catalog()
            if checkpoint:
                execution_task = {
                    **task,
                    "prompt": str(checkpoint["execution_prompt"]),
                    "knowledge_mission": bool(checkpoint.get("knowledge_mission")),
                }
                mission_evidence = checkpoint.get("mission_evidence")
                sources = [
                    RetrievedSource(
                        path=str(source.get("path") or ""),
                        score=float(source.get("score") or 0),
                        excerpt=str(source.get("excerpt") or ""),
                    )
                    for source in checkpoint.get("sources", [])
                    if isinstance(source, dict) and source.get("path")
                ]
                initial_plan = checkpoint.get("initial_plan", [])
                tool_results = checkpoint.get("tool_results", [])
                agent_rounds = checkpoint.get("agent_rounds", [])
                seen_signatures = {
                    str(value) for value in checkpoint.get("seen_signatures", [])
                }
                round_number = max(1, int(checkpoint.get("round_number") or 1))
                round_reason = str(
                    checkpoint.get("round_reason")
                    or "استئناف الجولة التي انتظرت موافقة المشغل."
                )
                round_planner_mode = str(
                    checkpoint.get("round_planner_mode") or "approval_resume"
                )
                round_planner_error = checkpoint.get("round_planner_error")
                round_completed_tools = [
                    str(tool)
                    for tool in checkpoint.get("round_completed_tools", [])
                    if tool
                ]
                current_steps = _materialize_round_steps(
                    checkpoint.get("next_steps", []),
                    tool_catalog,
                    round_number,
                )
                self._progress(
                    task,
                    30,
                    f"استئناف جولة الوكيل {round_number}",
                    "agent_round_resumed",
                    f"استؤنفت جولة الوكيل {round_number} دون إعادة الخطوات المكتملة.",
                    {
                        "round": round_number,
                        "completed_rounds": len(agent_rounds),
                        "completed_tools": len(tool_results),
                    },
                )
            else:
                mission = parse_knowledge_mission(task["prompt"])
                mission_evidence: dict[str, Any] | None = None
                execution_task = task
                mission_source: RetrievedSource | None = None
                if mission:
                    mission_evidence = persist_knowledge_mission(
                        self.config.knowledge_root,
                        mission,
                    )
                    execution_task = {
                        **task,
                        "prompt": mission.objective,
                        "knowledge_mission": True,
                    }
                    mission_source = RetrievedSource(
                        path=mission_evidence["path"],
                        score=1.0,
                        excerpt=mission.content[:500].replace("\n", " "),
                    )
                    self._progress(
                        task,
                        10,
                        "استيعاب التقرير",
                        "knowledge_intake",
                        "حُفظ التقرير كدليل غير موثوق قبل بناء خطة التنفيذ.",
                        mission_evidence,
                    )

                prompt_for_control = str(execution_task["prompt"])
                direct_control = (
                    []
                    if knowledge_only_requested(prompt_for_control)
                    else fast_control_steps(prompt_for_control, tool_catalog)
                )
                if direct_control:
                    sources = []
                    self._progress(
                        task,
                        20,
                        "توجيه تحكم مباشر",
                        "direct_control",
                        "تم التعرف على أمر تحكم محلي محدد ولا يحتاج استرجاع معرفة.",
                        {"tools": [step["tool"] for step in direct_control]},
                    )
                else:
                    query = execution_task["prompt"]
                    if mission_evidence:
                        query = (
                            f"{query}\n{mission_evidence['source_name']}\n"
                            f"{mission_evidence['path']}"
                        )
                    sources = self.retriever.search(query, limit=4 if mission_source else 5)
                    if mission_source:
                        sources = [
                            mission_source,
                            *[
                                source
                                for source in sources
                                if source.path != mission_source.path
                            ],
                        ][:5]
                    self._progress(
                        task,
                        20,
                        "استرجاع المعرفة",
                        "retrieved",
                        f"تم استرجاع {len(sources)} مصادر مرتبطة عبر {self.retriever.last_mode}.",
                        {
                            "retrieval_mode": self.retriever.last_mode,
                            "retrieval_error": self.retriever.last_error,
                            "sources": [source.__dict__ for source in sources],
                        },
                    )

                initial_plan = (
                    _direct_control_initial_plan(
                        execution_task,
                        direct_control,
                        tool_catalog,
                    )
                    if direct_control
                    else build_plan(
                        execution_task,
                        sources,
                        self.model,
                        tool_catalog,
                        max_tool_steps=self.config.max_tool_steps,
                    )
                )
                tool_results: list[dict[str, Any]] = []
                agent_rounds: list[dict[str, Any]] = []
                seen_signatures: set[str] = set()
                round_number = 1
                round_reason = "تنفيذ الخطة الأولية المبنية من طلب المشغل والأدلة."
                round_planner_mode = str(initial_plan[0].get("planner_mode") or "unknown")
                round_planner_error = initial_plan[0].get("planner_error")
                round_completed_tools: list[str] = []
                current_steps = _materialize_round_steps(
                    [step for step in initial_plan if step.get("kind") == "tool"],
                    tool_catalog,
                    round_number,
                )
                self.store.add_event(
                    task,
                    "planned",
                    "بُنيت الخطة الأولية وبدأت دورة الوكيل متعددة الجولات.",
                    status="running",
                    step="plan",
                    progress=30,
                    payload={"plan": initial_plan},
                )

            termination_reason = ""
            while current_steps and round_number <= self.config.max_agent_rounds:
                current_steps = [
                    step
                    for step in current_steps
                    if step_signature(step["tool"], step.get("args")) not in seen_signatures
                ]
                if not current_steps:
                    termination_reason = "منع المراجع تكرار خطوات نُفذت سابقًا."
                    break

                planned_steps = current_steps
                approval_index: int | None = None
                if task.get("approval_state") != "approved":
                    for index, step in enumerate(planned_steps):
                        requirement = self.tools.approval_requirement(
                            step["tool"],
                            step.get("args", {}),
                        )
                        if requirement.required:
                            approval_index = index
                            break
                execution_steps = (
                    planned_steps
                    if approval_index is None
                    else planned_steps[:approval_index]
                )
                deferred_steps = (
                    []
                    if approval_index is None
                    else planned_steps[approval_index:]
                )

                pending_round = {
                    "round": round_number,
                    "status": "planned",
                    "reason": round_reason,
                    "planner_mode": round_planner_mode,
                    "planner_error": round_planner_error,
                    "steps": _round_step_summary(planned_steps),
                }
                self.store.update_task(
                    task["id"],
                    plan={
                        "max_rounds": self.config.max_agent_rounds,
                        "initial": initial_plan,
                        "rounds": agent_rounds,
                        "pending_round": pending_round,
                    },
                    last_heartbeat_at=now_iso(),
                    current_step=f"جولة الوكيل {round_number}: مراجعة خطة التنفيذ",
                )
                round_progress_start, round_progress_end = _round_progress(
                    round_number,
                    self.config.max_agent_rounds,
                )
                self.store.add_event(
                    task,
                    "agent_round_planned",
                    f"خطط الوكيل الجولة {round_number} لتشغيل {len(planned_steps)} أدوات.",
                    status="running",
                    step=f"agent_round_{round_number}_plan",
                    progress=round_progress_start,
                    payload=pending_round,
                )
                if not execution_steps and deferred_steps:
                    checkpoint_payload = _build_execution_checkpoint(
                        execution_task,
                        mission_evidence,
                        sources,
                        initial_plan,
                        agent_rounds,
                        tool_results,
                        seen_signatures,
                        round_number,
                        deferred_steps,
                        round_reason,
                        round_planner_mode,
                        round_planner_error,
                        round_completed_tools,
                    )
                    if self._gate_plan_for_approval(
                        task,
                        deferred_steps,
                        checkpoint=checkpoint_payload,
                        progress=round_progress_start,
                    ):
                        return
                    execution_steps = deferred_steps
                    deferred_steps = []

                round_tools = [*round_completed_tools]
                for index, execution_step in enumerate(execution_steps, start=1):
                    execution_args = self._execution_args(task, execution_step)
                    start_progress = round_progress_start + int(
                        ((index - 1) / len(execution_steps))
                        * (round_progress_end - round_progress_start)
                    )
                    complete_progress = round_progress_start + int(
                        (index / len(execution_steps))
                        * (round_progress_end - round_progress_start)
                    )
                    self._progress(
                        task,
                        start_progress,
                        execution_step["description"],
                        "tool_started",
                        (
                            f"الجولة {round_number}: تشغيل الأداة "
                            f"{index}/{len(execution_steps)}: {execution_step['tool']}"
                        ),
                        {
                            "round": round_number,
                            "tool": execution_step["tool"],
                            "args": execution_args,
                        },
                    )
                    tool_result = self.tools.execute(
                        execution_step["tool"],
                        execution_task["prompt"],
                        execution_args,
                        tool_results,
                    )
                    seen_signatures.add(
                        step_signature(execution_step["tool"], execution_args)
                    )
                    round_tools.append(execution_step["tool"])
                    tool_results.append(
                        {
                            "round": round_number,
                            "step_id": execution_step["id"],
                            "description": execution_step["description"],
                            "result": tool_result,
                        }
                    )
                    self._progress(
                        task,
                        complete_progress,
                        f"اكتمل {execution_step['tool']}",
                        "tool_completed",
                        f"الجولة {round_number}: اكتمل تنفيذ {execution_step['tool']}.",
                        {"round": round_number, "tool_result": tool_result},
                    )

                if deferred_steps:
                    checkpoint_payload = _build_execution_checkpoint(
                        execution_task,
                        mission_evidence,
                        sources,
                        initial_plan,
                        agent_rounds,
                        tool_results,
                        seen_signatures,
                        round_number,
                        deferred_steps,
                        round_reason,
                        round_planner_mode,
                        round_planner_error,
                        round_tools,
                    )
                    self.store.add_event(
                        task,
                        "agent_round_paused",
                        (
                            f"نفذ الوكيل {len(execution_steps)} خطوات داخلية من الجولة "
                            f"{round_number} وتوقف قبل الأداة الحساسة."
                        ),
                        status="running",
                        step=f"agent_round_{round_number}_paused",
                        progress=round_progress_end,
                        payload={
                            "round": round_number,
                            "completed_tools": round_tools,
                            "deferred_steps": _round_step_summary(deferred_steps),
                        },
                    )
                    if self._gate_plan_for_approval(
                        task,
                        deferred_steps,
                        checkpoint=checkpoint_payload,
                        progress=round_progress_end,
                    ):
                        return
                    current_steps = deferred_steps
                    round_completed_tools = round_tools
                    round_reason = (
                        "استأنف الوكيل خطوات مؤجلة بعد أن أثبتت بوابة المخاطر "
                        "أنها لا تحتاج موافقة."
                    )
                    round_planner_mode = f"{round_planner_mode}+deferred_released"
                    round_planner_error = None
                    continue

                completed_round = {
                    **pending_round,
                    "status": "completed",
                    "tools": round_tools,
                }
                agent_rounds.append(completed_round)
                round_completed_tools = []
                self.store.update_task(
                    task["id"],
                    plan={
                        "max_rounds": self.config.max_agent_rounds,
                        "initial": initial_plan,
                        "rounds": agent_rounds,
                    },
                    last_heartbeat_at=now_iso(),
                    current_step=f"اكتملت جولة الوكيل {round_number}",
                )
                self.store.add_event(
                    task,
                    "agent_round_completed",
                    f"أكمل الوكيل الجولة {round_number} وراجع نتائجها.",
                    status="running",
                    step=f"agent_round_{round_number}_completed",
                    progress=round_progress_end,
                    payload=completed_round,
                )

                if round_number >= self.config.max_agent_rounds:
                    termination_reason = (
                        f"وصل الوكيل إلى حد الجولات المضبوط "
                        f"({self.config.max_agent_rounds})."
                    )
                    break
                decision = build_follow_up_decision(
                    execution_task,
                    sources,
                    self.model,
                    tool_catalog,
                    tool_results,
                    seen_signatures,
                    round_number=round_number,
                    max_tool_steps=self.config.max_tool_steps,
                )
                self.store.add_event(
                    task,
                    "agent_reviewed",
                    (
                        f"راجع الوكيل الجولة {round_number}: "
                        f"{'اكتملت المهمة' if decision['complete'] else 'تحتاج جولة أخرى'}."
                    ),
                    status="running",
                    step=f"agent_round_{round_number}_review",
                    progress=round_progress_end,
                    payload=decision,
                )
                if decision["complete"] or not decision["steps"]:
                    termination_reason = str(decision["reason"])
                    break
                round_number += 1
                round_reason = str(decision["reason"])
                round_planner_mode = str(decision["planner_mode"])
                round_planner_error = decision.get("planner_error")
                round_completed_tools = []
                current_steps = _materialize_round_steps(
                    decision["steps"],
                    tool_catalog,
                    round_number,
                )

            if not termination_reason:
                termination_reason = "اكتملت دورة الوكيل دون خطوات متابعة جديدة."

            self._progress(
                task,
                80,
                "تلخيص الأدلة",
                "synthesis_started",
                "بدأ تلخيص الأدلة ونتائج الأدوات.",
            )
            executed_tools = [
                str(item.get("result", {}).get("tool") or "")
                for item in tool_results
                if isinstance(item.get("result"), dict)
            ]
            if executed_tools and all(
                tool in DETERMINISTIC_SYNTHESIS_TOOLS for tool in executed_tools
            ):
                synthesis = _deterministic_synthesis(tool_results, len(sources))
                self.synthesis_mode = (
                    "local_deterministic_fast_control"
                    if all(tool in FAST_CONTROL_TOOLS for tool in executed_tools)
                    else "local_deterministic_tool_summary"
                )
            else:
                synthesis = self._synthesize(execution_task, sources, tool_results)
            self._progress(
                task,
                85,
                "تقييم النتيجة",
                "synthesized",
                "تم تلخيص النتيجة وبدأ التقييم.",
                {"synthesis": synthesis},
            )
            company_web_intake_evaluation = _company_web_intake_evaluation(tool_results)
            if self.synthesis_mode == "local_deterministic_explicit_sources":
                evaluation = {
                    "passed": True,
                    "mode": "local_deterministic_explicit_source_check",
                    "summary": "تم استخراج القيم الدقيقة من ملفات معرفة مصرح بها صراحة في الطلب.",
                    "concerns": [],
                }
            elif company_web_intake_evaluation:
                evaluation = company_web_intake_evaluation
            elif self.synthesis_mode.startswith("local_deterministic_"):
                evaluation = _deterministic_tool_evaluation(tool_results)
            else:
                evaluation = self.model.evaluate(
                    execution_task["prompt"],
                    {"tool_results": tool_results, "synthesis": synthesis},
                )
            model_trace = {
                "planner_provider": initial_plan[0].get("planner_mode"),
                "planner_error": initial_plan[0].get("planner_error"),
                "review_providers": [
                    round_item.get("planner_mode") for round_item in agent_rounds[1:]
                ],
                "synthesis_provider": self.synthesis_mode,
                "last_provider": self.model.last_provider,
                "last_openrouter_model": self.model.openrouter.last_model,
                "openrouter_model_candidates": list(self.model.openrouter.models),
                "provider_fallbacks": self.model.last_error,
            }
            result = {
                "synthesis": synthesis,
                "tool_results": tool_results,
                "tool_result": tool_results[-1]["result"] if tool_results else None,
                "evaluation": evaluation,
                "model_trace": model_trace,
                "sources": [source.__dict__ for source in sources],
                "knowledge_mission": mission_evidence,
                "agent_rounds": agent_rounds,
                "termination_reason": termination_reason,
            }

            self._ensure_not_canceled(task)
            receipt_id = self.store.add_receipt(
                task,
                "completed",
                synthesis[:1000],
                {
                    "worker_id": self.config.worker_id,
                    "tools": executed_tools,
                    "round_count": len(agent_rounds),
                    "termination_reason": termination_reason,
                    "evaluation": evaluation,
                    "model_trace": model_trace,
                    "source_count": len(sources),
                    "source_paths": [source.path for source in sources],
                    "knowledge_mission": mission_evidence,
                    "completed_at": now_iso(),
                },
            )
            self.store.update_task(
                task["id"],
                status="completed",
                progress=100,
                current_step="اكتملت المهمة وصدر الإيصال",
                result=result,
                last_heartbeat_at=now_iso(),
                completed_at=now_iso(),
                error_message=None,
            )
            self.store.add_event(
                task,
                "completed",
                f"اكتملت المهمة. الإيصال: {receipt_id}",
                status="completed",
                step="receipt",
                progress=100,
                payload={"receipt_id": receipt_id},
            )
        except TaskCanceledError:
            self.store.add_event(
                task,
                "cancellation_observed",
                "أوقف المشغّل التنفيذ بعد ملاحظة إلغاء المهمة.",
                status="canceled",
                step="canceled",
            )
        except Exception as exc:
            failure_result = {
                "error_type": type(exc).__name__,
                "error": str(exc),
                "tool_result": exc.result if isinstance(exc, ToolExecutionError) else None,
            }
            receipt_id: str | None = None
            try:
                receipt_id = self.store.add_receipt(
                    task,
                    "failed",
                    f"فشل التنفيذ: {str(exc)[:800]}",
                    {
                        "worker_id": self.config.worker_id,
                        "failure": failure_result,
                        "failed_at": now_iso(),
                    },
                )
            except Exception:
                receipt_id = None
            self.store.update_task(
                task["id"],
                status="failed",
                current_step="فشل التنفيذ",
                error_message=str(exc),
                result=failure_result,
                last_heartbeat_at=now_iso(),
                completed_at=now_iso(),
            )
            self.store.add_event(
                task,
                "failed",
                f"فشل التنفيذ: {exc}",
                status="failed",
                step="error",
                payload={"receipt_id": receipt_id, "failure": failure_result},
            )
        finally:
            heartbeat_stop.set()
            heartbeat_thread.join(timeout=1)
            self.store.heartbeat_worker(self.config.worker_id, "online")

    def _task_heartbeat_loop(
        self,
        task_id: str,
        stop_event: threading.Event,
        *,
        interval_seconds: float = 20.0,
    ) -> None:
        while not stop_event.wait(interval_seconds):
            try:
                self.store.update_task(task_id, last_heartbeat_at=now_iso())
                self.store.heartbeat_worker(self.config.worker_id, "busy")
            except Exception:
                continue

    def _execution_args(
        self,
        task: dict[str, Any],
        execution_step: dict[str, Any],
    ) -> dict[str, Any]:
        args = dict(execution_step.get("args") or {})
        if (
            execution_step.get("tool") == "connector_profile"
            and args.get("profile") == "n8n_fathiya_webhook"
        ):
            payload = args.get("payload")
            payload = dict(payload) if isinstance(payload, dict) else {}
            target_profile = str(
                payload.get("profile") or args.get("target_profile") or "n8n_health",
            ).strip()
            payload.update(
                {
                    "task_id": task["id"],
                    "profile": target_profile,
                    "approval_state": str(task.get("approval_state") or "pending"),
                    "source": "fathiya-agent-runtime",
                },
            )
            payload.setdefault("payload", {})
            payload.setdefault("query", {})
            args["payload"] = payload
        return args

    def _progress(
        self,
        task: dict[str, Any],
        progress: int,
        step: str,
        event_type: str,
        message: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._ensure_not_canceled(task)
        self.store.update_task(
            task["id"],
            status="running",
            progress=progress,
            current_step=step,
            last_heartbeat_at=now_iso(),
        )
        self.store.add_event(
            task,
            event_type,
            message,
            status="running",
            step=step,
            progress=progress,
            payload=payload,
        )

    def _ensure_not_canceled(self, task: dict[str, Any]) -> None:
        current = self.store.get_task(task["id"])
        if current and current["status"] == "canceled":
            raise TaskCanceledError(task["id"])

    def _gate_plan_for_approval(
        self,
        task: dict[str, Any],
        execution_steps: list[dict[str, Any]],
        *,
        checkpoint: dict[str, Any] | None = None,
        progress: int = 30,
    ) -> bool:
        if task.get("approval_state") == "approved":
            return False
        gated: list[dict[str, Any]] = []
        for step in execution_steps:
            requirement = self.tools.approval_requirement(
                step["tool"],
                step.get("args", {}),
            )
            if requirement.required:
                gated.append(
                    {
                        "step_id": step["id"],
                        "tool": step["tool"],
                        "risk_class": requirement.risk_class,
                        "reason": requirement.reason,
                    }
                )
        if not gated:
            return False
        risk_class = gated[0]["risk_class"]
        fields: dict[str, Any] = {
            "status": "awaiting_approval",
            "progress": progress,
            "current_step": f"الخطة تحتاج موافقة قبل تشغيل {gated[0]['tool']}",
            "risk_class": risk_class,
            "requires_approval": True,
            "approval_state": "pending",
            "last_heartbeat_at": now_iso(),
        }
        if checkpoint is not None:
            fields["result"] = {"execution_checkpoint": checkpoint}
        self.store.update_task(task["id"], **fields)
        self.store.add_event(
            task,
            "approval_required",
            "اختارت خطة التنفيذ أداة ذات أثر حساس وتوقفت قبل تشغيلها.",
            status="awaiting_approval",
            step="plan_approval_gate",
            progress=progress,
            payload={
                "gated_steps": gated,
                "resume_round": checkpoint.get("round_number") if checkpoint else None,
            },
        )
        return True

    def _synthesize(
        self,
        task: dict[str, Any],
        sources: list[Any],
        tool_results: list[dict[str, Any]],
    ) -> str:
        source_synthesis = _source_grounded_synthesis(task["prompt"], sources)
        if source_synthesis:
            self.synthesis_mode = "local_deterministic_explicit_sources"
            return source_synthesis
        if self.model.available:
            context = "\n".join(
                f"- {source.path}: {source.excerpt[:2000]}" for source in sources
            )
            try:
                synthesize = getattr(self.model, "synthesize", self.model.complete)
                synthesis = synthesize(
                    "أنت وكيل تنفيذ في فتحية. لخّص ما نُفذ وما ثبت وما يحتاج متابعة. لا تدّعِ شيئًا بلا دليل.",
                    (
                        f"الطلب:\n{task['prompt']}\n\nالمصادر:\n{context}\n\n"
                        f"ملخص نتائج الأدوات:\n"
                        f"{json.dumps(_compact_tool_results(tool_results), ensure_ascii=False)[:5000]}"
                    ),
                )
                if _is_useful_synthesis(synthesis, tool_results):
                    self.synthesis_mode = self.model.last_provider
                    return synthesis
                self.synthesis_mode = "local_deterministic_rejected_model_synthesis"
            except Exception:
                self.synthesis_mode = "local_deterministic_model_error"
        else:
            self.synthesis_mode = "local_deterministic_no_model"
        return _deterministic_synthesis(tool_results, len(sources))


def _execution_checkpoint(task: dict[str, Any]) -> dict[str, Any] | None:
    result = task.get("result")
    if not isinstance(result, dict):
        return None
    checkpoint = result.get("execution_checkpoint")
    if (
        not isinstance(checkpoint, dict)
        or checkpoint.get("version") != 1
        or not checkpoint.get("execution_prompt")
        or not isinstance(checkpoint.get("next_steps"), list)
    ):
        return None
    return checkpoint


def _build_execution_checkpoint(
    execution_task: dict[str, Any],
    mission_evidence: dict[str, Any] | None,
    sources: list[RetrievedSource],
    initial_plan: list[dict[str, Any]],
    agent_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    seen_signatures: set[str],
    round_number: int,
    next_steps: list[dict[str, Any]],
    round_reason: str,
    round_planner_mode: str,
    round_planner_error: Any,
    round_completed_tools: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "version": 1,
        "execution_prompt": execution_task["prompt"],
        "knowledge_mission": bool(execution_task.get("knowledge_mission")),
        "mission_evidence": mission_evidence,
        "sources": [source.__dict__ for source in sources],
        "initial_plan": initial_plan,
        "agent_rounds": agent_rounds,
        "tool_results": tool_results,
        "seen_signatures": sorted(seen_signatures),
        "round_number": round_number,
        "next_steps": next_steps,
        "round_reason": round_reason,
        "round_planner_mode": round_planner_mode,
        "round_planner_error": round_planner_error,
        "round_completed_tools": list(round_completed_tools or []),
    }


def _materialize_round_steps(
    requested: Any,
    tool_catalog: list[dict[str, Any]],
    round_number: int,
) -> list[dict[str, Any]]:
    if not isinstance(requested, list):
        return []
    catalog_by_name = {
        str(item.get("name")): item
        for item in tool_catalog
        if item.get("name")
    }
    steps: list[dict[str, Any]] = []
    for index, raw in enumerate(requested, start=1):
        if not isinstance(raw, dict):
            continue
        tool = str(raw.get("tool") or "")
        spec = catalog_by_name.get(tool)
        if not spec:
            continue
        steps.append(
            {
                "id": f"round-{round_number}-execute-{index}",
                "kind": "tool",
                "tool": tool,
                "description": str(raw.get("description") or spec.get("description") or tool),
                "args": raw.get("args") if isinstance(raw.get("args"), dict) else {},
                "risk_class": str(raw.get("risk_class") or spec.get("risk_class", "internal_owned")),
                "requires_approval": (
                    bool(raw.get("requires_approval"))
                    if "requires_approval" in raw
                    else bool(spec.get("requires_approval", False))
                ),
                "read_only": (
                    bool(raw.get("read_only"))
                    if "read_only" in raw
                    else bool(spec.get("read_only", True))
                ),
            }
        )
    return steps


def _direct_control_initial_plan(
    task: dict[str, Any],
    direct_steps: list[dict[str, Any]],
    tool_catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    catalog_by_name = {
        str(item.get("name")): item
        for item in tool_catalog
        if item.get("name")
    }
    planner_mode = _direct_control_planner_mode(direct_steps)
    plan: list[dict[str, Any]] = [
        {
            "id": "retrieve",
            "kind": "retrieval",
            "tool": "knowledge_search",
            "description": "استرجاع المعرفة المرتبطة بالطلب",
            "planner_mode": planner_mode,
            "planner_error": None,
            "retrieved_sources": 0,
            "source_paths": [],
            "knowledge_mission": bool(task.get("knowledge_mission")),
        }
    ]
    for index, step in enumerate(direct_steps, start=1):
        tool = str(step.get("tool") or "")
        spec = catalog_by_name.get(tool)
        if not spec:
            continue
        plan.append(
            {
                "id": f"execute-{index}",
                "kind": "tool",
                "tool": tool,
                "description": str(step.get("description") or spec.get("description") or tool),
                "args": step.get("args") if isinstance(step.get("args"), dict) else {},
                "risk_class": spec.get("risk_class", "internal_owned"),
                "requires_approval": bool(spec.get("requires_approval", False)),
                "read_only": bool(spec.get("read_only", True)),
            }
        )
    plan.append(
        {
            "id": "synthesize",
            "kind": "model",
            "tool": "synthesize",
            "description": "دمج الأدلة ونتائج الأدوات في نتيجة واحدة",
            "model": "deterministic:direct_control",
        }
    )
    plan.append(
        {
            "id": "evaluate",
            "kind": "evaluation",
            "tool": "evaluate",
            "description": "تقييم النتيجة وإصدار إيصال",
        }
    )
    return plan


def _direct_control_planner_mode(direct_steps: list[dict[str, Any]]) -> str:
    if direct_steps and str(direct_steps[0].get("tool") or "") == "learning_bootstrap":
        return "local_knowledge_execution"
    if len(direct_steps) != 1:
        return "local_fast_control"
    tool = str(direct_steps[0].get("tool") or "")
    return {
        "agent_mesh_execute": "local_agent_mesh_execute",
        "agent_mesh_audit": "local_agent_mesh_audit",
        "production_site_audit": "local_production_site_audit",
        "integration_probe": "local_integration_probe",
        "openrouter_model_strategy": "local_openrouter_model_strategy",
        "agent_provider_action_prepare": "local_agent_provider_action_prepare",
        "agent_provider_probe": "local_agent_provider_probe",
    }.get(tool, "local_fast_control")


def _knowledge_execution_should_plan(prompt: str) -> bool:
    return bool(
        re.search(
            r"(?:knowledge\s+execution\s+mission|fathiya_knowledge_execution_v1|"
            r"fathiya_operator_agent_request_v1|learn\s+and\s+execute|"
            r"report\s+to\s+execution|تقرير\s+إلى\s+تنفيذ|تقرير\s+الى\s+تنفيذ|"
            r"استيعاب\s+وتشغيل|استوعب\s+وشغّل|استوعب\s+وشغل|"
            r"استوعب\s+ونفّذ|استوعب\s+ونفذ|معرفة\s+ثم\s+تنفيذ|"
            r"المعرفة\s+ثم\s+التنفيذ)\s*:?",
            prompt,
            re.IGNORECASE,
        )
    )


def _round_step_summary(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": step["id"],
            "tool": step["tool"],
            "description": step["description"],
            "args": step.get("args", {}),
            "risk_class": step.get("risk_class", "internal_owned"),
            "requires_approval": bool(step.get("requires_approval", False)),
            "read_only": bool(step.get("read_only", True)),
        }
        for step in steps
    ]


def _round_progress(round_number: int, max_rounds: int) -> tuple[int, int]:
    start = 30 + int(((round_number - 1) / max_rounds) * 45)
    end = 30 + int((round_number / max_rounds) * 45)
    return max(30, min(74, start)), max(31, min(75, end))


def _compact_tool_results(tool_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for item in tool_results:
        result = item.get("result")
        if not isinstance(result, dict):
            compact.append(
                {
                    "step_id": item.get("step_id"),
                    "description": item.get("description"),
                    "result": str(result)[:500],
                }
            )
            continue
        summary: dict[str, Any] = {
            "step_id": item.get("step_id"),
            "description": item.get("description"),
            "tool": result.get("tool"),
        }
        for key in (
            "available",
            "configured",
            "clean",
            "execution_failed",
            "status_code",
            "return_code",
            "status",
            "distro",
            "version",
            "error",
            "message",
            "profile",
            "provider",
            "profile_count",
            "configured_count",
            "zapier_app_count",
            "zapier_action_count",
            "app_count",
            "action_count",
            "app",
            "action",
            "action_key",
            "mode",
        ):
            if key in result:
                summary[key] = result[key]
        if isinstance(result.get("tools"), list):
            summary["tool_count"] = len(result["tools"])
            summary["tool_names"] = [
                str(tool.get("name"))
                for tool in result["tools"][:20]
                if isinstance(tool, dict) and tool.get("name")
            ]
        if isinstance(result.get("capabilities"), list):
            summary["capabilities"] = [
                {
                    "id": capability.get("id"),
                    "status": capability.get("status"),
                    "available": capability.get("available"),
                    "authenticated": capability.get("authenticated"),
                }
                for capability in result["capabilities"][:20]
                if isinstance(capability, dict)
            ]
        if isinstance(result.get("metadata"), dict):
            summary["metadata"] = result["metadata"]
        if isinstance(result.get("workflows"), dict):
            summary["workflows"] = result["workflows"]
        if isinstance(result.get("trading"), dict):
            trading = result["trading"]
            quality = trading.get("prediction_quality", {})
            summary["trading"] = {
                "running": trading.get("running"),
                "mode": trading.get("mode"),
                "symbol": trading.get("symbol"),
                "current_market_source": trading.get("current_market_source"),
                "cycle_count": trading.get("cycle_count"),
                "live_execution_enabled": trading.get("live_execution_enabled"),
                "prediction_quality": {
                    "evaluated_count": quality.get("evaluated_count"),
                    "directional_accuracy": quality.get("directional_accuracy"),
                    "cumulative_strategy_return_bps": quality.get(
                        "cumulative_strategy_return_bps"
                    ),
                },
            }
        if isinstance(result.get("testnet"), dict):
            testnet = result["testnet"]
            summary["testnet"] = {
                "provider": testnet.get("provider"),
                "environment": testnet.get("environment"),
                "configured": testnet.get("configured"),
                "execution_enabled": testnet.get("execution_enabled"),
                "reachable": testnet.get("reachable"),
                "authenticated": testnet.get("authenticated"),
                "can_trade": testnet.get("can_trade"),
                "validated": testnet.get("validated"),
                "submitted": testnet.get("submitted"),
                "symbol": testnet.get("symbol"),
                "side": testnet.get("side"),
            }
        if isinstance(result.get("cycle"), dict):
            cycle = result["cycle"]
            summary["cycle"] = {
                "receipt_id": cycle.get("receipt_id"),
                "status": cycle.get("status"),
                "tick": cycle.get("tick"),
                "prediction": cycle.get("prediction"),
                "risk": cycle.get("risk"),
                "latency_ms": cycle.get("latency_ms"),
            }
        if isinstance(result.get("advisory"), dict):
            summary["advisory"] = result["advisory"]
            summary["model_provider"] = result.get("model_provider")
            summary["fallback"] = result.get("fallback")
        for key in ("found_commands", "missing_commands"):
            if isinstance(result.get(key), list):
                summary[key] = result[key][:20]
        if result.get("tool") == "agent_mesh_audit":
            mesh_summary = result.get("summary", {})
            if isinstance(mesh_summary, dict):
                summary["mesh_summary"] = mesh_summary
            next_actions = result.get("next_actions", [])
            if isinstance(next_actions, list):
                summary["next_actions"] = [
                    {
                        "id": action.get("id"),
                        "title": action.get("title"),
                        "prompt": action.get("prompt"),
                    }
                    for action in next_actions[:12]
                    if isinstance(action, dict)
                ]
        if result.get("stdout"):
            summary["stdout"] = str(result["stdout"])[:600]
        compact.append(summary)
    return compact


def _is_useful_synthesis(
    value: str,
    tool_results: list[dict[str, Any]] | None = None,
) -> bool:
    meaningful = re.sub(r"[\s#*_`~>\-:;,.!?()[\]{}]+", "", value)
    if len(meaningful) < 40:
        return False
    lowered = value.casefold()
    for anchors in _required_synthesis_anchors(tool_results or []):
        if not any(anchor.casefold() in lowered for anchor in anchors):
            return False
    return True


def _required_synthesis_anchors(
    tool_results: list[dict[str, Any]],
) -> list[tuple[str, ...]]:
    required: list[tuple[str, ...]] = []
    for item in tool_results:
        result = item.get("result")
        if not isinstance(result, dict):
            continue
        tool = str(result.get("tool") or "")
        if tool in {"n8n_status", "n8n_workflows"}:
            required.append(("n8n",))
        elif tool == "local_capability_inventory":
            required.append(("local", "محلي", "تنفيذ"))
        elif tool == "agent_delegate":
            required.append(("delegate", "تفويض", "وكيل"))
        elif tool == "connected_tool_inventory":
            required.append(("zapier", "زابير"))
        elif tool == "agent_mesh_audit":
            required.append(("agent", "mesh", "شبكة", "وكلاء"))
        elif tool in {"zapier_action_catalog", "zapier_action"}:
            required.append(("zapier", "زابير"))
        elif tool == "connector_catalog":
            required.append(("connector", "موصل"))
        elif tool == "connector_profile":
            anchors = tuple(
                str(result.get(key))
                for key in ("provider", "profile")
                if result.get(key)
            )
            if anchors:
                required.append(anchors)
        elif tool == "kali_tool_inventory":
            required.append(("kali", "كالي"))
            commands = tuple(
                str(command)
                for command in result.get("found_commands", [])
                if command
            )
            if commands:
                required.append(commands)
        elif tool == "hexstrike_lab_scan":
            required.append(("hexstrike", "مختبر", "فحص"))
            selected = tuple(
                str(command)
                for command in result.get("selected_tools", [])
                if command
            )
            if selected:
                required.append(selected)
        elif tool == "bug_bounty_static_review":
            required.append(("bug bounty", "bugcrowd", "تقرير", "static", "intake"))
        elif tool == "bug_bounty_draft_gate":
            required.append(("bugcrowd", "draft", "مسودة", "verdict"))
        elif tool == "learning_bootstrap":
            required.append(("learning", "تعلم", "mastery", "quiz"))
        elif tool == "repo_status":
            required.append(("repo", "repository", "مستودع"))
        elif tool == "github_repo_info":
            required.append(("github", "جيت"))
        elif tool == "security_core_plan":
            required.append(("security", "أمن"))
        elif tool.startswith("trading_"):
            required.append(("trading", "تداول"))
    return required


def _deterministic_synthesis(
    tool_results: list[dict[str, Any]],
    source_count: int,
) -> str:
    names: list[str] = []
    evidence: list[str] = []
    follow_up: list[str] = []
    for item in tool_results:
        result = item.get("result")
        if not isinstance(result, dict):
            continue
        tool = str(result.get("tool") or item.get("description") or "unknown")
        names.append(tool)
        if result.get("execution_failed"):
            evidence.append(f"{tool}: فشل التنفيذ.")
            follow_up.append(f"راجع خطأ {tool}.")
        elif tool == "tool_catalog" and isinstance(result.get("tools"), list):
            evidence.append(f"كتالوج المحرك يعرض {len(result['tools'])} أداة قابلة للاستخدام.")
        elif tool == "local_capability_inventory":
            capabilities = [
                item
                for item in result.get("capabilities", [])
                if isinstance(item, dict)
            ]
            ready = [
                str(item.get("name"))
                for item in capabilities
                if item.get("status") in {"active", "ready"} and item.get("name")
            ]
            degraded = [
                str(item.get("name"))
                for item in capabilities
                if item.get("status") in {"partial", "degraded"} and item.get("name")
            ]
            evidence.append(
                f"شبكة التنفيذ المحلية تؤكد جاهزية {len(ready)} من "
                f"{result.get('capability_count', len(capabilities))} بوابات: "
                f"{', '.join(ready) or 'لا توجد بوابات جاهزة'}."
            )
            if degraded:
                follow_up.append(
                    f"بوابات محلية تحتاج إكمالًا: {', '.join(degraded)}."
                )
        elif tool == "integration_probe":
            integration_id = result.get("integration_id", "unknown")
            status = result.get("status", "unknown")
            summary = result.get("summary", "لم يسجل الفحص ملخصًا.")
            evidence.append(f"فحص الاتصال {integration_id}: {status}. {summary}")
            if not result.get("ok"):
                follow_up.append(f"أكمل إعداد {integration_id} ثم أعد تشغيل فحص الاتصال.")
        elif tool == "agent_mesh_audit":
            summary = result.get("summary", {})
            if isinstance(summary, dict):
                evidence.append(
                    "مسح شبكة الوكلاء أثبت "
                    f"{summary.get('tool_count', 0)} أداة، "
                    f"{summary.get('ready_capability_count', 0)} من "
                    f"{summary.get('capability_count', 0)} بوابات جاهزة، "
                    f"{summary.get('configured_connector_count', 0)} من "
                    f"{summary.get('connector_count', 0)} موصلات مهيأة، "
                    f"{summary.get('zapier_app_count', 0)} تطبيق Zapier و"
                    f"{summary.get('zapier_action_count', 0)} إجراء، "
                    f"ووكيل التداول على {summary.get('trading_symbol', 'رمز غير معروف')} "
                    f"بنبضة {summary.get('trading_cycle_seconds', 'غير معروفة')} ثانية."
                )
            next_actions = result.get("next_actions", [])
            if isinstance(next_actions, list):
                for action in next_actions[:6]:
                    if isinstance(action, dict) and action.get("title"):
                        follow_up.append(str(action["title"]))
        elif tool == "agent_mesh_execute":
            summary = result.get("summary", {})
            if isinstance(summary, dict):
                zapier_inventory_available = bool(summary.get("zapier_inventory_available"))
                zapier_hosted_available = bool(summary.get("zapier_hosted_available"))
                zapier_app_count = (
                    summary.get("zapier_direct_app_count")
                    or summary.get("zapier_app_count")
                    or 0
                )
                zapier_action_count = (
                    summary.get("zapier_direct_action_count")
                    or summary.get("zapier_action_count")
                    or 0
                )
                zapier_state = "غير متصل"
                if summary.get("zapier_direct_needs_reconnect"):
                    zapier_state = "يحتاج إعادة ربط OAuth"
                elif summary.get("zapier_direct_live_available"):
                    zapier_state = "متصل حيًا محليًا"
                elif summary.get("zapier_direct_oauth_connected"):
                    zapier_state = "متصل بالمخزون المحلي فقط"
                elif zapier_hosted_available:
                    zapier_state = "مخزونه المستضاف متاح وOAuth المحلي غير مكتمل"
                elif zapier_inventory_available:
                    zapier_state = "مخزونه محفوظ وOAuth المحلي غير مكتمل"
                evidence.append(
                    "تشغيل شبكة الوكلاء نفذ "
                    f"{summary.get('safe_execution_count', 0)} خطوة داخلية، "
                    f"مع {summary.get('failed_step_count', 0)} فشل، "
                    f"وتخطى {summary.get('skipped_high_risk_count', 0)} خطوات عالية الأثر."
                )
                evidence.append(
                    f"الجاهزية الحالية: {summary.get('ready_capability_count', 0)} بوابات محلية جاهزة، "
                    f"Zapier {zapier_state} "
                    f"مع {zapier_app_count} تطبيقًا و"
                    f"{zapier_action_count} إجراء، "
                    f"وCodespaces حالته {summary.get('codespaces_agent_status', 'غير معروفة')}."
                )
                evidence.append(
                    f"فحوص التكاملات: {summary.get('ready_integration_count', 0)} جاهزة، "
                    f"{summary.get('partial_integration_count', 0)} جزئية، "
                    f"ووكيل التداول Paper {'يعمل' if summary.get('paper_trading_running') else 'متوقف'}."
                )
            command_center = result.get("execution_command_center")
            if isinstance(command_center, dict):
                command_summary = command_center.get("summary")
                if isinstance(command_summary, dict):
                    evidence.append(
                        "مركز أوامر التنفيذ جهز "
                        f"{command_summary.get('ready_command_count', 0)} أوامر تشغيل، "
                        f"{command_summary.get('routable_tool_count', 0)} أداة قابلة للتوجيه، "
                        f"و{command_summary.get('operator_queue_count', 0)} عناصر في طابور المشغّل."
                    )
                ready_commands = command_center.get("ready_commands")
                if isinstance(ready_commands, list):
                    titles = [
                        str(item.get("title"))
                        for item in ready_commands
                        if isinstance(item, dict) and item.get("title")
                    ][:5]
                    if titles:
                        follow_up.append("أوامر جاهزة: " + " · ".join(titles))
            activation_plan = result.get("activation_plan")
            if isinstance(activation_plan, dict):
                entries = [
                    item
                    for item in activation_plan.get("entries", [])
                    if isinstance(item, dict)
                ]
                activation_required = [
                    item
                    for item in entries
                    if item.get("state") == "activation_required"
                ]
                ready_entries = [
                    item for item in entries if item.get("state") == "ready"
                ]
                if entries:
                    evidence.append(
                        "خطة التفعيل المنظمة: "
                        f"{len(ready_entries)} جاهزة الآن و"
                        f"{len(activation_required)} تحتاج تفعيلًا."
                    )
                for item in activation_required[:4]:
                    action = item.get("next_action")
                    title = (
                        action.get("title")
                        if isinstance(action, dict) and action.get("title")
                        else item.get("integration_id")
                    )
                    status = item.get("status", "غير معروف")
                    follow_up.append(f"{title}: {status}")
            policy = result.get("execution_policy")
            if isinstance(policy, dict) and policy.get("approval_gated_steps_skipped"):
                follow_up.append("راجع الخطوات عالية الأثر من بوابة الموافقة قبل أي تنفيذ خارجي.")
            next_actions = result.get("next_actions", [])
            if isinstance(next_actions, list):
                for action in next_actions[:5]:
                    if isinstance(action, dict) and action.get("title"):
                        follow_up.append(str(action["title"]))
        elif tool == "agent_delegate":
            provider = result.get("provider", "غير معروف")
            if result.get("delegated"):
                evidence.append(
                    f"تم تفويض المهمة إلى الوكيل {provider} بوضع "
                    f"{result.get('mode', 'غير معروف')}."
                )
            else:
                evidence.append(f"تعذر تفويض المهمة إلى الوكيل {provider}.")
        elif tool == "repo_status":
            evidence.append(
                "المستودع الأساسي نظيف."
                if result.get("clean")
                else "المستودع الأساسي يحتوي تغييرات عمل حالية."
            )
        elif tool == "github_repo_info" and isinstance(result.get("metadata"), dict):
            metadata = result["metadata"]
            evidence.append(
                f"مستودع GitHub المصادق هو {metadata.get('nameWithOwner', 'غير معروف')} "
                f"وفرعه الافتراضي {metadata.get('defaultBranchRef', {}).get('name', 'غير معروف')}."
            )
        elif tool == "n8n_status":
            evidence.append(
                f"n8n المحلية متاحة بإصدار {result.get('version', 'غير معروف')}."
                if result.get("available")
                else "n8n المحلية غير متاحة."
            )
        elif tool == "n8n_workflows":
            if result.get("available"):
                workflows = result.get("workflows")
                count = len(workflows) if isinstance(workflows, list) else "غير معروف"
                evidence.append(f"تمت قراءة مسارات n8n وعددها {count}.")
            else:
                evidence.append(
                    f"تعذر سرد مسارات n8n، وحالة الواجهة {result.get('status_code', 'غير معروفة')}."
                )
                follow_up.append("أضف N8N_API_KEY لقراءة مسارات n8n.")
        elif tool == "connected_tool_inventory":
            evidence.append(
                f"مخزون الموصلات يعرض {result.get('zapier_app_count', 0)} تطبيقات Zapier "
                f"و{result.get('zapier_action_count', 0)} إجراءات."
            )
            zapier_status = result.get("zapier_mcp_status")
            if (
                isinstance(zapier_status, dict)
                and zapier_status.get("action_execution") != "active"
            ):
                direct = result.get("direct_zapier_mcp")
                if not isinstance(direct, dict) or not direct.get("connected"):
                    follow_up.append("اربط بوابة Zapier MCP المحلية عبر OAuth لتفعيل التنفيذ المباشر.")
        elif tool == "zapier_action_catalog":
            if result.get("connected"):
                evidence.append(
                    f"بوابة Zapier MCP المباشرة متصلة وتعرض {result.get('app_count', 0)} تطبيقات "
                    f"و{result.get('action_count', 0)} إجراءات."
                )
            else:
                evidence.append("بوابة Zapier MCP المباشرة لم تُربط محليًا بعد.")
                follow_up.append("استخدم زر ربط Zapier MCP المحلي عبر OAuth.")
        elif tool == "zapier_action":
            evidence.append(
                f"تم تنفيذ إجراء Zapier {result.get('app', 'غير معروف')}/"
                f"{result.get('action', 'غير معروف')} بوضع {result.get('mode', 'غير معروف')}."
            )
        elif tool == "connector_catalog":
            evidence.append(
                f"بوابة الموصلات تعرض {result.get('configured_count', 0)} موصلات جاهزة "
                f"من أصل {result.get('profile_count', 0)}."
            )
        elif tool == "connector_profile":
            profile = result.get("profile", "غير معروف")
            provider = result.get("provider", "connector")
            if result.get("available"):
                evidence.append(f"تم تشغيل موصل {provider}/{profile} بنجاح.")
            else:
                evidence.append(
                    f"موصل {provider}/{profile} غير متاح، وحالة الواجهة "
                    f"{result.get('status_code', 'غير معروفة')}."
                )
        elif tool == "kali_tool_inventory":
            found = result.get("found_commands", [])
            missing = result.get("missing_commands", [])
            if result.get("available"):
                evidence.append(
                    f"Kali WSL متاحة، وتم العثور على {len(found)} أدوات: "
                    f"{', '.join(found) or 'لا توجد أدوات'}."
                )
                if missing:
                    follow_up.append(
                        f"أدوات Kali غير المتاحة: {', '.join(missing)}."
                    )
            else:
                evidence.append("تعذر الوصول إلى Kali WSL.")
                follow_up.append("راجع إعداد KALI_WSL_DISTRO وحالة WSL.")
        elif tool == "hexstrike_lab_scan":
            analysis = result.get("analysis") if isinstance(result.get("analysis"), dict) else {}
            nmap = result.get("nmap") if isinstance(result.get("nmap"), dict) else {}
            hexstrike = result.get("hexstrike") if isinstance(result.get("hexstrike"), dict) else {}
            if result.get("available"):
                evidence.append(
                    "HexStrike-AI جاهز "
                    f"({hexstrike.get('total_tools_available', 'غير معروف')}/"
                    f"{hexstrike.get('total_tools_count', 'غير معروف')} أدوات)، "
                    f"وصنف {result.get('target_url', 'الهدف المحلي')} كـ "
                    f"{analysis.get('target_type', 'هدف غير مصنف')} بمخاطر "
                    f"{analysis.get('risk_level', 'غير معروفة')}."
                )
                evidence.append(
                    f"فحص nmap عبر HexStrike على {result.get('target_host', '127.0.0.1')}:"
                    f"{result.get('port', '3000')} "
                    f"{'نجح' if nmap.get('success') else 'لم يكتمل'}."
                )
            else:
                evidence.append("HexStrike-AI المحلي غير متاح الآن.")
                follow_up.append("شغل hexstrike_server داخل Kali ثم أعد فحص المختبر المحلي.")
        elif tool == "bug_bounty_static_review":
            candidate_count = int(result.get("candidate_count") or 0)
            report_path = str(result.get("report_path") or "")
            title = str(result.get("report_title") or "مسودة Bugcrowd")
            mode = str(result.get("mode") or "")
            if mode == "web_url_passive_intake":
                evidence_count = int(result.get("evidence_count") or 0)
                company_ready = bool(result.get("company_report_ready"))
                evidence.append(
                    f"استطلاع الويب الآمن جمع {evidence_count} ملاحظات عامة "
                    f"بعنوان: {title}."
                )
                if company_ready:
                    evidence.append(
                        "صُنّف الناتج كتقرير شركة أولي جاهز داخليًا، وليس كبلاغ ثغرة خارجي."
                    )
            else:
                evidence.append(
                    f"مراجعة Bugcrowd الساكنة أنشأت {candidate_count} مرشحات "
                    f"بعنوان أولي: {title}."
                )
            if report_path:
                evidence.append(f"حُفظت المسودة محليًا في {report_path}.")
            if mode == "web_url_passive_intake":
                follow_up.append(
                    "استخدم التقرير كمسودة شركة أولية، وأضف لقطات شاشة أو تحقق هوية إذا أردت نسخة إرسال نهائية."
                )
            elif candidate_count:
                follow_up.append("راجع المسودة وثبت الاستغلال والنطاق قبل أي رفع خارجي.")
            else:
                follow_up.append("اختر مستودعًا أو هدفًا آخر أو وسع نطاق المراجعة الساكنة.")
        elif tool == "bug_bounty_draft_gate":
            verdict = str(result.get("verdict") or "unknown")
            draft_path = str(result.get("draft_path") or "")
            external_ready = bool(result.get("external_upload_recommended"))
            validated = [
                item
                for item in result.get("validated_findings", [])
                if isinstance(item, dict)
            ]
            evidence.append(
                f"بوابة مسودة Bugcrowd أعطت القرار: {verdict}. "
                f"الرفع الخارجي الموصى به: {'نعم' if external_ready else 'لا'}."
            )
            if verdict == "company_report_ready":
                evidence.append(
                    "بوابة المسودة قبلت الناتج كتقرير شركة داخلي، لا كبلاغ ثغرة لمنصة."
                )
            if draft_path:
                evidence.append(f"رُفعت المسودة داخل فتحية في {draft_path}.")
            if validated:
                rejected = [
                    str(item.get("id"))
                    for item in validated
                    if item.get("status") not in {"submission_ready", "company_report_ready"}
                ]
                if rejected:
                    evidence.append(
                        "المرشحات غير الجاهزة للرفع: " + ", ".join(rejected[:6]) + "."
                    )
            if external_ready:
                follow_up.append("افتح Bugcrowd وأنشئ draft خارجي بعد مراجعة النطاق يدويًا.")
            elif verdict == "company_report_ready":
                follow_up.append("لا يلزم رفع خارجي؛ حسّن نسخة التقرير فقط إذا كانت ستُرسل للشركة.")
            else:
                follow_up.append("لا ترفع خارجيًا الآن؛ ابحث عن مسار استغلال مثبت أو هدف آخر.")
        elif tool == "learning_bootstrap":
            evidence.append(
                "جلسة التعلم أنشأت "
                f"{result.get('card_count', 0)} بطاقات قرار و"
                f"{result.get('quiz_count', 0)} أسئلة اختبار، "
                f"ودرجة mastery {result.get('mastery_score', 0)}/100 "
                f"بحالة {result.get('status', 'unknown')}."
            )
            report_path = str(result.get("report_path") or "")
            if report_path:
                evidence.append(f"حُفظ تقرير التعلم في {report_path}.")
            gaps = result.get("gaps")
            if isinstance(gaps, list) and gaps:
                follow_up.append("أكمل فجوات التعلم: " + ", ".join(str(gap) for gap in gaps[:6]) + ".")
        elif tool == "production_site_audit":
            status = str(result.get("status") or "unknown")
            route_count = int(result.get("route_count") or 0)
            reachable_count = int(result.get("reachable_route_count") or 0)
            matched = bool(result.get("public_matches_local"))
            evidence.append(
                f"فحص الإنتاج على {result.get('base_url', 'الدومين')} أعطى حالة {status}: "
                f"{reachable_count}/{route_count} مسارات عامة ترد. "
                f"مطابقة المحلي: {'نعم' if matched else 'لا'}."
            )
            signals = result.get("signals") if isinstance(result.get("signals"), dict) else {}
            missing = [
                label
                for label, ok in (
                    ("مسار /agent-tasks", signals.get("agent_tasks_ok")),
                    ("هوية فتحية", signals.get("fathiya_identity")),
                    ("واجهة التشغيل المركزة", signals.get("focused_operator_console") or signals.get("command_center")),
                    ("Supabase للإنتاج", signals.get("supabase_active_store")),
                )
                if not ok
            ]
            if missing:
                evidence.append("النواقص المثبتة: " + ", ".join(missing[:6]) + ".")
            next_actions = result.get("next_actions")
            if isinstance(next_actions, list) and next_actions:
                first_action = next_actions[0] if isinstance(next_actions[0], dict) else {}
                follow_up.append(
                    str(first_action.get("reason") or first_action.get("title") or "راجع إجراءات الإنتاج التالية.")
                )
        elif tool.startswith("trading_"):
            trading = result.get("trading")
            cycle = result.get("cycle")
            advisory = result.get("advisory")
            testnet = result.get("testnet")
            if isinstance(trading, dict):
                quality = trading.get("prediction_quality", {})
                evidence.append(
                    f"وكيل التداول Paper {'يعمل' if trading.get('running') else 'متوقف'} "
                    f"على {trading.get('symbol', 'رمز غير معروف')} من مصدر "
                    f"{trading.get('current_market_source') or trading.get('market_provider', 'غير معروف')}، "
                    f"وتم قياس {quality.get('evaluated_count', 0)} تنبؤات."
                )
            elif isinstance(cycle, dict):
                evidence.append(
                    f"نُفذت نبضة تداول Paper بإيصال {cycle.get('receipt_id', 'غير معروف')} "
                    f"وقرار {cycle.get('prediction', {}).get('action', 'غير معروف')}."
                )
            elif isinstance(advisory, dict):
                evidence.append(
                    f"تم تحديث مستشار الاستراتيجية عبر {result.get('model_provider', 'غير معروف')} "
                    f"بإشارة {advisory.get('action', 'غير معروفة')} وثقة "
                    f"{advisory.get('confidence', 0):.2f} وسياسة veto-only."
                )
            elif isinstance(testnet, dict):
                evidence.append(
                    f"بوابة {testnet.get('provider', 'Testnet')} التجريبية "
                    f"{'مربوطة' if testnet.get('configured') else 'تنتظر المفاتيح المحلية'} "
                    f"على {testnet.get('symbol', 'رمز غير معروف')}، والتنفيذ التجريبي "
                    f"{'مفعل' if testnet.get('execution_enabled') else 'مقفل'}."
                )
        elif tool == "github_codespaces_inventory":
            if result.get("auth_state") == "missing_scope":
                auth_command = (
                    result.get("auth_command")
                    or "gh auth refresh -h github.com -s codespace"
                )
                evidence.append(
                    "GitHub Codespaces يحتاج صلاحية codespace على GitHub CLI؛ "
                    f"الأمر المطلوب: {auth_command}."
                )
                follow_up.append("أكمل تفويض GitHub Codespaces ثم أعد فحص الوكيل.")
            else:
                evidence.append(
                    f"GitHub Codespaces: {result.get('codespace_count', 0)} بيئات ظاهرة، "
                    f"{result.get('active_codespace_count', 0)} نشطة."
                )
        elif tool == "agent_provider_action_prepare":
            selected = (
                result.get("selected_action")
                if isinstance(result.get("selected_action"), dict)
                else {}
            )
            provider = str(result.get("provider") or "مزود غير معروف")
            action = str(selected.get("name") or "إجراء غير محدد")
            mode = str(selected.get("mode") or "unknown")
            if result.get("can_execute_now"):
                evidence.append(
                    f"وكيل {provider} جاهز للتنفيذ الحي عبر Zapier: "
                    f"{action} بوضع {mode}."
                )
            else:
                missing = [
                    str(item)
                    for item in result.get("missing_params", [])
                    if item
                ]
                evidence.append(
                    f"وكيل {provider} حضّر إجراء {action} بوضع {mode}، "
                    "لكنه لا ينفذ الآن"
                    + (f" حتى تكتمل الحقول: {', '.join(missing[:6])}." if missing else ".")
                )
                next_step = str(result.get("next_step") or "").strip()
                if next_step:
                    follow_up.append(next_step)
        elif tool == "zapier_action_preflight":
            app = str(result.get("app") or "Zapier")
            action = str(result.get("action") or "إجراء غير محدد")
            if result.get("params_ready") and result.get("live_available"):
                evidence.append(f"تحقق Zapier جهّز {app}/{action} للتنفيذ الحي.")
            else:
                missing = [
                    str(item)
                    for item in result.get("missing_params", [])
                    if item
                ]
                evidence.append(
                    f"تحقق Zapier حضّر {app}/{action} "
                    + (f"وينتظر الحقول: {', '.join(missing[:6])}." if missing else "وينتظر تفعيلًا أو ربطًا.")
                )
        elif "available" in result:
            evidence.append(f"{tool}: {'متاح' if result.get('available') else 'غير متاح'}.")
        elif result.get("return_code") is not None:
            evidence.append(f"{tool}: رمز الخروج {result.get('return_code')}.")

    lines = [
        f"اكتمل تنفيذ {len(names)} أدوات داخلية: {', '.join(names) or 'لا توجد أدوات'}.",
    ]
    if source_count:
        lines.append(f"استُرجع {source_count} مصادر معرفة مرتبطة بالطلب.")
    elif names and all(name in FAST_CONTROL_TOOLS for name in names):
        lines.append("لم يحتج أمر التحكم المحلي إلى استرجاع مصادر معرفة.")
    else:
        lines.append("لم يتم العثور على مصادر معرفة مرتبطة بالطلب.")
    if evidence:
        lines.append("الأدلة المثبتة: " + " ".join(evidence))
    if follow_up:
        lines.append("المتابعة المطلوبة: " + " ".join(dict.fromkeys(follow_up)))
    return "\n".join(lines)


def _deterministic_tool_evaluation(tool_results: list[dict[str, Any]]) -> dict[str, Any]:
    compact = _compact_tool_results(tool_results)
    failed: list[str] = []
    executed: list[str] = []
    for item in compact:
        tool = str(item.get("tool") or item.get("step_id") or "unknown")
        executed.append(tool)
        if item.get("execution_failed") or item.get("error"):
            failed.append(f"{tool}: {str(item.get('error') or 'execution_failed')[:180]}")
    return {
        "passed": bool(compact) and not failed,
        "mode": "local_deterministic_tool_evaluation",
        "summary": (
            f"تم تقييم {len(compact)} نتائج أدوات محليًا دون استدعاء نموذج خارجي. "
            + ("كل النتائج قابلة للتسجيل." if not failed else "توجد نتائج تحتاج مراجعة.")
        ),
        "concerns": failed,
        "executed_tools": executed,
    }


def _company_web_intake_evaluation(tool_results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in tool_results:
        result = item.get("result") if isinstance(item, dict) else None
        if not isinstance(result, dict):
            continue
        if (
            result.get("mode") == "web_url_passive_intake"
            and result.get("deliverable_type") == "company_web_intake_report"
        ):
            title = str(result.get("report_title") or "تقرير حضور ويب أولي")
            evidence_count = int(result.get("evidence_count") or 0)
            return {
                "passed": True,
                "mode": "local_deterministic_company_web_intake",
                "summary": (
                    f"أنتجت فتحية {title} وجمعت {evidence_count} ملاحظات عامة "
                    "ضمن حدود استطلاع ويب آمن. النتيجة ناجحة كتقرير شركة أولي داخلي، "
                    "وليست بلاغ ثغرة خارجيًا."
                ),
                "concerns": [
                    "لا توجد ثغرة مثبتة أو أثر أمني يصلح للرفع الخارجي في هذا المرور.",
                    "أي نسخة مرسلة للشركة تستفيد من إضافة لقطات شاشة وتحقق هوية تجاري يدوي.",
                ],
            }
        if result.get("verdict") == "company_report_ready":
            return {
                "passed": True,
                "mode": "local_deterministic_company_report_gate",
                "summary": (
                    "بوابة المسودة صنفت الناتج كتقرير شركة داخلي جاهز، مع منع الرفع "
                    "الخارجي لأنه لا يحتوي إثبات ثغرة."
                ),
                "concerns": [
                    "الحكم الإيجابي خاص بتقرير الشركة الداخلي فقط، وليس بجاهزية بلاغ Bugcrowd/HackerOne.",
                ],
            }
    return None


def _source_grounded_synthesis(prompt: str, sources: list[Any]) -> str | None:
    if not _requests_exact_source_values(prompt):
        return None
    explicit_sources = [
        source
        for source in sources
        if float(getattr(source, "score", 0) or 0) >= 1.0
    ]
    if not explicit_sources:
        return None

    in_scope: list[str] = []
    out_of_scope: list[str] = []
    headers: list[str] = []
    identity_notes: list[str] = []
    stop_rules: list[str] = []
    passive_steps: list[str] = []
    tool_notes: list[str] = []
    source_paths: list[str] = []

    for source in explicit_sources:
        path = str(getattr(source, "path", ""))
        source_paths.append(path)
        excerpt = str(getattr(source, "excerpt", ""))
        payload = _json_source(excerpt)
        if not isinstance(payload, dict):
            _collect_markdown_scope(
                excerpt,
                in_scope=in_scope,
                out_of_scope=out_of_scope,
                headers=headers,
                identity_notes=identity_notes,
                stop_rules=stop_rules,
                passive_steps=passive_steps,
            )
            continue

        for item in _list_value(payload.get("in_scope")):
            _add_unique(in_scope, _asset_value(item))
        for item in _list_value(payload.get("authorized_scope")):
            _add_unique(in_scope, _asset_value(item))
        for item in _list_value(payload.get("out_of_scope")):
            _add_unique(out_of_scope, _asset_value(item))
        for item in _list_value(payload.get("forbidden_scope")):
            _add_unique(out_of_scope, _asset_value(item))

        for item in _list_value(payload.get("required_testing_headers")):
            if isinstance(item, dict):
                name = str(item.get("name") or "").strip()
                value = str(item.get("value") or "").strip()
                if name and value:
                    label = f"{name}: {value}"
                    if item.get("required"):
                        label += " (required)"
                    _add_unique(headers, label)
        required_headers = payload.get("required_headers")
        if isinstance(required_headers, dict):
            for name, value in required_headers.items():
                _add_unique(headers, f"{name}: {value}")

        submission_gate = payload.get("submission_gate")
        if isinstance(submission_gate, dict):
            if submission_gate.get("operator_reports_completed"):
                _add_unique(
                    identity_notes,
                    "Operator reports Bugcrowd identity verification completed.",
                )
            if submission_gate.get("operator_action"):
                _add_unique(identity_notes, str(submission_gate["operator_action"]))
        if payload.get("submission_status"):
            _add_unique(identity_notes, str(payload["submission_status"]))

        boundary = payload.get("fathiya_execution_boundary")
        if isinstance(boundary, dict):
            for item in _list_value(boundary.get("blocked_now")):
                _add_unique(stop_rules, str(item))
            for item in _list_value(boundary.get("allowed_now")):
                _add_unique(passive_steps, str(item))
            if boundary.get("next_gate"):
                _add_unique(passive_steps, str(boundary["next_gate"]))
        for key in ("rate_and_noise_limits", "blocked_agent_modes", "production_constraints"):
            for item in _list_value(payload.get(key)):
                _add_unique(stop_rules, str(item))
        tool_policy = payload.get("tool_policy")
        if isinstance(tool_policy, dict):
            for tool, policy in tool_policy.items():
                _add_unique(tool_notes, f"{tool}: {policy}")

    if not in_scope and not out_of_scope and not headers:
        return None

    lines = [
        "فهم نطاق Web.com Bugcrowd من المصادر الصريحة:",
        "",
        "الأهداف داخل النطاق:",
        *_bullet_lines(in_scope or ["لم تسجل المصادر الصريحة أهدافا داخل النطاق."]),
        "",
        "الأصول الخارجة عن النطاق:",
        *_bullet_lines(out_of_scope or ["لم تسجل المصادر الصريحة أصولا خارجة عن النطاق."]),
        "",
        "الهيدرات المطلوبة أو الاختيارية:",
        *_bullet_lines(headers or ["لم تسجل المصادر الصريحة هيدرات."]),
        "",
        "حالة الهوية والتقديم:",
        *_bullet_lines(identity_notes or ["لا توجد ملاحظة هوية في المصادر الصريحة."]),
        "",
        "قواعد الإيقاف:",
        *_bullet_lines(stop_rules or ["لا توجد قواعد إيقاف في المصادر الصريحة."]),
        "",
        "خطة passive-only التالية:",
        *_bullet_lines(passive_steps or ["راجع النطاق ثم ابن خطة غير تدميرية قبل أي طلب حي."]),
    ]
    if tool_notes:
        lines.extend(["", "سياسة الأدوات:", *_bullet_lines(tool_notes)])
    lines.extend(["", "المصادر:", *_bullet_lines(source_paths)])
    return "\n".join(lines)


def _requests_exact_source_values(prompt: str) -> bool:
    lowered = prompt.casefold()
    return any(
        term in lowered
        for term in (
            "knowledge/",
            "القيم الدقيقة",
            "حرفيًا",
            "حرفيا",
            "exact",
            "اذكر",
        )
    )


def _json_source(value: str) -> dict[str, Any] | None:
    stripped = value.strip()
    if not stripped.startswith("{"):
        return None
    try:
        payload = json.JSONDecoder().raw_decode(stripped)[0]
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _collect_markdown_scope(
    text: str,
    *,
    in_scope: list[str],
    out_of_scope: list[str],
    headers: list[str],
    identity_notes: list[str],
    stop_rules: list[str],
    passive_steps: list[str],
) -> None:
    for asset in re.findall(r"`(https://www\.(?:networksolutions|bluehost|hostgator)\.com/)`", text):
        _add_unique(in_scope, asset)
    for asset in re.findall(
        r"`(\*\.(?:web|register|networksolutions|bluehost|hostgator)\.com|https://app\.(?:gator|web)\.com/)`",
        text,
    ):
        _add_unique(out_of_scope, asset)
    for header in re.findall(r"`(X-[A-Za-z-]+:\s*[^`]+)`", text):
        _add_unique(headers, header)
    if "identity verification is complete" in text:
        _add_unique(identity_notes, "Operator reports Bugcrowd identity verification completed.")
    for line in re.findall(r"(?:^|\s)(?:Do not|Stop before|Before final submission)[^.]+[.]", text):
        _add_unique(stop_rules, line.strip())
    for line in re.findall(r"\d+\.\s+([^0-9\n][^\n]+)", text):
        if any(term in line.casefold() for term in ("scope", "target", "header", "plan", "stop")):
            _add_unique(passive_steps, line.strip())


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _asset_value(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("asset") or item.get("url") or "").strip()
    return str(item).strip()


def _add_unique(items: list[str], value: str) -> None:
    clean = re.sub(r"\s+", " ", value).strip()
    if clean and clean not in items:
        items.append(clean)


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items]
