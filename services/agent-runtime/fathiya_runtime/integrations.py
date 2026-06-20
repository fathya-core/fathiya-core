from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .trading import BinanceSpotTestnetGateway
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
    zapier_status = ZapierTokenStore(
        config.zapier_mcp_token_path,
        config.zapier_mcp_access_token,
    )
    zapier_auth = zapier_status.status()
    zapier_direct_connected = bool(zapier_auth.get("connected"))
    zapier_needs_reconnect = bool(
        zapier_direct_connected
        and (
            zapier_auth.get("expired")
            or zapier_auth.get("refresh_recommended")
            or zapier_auth.get("last_refresh_error")
        )
    )
    zapier_direct_ready = bool(zapier_direct_connected and not zapier_needs_reconnect)
    zapier_ready = bool(zapier_inventory_ready and zapier_direct_ready)
    zapier_partial = bool(
        (zapier_inventory_ready or zapier_direct_connected) and not zapier_ready
    )
    zapier_action_path = (
        None
        if zapier_direct_ready
        else "/api/agent/oauth/zapier/start?force=1"
        if zapier_needs_reconnect
        else "/api/agent/oauth/zapier/start"
    )
    if zapier_ready:
        zapier_summary = (
            f"{len(zapier_apps)} تطبيقًا متصلًا عبر OAuth و"
            f"{int(inventory.get('zapier_action_count', 0))} إجراءً متاحًا."
        )
        zapier_next_step = "لا إجراء مطلوب."
    elif zapier_direct_ready and not zapier_inventory_ready:
        zapier_summary = (
            "Zapier OAuth المحلي متصل، لكن مخزون التطبيقات والإجراءات فارغ أو غير متزامن."
        )
        zapier_next_step = (
            "فعّل أو أعد مزامنة التطبيقات والإجراءات داخل Zapier MCP؛ OAuth المحلي نفسه متصل."
        )
    elif zapier_inventory_ready and zapier_needs_reconnect:
        zapier_summary = (
            f"مخزون Zapier محمّل وفيه {len(zapier_apps)} تطبيقًا، "
            "لكن التنفيذ الحي يحتاج إعادة ربط OAuth."
        )
        zapier_next_step = (
            "أعد ربط Zapier MCP بالكامل؛ رمز OAuth المحلي منتهي أو فشل تجديده."
        )
    elif zapier_inventory_ready:
        zapier_summary = (
            f"مخزون Zapier محمّل وفيه {len(zapier_apps)} تطبيقًا، "
            "لكن OAuth المحلي غير مكتمل."
        )
        zapier_next_step = (
            "اربط Zapier MCP بالمحرك المحلي عبر OAuth؛ لا ترسل كلمة مرور أو رمزًا."
        )
    else:
        zapier_summary = "لم يُحمّل مخزون حسابات Zapier المتصلة."
        zapier_next_step = "اربط التطبيقات المطلوبة داخل Zapier MCP عبر OAuth."
    n8n_health_ready = bool(
        connector_by_name.get("n8n_health", {}).get("configured")
    )
    n8n_workflows_ready = bool(
        connector_by_name.get("n8n_workflows", {}).get("configured")
    )
    n8n_cli_ready = bool(
        shutil.which("n8n")
        or shutil.which("n8n.cmd")
        or (Path.home() / "AppData" / "Roaming" / "npm" / "n8n.cmd").exists()
    )
    n8n_catalog_ready = bool(n8n_workflows_ready or n8n_cli_ready)
    n8n_ready = bool(n8n_health_ready and n8n_catalog_ready)
    n8n_partial = bool(n8n_health_ready or n8n_catalog_ready)
    hugging_face_ready = config.enable_hf_retrieval or config.enable_local_generation
    testnet = BinanceSpotTestnetGateway.from_config(config).status()
    capability_rows = [
        item
        for item in (local_capabilities or {}).get("capabilities", [])
        if isinstance(item, dict)
    ]
    capability_by_id = {
        str(item.get("id")): item for item in capability_rows if item.get("id")
    }
    ready_capabilities = [
        str(item.get("name"))
        for item in capability_rows
        if item.get("status") in {"active", "ready"} and item.get("name")
    ]
    required_partial_capabilities = [
        str(item.get("name"))
        for item in capability_rows
        if item.get("status") in {"partial", "degraded"}
        and item.get("name")
        and item.get("required_for_core") is not False
    ]
    optional_attention_capabilities = [
        str(item.get("name"))
        for item in capability_rows
        if item.get("status") in {"partial", "degraded", "unavailable"}
        and item.get("name")
        and item.get("required_for_core") is False
    ]
    kali_capability = capability_by_id.get("kali_wsl", {})
    kali_status = str(kali_capability.get("status") or "")
    kali_ready = kali_status in {"active", "ready"}
    kali_partial = kali_status in {"partial", "degraded"}
    codespaces_capability = capability_by_id.get("github_codespaces", {})
    codespaces_status = str(codespaces_capability.get("status") or "")
    codespaces_ready = codespaces_status in {"active", "ready"}
    codespaces_partial = codespaces_status in {"partial", "degraded"}
    codespace_count = int(codespaces_capability.get("codespace_count") or 0)
    active_codespace_count = int(
        codespaces_capability.get("active_codespace_count") or 0
    )
    codespaces_auth_command = (
        str(codespaces_capability.get("auth_command") or "").strip()
        or "gh auth login -h github.com -p https -s repo,workflow,read:org,gist,codespace -w"
    )

    supabase_missing = [
        name
        for name, value in (
            ("SUPABASE_URL", config.supabase_url),
            ("SUPABASE_SERVICE_ROLE_KEY", config.supabase_service_role_key),
        )
        if not value
    ]
    supabase_active = not supabase_missing and config.store == "supabase"
    core_ready_count = int(
        (local_capabilities or {}).get("core_ready_count") or len(ready_capabilities)
    )
    core_capability_count = int(
        (local_capabilities or {}).get("core_capability_count") or len(capability_rows)
    )

    integrations = [
        {
            "id": "local_execution_mesh",
            "name": "شبكة التنفيذ المحلية",
            "category": "automation",
            "status": (
                "ready"
                if capability_rows and not required_partial_capabilities
                else "partial"
                if ready_capabilities
                else "needs_setup"
            ),
            "connection_mode": "local_runtime_probe",
            "account_required": False,
            "credential_policy": "none",
            "summary": (
                f"{core_ready_count} من {core_capability_count} بوابات تشغيل أساسية جاهزة."
                if capability_rows
                else "لم يُنفذ فحص شبكة التنفيذ المحلية."
            ),
            "next_step": (
                f"أكمل البوابات الأساسية الجزئية: {', '.join(required_partial_capabilities)}."
                if required_partial_capabilities
                else f"اختياري فقط: {', '.join(optional_attention_capabilities)}."
                if optional_attention_capabilities
                else "لا إجراء مطلوب."
            ),
            "missing_env": [],
            "connected_apps": ready_capabilities,
            "settings_path": "/api/agent/settings/local_execution_mesh",
            "settings_label": "إعداد جسور الوكلاء",
            "probe_path": "/api/agent/integrations/local_execution_mesh/probe",
            "probe_label": "اختبار الشبكة",
            "task_label": "تشغيل وكيل الشبكة",
            "task_prompt": (
                "integration probe: local_execution_mesh\n"
                "اعرض كتالوج الأدوات والوكلاء وافحص شبكة التنفيذ المحلية، ثم سجل إيصالًا."
            ),
            "details": {
                "ready_count": len(ready_capabilities),
                "partial_count": len(required_partial_capabilities),
                "optional_attention_count": len(optional_attention_capabilities),
                "capability_count": len(capability_rows),
                "core_ready_count": core_ready_count,
                "core_capability_count": core_capability_count,
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
            "settings_path": "/api/agent/settings/huggingface_local",
            "settings_label": "إعداد Hugging Face المحلي",
            "probe_path": "/api/agent/integrations/huggingface_local/probe",
            "probe_label": "اختبار المحلي",
            "task_label": "تشغيل وكيل النموذج",
            "task_prompt": (
                "integration probe: huggingface_local\n"
                "افحص Hugging Face المحلي والنماذج المحلية المتاحة، ثم سجل إيصالًا."
            ),
            "details": {
                "retrieval_enabled": config.enable_hf_retrieval,
                "generation_enabled": config.enable_local_generation,
                "planning_enabled": config.enable_local_planning,
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
            else "أنشئ مفتاح OpenRouter وأدخله من إعداد OpenRouter المحلي.",
            "missing_env": [] if config.openrouter_api_key else ["OPENROUTER_API_KEY"],
            "connected_apps": [],
            "settings_path": "/api/agent/settings/openrouter",
            "settings_label": "إعداد OpenRouter محليًا",
            "probe_path": "/api/agent/integrations/openrouter/probe",
            "probe_label": "اختبار الجاهزية",
            "task_label": "تشغيل وكيل OpenRouter",
            "task_prompt": (
                "integration probe: openrouter\n"
                "افحص جاهزية OpenRouter للمحرك المحلي دون صرف tokens، ثم سجل إيصالًا."
            ),
            "details": {
                "model": config.openrouter_model,
                "model_candidates": list(config.openrouter_model_candidates),
                "research_model": config.openrouter_research_model,
                "safety_model": config.openrouter_safety_model,
                "trading_advisory_model": config.trading_advisory_model,
                "trading_advisory_model_candidates": list(
                    config.trading_advisory_model_candidates
                ),
                "fusion_policy": {
                    "invocation_modes": [
                        "direct_model_slug",
                        "server_tool_from_current_model",
                    ],
                    "enabled_for": [
                        "deep research",
                        "knowledge learning",
                        "source-grounded comparison",
                    ],
                    "not_default_for": ["coding agents", "general chat"],
                    "panel_limit": 8,
                    "web_search_default": True,
                },
                "free_model_routing": True,
            },
        },
        {
            "id": "github_codespaces",
            "name": "GitHub Codespaces",
            "category": "engineering",
            "status": (
                "ready"
                if codespaces_ready
                else "partial"
                if codespaces_partial
                else "needs_setup"
            ),
            "connection_mode": "github_remote_dev",
            "account_required": True,
            "credential_policy": "oauth_managed",
            "summary": (
                f"حساب GitHub يعرض {codespace_count} Codespaces، منها {active_codespace_count} نشطة."
                if codespaces_ready
                else "GitHub CLI موجود لكن وصول Codespaces غير مؤكد."
                if codespaces_partial
                else "لم تُؤكد جاهزية GitHub Codespaces بعد."
            ),
            "next_step": (
                "لا إجراء مطلوب للفحص؛ التنفيذ داخل Codespace يبقى موافقة منفصلة."
                if codespaces_ready
                else f"أكمل تفويض GitHub CLI: {codespaces_auth_command}"
            ),
            "missing_env": [],
            "connected_apps": ["gh codespace"] if codespaces_ready else [],
            "action_path": None
            if codespaces_ready
            else "/api/agent/oauth/github/codespaces/start",
            "action_label": None
            if codespaces_ready
            else "تفويض GitHub Codespaces",
            "probe_path": "/api/agent/integrations/github_codespaces/probe",
            "probe_label": "اختبار Codespaces",
            "task_label": "تشغيل وكيل Codespaces",
            "task_prompt": (
                "integration probe: github_codespaces\n"
                "افحص GitHub Codespaces المتاحة لحساب GitHub المصادق دون تنفيذ أوامر بعيدة، ثم سجل إيصالًا."
            ),
            "details": {
                "status": codespaces_status or "unknown",
                "codespace_count": codespace_count,
                "active_codespace_count": active_codespace_count,
                "execution_mode": codespaces_capability.get("execution_mode"),
                "auth_state": codespaces_capability.get("auth_state"),
                "missing_scope": codespaces_capability.get("missing_scope"),
                "operator_action_required": bool(
                    codespaces_capability.get("operator_action_required")
                ),
                "required_scope": "codespace",
                "auth_command": codespaces_auth_command,
                "requires_approval_for_remote_execution": True,
            },
        },
        {
            "id": "supabase",
            "name": "Supabase",
            "category": "control_plane",
            "status": (
                "ready"
                if supabase_active
                else "partial"
                if not supabase_missing
                else "needs_setup"
            ),
            "connection_mode": "server_api_key",
            "account_required": True,
            "credential_policy": "local_server_only",
            "summary": "قناة المهام الإنتاجية مفعلة."
            if supabase_active
            else "بيانات Supabase محفوظة، والمشغّل الحالي ما زال على SQLite."
            if not supabase_missing
            else "المشغّل المحلي يعمل على SQLite؛ قناة الإنتاج غير مربوطة.",
            "next_step": "لا إجراء مطلوب."
            if supabase_active
            else (
                "طبّق supabase/migrations/20260604120000_agent_runtime_v1.sql "
                "ثم أعد تشغيل المشغّل بوضع Supabase."
            )
            if not supabase_missing
            else (
                "طبّق supabase/migrations/20260604120000_agent_runtime_v1.sql، "
                "ثم أدخل URL ومفتاح الخدمة من إعداد Supabase المحلي."
            ),
            "missing_env": supabase_missing,
            "connected_apps": [],
            "settings_path": "/api/agent/settings/supabase",
            "settings_label": "إعداد Supabase محليًا",
            "probe_path": "/api/agent/integrations/supabase/probe",
            "probe_label": "اختبار القناة",
            "task_label": "تشغيل وكيل القناة",
            "task_prompt": (
                "integration probe: supabase\n"
                "افحص قناة Supabase للموقع والمشغل المحلي دون كشف المفاتيح، ثم سجل إيصالًا."
            ),
            "details": {
                "active_store": config.store,
                "restart_required": not supabase_active,
                "migration_path": "supabase/migrations/20260604120000_agent_runtime_v1.sql",
            },
        },
        {
            "id": "n8n_local",
            "name": "n8n المحلي",
            "category": "automation",
            "status": (
                "ready"
                if n8n_ready
                else "partial"
                if n8n_partial
                else "needs_setup"
            ),
            "connection_mode": "local_service",
            "account_required": False,
            "credential_policy": "local_server_only",
            "summary": "الخدمة ومساراتها الموثقة جاهزة."
            if n8n_ready
            else "خدمة n8n المحلية جاهزة، لكن قراءة المسارات تحتاج مفتاح API."
            if n8n_health_ready
            else "مسارات n8n قابلة للقراءة عبر CLI، لكن نقطة صحة الخدمة بطيئة أو غير متاحة."
            if n8n_catalog_ready
            else "خدمة n8n المحلية غير مهيأة.",
            "next_step": "لا إجراء مطلوب."
            if n8n_ready
            else "أضف N8N_API_KEY محليًا لقراءة المسارات."
            if n8n_health_ready
            else "أعد تشغيل n8n أو افتح واجهته المحلية إذا احتجت health endpoint، مع بقاء CLI fallback فعالًا."
            if n8n_catalog_ready
            else "شغّل n8n المحلي واربط عنوانه.",
            "missing_env": [] if n8n_catalog_ready else ["N8N_API_KEY"],
            "connected_apps": [],
            "settings_path": "/api/agent/settings/n8n_local",
            "settings_label": "إعداد n8n محليًا",
            "probe_path": "/api/agent/integrations/n8n_local/probe",
            "probe_label": "اختبار n8n",
            "task_label": "تشغيل وكيل n8n",
            "task_prompt": (
                "integration probe: n8n_local\n"
                "افحص n8n المحلي وبوابة n8n_health، ثم سجل إيصالًا."
            ),
            "details": {
                "base_url": config.n8n_base_url,
                "workflow_source": "rest_api" if n8n_workflows_ready else "local_cli",
                "health_ready": n8n_health_ready,
                "catalog_ready": n8n_catalog_ready,
            },
        },
        {
            "id": "kali_wsl",
            "name": "Kali Linux WSL",
            "category": "security",
            "status": (
                "ready"
                if kali_ready
                else "partial"
                if kali_partial
                else "needs_setup"
            ),
            "connection_mode": "local_wsl",
            "account_required": False,
            "credential_policy": "none",
            "summary": (
                f"Kali WSL جاهز وفيه {int(kali_capability.get('tool_count') or 0)} أدوات أمنية أساسية."
                if kali_ready
                else "Kali WSL موجود جزئيًا؛ بعض أدوات الأمن غير مؤكدة."
                if kali_partial
                else "لم تُؤكد جاهزية Kali WSL بعد."
            ),
            "next_step": (
                "لا إجراء مطلوب."
                if kali_ready
                else "شغّل فحص Kali أو راجع WSL وتثبيت أدوات nmap/nuclei/httpx/subfinder."
            ),
            "missing_env": [],
            "connected_apps": (
                ["nmap", "nuclei", "httpx", "subfinder", "git", "python3"]
                if kali_ready
                else []
            ),
            "probe_path": "/api/agent/integrations/kali_wsl/probe",
            "probe_label": "اختبار Kali",
            "task_label": "تشغيل وكيل Kali",
            "task_prompt": (
                "integration probe: kali_wsl\n"
                "افحص Kali WSL وأدواته الأمنية المتاحة، ثم سجل إيصالًا."
            ),
            "details": {
                "status": kali_status or "unknown",
                "tool_count": int(kali_capability.get("tool_count") or 0),
                "missing_tool_count": int(kali_capability.get("missing_tool_count") or 0),
                "execution_mode": kali_capability.get("execution_mode"),
            },
        },
        {
            "id": "zapier_mcp",
            "name": "Zapier MCP",
            "category": "automation",
            "status": (
                "ready"
                if zapier_ready
                else "partial"
                if zapier_partial
                else "needs_setup"
            ),
            "connection_mode": "local_oauth_mcp",
            "account_required": True,
            "credential_policy": "oauth_managed",
            "summary": zapier_summary,
            "next_step": zapier_next_step,
            "missing_env": [],
            "connected_apps": zapier_apps,
            "action_path": zapier_action_path,
            "action_label": (
                None
                if zapier_direct_ready
                else "إعادة ربط كاملة"
                if zapier_needs_reconnect
                else "ربط Zapier MCP محليًا"
            ),
            "probe_path": "/api/agent/integrations/zapier_mcp/probe",
            "probe_label": "اختبار Zapier",
            "task_label": "تشغيل وكيل Zapier",
            "task_prompt": (
                "integration probe: zapier_mcp\n"
                "افحص Zapier MCP ومخزون التطبيقات والإجراءات المتاحة، ثم سجل إيصالًا."
            ),
            "details": {
                "app_count": len(zapier_apps),
                "action_count": int(inventory.get("zapier_action_count", 0)),
                "direct_oauth_connected": zapier_direct_connected,
                "direct_live_available": zapier_direct_ready,
                "needs_reconnect": zapier_needs_reconnect,
                "expired": bool(zapier_auth.get("expired")),
                "refresh_recommended": bool(zapier_auth.get("refresh_recommended")),
                "last_refresh_error": zapier_auth.get("last_refresh_error"),
                "last_refresh_status_code": zapier_auth.get("last_refresh_status_code"),
                "webhook_bridge_ready": zapier_bridge_ready,
            },
        },
        {
            "id": "broker_testnet",
            "name": "وسيط التداول التجريبي",
            "category": "financial",
            "status": (
                "ready"
                if testnet["execution_enabled"]
                else "partial" if testnet["configured"] else "needs_operator"
            ),
            "connection_mode": "trade_only_testnet_api",
            "account_required": True,
            "credential_policy": "local_server_only",
            "summary": (
                "بوابة Binance Spot Testnet مربوطة ومفعلة للتنفيذ التجريبي فقط."
                if testnet["execution_enabled"]
                else "مفاتيح Binance Spot Testnet موجودة، لكن تنفيذ الأوامر التجريبية غير مفعّل."
                if testnet["configured"]
                else "لا يوجد حساب Binance Spot Testnet مربوط، والتنفيذ الحقيقي مقفل."
            ),
            "next_step": (
                "لا إجراء مطلوب."
                if testnet["execution_enabled"]
                else "فعّل FATHIYA_TRADING_TESTNET_EXECUTION_ENABLED محليًا بعد اختبار الحساب."
                if testnet["configured"]
                else "أنشئ مفاتيح Binance Spot Testnet وأدخلها من إعداد Testnet المحلي."
            ),
            "missing_env": (
                []
                if testnet["configured"]
                else [
                    "FATHIYA_TRADING_TESTNET_API_KEY",
                    "FATHIYA_TRADING_TESTNET_API_SECRET",
                ]
            ),
            "connected_apps": [],
            "settings_path": "/api/agent/settings/broker_testnet",
            "settings_label": "إعداد Testnet محليًا",
            "probe_path": "/api/agent/integrations/broker_testnet/probe",
            "probe_label": "اختبار Testnet",
            "task_label": "تشغيل وكيل Testnet",
            "task_prompt": (
                "integration probe: broker_testnet\n"
                "افحص جاهزية حساب التداول التجريبي دون إرسال أوامر، ثم سجل إيصالًا."
            ),
            "details": {
                "provider": testnet["provider"],
                "environment": testnet["environment"],
                "symbol": testnet["symbol"],
                "configured": testnet["configured"],
                "testnet_execution_enabled": testnet["execution_enabled"],
                "live_execution_enabled": False,
                "withdrawal_permission_allowed": False,
                "real_funds_possible": False,
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
