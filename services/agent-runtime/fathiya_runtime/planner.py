from __future__ import annotations

import json
import re
from typing import Any

from .models import ModelClient
from .retrieval import RetrievedSource


def build_plan(
    task: dict[str, Any],
    sources: list[RetrievedSource],
    model: ModelClient,
    tool_catalog: list[dict[str, Any]],
    *,
    max_tool_steps: int = 6,
) -> list[dict[str, Any]]:
    tool_steps, planner_mode, planner_error = _model_steps(
        task,
        sources,
        model,
        tool_catalog,
        max_tool_steps,
    )
    if not tool_steps:
        tool_steps = _fallback_steps(task["prompt"], tool_catalog, max_tool_steps)
        planner_mode = "local_fallback"

    plan: list[dict[str, Any]] = [
        {
            "id": "retrieve",
            "kind": "retrieval",
            "tool": "knowledge_search",
            "description": "استرجاع المعرفة المرتبطة بالطلب",
            "planner_mode": planner_mode,
            "planner_error": planner_error,
            "retrieved_sources": len(sources),
        }
    ]
    catalog_by_name = {str(item["name"]): item for item in tool_catalog}
    for index, step in enumerate(tool_steps, start=1):
        tool = str(step["tool"])
        spec = catalog_by_name[tool]
        plan.append(
            {
                "id": f"execute-{index}",
                "kind": "tool",
                "tool": tool,
                "description": str(step.get("description") or spec["description"]),
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
            "model": model.model if model.available else "local_fallback",
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


def _model_steps(
    task: dict[str, Any],
    sources: list[RetrievedSource],
    model: ModelClient,
    tool_catalog: list[dict[str, Any]],
    max_tool_steps: int,
) -> tuple[list[dict[str, Any]], str, str | None]:
    if not model.available:
        return [], "local_fallback", None
    compact_catalog = [
        {
            "name": item["name"],
            "description": item["description"],
            "category": item["category"],
            "risk_class": item["risk_class"],
            "requires_approval": item["requires_approval"],
            "inputs": item.get("inputs", []),
            "profiles": item.get("profiles", []),
            "configured": item.get("configured", True),
        }
        for item in tool_catalog
    ]
    source_map = [
        {"path": source.path, "excerpt": source.excerpt[:500], "score": source.score}
        for source in sources
    ]
    try:
        plan_complete = getattr(model, "plan_complete", model.complete)
        raw = plan_complete(
            (
                "You are the FATHIYA execution planner. Return JSON only with a steps array. "
                "Select one or more registered tools that genuinely move the request forward. "
                "Use at most the requested maximum. Do not invent tools. Put tool inputs in args. "
                "A sensitive tool may be selected because the runtime will enforce approval. "
                "Prefer useful execution over analysis-only filler."
            ),
            json.dumps(
                {
                    "request": task["prompt"],
                    "max_tool_steps": max_tool_steps,
                    "retrieved_sources": source_map,
                    "tools": compact_catalog,
                    "output_schema": {
                        "steps": [
                            {
                                "tool": "registered tool name",
                                "description": "what this step proves or changes",
                                "args": {},
                            }
                        ]
                    },
                },
                ensure_ascii=False,
            ),
            json_mode=True,
        )
        payload = _json_value(raw)
        requested = payload.get("steps", []) if isinstance(payload, dict) else payload
        validated = _validate_steps(requested, tool_catalog, max_tool_steps)
        provider = getattr(model, "last_provider", "openrouter")
        return validated, provider, None if validated else f"{provider} returned no valid tools"
    except Exception as exc:
        return [], "local_fallback", f"{type(exc).__name__}: {str(exc)[:500]}"


def _validate_steps(
    requested: Any,
    tool_catalog: list[dict[str, Any]],
    max_tool_steps: int,
) -> list[dict[str, Any]]:
    if not isinstance(requested, list):
        return []
    available = {
        str(item["name"]): item
        for item in tool_catalog
        if bool(item.get("configured", True))
    }
    validated: list[dict[str, Any]] = []
    for item in requested:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "")
        if tool not in available:
            continue
        args = item.get("args")
        clean_args = args if isinstance(args, dict) else {}
        if not _profile_args_are_configured(tool, clean_args, available[tool]):
            continue
        validated.append(
            {
                "tool": tool,
                "description": str(item.get("description") or ""),
                "args": clean_args,
            }
        )
        if len(validated) >= max_tool_steps:
            break
    return validated


def _profile_args_are_configured(
    tool: str,
    args: dict[str, Any],
    spec: dict[str, Any],
) -> bool:
    if tool not in {"command_profile", "connector_profile"}:
        return True
    requested = str(args.get("profile") or "")
    profiles = spec.get("profiles", [])
    return any(
        isinstance(profile, dict)
        and profile.get("name") == requested
        and bool(profile.get("configured", True))
        for profile in profiles
    )


def _fallback_steps(
    prompt: str,
    tool_catalog: list[dict[str, Any]],
    max_tool_steps: int,
) -> list[dict[str, Any]]:
    text = prompt.lower()
    available = {
        str(item["name"]): item
        for item in tool_catalog
        if bool(item.get("configured", True))
    }
    steps: list[dict[str, Any]] = []

    def add(tool: str, description: str, args: dict[str, Any] | None = None) -> None:
        if tool in available and not any(step["tool"] == tool for step in steps):
            steps.append({"tool": tool, "description": description, "args": args or {}})

    urls = re.findall(r"https?://[^\s<>'\"،]+", prompt, re.IGNORECASE)
    if urls and any(term in text for term in ("ingest", "استوعب", "احفظ", "تقرير", "report")):
        add(
            "knowledge_ingest_url",
            "جلب المصدر وحفظه داخل معرفة فتحية",
            {"url": urls[0].rstrip(").,]")},
        )
    elif urls:
        add("web_fetch", "جلب المصدر الخارجي كدليل", {"url": urls[0].rstrip(").,]")})

    if any(term in text for term in ("tool", "agent", "capabil", "أداة", "أدوات", "وكلاء")):
        add("tool_catalog", "عرض كتالوج التنفيذ المتاح للمحرك")
    if any(
        term in text
        for term in (
            "connector",
            "zapier",
            "زابير",
            "manus",
            "cursor",
            "gmail",
            "netlify",
            "موصل",
            "موصلات",
        )
    ):
        add("connector_catalog", "عرض جاهزية بوابات تنفيذ الموصلات")
        add("connected_tool_inventory", "قراءة موصلات ووكلاء الحساب المتاحين")
    if any(term in text for term in ("git", "repo", "repository", "مستودع", "الكود", "github")):
        add("repo_status", "قراءة حالة المستودع الأساسي")
    if any(term in text for term in ("github", "pull request", " pr ", "issue", "جيت هب")):
        add("github_repo_info", "قراءة بيانات مستودع GitHub المصادق")
    if any(term in text for term in ("search code", "find in repo", "ابحث في الكود", "ابحث بالمستودع")):
        add("repo_search", "البحث داخل المستودع", {"query": prompt[:300]})
    if "n8n" in text:
        add("connector_catalog", "عرض جاهزية بوابات تنفيذ الموصلات")
        add("n8n_status", "قراءة حالة n8n المحلية")
        add("n8n_workflows", "قراءة مسارات n8n المتاحة")
    if any(term in text for term in ("kali", "كالي", "nmap", "nuclei")):
        add("kali_tool_inventory", "قراءة الأدوات المتاحة داخل Kali WSL")
    if any(term in text for term in ("security", "أمن", "اختراق", "ثغرات", "فحص")):
        add("security_core_plan", "تشغيل نواة الأمن الدفاعية المحلية", {"target_or_question": prompt})

    profiles = _profile_names(available.get("command_profile", {}))
    connector_profiles = _profile_names(available.get("connector_profile", {}))
    if "n8n" in text and "n8n_health" in connector_profiles:
        add(
            "connector_profile",
            "التحقق من n8n عبر بوابة الموصلات العامة",
            {"profile": "n8n_health"},
        )
    for connector_profile in sorted(connector_profiles):
        if connector_profile.lower() in text:
            add(
                "connector_profile",
                f"تشغيل موصل {connector_profile}",
                {"profile": connector_profile},
            )
    if any(term in text for term in ("runtime test", "agent runtime test", "اختبارات المحرك")):
        if "runtime_tests" in profiles:
            add("command_profile", "تشغيل اختبارات محرك الوكلاء", {"profile": "runtime_tests"})
    elif any(term in text for term in ("typecheck", "type check", "فحص الأنواع")):
        if "repo_typecheck" in profiles:
            add("command_profile", "تشغيل فحص الأنواع", {"profile": "repo_typecheck"})
    elif any(term in text for term in ("lint", "eslint")):
        if "repo_lint" in profiles:
            add("command_profile", "تشغيل lint للمستودع", {"profile": "repo_lint"})
    elif any(term in text for term in ("build", "بناء المشروع", "ابن المشروع")):
        if "repo_build" in profiles:
            add("command_profile", "بناء المستودع الأساسي", {"profile": "repo_build"})

    if not steps:
        add("internal_echo", "تنفيذ إثبات داخلي وتسجيل نتيجة", {"message": "تم استلام الطلب وتنفيذه داخليًا."})
    return steps[:max_tool_steps]


def _profile_names(command_profile_spec: dict[str, Any]) -> set[str]:
    profiles = command_profile_spec.get("profiles", [])
    if not isinstance(profiles, list):
        return set()
    return {
        str(profile.get("name"))
        for profile in profiles
        if isinstance(profile, dict)
        and profile.get("name")
        and bool(profile.get("configured", True))
    }


def _json_value(raw: str) -> dict[str, Any] | list[Any]:
    object_start = raw.find("{")
    array_start = raw.find("[")
    candidates = [index for index in (object_start, array_start) if index >= 0]
    if not candidates:
        raise ValueError("No JSON object or array found")
    start = min(candidates)
    payload, _end = json.JSONDecoder().raw_decode(raw[start:])
    if not isinstance(payload, (dict, list)):
        raise ValueError("Model planner output must be a JSON object or array")
    return payload
