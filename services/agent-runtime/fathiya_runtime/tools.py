from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from .config import RuntimeConfig
from .models import ModelClient
from .trading import BinanceSpotTestnetGateway, PaperTradingAgent
from .zapier_mcp import ZapierMCPGateway


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    category: str
    risk_class: str = "internal_owned"
    requires_approval: bool = False
    read_only: bool = True
    inputs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["inputs"] = list(self.inputs)
        return payload


@dataclass(frozen=True)
class ApprovalRequirement:
    required: bool
    risk_class: str
    reason: str


class ToolExecutionError(RuntimeError):
    def __init__(self, message: str, result: dict[str, Any]):
        super().__init__(message)
        self.result = result


ToolHandler = Callable[[str, dict[str, Any], list[dict[str, Any]]], dict[str, Any]]


class ToolExecutor:
    def __init__(
        self,
        config: RuntimeConfig,
        *,
        trading_agent: PaperTradingAgent | None = None,
        model_router: ModelClient | None = None,
    ):
        self.config = config
        self._trading = trading_agent
        self._testnet: BinanceSpotTestnetGateway | None = None
        self._model_router = model_router
        self._capability_cache: tuple[float, dict[str, Any]] | None = None
        self._cursor_agent_cache: tuple[float, dict[str, Any]] | None = None
        self.zapier = ZapierMCPGateway(config)
        self._handlers: dict[str, ToolHandler] = {
            "tool_catalog": self._tool_catalog,
            "local_capability_inventory": self._local_capability_inventory,
            "agent_delegate": self._agent_delegate,
            "internal_echo": self._internal_echo,
            "repo_status": self._repo_status,
            "repo_search": self._repo_search,
            "github_repo_info": self._github_repo_info,
            "web_fetch": self._web_fetch,
            "knowledge_ingest_url": self._knowledge_ingest_url,
            "n8n_status": self._n8n_status,
            "n8n_workflows": self._n8n_workflows,
            "n8n_webhook": self._n8n_webhook,
            "connector_catalog": self._connector_catalog,
            "connector_profile": self._connector_profile,
            "connected_tool_inventory": self._connected_tool_inventory,
            "integration_probe": self._integration_probe,
            "zapier_action_catalog": self._zapier_action_catalog,
            "zapier_action": self._zapier_action,
            "kali_tool_inventory": self._kali_tool_inventory,
            "security_core_plan": self._security_core_plan,
            "command_profile": self._command_profile,
            "trading_status": self._trading_status,
            "trading_start": self._trading_start,
            "trading_stop": self._trading_stop,
            "trading_tick": self._trading_tick,
            "trading_strategy_refresh": self._trading_strategy_refresh,
            "trading_testnet_status": self._trading_testnet_status,
            "trading_testnet_order": self._trading_testnet_order,
        }
        self._specs = {
            spec.name: spec
            for spec in (
                ToolSpec(
                    "tool_catalog",
                    "List every executable local tool, risk class, and required input.",
                    "runtime",
                ),
                ToolSpec(
                    "local_capability_inventory",
                    "Probe the local execution mesh and report which agent, automation, model, security, and engineering runtimes are actually ready.",
                    "runtime",
                    inputs=("refresh",),
                ),
                ToolSpec(
                    "integration_probe",
                    "Run one secret-safe readiness probe for a named integration and return receipt-safe evidence.",
                    "runtime",
                    inputs=("integration_id",),
                ),
                ToolSpec(
                    "agent_delegate",
                    "Delegate an approved objective to the best ready agent, Claude Code locally, Cursor Agent locally or through Zapier MCP, or Manus through Zapier MCP.",
                    "agents",
                    risk_class="external",
                    requires_approval=True,
                    read_only=False,
                    inputs=(
                        "provider",
                        "objective",
                        "mode",
                        "params",
                        "max_budget_usd",
                        "timeout_seconds",
                    ),
                ),
                ToolSpec(
                    "internal_echo",
                    "Record an internal execution proof when no specialist tool is required.",
                    "runtime",
                    read_only=False,
                    inputs=("message",),
                ),
                ToolSpec(
                    "repo_status",
                    "Read the canonical repository working-tree status.",
                    "engineering",
                ),
                ToolSpec(
                    "repo_search",
                    "Search the canonical repository with ripgrep and return evidence lines.",
                    "engineering",
                    inputs=("query", "path"),
                ),
                ToolSpec(
                    "github_repo_info",
                    "Read canonical GitHub repository metadata through the authenticated gh CLI.",
                    "github",
                ),
                ToolSpec(
                    "web_fetch",
                    "Fetch a public or operator-provided HTTP(S) source for evidence.",
                    "research",
                    inputs=("url",),
                ),
                ToolSpec(
                    "knowledge_ingest_url",
                    "Fetch an HTTP(S) report and persist it in the local knowledge intake.",
                    "knowledge",
                    read_only=False,
                    inputs=("url",),
                ),
                ToolSpec(
                    "n8n_status",
                    "Read local n8n health and version.",
                    "automation",
                ),
                ToolSpec(
                    "n8n_workflows",
                    "List workflows from the configured local n8n API.",
                    "automation",
                ),
                ToolSpec(
                    "n8n_webhook",
                    "Call the configured FATHIYA n8n execution webhook with a validated payload.",
                    "automation",
                    risk_class="external",
                    requires_approval=True,
                    read_only=False,
                    inputs=("payload",),
                ),
                ToolSpec(
                    "connector_catalog",
                    "List version-controlled connector profiles and their readiness without exposing secrets.",
                    "connectors",
                ),
                ToolSpec(
                    "connector_profile",
                    "Execute a named version-controlled connector profile.",
                    "connectors",
                    inputs=("profile", "payload", "query"),
                ),
                ToolSpec(
                    "connected_tool_inventory",
                    "Read the connected Zapier, agent-provider, and local-tool inventory.",
                    "connectors",
                ),
                ToolSpec(
                    "zapier_action_catalog",
                    "Read the live Zapier MCP app and action catalog through local OAuth.",
                    "connectors",
                    inputs=("app", "refresh"),
                ),
                ToolSpec(
                    "zapier_action",
                    "Execute an exact enabled Zapier MCP action through the local OAuth gateway.",
                    "connectors",
                    risk_class="external",
                    requires_approval=True,
                    read_only=False,
                    inputs=("app", "action", "params", "instructions", "output"),
                ),
                ToolSpec(
                    "kali_tool_inventory",
                    "Read available defensive tools inside Kali Linux WSL.",
                    "security",
                ),
                ToolSpec(
                    "security_core_plan",
                    "Run the local defensive security reasoning core without live probing.",
                    "security",
                    inputs=("target_or_question",),
                ),
                ToolSpec(
                    "command_profile",
                    "Run a named, version-controlled local command profile.",
                    "local_execution",
                    read_only=False,
                    inputs=("profile",),
                ),
                ToolSpec(
                    "trading_status",
                    "Read the local primary paper-trading agent status and measured prediction quality.",
                    "trading",
                ),
                ToolSpec(
                    "trading_start",
                    "Start the local primary paper-trading agent loop.",
                    "trading",
                    read_only=False,
                ),
                ToolSpec(
                    "trading_stop",
                    "Stop the local primary paper-trading agent loop.",
                    "trading",
                    read_only=False,
                ),
                ToolSpec(
                    "trading_tick",
                    "Run one local paper-trading cycle while the automatic loop is stopped.",
                    "trading",
                    read_only=False,
                ),
                ToolSpec(
                    "trading_strategy_refresh",
                    "Refresh the short-lived paper-trading strategy advisory through OpenRouter or local Hugging Face.",
                    "trading",
                    read_only=False,
                ),
                ToolSpec(
                    "trading_testnet_status",
                    "Read or probe the configured Binance Spot Testnet gateway without exposing credentials.",
                    "trading",
                    inputs=("probe",),
                ),
                ToolSpec(
                    "trading_testnet_order",
                    "Validate or submit an approved market order to Binance Spot Testnet only.",
                    "trading",
                    risk_class="financial",
                    requires_approval=True,
                    read_only=False,
                    inputs=("side", "quote_order_qty", "quantity", "validate_only"),
                ),
            )
        }

    def set_model_router(self, model_router: ModelClient) -> None:
        self._model_router = model_router

    def catalog(self) -> list[dict[str, Any]]:
        profiles = self._command_profiles()
        connector_profiles = self.connector_catalog()
        catalog: list[dict[str, Any]] = []
        for spec in self._specs.values():
            item = spec.to_dict()
            if spec.name == "command_profile":
                item["profiles"] = [
                    {
                        "name": profile.get("name"),
                        "description": profile.get("description"),
                        "risk_class": profile.get("risk_class", "internal_owned"),
                        "requires_approval": bool(profile.get("requires_approval", False)),
                    }
                    for profile in profiles
                ]
                item["configured"] = bool(profiles)
            elif spec.name == "agent_delegate":
                claude_installed = bool(shutil.which("claude"))
                cursor = (
                    dict(self._cursor_agent_cache[1])
                    if self._cursor_agent_cache
                    else {
                        "installed": bool(shutil.which("wsl.exe")),
                        "authenticated": False,
                    }
                )
                item["providers"] = [
                    {
                        "name": "auto",
                        "configured": bool(
                            claude_installed
                            or cursor.get("authenticated")
                            or self.zapier.configured
                        ),
                        "connection_mode": "best_ready_agent",
                    },
                    {
                        "name": "claude_code",
                        "configured": claude_installed,
                        "connection_mode": "local_cli",
                    },
                    {
                        "name": "cursor",
                        "configured": bool(
                            cursor.get("authenticated") or self.zapier.configured
                        ),
                        "installed": bool(cursor.get("installed")),
                        "local_ready": bool(cursor.get("authenticated")),
                        "zapier_ready": self.zapier.configured,
                        "connection_mode": "local_wsl_or_zapier_mcp",
                    },
                    {
                        "name": "manus",
                        "configured": self.zapier.configured,
                        "connection_mode": "zapier_mcp",
                    },
                ]
                item["configured"] = any(
                    provider["configured"] for provider in item["providers"]
                )
            elif spec.name == "connector_profile":
                item["profiles"] = connector_profiles
                item["configured"] = any(
                    bool(profile.get("configured")) for profile in connector_profiles
                )
            elif spec.name == "connector_catalog":
                item["configured"] = bool(connector_profiles)
            elif spec.name == "zapier_action_catalog":
                item["configured"] = True
            elif spec.name == "zapier_action":
                item["configured"] = self.zapier.configured
            elif spec.name == "n8n_webhook":
                item["configured"] = bool(self.config.n8n_webhook_url)
            elif spec.name in {"trading_testnet_status", "trading_testnet_order"}:
                testnet = self._trading_testnet_gateway().status()
                item["configured"] = (
                    True
                    if spec.name == "trading_testnet_status"
                    else bool(testnet["configured"])
                )
                item["environment"] = "testnet"
                item["execution_enabled"] = bool(testnet["execution_enabled"])
            else:
                item["configured"] = True
            catalog.append(item)
        return catalog

    def connector_catalog(self) -> list[dict[str, Any]]:
        catalog: list[dict[str, Any]] = []
        for profile in self._connector_profiles():
            missing_env = self._connector_missing_env(profile)
            catalog.append(
                {
                    "name": profile.get("name"),
                    "provider": profile.get("provider", "connector"),
                    "description": profile.get("description"),
                    "method": str(profile.get("method", "GET")).upper(),
                    "risk_class": profile.get("risk_class", "internal_owned"),
                    "requires_approval": bool(profile.get("requires_approval", False)),
                    "read_only": bool(profile.get("read_only", True)),
                    "bridge_dispatch_allowed": bool(
                        profile.get("bridge_dispatch_allowed", False)
                    ),
                    "configured": not missing_env,
                    "missing_env": missing_env,
                }
            )
        return catalog

    def bridge_dispatch_profiles(self) -> list[dict[str, Any]]:
        return [
            profile
            for profile in self.connector_catalog()
            if profile.get("bridge_dispatch_allowed")
        ]

    def get_spec(self, tool: str) -> ToolSpec:
        try:
            return self._specs[tool]
        except KeyError as exc:
            raise ValueError(f"Tool is not registered: {tool}") from exc

    def approval_requirement(
        self,
        tool: str,
        args: dict[str, Any] | None = None,
    ) -> ApprovalRequirement:
        spec = self.get_spec(tool)
        if tool == "command_profile":
            requested = str((args or {}).get("profile", ""))
            profile = next(
                (item for item in self._command_profiles() if item.get("name") == requested),
                None,
            )
            if profile:
                required = bool(profile.get("requires_approval", False))
                risk_class = str(profile.get("risk_class", "internal_owned"))
                return ApprovalRequirement(
                    required,
                    risk_class,
                    f"command profile {requested} requires approval" if required else "",
                )
        if tool == "connector_profile":
            requested = str((args or {}).get("profile", ""))
            profile = self._connector_profile_by_name(requested)
            if profile:
                required = bool(profile.get("requires_approval", False))
                risk_class = str(profile.get("risk_class", "internal_owned"))
                return ApprovalRequirement(
                    required,
                    risk_class,
                    f"connector profile {requested} requires approval" if required else "",
                )
        if tool == "zapier_action":
            requirement = self.zapier.action_requirement(
                str((args or {}).get("app") or ""),
                str((args or {}).get("action") or ""),
            )
            return ApprovalRequirement(
                bool(requirement["required"]),
                str(requirement["risk_class"]),
                str(requirement["reason"]),
            )
        return ApprovalRequirement(
            spec.requires_approval,
            spec.risk_class,
            f"tool {tool} requires approval" if spec.requires_approval else "",
        )

    def execute(
        self,
        tool: str,
        prompt: str,
        args: dict[str, Any] | None = None,
        context: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if tool not in self._handlers:
            raise ValueError(f"Tool is not registered: {tool}")
        result = self._handlers[tool](prompt, args or {}, context or [])
        result = {"tool": tool, **result}
        if result.get("execution_failed"):
            raise ToolExecutionError(
                str(result.get("error") or f"{tool} execution failed"),
                result,
            )
        return result

    def integration_probe(self, integration_id: str) -> dict[str, Any]:
        checked_at = datetime.now(UTC).isoformat()
        if integration_id == "local_execution_mesh":
            result = self._local_capability_inventory("", {}, [])
            ready_count = int(result.get("ready_count") or 0)
            capability_count = int(result.get("capability_count") or 0)
            partial_count = int(result.get("partial_count") or 0)
            ok = bool(capability_count and ready_count == capability_count)
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "partial" if ready_count else "needs_setup",
                summary=(
                    f"{ready_count} من {capability_count} بوابات التنفيذ جاهزة"
                    + (f" و{partial_count} جزئية." if partial_count else ".")
                ),
                checked_at=checked_at,
                action="local_capability_inventory",
                details={
                    "ready_count": ready_count,
                    "partial_count": partial_count,
                    "capability_count": capability_count,
                },
            )
        if integration_id == "huggingface_local":
            retrieval = bool(self.config.enable_hf_retrieval)
            generation = bool(self.config.enable_local_generation)
            ok = retrieval or generation
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "needs_setup",
                summary=(
                    "النماذج المحلية مفعلة للاسترجاع أو التوليد."
                    if ok
                    else "النماذج المحلية غير مفعلة في إعدادات المشغّل."
                ),
                checked_at=checked_at,
                action="configuration_check",
                details={
                    "retrieval_enabled": retrieval,
                    "generation_enabled": generation,
                    "retrieval_model": self.config.hf_model,
                    "generation_model": self.config.local_model,
                    "network_call": False,
                },
            )
        if integration_id == "openrouter":
            configured = bool(self.config.openrouter_api_key)
            return _integration_probe_payload(
                integration_id,
                ok=configured,
                status="ready" if configured else "needs_setup",
                summary=(
                    "مفتاح OpenRouter موجود محليًا؛ المكالمات الثقيلة جاهزة عند طلب الوكيل."
                    if configured
                    else "OpenRouter ينتظر مفتاحًا محليًا؛ لم تُجر مكالمة نموذج."
                ),
                checked_at=checked_at,
                action="configuration_check",
                details={
                    "configured": configured,
                    "model": self.config.openrouter_model,
                    "network_call": False,
                    "cost_incurred": False,
                },
            )
        if integration_id == "supabase":
            configured = bool(
                self.config.supabase_url and self.config.supabase_service_role_key
            )
            active = configured and self.config.store == "supabase"
            return _integration_probe_payload(
                integration_id,
                ok=active,
                status="ready" if active else "partial" if configured else "needs_setup",
                summary=(
                    "Supabase مفعّل كقناة مهام حالية."
                    if active
                    else "بيانات Supabase موجودة، لكن المشغّل الحالي ما زال على SQLite."
                    if configured
                    else "Supabase ينتظر URL ومفتاح خدمة محلي."
                ),
                checked_at=checked_at,
                action="configuration_check",
                details={
                    "configured": configured,
                    "active_store": self.config.store,
                    "network_call": False,
                },
            )
        if integration_id == "n8n_local":
            result = self._connector_profile("", {"profile": "n8n_health"}, [])
            ok = bool(result.get("available") and result.get("executed"))
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "partial",
                summary=(
                    "n8n المحلي استجاب لفحص الصحة."
                    if ok
                    else "تعذر تأكيد استجابة n8n المحلي."
                ),
                checked_at=checked_at,
                action="connector_profile:n8n_health",
                details=_connector_result_evidence(result),
            )
        if integration_id == "zapier_mcp":
            status = self.zapier.status()
            inventory = self._connected_tool_inventory("", {}, [])
            connected = bool(status.get("connected"))
            app_count = int(inventory.get("zapier_app_count") or 0)
            action_count = int(inventory.get("zapier_action_count") or 0)
            ok = connected and app_count > 0
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "partial" if app_count else "needs_setup",
                summary=(
                    f"Zapier OAuth المباشر جاهز، والمخزون يعرض {app_count} تطبيقًا و{action_count} إجراء."
                    if connected
                    else f"مخزون Zapier يعرض {app_count} تطبيقًا و{action_count} إجراء، لكن OAuth المحلي المباشر لم يكتمل."
                ),
                checked_at=checked_at,
                action="oauth_status_and_inventory",
                details={
                    "direct_oauth_connected": connected,
                    "app_count": app_count,
                    "action_count": action_count,
                    "endpoint": status.get("endpoint"),
                },
            )
        if integration_id == "broker_testnet":
            status = self._trading_testnet_gateway().status()
            configured = bool(status.get("configured"))
            probe = self._trading_testnet_gateway().probe() if configured else status
            authenticated = bool(probe.get("authenticated"))
            reachable = bool(probe.get("reachable")) if configured else False
            ok = configured and reachable and authenticated
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "partial" if configured else "needs_operator",
                summary=(
                    "حساب Testnet استجاب وجرى التحقق من المصادقة."
                    if ok
                    else "مفاتيح Testnet موجودة لكن التحقق لم ينجح بعد."
                    if configured
                    else "Testnet ينتظر مفاتيح محلية؛ لم يُرسل أي طلب وساطة."
                ),
                checked_at=checked_at,
                action="testnet_status" if not configured else "testnet_probe",
                details={
                    key: probe.get(key)
                    for key in (
                        "provider",
                        "environment",
                        "configured",
                        "execution_enabled",
                        "symbol",
                        "reachable",
                        "authenticated",
                        "can_trade",
                        "base_host",
                        "error",
                    )
                    if key in probe
                },
            )
        raise ValueError(f"Unknown integration probe: {integration_id}")

    def _tool_catalog(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {"available": True, "tools": self.catalog()}

    def _local_capability_inventory(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = time.monotonic()
        if (
            self._capability_cache
            and not bool(args.get("refresh"))
            and now - self._capability_cache[0] < 60
        ):
            return {**self._capability_cache[1], "cached": True}

        cursor = self._probe_cursor_agent()
        cursor.update(
            {
                "id": "cursor_agent",
                "name": "Cursor Agent",
                "execution_mode": "local_wsl_and_zapier",
                "requires_approval": True,
                "zapier_ready": self.zapier.configured,
            }
        )
        claude = self._probe_cli("claude", ("--version",), auth_args=("auth", "status"))
        claude.update(
            {
                "id": "claude_code",
                "name": "Claude Code",
                "execution_mode": "local_cli",
                "requires_approval": True,
            }
        )
        github = self._probe_cli("gh", ("--version",), auth_args=("auth", "status"))
        github.update(
            {
                "id": "github_cli",
                "name": "GitHub CLI",
                "execution_mode": "local_cli",
                "requires_approval": False,
            }
        )
        docker = self._probe_docker()
        n8n_status = self._n8n_status("", {}, [])
        n8n = {
            "id": "n8n",
            "name": "n8n",
            "installed": bool(shutil.which("n8n")),
            "available": bool(n8n_status.get("available")),
            "status": "active" if n8n_status.get("available") else "degraded",
            "version": n8n_status.get("version"),
            "execution_mode": "local_service",
            "requires_approval": False,
        }
        kali_status = self._kali_tool_inventory("", {}, [])
        kali = {
            "id": "kali_wsl",
            "name": "Kali Linux WSL",
            "installed": bool(shutil.which("wsl.exe")),
            "available": bool(kali_status.get("available")),
            "status": str(kali_status.get("status") or "unavailable"),
            "tool_count": len(kali_status.get("found_commands", [])),
            "missing_tool_count": len(kali_status.get("missing_commands", [])),
            "execution_mode": "local_wsl",
            "requires_approval": False,
        }
        zapier_status = self.zapier.status()
        zapier = {
            "id": "zapier_mcp",
            "name": "Zapier MCP",
            "installed": True,
            "available": bool(zapier_status.get("connected")),
            "status": "active" if zapier_status.get("connected") else "partial",
            "execution_mode": "oauth_mcp",
            "requires_approval": True,
        }
        hugging_face_ready = (
            self.config.enable_hf_retrieval or self.config.enable_local_generation
        )
        hugging_face = {
            "id": "huggingface_local",
            "name": "Hugging Face Local",
            "installed": hugging_face_ready,
            "available": hugging_face_ready,
            "status": "active" if hugging_face_ready else "unavailable",
            "execution_mode": "local_model",
            "requires_approval": False,
        }
        openrouter = {
            "id": "openrouter",
            "name": "OpenRouter",
            "installed": bool(self.config.openrouter_api_key),
            "available": bool(self.config.openrouter_api_key),
            "status": "active" if self.config.openrouter_api_key else "unavailable",
            "execution_mode": "server_api",
            "requires_approval": False,
        }
        trading = self._trading_agent().status()
        testnet = self._trading_testnet_gateway().status()
        trading_agent = {
            "id": "trading_primary",
            "name": "Primary Trading Agent",
            "installed": True,
            "available": True,
            "status": "active" if trading.get("running") else "ready",
            "execution_mode": "local_paper",
            "requires_approval": False,
            "symbol": trading.get("symbol"),
            "live_execution_enabled": False,
            "testnet_configured": testnet["configured"],
            "testnet_execution_enabled": testnet["execution_enabled"],
        }
        capabilities = [
            cursor,
            claude,
            github,
            docker,
            n8n,
            kali,
            zapier,
            hugging_face,
            openrouter,
            trading_agent,
        ]
        ready_count = sum(
            item.get("status") in {"active", "ready"} for item in capabilities
        )
        result = {
            "available": True,
            "captured_at": datetime.now(UTC).isoformat(),
            "ready_count": ready_count,
            "partial_count": sum(
                item.get("status") in {"partial", "degraded"} for item in capabilities
            ),
            "unavailable_count": sum(
                item.get("status") == "unavailable" for item in capabilities
            ),
            "capability_count": len(capabilities),
            "capabilities": capabilities,
            "cached": False,
        }
        self._capability_cache = (now, result)
        return result

    def _integration_probe(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        integration_id = str(args.get("integration_id") or "").strip()
        if not integration_id:
            raise ValueError("integration_probe requires integration_id")
        return self.integration_probe(integration_id)

    def _probe_cli(
        self,
        command: str,
        version_args: tuple[str, ...],
        *,
        auth_args: tuple[str, ...] | None = None,
    ) -> dict[str, Any]:
        executable = shutil.which(command)
        if not executable:
            return {
                "installed": False,
                "available": False,
                "status": "unavailable",
                "version": None,
                "authenticated": False if auth_args else None,
            }
        version = self._run(
            [executable, *version_args],
            cwd=self.config.repo_root,
            timeout=10,
        )
        version_text = next(
            (
                line.strip()
                for line in version["stdout"].splitlines()
                if line.strip()
            ),
            None,
        )
        authenticated: bool | None = None
        if auth_args:
            auth = self._run(
                [executable, *auth_args],
                cwd=self.config.repo_root,
                timeout=10,
            )
            authenticated = auth["return_code"] == 0
            if authenticated and auth["stdout"].lstrip().startswith("{"):
                try:
                    payload = json.loads(auth["stdout"])
                    authenticated = bool(payload.get("loggedIn", authenticated))
                except json.JSONDecodeError:
                    pass
        available = version["return_code"] == 0
        return {
            "installed": True,
            "available": available,
            "status": (
                "active"
                if available and authenticated is not False
                else "partial" if available else "degraded"
            ),
            "version": version_text,
            "authenticated": authenticated,
        }

    def _probe_cursor_agent(self) -> dict[str, Any]:
        now = time.monotonic()
        if (
            self._cursor_agent_cache
            and now - self._cursor_agent_cache[0] < 60
        ):
            return dict(self._cursor_agent_cache[1])
        if not shutil.which("wsl.exe"):
            return {
                "installed": False,
                "available": False,
                "status": "unavailable",
                "version": None,
                "authenticated": False,
            }
        version = self._run(
            [
                "wsl.exe",
                "-d",
                self.config.kali_wsl_distro,
                "--exec",
                "bash",
                "-lc",
                'test -x "$HOME/.local/bin/cursor-agent" && exec "$HOME/.local/bin/cursor-agent" --version',
            ],
            cwd=self.config.repo_root,
            timeout=20,
        )
        installed = version["return_code"] == 0
        version_text = next(
            (
                line.strip()
                for line in version["stdout"].splitlines()
                if line.strip()
            ),
            None,
        )
        authenticated = False
        if installed:
            auth = self._run(
                [
                    "wsl.exe",
                    "-d",
                    self.config.kali_wsl_distro,
                    "--exec",
                    "bash",
                    "-lc",
                    'exec "$HOME/.local/bin/cursor-agent" status',
                ],
                cwd=self.config.repo_root,
                timeout=20,
            )
            auth_text = f"{auth['stdout']}\n{auth['stderr']}".casefold()
            authenticated = (
                auth["return_code"] == 0
                and "not logged in" not in auth_text
                and "not authenticated" not in auth_text
            )
        result = {
            "installed": installed,
            "available": installed,
            "status": (
                "active"
                if installed and authenticated
                else "partial" if installed else "unavailable"
            ),
            "version": version_text,
            "authenticated": authenticated,
        }
        self._cursor_agent_cache = (now, result)
        return dict(result)

    def _probe_docker(self) -> dict[str, Any]:
        executable = shutil.which("docker")
        if not executable:
            return {
                "id": "docker",
                "name": "Docker",
                "installed": False,
                "available": False,
                "status": "unavailable",
                "version": None,
                "daemon_running": False,
                "execution_mode": "local_service",
                "requires_approval": True,
            }
        probe = self._run(
            [
                executable,
                "version",
                "--format",
                "{{.Client.Version}}|{{if .Server}}{{.Server.Version}}{{end}}",
            ],
            cwd=self.config.repo_root,
            timeout=10,
        )
        client_version, _, server_version = probe["stdout"].strip().partition("|")
        daemon_running = bool(server_version)
        return {
            "id": "docker",
            "name": "Docker",
            "installed": True,
            "available": daemon_running,
            "status": "active" if daemon_running else "degraded",
            "version": client_version or None,
            "daemon_running": daemon_running,
            "execution_mode": "local_service",
            "requires_approval": True,
        }

    def _wsl_path(self, path: Path) -> str:
        result = self._run(
            [
                "wsl.exe",
                "-d",
                self.config.kali_wsl_distro,
                "--exec",
                "wslpath",
                "-a",
                str(path.resolve()),
            ],
            cwd=self.config.repo_root,
            timeout=20,
        )
        value = result["stdout"].strip()
        if result["return_code"] != 0 or not value.startswith("/"):
            raise RuntimeError("Unable to map the repository path into Kali WSL")
        return value

    def _agent_delegate(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        requested_provider = str(args.get("provider") or "auto").strip().lower()
        aliases = {
            "claude": "claude_code",
            "claude-code": "claude_code",
            "cursor_agent": "cursor",
            "best": "auto",
            "available": "auto",
        }
        requested_provider = aliases.get(requested_provider, requested_provider)
        provider = (
            self._select_delegate_provider()
            if requested_provider == "auto"
            else requested_provider
        )
        objective = " ".join(str(args.get("objective") or prompt).split()).strip()
        if not objective:
            raise ValueError("agent_delegate requires an objective")
        if len(objective) > 8_000:
            raise ValueError("agent_delegate objective is limited to 8,000 characters")
        mode = str(args.get("mode") or "plan").strip().lower()
        if mode not in {"plan", "execute"}:
            raise ValueError("agent_delegate mode must be plan or execute")
        requested_params = args.get("params")
        params = dict(requested_params) if isinstance(requested_params, dict) else {}

        if provider == "claude_code":
            executable = shutil.which("claude")
            if not executable:
                raise RuntimeError("Claude Code CLI is not installed")
            try:
                budget = max(0.1, min(5.0, float(args.get("max_budget_usd", 1.0))))
            except (TypeError, ValueError) as exc:
                raise ValueError("max_budget_usd must be numeric") from exc
            timeout = max(30, min(900, int(args.get("timeout_seconds", 300))))
            result = self._run(
                [
                    executable,
                    "-p",
                    objective,
                    "--output-format",
                    "json",
                    "--permission-mode",
                    "acceptEdits" if mode == "execute" else "plan",
                    "--max-budget-usd",
                    str(budget),
                    "--no-session-persistence",
                    "--name",
                    "FATHIYA delegated agent",
                ],
                cwd=self.config.repo_root,
                timeout=timeout,
            )
            try:
                response: Any = json.loads(result["stdout"])
            except json.JSONDecodeError:
                response = result["stdout"][:20_000]
            return {
                "provider": provider,
                "requested_provider": requested_provider,
                "connection_mode": "local_cli",
                "mode": mode,
                "delegated": result["return_code"] == 0,
                "execution_failed": result["return_code"] != 0,
                "error": result["stderr"] or None,
                "response": response,
                "return_code": result["return_code"],
            }

        if provider == "cursor":
            cursor = self._probe_cursor_agent()
            if cursor.get("authenticated"):
                timeout = max(30, min(900, int(args.get("timeout_seconds", 300))))
                cursor_args = [
                    "-p",
                    "--output-format",
                    "json",
                    "--trust",
                    "--workspace",
                    self._wsl_path(self.config.repo_root),
                ]
                if mode == "execute":
                    cursor_args.extend(["--force", "--sandbox", "enabled"])
                else:
                    cursor_args.extend(["--mode", "plan"])
                cursor_args.append(objective)
                result = self._run(
                    [
                        "wsl.exe",
                        "-d",
                        self.config.kali_wsl_distro,
                        "--exec",
                        "bash",
                        "-lc",
                        'exec "$HOME/.local/bin/cursor-agent" "$@"',
                        "fathiya-cursor-agent",
                        *cursor_args,
                    ],
                    cwd=self.config.repo_root,
                    timeout=timeout,
                )
                try:
                    response: Any = json.loads(result["stdout"])
                except json.JSONDecodeError:
                    response = result["stdout"][:20_000]
                return {
                    "provider": provider,
                    "requested_provider": requested_provider,
                    "connection_mode": "local_wsl",
                    "mode": mode,
                    "delegated": result["return_code"] == 0,
                    "execution_failed": result["return_code"] != 0,
                    "error": result["stderr"] or None,
                    "response": response,
                    "return_code": result["return_code"],
                }
            if not self.zapier.configured:
                raise RuntimeError(
                    "Cursor Agent CLI is installed but not authenticated; run cursor-agent login in Kali WSL or connect Zapier MCP"
                )
            params.setdefault("prompt_text", objective)
            params.setdefault("repository_url", self._canonical_repo_url())
            params.setdefault("repository_ref", "main")
            params.setdefault("target_auto_create_pr", False)
            return {
                "provider": provider,
                "requested_provider": requested_provider,
                "connection_mode": "zapier_mcp",
                "mode": mode,
                "delegated": True,
                **self.zapier.execute_action(
                    "Cursor",
                    "Launch Agent",
                    params,
                    objective,
                    "Return the launched Cursor agent identifier and status.",
                ),
            }

        if provider == "manus":
            params.setdefault("prompt", objective)
            params.setdefault("agent_profile", "manus-1.6")
            params.setdefault("share_visibility", "private")
            params.setdefault("hide_in_task_list", True)
            return {
                "provider": provider,
                "requested_provider": requested_provider,
                "connection_mode": "zapier_mcp",
                "mode": mode,
                "delegated": True,
                **self.zapier.execute_action(
                    "Manus",
                    "Create Task",
                    params,
                    objective,
                    "Return the private Manus task identifier and status.",
                ),
            }

        raise ValueError(
            "agent_delegate provider must be auto, claude_code, cursor, or manus"
        )

    def _select_delegate_provider(self) -> str:
        claude = self._probe_cli(
            "claude",
            ("--version",),
            auth_args=("auth", "status"),
        )
        if claude.get("authenticated"):
            return "claude_code"
        if self._probe_cursor_agent().get("authenticated"):
            return "cursor"
        if self.zapier.configured:
            return "cursor"
        raise RuntimeError(
            "No authenticated delegated agent is ready; connect Claude Code, Cursor Agent, or Zapier MCP"
        )

    def _canonical_repo_url(self) -> str:
        result = self._run(
            ["gh", "repo", "view", "--json", "url"],
            cwd=self.config.repo_root,
            timeout=30,
        )
        try:
            url = str(json.loads(result["stdout"]).get("url") or "")
        except json.JSONDecodeError:
            url = ""
        if not url.startswith("https://github.com/"):
            raise RuntimeError("Canonical GitHub repository URL is unavailable")
        return url

    def _trading_agent(self) -> PaperTradingAgent:
        if self._trading is None:
            self._trading = PaperTradingAgent.from_config(self.config)
        return self._trading

    def _trading_testnet_gateway(self) -> BinanceSpotTestnetGateway:
        if self._testnet is None:
            self._testnet = BinanceSpotTestnetGateway.from_config(self.config)
        return self._testnet

    def _trading_status(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "available": True,
            "action": "status",
            "trading": self._trading_agent().status(),
        }

    def _trading_start(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "available": True,
            "executed": True,
            "action": "start",
            "trading": self._trading_agent().start(),
        }

    def _trading_stop(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "available": True,
            "executed": True,
            "action": "stop",
            "trading": self._trading_agent().stop(),
        }

    def _trading_tick(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "available": True,
            "executed": True,
            "action": "tick",
            "cycle": self._trading_agent().tick_once(),
        }

    def _trading_strategy_refresh(
        self,
        prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        trading = self._trading_agent()
        status = trading.status()
        compact_status = {
            "symbol": status["symbol"],
            "running": status["running"],
            "mode": status["mode"],
            "current_market_source": status["current_market_source"],
            "latest_prediction": (
                status["latest_cycle"]["prediction"] if status["latest_cycle"] else None
            ),
            "portfolio": status["portfolio"],
            "prediction_quality": status["prediction_quality"],
            "risk_limits": status["risk_limits"],
            "live_execution_enabled": status["live_execution_enabled"],
        }
        provider = "deterministic_fallback"
        fallback = True
        error_type: str | None = None
        action = "hold"
        confidence = 0.0
        rationale = "No configured model produced a valid advisory; no veto is applied."
        model = self._model_router
        if model and model.available:
            try:
                raw = model.complete(
                    (
                        "You are the FATHIYA paper-trading strategy advisor. "
                        "Return one JSON object only with action, confidence, and rationale. "
                        "action must be buy, sell, or hold. confidence must be 0 through 1. "
                        "Use only the supplied snapshot, choose hold when uncertain, and do not "
                        "claim live execution or invent evidence."
                    ),
                    json.dumps(
                        {
                            "operator_request": prompt[:1000],
                            "trading_snapshot": compact_status,
                            "policy": {
                                "mode": "veto_only",
                                "can_originate_orders": False,
                                "live_execution_enabled": False,
                            },
                        },
                        ensure_ascii=False,
                    ),
                    json_mode=True,
                    max_new_tokens=180,
                )
                payload = _json_object(raw)
                requested_action = str(payload.get("action") or "").strip().lower()
                requested_confidence = float(payload.get("confidence"))
                requested_rationale = " ".join(
                    str(payload.get("rationale") or "").split()
                )
                if requested_action not in {"buy", "sell", "hold"}:
                    raise ValueError("model returned an unsupported advisory action")
                if not requested_rationale:
                    raise ValueError("model returned an empty advisory rationale")
                action = requested_action
                confidence = max(0.0, min(1.0, requested_confidence))
                rationale = requested_rationale[:400]
                provider = str(getattr(model, "last_provider", "model"))[:120]
                fallback = False
            except Exception as exc:
                error_type = type(exc).__name__
        advisory = trading.update_advisory(
            action=action,
            confidence=confidence,
            rationale=rationale,
            provider=provider,
            ttl_seconds=self.config.trading_advisory_ttl_seconds,
        )
        return {
            "available": True,
            "executed": True,
            "action": "strategy_refresh",
            "model_provider": provider,
            "fallback": fallback,
            "error_type": error_type,
            "advisory": advisory,
            "policy": status["strategy_advisory_policy"],
            "live_execution_enabled": False,
        }

    def _trading_testnet_status(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        gateway = self._trading_testnet_gateway()
        return {
            "available": True,
            "action": "testnet_probe" if bool(args.get("probe")) else "testnet_status",
            "testnet": gateway.probe() if bool(args.get("probe")) else gateway.status(),
        }

    def _trading_testnet_order(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        validate_only = args.get("validate_only", True)
        if isinstance(validate_only, str):
            validate_only = validate_only.strip().lower() not in {
                "0",
                "false",
                "no",
            }
        return {
            "available": True,
            "executed": True,
            "action": "testnet_order_validation"
            if bool(validate_only)
            else "testnet_order_submission",
            "testnet": self._trading_testnet_gateway().market_order(
                side=str(args.get("side") or ""),
                quote_order_qty=args.get("quote_order_qty"),
                quantity=args.get("quantity"),
                validate_only=bool(validate_only),
            ),
        }

    @staticmethod
    def _internal_echo(
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "executed": True,
            "message": str(args.get("message") or "اكتمل إثبات التنفيذ الداخلي."),
            "prompt_excerpt": prompt[:240],
            "prior_result_count": len(context),
        }

    def _repo_status(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = self._run(["git", "status", "--short", "--branch"], cwd=self.config.repo_root)
        return {
            "repo": str(self.config.repo_root),
            "clean": not any(
                line and not line.startswith("##") for line in result["stdout"].splitlines()
            ),
            "execution_failed": result["return_code"] != 0,
            "error": result["stderr"] or None,
            **result,
        }

    def _repo_search(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query = str(args.get("query") or prompt).strip()[:300]
        if not query:
            raise ValueError("repo_search requires a query")
        target = self._bounded_repo_path(str(args.get("path") or "."))
        result = self._run(
            ["rg", "-n", "--max-count", "80", "--", query, str(target)],
            cwd=self.config.repo_root,
            timeout=60,
        )
        return {
            "query": query,
            "path": str(target),
            "matched": result["return_code"] == 0,
            "execution_failed": result["return_code"] not in {0, 1},
            "error": result["stderr"] or None,
            **result,
        }

    def _github_repo_info(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        result = self._run(
            [
                "gh",
                "repo",
                "view",
                "--json",
                "nameWithOwner,url,description,isPrivate,defaultBranchRef",
            ],
            cwd=self.config.repo_root,
            timeout=45,
        )
        try:
            metadata = json.loads(result["stdout"]) if result["stdout"].strip() else None
        except json.JSONDecodeError:
            metadata = None
        return {
            "metadata": metadata,
            "execution_failed": result["return_code"] != 0,
            "error": result["stderr"] or None,
            **result,
        }

    def _web_fetch(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        url = self._requested_url(prompt, args)
        return self._fetch_url(url)

    def _knowledge_ingest_url(
        self,
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fetched = self._web_fetch(prompt, args, context)
        if not fetched["ok"]:
            raise RuntimeError(f"Cannot ingest URL with HTTP {fetched['status_code']}")
        parsed = urlparse(fetched["url"])
        source_name = f"{parsed.netloc}{parsed.path}".strip("/") or parsed.netloc or "source"
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", source_name).strip("-")[:80] or "source"
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        intake = self.config.knowledge_root / "intake" / "runtime"
        intake.mkdir(parents=True, exist_ok=True)
        path = intake / f"{timestamp}-{slug}.txt"
        path.write_text(
            f"Source: {fetched['url']}\nCaptured: {datetime.now(UTC).isoformat()}\n\n"
            f"{fetched['text']}",
            encoding="utf-8",
        )
        return {
            "ingested": True,
            "path": str(path.relative_to(self.config.knowledge_root)),
            "source": fetched["url"],
            "content_type": fetched["content_type"],
            "characters": len(fetched["text"]),
        }

    def _n8n_status(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        headers = {"X-N8N-API-KEY": self.config.n8n_api_key} if self.config.n8n_api_key else {}
        errors: list[str] = []
        for path in ("/healthz", "/healthz/readiness", "/rest/healthz"):
            try:
                response = requests.get(
                    f"{self.config.n8n_base_url}{path}",
                    headers=headers,
                    timeout=5,
                )
                if response.ok:
                    version = self._run(["n8n.cmd", "--version"], cwd=self.config.repo_root)
                    return {
                        "available": True,
                        "endpoint": path,
                        "status_code": response.status_code,
                        "body": response.text[:500],
                        "version": version["stdout"].strip() or None,
                    }
                errors.append(f"{path}: HTTP {response.status_code}")
            except requests.RequestException as exc:
                errors.append(f"{path}: {exc}")
        return {"available": False, "errors": errors}

    def _n8n_workflows(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        headers = {"X-N8N-API-KEY": self.config.n8n_api_key} if self.config.n8n_api_key else {}
        response = requests.get(
            f"{self.config.n8n_base_url}/api/v1/workflows",
            headers=headers,
            params={"limit": 50},
            timeout=15,
        )
        text = response.text[:20_000]
        try:
            payload = response.json()
        except requests.JSONDecodeError:
            payload = {"raw": text}
        return {
            "available": response.ok,
            "status_code": response.status_code,
            "workflows": payload,
        }

    def _n8n_webhook(
        self,
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self.config.n8n_webhook_url:
            raise RuntimeError("FATHIYA_N8N_WEBHOOK_URL is not configured")
        payload = args.get("payload")
        if not isinstance(payload, dict):
            payload = {"prompt": prompt, "prior_results": context[-5:]}
        response = requests.post(self.config.n8n_webhook_url, json=payload, timeout=60)
        return {
            "executed": response.ok,
            "execution_failed": not response.ok,
            "error": None if response.ok else f"n8n webhook returned HTTP {response.status_code}",
            "status_code": response.status_code,
            "response": response.text[:20_000],
        }

    def _connector_catalog(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        profiles = self.connector_catalog()
        return {
            "available": bool(profiles),
            "configured_count": sum(bool(profile["configured"]) for profile in profiles),
            "profile_count": len(profiles),
            "profiles": profiles,
        }

    def _connector_profile(
        self,
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        requested = str(args.get("profile") or "").strip()
        profile = self._connector_profile_by_name(requested)
        if not profile:
            raise ValueError(f"Unknown connector profile: {requested or '<missing>'}")
        missing_env = self._connector_missing_env(profile)
        if missing_env:
            raise RuntimeError(
                f"Connector profile {requested} requires environment variables: "
                f"{', '.join(missing_env)}"
            )

        method = str(profile.get("method", "GET")).upper()
        if method not in {"GET", "POST"}:
            raise ValueError(f"Unsupported connector method for {requested}: {method}")
        url = self._connector_url(profile)
        timeout = max(1, min(120, int(profile.get("timeout_seconds", 30))))
        headers = {
            str(header): os.getenv(str(env_name), "")
            for header, env_name in dict(profile.get("headers_env") or {}).items()
            if os.getenv(str(env_name), "")
        }
        default_query = profile.get("default_query")
        query = dict(default_query) if isinstance(default_query, dict) else {}
        requested_query = args.get("query")
        if isinstance(requested_query, dict):
            query.update(requested_query)
        payload = args.get("payload")
        if method == "POST" and not isinstance(payload, dict):
            payload = {
                "prompt": prompt,
                "prior_results": context[-5:],
                "source": "fathiya-agent-runtime",
            }

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                params=query or None,
                json=payload if method == "POST" else None,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            return {
                "profile": requested,
                "provider": profile.get("provider", "connector"),
                "method": method,
                "configured": True,
                "available": False,
                "executed": False,
                "execution_failed": method != "GET",
                "error": f"{type(exc).__name__}: connector request failed",
            }

        text = response.text[:20_000]
        try:
            response_payload: Any = json.loads(text) if text else None
        except json.JSONDecodeError:
            response_payload = text
        return {
            "profile": requested,
            "provider": profile.get("provider", "connector"),
            "method": method,
            "configured": True,
            "available": response.ok,
            "executed": response.ok,
            "execution_failed": method != "GET" and not response.ok,
            "status_code": response.status_code,
            "error": None if response.ok else f"Connector returned HTTP {response.status_code}",
            "response": response_payload,
        }

    def _connected_tool_inventory(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        path = self.config.tool_inventory_path
        if not path.exists():
            return {
                "available": False,
                "path": str(path),
                "error": "Connected tool inventory is missing",
            }
        inventory = json.loads(path.read_text(encoding="utf-8"))
        apps = inventory.get("zapier_apps", [])
        return {
            "available": True,
            "path": str(path),
            "captured_at": inventory.get("captured_at"),
            "policy": inventory.get("policy", {}),
            "zapier_mcp_status": inventory.get("zapier_mcp_status", {}),
            "local_tools": inventory.get("local_tools", []),
            "zapier_app_count": len(apps),
            "zapier_action_count": sum(int(app.get("action_count", 0)) for app in apps),
            "zapier_apps": apps,
            "agent_provider_actions": inventory.get("agent_provider_actions", {}),
            "direct_zapier_mcp": self.zapier.status(),
        }

    def _zapier_action_catalog(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self.zapier.action_catalog(
            str(args.get("app") or ""),
            force=bool(args.get("refresh")),
        )

    def _zapier_action(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        app = str(args.get("app") or "").strip()
        action = str(args.get("action") or "").strip()
        params = args.get("params")
        if not app or not action:
            raise ValueError("Zapier action requires app and action")
        if not isinstance(params, dict):
            params = {}
        return self.zapier.execute_action(
            app,
            action,
            params,
            str(args.get("instructions") or prompt),
            str(args.get("output") or "Return the action result and receipt-safe identifiers."),
        )

    def _kali_tool_inventory(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        commands = ["nmap", "nuclei", "httpx", "subfinder", "git", "python3"]
        # Explicit commands avoid WSL argument translation dropping a shell loop variable.
        script = "; ".join(f"command -v {command} || true" for command in commands)
        result = self._run(
            ["wsl.exe", "-d", self.config.kali_wsl_distro, "--", "bash", "-lc", script],
            cwd=self.config.repo_root,
            timeout=30,
        )
        found = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
        found_commands = [line.rsplit("/", 1)[-1] for line in found]
        missing_commands = [
            command for command in commands if command not in found_commands
        ]
        available = result["return_code"] == 0
        return {
            "available": available,
            "status": (
                "active"
                if available and not missing_commands
                else "degraded" if available else "unavailable"
            ),
            "distro": self.config.kali_wsl_distro,
            "requested_commands": commands,
            "found": found,
            "found_commands": found_commands,
            "missing_commands": missing_commands,
            "execution_failed": result["return_code"] != 0,
            "error": result["stderr"] or None,
            **result,
        }

    def _security_core_plan(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        core_root = (
            self.config.service_root / "tools" / "security_core" / "fathiya_core"
        ).resolve()
        question = str(args.get("target_or_question") or prompt)
        code = (
            "import json,sys;"
            "sys.path.insert(0,'.');"
            "from core.orchestrator import FathiyaOrchestrator;"
            "r=FathiyaOrchestrator().run(sys.argv[1]);"
            "print(json.dumps({'final_answer':r.get('final_answer'),"
            "'analysis':r.get('analysis'),"
            "'session_id':r.get('session_id')},ensure_ascii=False,default=str))"
        )
        result = self._run([sys.executable, "-c", code, question], cwd=core_root, timeout=90)
        try:
            output = json.loads(result["stdout"])
        except json.JSONDecodeError:
            output = {"raw": result["stdout"][:8000]}
        return {
            "output": output,
            "execution_failed": result["return_code"] != 0,
            "error": result["stderr"] or None,
            "stderr": result["stderr"],
        }

    def _command_profile(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        requested = str(args.get("profile") or "")
        profile = next(
            (item for item in self._command_profiles() if item.get("name") == requested),
            None,
        )
        if not profile:
            raise ValueError(f"Unknown command profile: {requested or '<missing>'}")
        command = profile.get("command")
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            raise ValueError(f"Invalid command profile: {requested}")
        cwd_name = str(profile.get("cwd", "repo"))
        if cwd_name == "repo":
            cwd = self.config.repo_root
        elif cwd_name == "service":
            cwd = self.config.service_root
        else:
            raise ValueError(f"Unsupported command profile cwd: {cwd_name}")
        timeout = max(1, min(900, int(profile.get("timeout_seconds", 120))))
        resolved_command = [
            sys.executable if index == 0 and part in {"python", "python3"} else part
            for index, part in enumerate(command)
        ]
        result = self._run(resolved_command, cwd=cwd, timeout=timeout)
        return {
            "profile": requested,
            "description": profile.get("description"),
            "risk_class": profile.get("risk_class", "internal_owned"),
            "execution_failed": result["return_code"] != 0,
            "error": result["stderr"] or None,
            **result,
        }

    def _command_profiles(self) -> list[dict[str, Any]]:
        path = self.config.command_profiles_path
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        profiles = payload.get("profiles", [])
        return [item for item in profiles if isinstance(item, dict)]

    def _connector_profiles(self) -> list[dict[str, Any]]:
        path = self.config.connector_profiles_path
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        profiles = payload.get("profiles", [])
        return [
            item
            for item in profiles
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]

    def _connector_profile_by_name(self, requested: str) -> dict[str, Any] | None:
        return next(
            (profile for profile in self._connector_profiles() if profile.get("name") == requested),
            None,
        )

    @staticmethod
    def _connector_missing_env(profile: dict[str, Any]) -> list[str]:
        required = [
            str(name)
            for name in profile.get("required_env", [])
            if isinstance(name, str) and name
        ]
        url_env = str(profile.get("url_env") or "")
        if url_env and not os.getenv(url_env) and not profile.get("default_url"):
            required.append(url_env)
        return list(dict.fromkeys(name for name in required if not os.getenv(name)))

    @staticmethod
    def _connector_url(profile: dict[str, Any]) -> str:
        url_env = str(profile.get("url_env") or "")
        base = (os.getenv(url_env, "") if url_env else "") or str(
            profile.get("default_url") or ""
        )
        path = str(profile.get("path") or "")
        url = f"{base.rstrip('/')}/{path.lstrip('/')}" if path else base
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"Connector profile {profile.get('name')} has no valid HTTP(S) URL")
        return url

    def _bounded_repo_path(self, requested: str) -> Path:
        target = (self.config.repo_root / requested).resolve()
        repo = self.config.repo_root.resolve()
        if target != repo and repo not in target.parents:
            raise ValueError("Requested path must stay inside the canonical repository")
        return target

    @staticmethod
    def _requested_url(prompt: str, args: dict[str, Any]) -> str:
        candidate = str(args.get("url") or "").strip()
        if not candidate:
            match = re.search(r"https?://[^\s<>'\"،]+", prompt, re.IGNORECASE)
            candidate = match.group(0).rstrip(").,]") if match else ""
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("An HTTP(S) URL is required")
        return candidate

    @staticmethod
    def _fetch_url(url: str) -> dict[str, Any]:
        response = requests.get(
            url,
            headers={"User-Agent": "FATHIYA-Agent-Runtime/1.0"},
            timeout=30,
            allow_redirects=True,
            stream=True,
        )
        chunks: list[bytes] = []
        size = 0
        for chunk in response.iter_content(chunk_size=16_384):
            if not chunk:
                continue
            remaining = 200_000 - size
            if remaining <= 0:
                break
            chunks.append(chunk[:remaining])
            size += min(len(chunk), remaining)
        raw = b"".join(chunks)
        encoding = response.encoding or "utf-8"
        return {
            "ok": response.ok,
            "url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "truncated": size >= 200_000,
            "text": raw.decode(encoding, errors="replace"),
        }

    @staticmethod
    def _run(command: list[str], *, cwd: Path, timeout: int = 20) -> dict[str, Any]:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            return {
                "command": command,
                "return_code": completed.returncode,
                "stdout": completed.stdout[:20_000],
                "stderr": completed.stderr[:8_000],
            }
        except FileNotFoundError as exc:
            return {
                "command": command,
                "return_code": 127,
                "stdout": "",
                "stderr": str(exc),
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "command": command,
                "return_code": 124,
                "stdout": (exc.stdout or "")[:20_000],
                "stderr": f"Command timed out after {timeout} seconds",
            }


def _json_object(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    if start < 0:
        raise ValueError("Model advisory did not contain a JSON object")
    payload, _end = json.JSONDecoder().raw_decode(raw[start:])
    if not isinstance(payload, dict):
        raise ValueError("Model advisory must be a JSON object")
    return payload


def _integration_probe_payload(
    integration_id: str,
    *,
    ok: bool,
    status: str,
    summary: str,
    checked_at: str,
    action: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "available": True,
        "executed": True,
        "integration_id": integration_id,
        "ok": ok,
        "status": status,
        "summary": summary,
        "checked_at": checked_at,
        "secret_safe": True,
        "action": action,
        "details": details,
    }


def _connector_result_evidence(result: dict[str, Any]) -> dict[str, Any]:
    return {
        key: result.get(key)
        for key in (
            "profile",
            "provider",
            "method",
            "configured",
            "available",
            "executed",
            "execution_failed",
            "status_code",
            "error",
        )
        if key in result
    }
