from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any

from .config import RuntimeConfig
from .models import OpenRouterClient
from .planner import build_plan
from .retrieval import KnowledgeRetriever
from .store import TaskStore, now_iso
from .tools import ToolExecutor


class TaskCanceledError(RuntimeError):
    pass


class AgentWorker:
    capabilities = [
        "knowledge_search",
        "openrouter_reasoning",
        "repo_status",
        "n8n_status",
        "connected_tool_inventory",
        "kali_tool_inventory",
        "security_core_plan",
    ]

    def __init__(self, config: RuntimeConfig, store: TaskStore):
        self.config = config
        self.store = store
        self.model = OpenRouterClient(config.openrouter_api_key, config.openrouter_model)
        self.retriever = KnowledgeRetriever(
            config.knowledge_root,
            enable_hf=config.enable_hf_retrieval,
            hf_model=config.hf_model,
        )
        self.tools = ToolExecutor(config)

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

            plan = build_plan(task, sources, self.model)
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

            execution_step = next(step for step in plan if step["id"] == "execute")
            self._progress(
                task,
                45,
                execution_step["description"],
                "tool_started",
                f"تشغيل الأداة: {execution_step['tool']}",
            )
            tool_result = self.tools.execute(execution_step["tool"], task["prompt"])
            self._progress(
                task,
                70,
                "اكتمل تنفيذ الأداة",
                "tool_completed",
                f"اكتمل تنفيذ {execution_step['tool']}.",
                {"tool_result": tool_result},
            )

            synthesis = self._synthesize(task, sources, tool_result)
            self._progress(
                task,
                85,
                "تقييم النتيجة",
                "synthesized",
                "تم تلخيص النتيجة وبدأ التقييم.",
                {"synthesis": synthesis},
            )
            evaluation = self.model.evaluate(task["prompt"], {"tool_result": tool_result, "synthesis": synthesis})
            result = {
                "synthesis": synthesis,
                "tool_result": tool_result,
                "evaluation": evaluation,
                "sources": [source.__dict__ for source in sources],
            }

            self._ensure_not_canceled(task)
            receipt_id = self.store.add_receipt(
                task,
                "completed",
                synthesis[:1000],
                {
                    "worker_id": self.config.worker_id,
                    "tool": execution_step["tool"],
                    "evaluation": evaluation,
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
            self.store.update_task(
                task["id"],
                status="failed",
                current_step="فشل التنفيذ",
                error_message=str(exc),
                last_heartbeat_at=now_iso(),
                completed_at=now_iso(),
            )
            self.store.add_event(
                task,
                "failed",
                f"فشل التنفيذ: {exc}",
                status="failed",
                step="error",
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

    def _synthesize(
        self,
        task: dict[str, Any],
        sources: list[Any],
        tool_result: dict[str, Any],
    ) -> str:
        if self.model.available:
            context = "\n".join(
                f"- {source.path}: {source.excerpt[:400]}" for source in sources
            )
            try:
                return self.model.complete(
                    "أنت وكيل تنفيذ في فتحية. لخّص ما نُفذ وما ثبت وما يحتاج متابعة. لا تدّعِ شيئًا بلا دليل.",
                    f"الطلب:\n{task['prompt']}\n\nالمصادر:\n{context}\n\nنتيجة الأداة:\n{json.dumps(tool_result, ensure_ascii=False)[:8000]}",
                )
            except Exception as exc:
                return f"اكتمل التنفيذ المحلي، وتعذر تلخيص OpenRouter: {exc}"
        return (
            "اكتمل التنفيذ المحلي بنجاح. "
            f"الأداة المستخدمة: {tool_result.get('tool', 'unknown')}. "
            f"عدد مصادر المعرفة المسترجعة: {len(sources)}."
        )
