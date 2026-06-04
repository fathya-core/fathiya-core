from __future__ import annotations

from typing import Any

from .config import RuntimeConfig
from .zapier_mcp import ZapierTokenStore


def build_integration_readiness(
    config: RuntimeConfig,
    connectors: list[dict[str, Any]],
    inventory: dict[str, Any],
    local_capabilities: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return secret-safe account and integration readiness for the operator UI."""

    connector_by_name = {item["name"]: item for item in connectors}
    zapier_apps = [
        str(item.get("app"))
        for item in inventory.get("zapier_apps", [])
        if item.get("app")
    ]
    zapier_inventory_ready = (
        inventory.get("available") is True
        and inventory.get("zapier_mcp_status", {}).get("inventory") == "active"
    )
    zapier_bridge_ready = bool(
        connector_by_name.get("zapier_fathiya_webhook", {}).get("configured")
    )
    zapier_direct_ready = bool(
        ZapierTokenStore(
            config.zapier_mcp_token_path,
            config.zapier_mcp_access_token,
        ).status()["connected"]
    )
    n8n_health_ready = bool(
        connector_by_name.get("n8n_health", {}).get("configured")
    )
    n8n_workflows_ready = bool(
        connector_by_name.get("n8n_workflows", {}).get("configured")
    )
    hugging_face_ready = config.enable_hf_retrieval or config.enable_local_generation
    capability_rows = [
        item
        for item in (local_capabilities or {}).get("capabilities", [])
        if isinstance(item, dict)
    ]
    ready_capabilities = [
        str(item.get("name"))
        for item in capability_rows
        if item.get("status") in {"active", "ready"} and item.get("name")
    ]
    partial_capabilities = [
        str(item.get("name"))
        for item in capability_rows
        if item.get("status") in {"partial", "degraded"} and item.get("name")
    ]

    supabase_missing = [
        name
        for name, value in (
            ("SUPABASE_URL", config.supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", config.supabase_service_role_key),
        )
        if not value
    ]

    integrations = [
        {
            "id": "local_execution_mesh",
            "name": "شبكة التنفيذ المحلية",
            "category": "automation",
            "status": (
                "ready"
                if capability_rows and not partial_capabilities
                else "partial"
                if ready_capabilities
                else "needs_setup"
            ),
            "connection_mode": "local_runtime_probe",
            "account_required": False,
            "credential_policy": "none",
            "summary": (
                f"{len(ready_capabilities)} من {len(capability_rows)} بوابات محلية جاهزة للتنفيذ."
                if capability_rows
                else "لم يُنفذ فحص شبكة التنفيذ المحلية."
            ),
            "next_step": (
                f"أكمل البوابات الجزئية: {', '.join(partial_capabilities)}."
                if partial_capabilities
                else "لا إجراء مطلوب."
            ),
            "missing_env": [],
            "connected_apps": ready_capabilities,
            "details": {
                "ready_count": len(ready_capabilities),
                "partial_count": len(partial_capabilities),
                "capability_count": len(capability_rows),
            },
        },
        {
            "id": "huggingface_local",
            "name": "Hugging Face المحلي",
            "category": "model",
            "status": "ready" if hugging_face_ready else "needs_setup",
            "connection_mode": "local_model",
            "account_required": False,
            "credential_policy": "none",
            "summary": "استرجاع وتوليد محليان دون حساب خارجي."
            if hugging_face_ready
            else "النماذج المحلية مثبتة لكن تشغيلها غير مفعّل.",
            "next_step": "لا يلزم حساب."
            if hugging_face_ready
            else "فعّل FATHIYA_ENABLE_HF_RETRIEVAL أو FATHIYA_ENABLE_LOCAL_GENERATION محليًا.",
            "missing_env": [],
            "connected_apps": [],
            "details": {
                "retrieval_enabled": config.enable_hf_retrieval,
                "generation_enabled": config.enable_local_generation,
                "retrieval_model": config.hf_model,
                "generation_model": config.local_model,
            },
        },
        {
            "id": "openrouter",
            "name": "OpenRouter",
            "category": "model",
            "status": "ready" if config.openrouter_api_key else "needs_setup",
            "connection_mode": "server_api_key",
            "account_required": True,
            "credential_policy": "local_server_only",
            "summary": "مفتاح الخادم موجود ويمكن للنماذج الثقيلة العمل."
            if config.openrouter_api_key
            else "لا يوجد مفتاح OpenRouter في المشغّل المحلي.",
            "next_step": "لا إجراء مطلوب."
            if config.openrouter_api_key
            else "أنشئ مفتاح OpenRouter واحفظه في ملف .env المحلي؛ لا ترسله في المحادثة.",
            "missing_env": [] if config.openrouter_api_key else ["OPENROUTER_API_KEY"],
            "connected_apps": [],
            "details": {"model": config.openrouter_model},
        },
        {
            "id": "supabase",
            "name": "Supabase",
            "category": "control_plane",
            "status": "ready" if not supabase_missing else "needs_setup",
            "connection_mode": "server_api_key",
            "account_required": True,
            "credential_policy": "local_server_only",
            "summary": "قناة المهام الإنتاجية جاهزة."
            if not supabase_missing
            else "المشغّل المحلي يعمل على SQLite؛ قناة الإنتاج غير مربوطة.",
            "next_step": "لا إجراء مطلوب."
            if not supabase_missing
            else "اربط مشروع Supabase واحفظ URL ومفتاح الخدمة في الخادم فقط.",
            "missing_env": supabase_missing,
            "connected_apps": [],
            "details": {"local_fallback": "sqlite"},
        },
        {
            "id": "n8n_local",
            "name": "n8n المحلي",
            "category": "automation",
            "status": (
                "ready"
                if n8n_health_ready and n8n_workflows_ready
                else "partial"
                if n8n_health_ready
                else "needs_setup"
            ),
            "connection_mode": "local_service",
            "account_required": False,
            "credential_policy": "local_server_only",
            "summary": "الخدمة ومساراتها الموثقة جاهزة."
            if n8n_health_ready and n8n_workflows_ready
            else "خدمة n8n المحلية جاهزة، لكن قراءة المسارات تحتاج مفتاح API."
            if n8n_health_ready
            else "خدمة n8n المحلية غير مهيأة.",
            "next_step": "لا إجراء مطلوب."
            if n8n_health_ready and n8n_workflows_ready
            else "أضف N8N_API_KEY محليًا لقراءة المسارات."
            if n8n_health_ready
            else "شغّل n8n المحلي واربط عنوانه.",
            "missing_env": [] if n8n_workflows_ready else ["N8N_API_KEY"],
            "connected_apps": [],
            "details": {"base_url": config.n8n_base_url},
        },
        {
            "id": "zapier_mcp",
            "name": "Zapier MCP",
            "category": "automation",
            "status": (
                "ready"
                if zapier_inventory_ready and (zapier_direct_ready or zapier_bridge_ready)
                else "partial"
                if zapier_inventory_ready
                else "needs_setup"
            ),
            "connection_mode": "local_oauth_mcp",
            "account_required": True,
            "credential_policy": "oauth_managed",
            "summary": (
                f"{len(zapier_apps)} تطبيقًا متصلًا عبر OAuth و"
                f"{int(inventory.get('zapier_action_count', 0))} إجراءً متاحًا."
            )
            if zapier_inventory_ready
            else "لم يُحمّل مخزون حسابات Zapier المتصلة.",
            "next_step": "اربط Zapier MCP بالمحرك المحلي عبر OAuth؛ لا ترسل كلمة مرور أو رمزًا."
            if zapier_inventory_ready and not zapier_direct_ready
            else "لا إجراء مطلوب."
            if zapier_inventory_ready and (zapier_direct_ready or zapier_bridge_ready)
            else "اربط التطبيقات المطلوبة داخل Zapier MCP عبر OAuth.",
            "missing_env": [],
            "connected_apps": zapier_apps,
            "action_path": (
                None
                if zapier_direct_ready
                else "/api/agent/oauth/zapier/start"
            ),
            "action_label": (
                None
                if zapier_direct_ready
                else "ربط Zapier MCP محليًا"
            ),
            "details": {
                "app_count": len(zapier_apps),
                "action_count": int(inventory.get("zapier_action_count", 0)),
                "direct_oauth_connected": zapier_direct_ready,
                "webhook_bridge_ready": zapier_bridge_ready,
            },
        },
        {
            "id": "broker_testnet",
            "name": "وسيط التداول التجريبي",
            "category": "financial",
            "status": "needs_operator",
            "connection_mode": "trade_only_testnet_api",
            "account_required": True,
            "credential_policy": "local_server_only",
            "summary": "لا يوجد حساب وسيط أو Testnet مربوط، والتنفيذ الحقيقي مقفل.",
            "next_step": "اختر وسيطًا وسوقًا وحساب Testnet بمفتاح تداول فقط دون صلاحية سحب.",
            "missing_env": [],
            "connected_apps": [],
            "details": {
                "live_execution_enabled": False,
                "withdrawal_permission_allowed": False,
            },
        },
    ]

    return {
        "integrations": integrations,
        "summary": {
            "total": len(integrations),
            "ready": sum(item["status"] == "ready" for item in integrations),
            "partial": sum(item["status"] == "partial" for item in integrations),
            "needs_setup": sum(
                item["status"] == "needs_setup" for item in integrations
            ),
            "needs_operator": sum(
                item["status"] == "needs_operator" for item in integrations
            ),
        },
        "security_policy": {
            "accept_passwords_in_chat": False,
            "oauth_accounts_managed_by_provider": True,
            "server_keys_stay_local": True,
            "financial_live_execution_requires_approval": True,
        },
    }
