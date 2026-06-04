from __future__ import annotations

from typing import Any

from .models import OpenRouterClient
from .retrieval import RetrievedSource


def build_plan(
    task: dict[str, Any],
    sources: list[RetrievedSource],
    model: OpenRouterClient,
) -> list[dict[str, Any]]:
    prompt = task["prompt"].lower()
    steps: list[dict[str, Any]] = [
        {
            "id": "retrieve",
            "tool": "knowledge_search",
            "description": "استرجاع المعرفة المرتبطة بالطلب",
        }
    ]

    if any(term in prompt for term in ("git", "repo", "repository", "مستودع", "الكود")):
        tool = "repo_status"
        description = "قراءة حالة المستودع الأساسي"
    elif "n8n" in prompt:
        tool = "n8n_status"
        description = "قراءة حالة n8n المحلية"
    elif any(
        term in prompt
        for term in ("zapier", "زابير", "manus", "cursor", "gmail", "netlify", "agents")
    ):
        tool = "connected_tool_inventory"
        description = "قراءة مخزون الأدوات والوكلاء المتصلين وسياسة تنفيذهم"
    elif any(term in prompt for term in ("kali", "كالي", "nmap", "nuclei", "الأدوات")):
        tool = "kali_tool_inventory"
        description = "قراءة توفر الأدوات داخل Kali WSL"
    elif any(term in prompt for term in ("security", "أمن", "اختراق", "ثغرات", "فحص")):
        tool = "security_core_plan"
        description = "تشغيل نواة الأمن الدفاعية بدون فحص حي"
    else:
        tool = "internal_echo"
        description = "تنفيذ إثبات داخلي آمن"

    steps.append({"id": "execute", "tool": tool, "description": description})
    steps.append(
        {
            "id": "synthesize",
            "tool": "synthesize",
            "description": "تلخيص الأدلة والنتيجة",
            "model": model.model if model.available else "local_fallback",
            "retrieved_sources": len(sources),
        }
    )
    steps.append({"id": "evaluate", "tool": "evaluate", "description": "تقييم النتيجة وإصدار إيصال"})
    return steps
