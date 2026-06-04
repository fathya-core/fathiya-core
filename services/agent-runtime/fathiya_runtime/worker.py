from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from typing import Any

from .config import RuntimeConfig
from .models import AgentModelRouter
from .planner import build_plan
from .retrieval import KnowledgeRetriever
from .store import TaskStore, now_iso
from .tools import ToolExecutionError, ToolExecutor


class TaskCanceledError(RuntimeError):
    pass


class AgentWorker:
    def __init__(self, config: RuntimeConfig, store: TaskStore):
        self.config = config
        self.store = store
        self.model = AgentModelRouter(
            config.openrouter_api_key,
            config.openrouter_model,
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
        self.tools = ToolExecutor(config)
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
                self._process(task)
            if once:
                self.store.heartbeat_worker(self.config.worker_id, "online")
                return processed
            time.sleep(poll_seconds)

    def _process(self, task: dict[str, Any]) -> None:
        try:
            self.store.heartbeat_worker(self.config.worker_id, "busy")
            self._progress(task, 5, "بدء التنفيذ", "started", "بدأ المشغّل المحلي المهمة.")

            sources = self.retriever.search(task["prompt"], limit=5)
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

            plan = build_plan(
                task,
                sources,
                self.model,
                self.tools.catalog(),
                max_tool_steps=self.config.max_tool_steps,
            )
            self.store.update_task(
                task["id"],
                plan=plan,
                last_heartbeat_at=now_iso(),
                current_step="تم بناء خطة التنفيذ",
            )
            self.store.add_event(
                task,
                "planned",
                "بُنيت خطة التنفيذ من الأدلة والأدوات المسموحة.",
                status="running",
                step="plan",
                progress=30,
                payload={"plan": plan},
            )

            execution_steps = [step for step in plan if step.get("kind") == "tool"]
            if self._gate_plan_for_approval(task, execution_steps):
                return

            tool_results: list[dict[str, Any]] = []
            for index, execution_step in enumerate(execution_steps, start=1):
                start_progress = 35 + int(((index - 1) / len(execution_steps)) * 40)
                complete_progress = 35 + int((index / len(execution_steps)) * 40)
                self._progress(
                    task,
                    start_progress,
                    execution_step["description"],
                    "tool_started",
                    f"تشغيل الأداة {index}/{len(execution_steps)}: {execution_step['tool']}",
                    {
                        "tool": execution_step["tool"],
                        "args": execution_step.get("args", {}),
                    },
                )
                tool_result = self.tools.execute(
                    execution_step["tool"],
                    task["prompt"],
                    execution_step.get("args", {}),
                    tool_results,
                )
                tool_results.append(
                    {
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
                    f"اكتمل تنفيذ {execution_step['tool']}.",
                    {"tool_result": tool_result},
                )

            self._progress(
                task,
                80,
                "تلخيص الأدلة",
                "synthesis_started",
                "بدأ تلخيص الأدلة ونتائج الأدوات.",
            )
            synthesis = self._synthesize(task, sources, tool_results)
            self._progress(
                task,
                85,
                "تقييم النتيجة",
                "synthesized",
                "تم تلخيص النتيجة وبدأ التقييم.",
                {"synthesis": synthesis},
            )
            evaluation = self.model.evaluate(
                task["prompt"],
                {"tool_results": tool_results, "synthesis": synthesis},
            )
            model_trace = {
                "planner_provider": plan[0].get("planner_mode"),
                "planner_error": plan[0].get("planner_error"),
                "last_provider": self.model.last_provider,
                "provider_fallbacks": self.model.last_error,
            }
            result = {
                "synthesis": synthesis,
                "tool_results": tool_results,
                "tool_result": tool_results[-1]["result"] if tool_results else None,
                "evaluation": evaluation,
                "model_trace": model_trace,
                "sources": [source.__dict__ for source in sources],
            }

            self._ensure_not_canceled(task)
            receipt_id = self.store.add_receipt(
                task,
                "completed",
                synthesis[:1000],
                {
                    "worker_id": self.config.worker_id,
                    "tools": [step["tool"] for step in execution_steps],
                    "evaluation": evaluation,
                    "model_trace": model_trace,
                    "source_count": len(sources),
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
            self.store.heartbeat_worker(self.config.worker_id, "online")

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
        self.store.update_task(
            task["id"],
            status="awaiting_approval",
            progress=30,
            current_step=f"الخطة تحتاج موافقة قبل تشغيل {gated[0]['tool']}",
            risk_class=risk_class,
            requires_approval=True,
            approval_state="pending",
            last_heartbeat_at=now_iso(),
        )
        self.store.add_event(
            task,
            "approval_required",
            "اختارت خطة التنفيذ أداة ذات أثر حساس وتوقفت قبل تشغيلها.",
            status="awaiting_approval",
            step="plan_approval_gate",
            progress=30,
            payload={"gated_steps": gated},
        )
        return True

    def _synthesize(
        self,
        task: dict[str, Any],
        sources: list[Any],
        tool_results: list[dict[str, Any]],
    ) -> str:
        if self.model.available:
            context = "\n".join(
                f"- {source.path}: {source.excerpt[:400]}" for source in sources
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
                if _is_useful_synthesis(synthesis):
                    return synthesis
            except Exception:
                pass
        return _deterministic_synthesis(tool_results, len(sources))


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
            "version",
            "error",
            "message",
            "profile",
            "provider",
            "profile_count",
            "configured_count",
            "zapier_app_count",
            "zapier_action_count",
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
        if isinstance(result.get("metadata"), dict):
            summary["metadata"] = result["metadata"]
        if isinstance(result.get("workflows"), dict):
            summary["workflows"] = result["workflows"]
        if result.get("stdout"):
            summary["stdout"] = str(result["stdout"])[:600]
        compact.append(summary)
    return compact


def _is_useful_synthesis(value: str) -> bool:
    meaningful = re.sub(r"[\s#*_`~>\-:;,.!?()[\]{}]+", "", value)
    return len(meaningful) >= 40


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
            if isinstance(zapier_status, dict) and zapier_status.get("action_execution") == "degraded":
                follow_up.append("تنفيذ إجراءات Zapier MCP يحتاج إصلاح تمرير selected_api.")
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
        elif "available" in result:
            evidence.append(f"{tool}: {'متاح' if result.get('available') else 'غير متاح'}.")
        elif result.get("return_code") is not None:
            evidence.append(f"{tool}: رمز الخروج {result.get('return_code')}.")

    lines = [
        f"اكتمل تنفيذ {len(names)} أدوات داخلية: {', '.join(names) or 'لا توجد أدوات'}.",
        f"استُرجع {source_count} مصادر معرفة مرتبطة بالطلب.",
    ]
    if evidence:
        lines.append("الأدلة المثبتة: " + " ".join(evidence))
    if follow_up:
        lines.append("المتابعة المطلوبة: " + " ".join(dict.fromkeys(follow_up)))
    return "\n".join(lines)
