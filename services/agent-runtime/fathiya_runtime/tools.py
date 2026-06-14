from __future__ import annotations

import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from .config import RuntimeConfig
from .models import ModelClient, OpenRouterClient
from .trading import BinanceSpotTestnetGateway, PaperTradingAgent
from .zapier_mcp import ZapierMCPError, ZapierMCPGateway


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
            "agent_mesh_audit": self._agent_mesh_audit,
            "agent_mesh_execute": self._agent_mesh_execute,
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
            "hexstrike_lab_scan": self._hexstrike_lab_scan,
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
                    "agent_mesh_audit",
                    "Run a secret-safe execution-mesh audit across local agents, models, connectors, Zapier MCP inventory, n8n, Kali, and the primary trading agent.",
                    "runtime",
                    inputs=("refresh",),
                ),
                ToolSpec(
                    "agent_mesh_execute",
                    "Execute the safe local agent mesh now: inventory, connector readiness, paper-trading advisor refresh, n8n/Kali probes, and receipt-safe evidence without external writes.",
                    "runtime",
                    read_only=False,
                    inputs=("refresh", "max_steps"),
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
                    "hexstrike_lab_scan",
                    "Use the local HexStrike-AI server to analyze and lightly scan an owned loopback lab target.",
                    "security",
                    inputs=("target_url", "target_host", "port", "objective"),
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
                    "model_candidates": list(self.config.openrouter_model_candidates),
                    "trading_advisory_model": self.config.trading_advisory_model,
                    "trading_advisory_model_candidates": list(
                        self.config.trading_advisory_model_candidates
                    ),
                    "free_model_routing": True,
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

    def _agent_mesh_audit(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        refresh = bool(args.get("refresh", True))
        captured_at = datetime.now(UTC).isoformat()
        tool_catalog = self.catalog()
        capabilities = self._local_capability_inventory("", {"refresh": refresh}, [])
        connectors = self.connector_catalog()
        connected_inventory = self._connected_tool_inventory("", {}, [])
        zapier_direct = self._zapier_action_catalog(
            "",
            {"refresh": bool(args.get("refresh_zapier", False))},
            [],
        )
        n8n_status = self._n8n_status("", {}, [])
        try:
            n8n_workflows = self._n8n_workflows("", {}, [])
        except requests.RequestException as exc:
            n8n_workflows = {
                "available": False,
                "status_code": None,
                "workflows": None,
                "error": f"{type(exc).__name__}: n8n workflow listing failed",
            }
        kali = self._kali_tool_inventory("", {}, [])
        trading = self._trading_status("", {}, [])
        integration_ids = (
            "local_execution_mesh",
            "huggingface_local",
            "openrouter",
            "supabase",
            "n8n_local",
            "zapier_mcp",
            "broker_testnet",
        )
        integration_probes: dict[str, dict[str, Any]] = {}
        for integration_id in integration_ids:
            try:
                probe = self.integration_probe(integration_id)
                integration_probes[integration_id] = {
                    "ok": probe.get("ok"),
                    "status": probe.get("status"),
                    "summary": probe.get("summary"),
                    "action": probe.get("action"),
                    "secret_safe": True,
                }
            except Exception as exc:
                integration_probes[integration_id] = {
                    "ok": False,
                    "status": "failed",
                    "summary": f"{type(exc).__name__}: audit probe failed",
                    "action": "agent_mesh_audit",
                    "secret_safe": True,
                }

        ready_capabilities = [
            capability
            for capability in capabilities.get("capabilities", [])
            if isinstance(capability, dict)
            and capability.get("status") in {"active", "ready"}
        ]
        partial_capabilities = [
            capability
            for capability in capabilities.get("capabilities", [])
            if isinstance(capability, dict)
            and capability.get("status") in {"partial", "degraded"}
        ]
        configured_connectors = [
            connector for connector in connectors if connector.get("configured")
        ]
        zapier_apps = connected_inventory.get("zapier_apps", [])
        zapier_app_count = int(connected_inventory.get("zapier_app_count") or 0)
        zapier_action_count = int(connected_inventory.get("zapier_action_count") or 0)
        direct_connected = bool(zapier_direct.get("connected"))
        workflows_payload = n8n_workflows.get("workflows")
        workflow_count = (
            len(workflows_payload) if isinstance(workflows_payload, list) else None
        )
        trading_status = trading.get("trading", {})
        quality = (
            trading_status.get("prediction_quality", {})
            if isinstance(trading_status, dict)
            else {}
        )

        next_actions = _agent_mesh_next_actions(
            integration_probes=integration_probes,
            connectors=connectors,
            zapier_direct=zapier_direct,
            n8n_workflows=n8n_workflows,
            kali=kali,
        )
        summary = {
            "tool_count": len(tool_catalog),
            "capability_count": int(capabilities.get("capability_count") or 0),
            "ready_capability_count": len(ready_capabilities),
            "partial_capability_count": len(partial_capabilities),
            "connector_count": len(connectors),
            "configured_connector_count": len(configured_connectors),
            "zapier_app_count": zapier_app_count,
            "zapier_action_count": zapier_action_count,
            "zapier_direct_oauth_connected": direct_connected,
            "n8n_available": bool(n8n_status.get("available")),
            "n8n_workflow_count": workflow_count,
            "kali_status": kali.get("status"),
            "kali_found_tool_count": len(kali.get("found_commands", [])),
            "trading_running": bool(trading_status.get("running"))
            if isinstance(trading_status, dict)
            else False,
            "trading_symbol": trading_status.get("symbol")
            if isinstance(trading_status, dict)
            else None,
            "trading_cycle_seconds": trading_status.get("cycle_target_seconds")
            if isinstance(trading_status, dict)
            else None,
            "trading_evaluated_predictions": quality.get("evaluated_count"),
        }
        return {
            "available": True,
            "executed": True,
            "secret_safe": True,
            "captured_at": captured_at,
            "summary": summary,
            "execution_policy": {
                "audit_mode": "read_only",
                "automatic_internal_execution": True,
                "external_writes_require_approval": True,
                "live_trading_requires_explicit_testnet_enablement": True,
                "live_security_testing_requires_approval": True,
            },
            "tools": [
                {
                    "name": item.get("name"),
                    "category": item.get("category"),
                    "configured": item.get("configured", True),
                    "requires_approval": item.get("requires_approval", False),
                    "read_only": item.get("read_only", True),
                }
                for item in tool_catalog
            ],
            "capabilities": [
                {
                    key: capability.get(key)
                    for key in (
                        "id",
                        "name",
                        "status",
                        "available",
                        "installed",
                        "authenticated",
                        "execution_mode",
                        "requires_approval",
                    )
                    if key in capability
                }
                for capability in capabilities.get("capabilities", [])
                if isinstance(capability, dict)
            ],
            "connectors": connectors,
            "connected_tools": {
                "captured_at": connected_inventory.get("captured_at"),
                "zapier_app_count": zapier_app_count,
                "zapier_action_count": zapier_action_count,
                "top_zapier_apps": [
                    {
                        "name": app.get("name"),
                        "action_count": app.get("action_count"),
                    }
                    for app in zapier_apps[:12]
                    if isinstance(app, dict)
                ],
                "agent_provider_actions": connected_inventory.get(
                    "agent_provider_actions",
                    {},
                ),
            },
            "zapier_direct": {
                "connected": direct_connected,
                "app_count": zapier_direct.get("app_count"),
                "action_count": zapier_direct.get("action_count"),
                "error": zapier_direct.get("error"),
            },
            "n8n": {
                "status": _connector_result_evidence(n8n_status),
                "workflows_available": bool(n8n_workflows.get("available")),
                "workflow_count": workflow_count,
                "error": n8n_workflows.get("error"),
                "status_code": n8n_workflows.get("status_code"),
            },
            "kali": {
                "status": kali.get("status"),
                "available": kali.get("available"),
                "distro": kali.get("distro"),
                "found_commands": kali.get("found_commands", []),
                "missing_commands": kali.get("missing_commands", []),
                "error": kali.get("error"),
            },
            "trading": {
                "running": trading_status.get("running")
                if isinstance(trading_status, dict)
                else None,
                "mode": trading_status.get("mode")
                if isinstance(trading_status, dict)
                else None,
                "symbol": trading_status.get("symbol")
                if isinstance(trading_status, dict)
                else None,
                "cycle_target_seconds": trading_status.get("cycle_target_seconds")
                if isinstance(trading_status, dict)
                else None,
                "live_execution_enabled": trading_status.get("live_execution_enabled")
                if isinstance(trading_status, dict)
                else False,
                "current_market_source": trading_status.get("current_market_source")
                if isinstance(trading_status, dict)
                else None,
                "prediction_quality": quality,
            },
            "integration_probes": integration_probes,
            "next_actions": next_actions,
            "executable_prompts": [
                "شغّل وكيل التداول الورقي",
                "حدّث مستشار استراتيجية وكيل التداول",
                "integration probe: openrouter",
                "integration probe: zapier_mcp",
                "zapier action: <app>/<action> params:{...}",
                "فوّض إلى Manus خطة تنفيذ هذا الهدف بعد الموافقة",
            ],
        }

    def _agent_mesh_execute(
        self,
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        refresh = bool(args.get("refresh", True))
        max_steps = _bounded_int(args.get("max_steps", 20), default=20, minimum=3, maximum=24)
        captured_at = datetime.now(UTC).isoformat()
        start_primary_trading = _agent_mesh_requests_trading_start(prompt)
        safe_executions: list[dict[str, Any]] = []
        skipped_high_risk: list[dict[str, Any]] = []
        integration_probes: dict[str, dict[str, Any]] = {}

        def run_safe(
            tool: str,
            description: str,
            tool_args: dict[str, Any] | None = None,
        ) -> dict[str, Any] | None:
            if len(safe_executions) >= max_steps:
                return None
            safe_args = tool_args or {}
            requirement = self.approval_requirement(tool, safe_args)
            if requirement.required:
                skipped_high_risk.append(
                    {
                        "tool": tool,
                        "description": description,
                        "risk_class": requirement.risk_class,
                        "reason": requirement.reason,
                    }
                )
                return None
            try:
                result = self.execute(tool, description, safe_args, context)
            except ToolExecutionError as exc:
                result = exc.result
            except Exception as exc:
                result = {
                    "tool": tool,
                    "available": False,
                    "executed": False,
                    "execution_failed": True,
                    "error": f"{type(exc).__name__}: safe mesh step failed",
                }
            safe_executions.append(
                {
                    "tool": tool,
                    "description": description,
                    "args": {
                        key: value
                        for key, value in safe_args.items()
                        if key not in {"payload", "params", "token", "api_key", "secret"}
                    },
                    "result": _agent_mesh_step_evidence(result),
                }
            )
            return result

        capabilities = run_safe(
            "local_capability_inventory",
            "فحص شبكة التنفيذ المحلية والنماذج والبوابات الجاهزة",
            {"refresh": refresh},
        )
        connected_inventory = run_safe(
            "connected_tool_inventory",
            "قراءة موصلات Zapier MCP ووكلاء الحساب المتاحين",
        )
        zapier_direct = run_safe(
            "zapier_action_catalog",
            "قراءة كتالوج Zapier MCP المباشر عبر OAuth المحلي إن كان متصلًا",
            {"refresh": False},
        )
        connector_catalog_result = run_safe(
            "connector_catalog",
            "قراءة كتالوج الموصلات المعرّفة في المستودع",
        )
        run_safe("kali_tool_inventory", "قراءة أدوات Kali WSL الدفاعية المتاحة")
        run_safe("trading_status", "قراءة حالة وكيل التداول Paper الأساسي")
        run_safe(
            "trading_strategy_refresh",
            "تحديث مستشار استراتيجية وكيل التداول Paper بمهلة قصيرة",
            {
                "model_override": self.config.trading_advisory_model,
                "model_timeout_seconds": self.config.trading_advisory_timeout_seconds,
            },
        )
        if start_primary_trading:
            run_safe(
                "trading_start",
                "تشغيل وكيل التداول Paper الأساسي بنبض الثانية",
            )
            run_safe(
                "trading_status",
                "قراءة حالة وكيل التداول Paper بعد التشغيل",
            )
        run_safe(
            "trading_testnet_status",
            "قراءة جاهزية وسيط التداول التجريبي دون إرسال أمر",
            {"probe": False},
        )
        for integration_id in (
            "local_execution_mesh",
            "huggingface_local",
            "openrouter",
            "supabase",
            "n8n_local",
            "zapier_mcp",
            "broker_testnet",
        ):
            probe_result = run_safe(
                "integration_probe",
                f"فحص جاهزية تكامل {integration_id}",
                {"integration_id": integration_id},
            )
            if isinstance(probe_result, dict):
                integration_probes[integration_id] = {
                    "ok": probe_result.get("ok"),
                    "status": probe_result.get("status"),
                    "summary": probe_result.get("summary"),
                    "action": probe_result.get("action"),
                    "secret_safe": True,
                }

        connectors = (
            connector_catalog_result.get("profiles")
            if isinstance(connector_catalog_result, dict)
            and isinstance(connector_catalog_result.get("profiles"), list)
            else self.connector_catalog()
        )
        for connector in connectors:
            if not isinstance(connector, dict):
                continue
            profile = str(connector.get("name") or "").strip()
            if not profile:
                continue
            if connector.get("requires_approval") or not connector.get("read_only", True):
                skipped_high_risk.append(
                    {
                        "tool": "connector_profile",
                        "description": f"تخطي موصل {profile}",
                        "risk_class": connector.get("risk_class", "external"),
                        "reason": "connector profile is write/external or requires approval",
                        "configured": bool(connector.get("configured")),
                        "profile": profile,
                    }
                )
                continue
            if not connector.get("configured"):
                continue
            if len(safe_executions) >= max_steps:
                continue
            run_safe(
                "connector_profile",
                f"تنفيذ موصل القراءة الآمن {profile}",
                {"profile": profile},
            )

        failed_steps = [
            step
            for step in safe_executions
            if isinstance(step.get("result"), dict)
            and step["result"].get("execution_failed")
        ]
        ready_count = (
            int(capabilities.get("ready_count") or 0)
            if isinstance(capabilities, dict)
            else None
        )
        zapier_app_count = (
            int(connected_inventory.get("zapier_app_count") or 0)
            if isinstance(connected_inventory, dict)
            else None
        )
        zapier_action_count = (
            int(connected_inventory.get("zapier_action_count") or 0)
            if isinstance(connected_inventory, dict)
            else None
        )
        zapier_direct_connected = (
            bool(zapier_direct.get("connected")) if isinstance(zapier_direct, dict) else False
        )
        ready_integrations = [
            probe
            for probe in integration_probes.values()
            if isinstance(probe, dict) and probe.get("ok")
        ]
        partial_integrations = [
            probe
            for probe in integration_probes.values()
            if isinstance(probe, dict)
            and probe.get("status") in {"partial", "needs_setup", "needs_operator"}
        ]
        next_actions = _agent_mesh_next_actions(
            integration_probes=integration_probes,
            connectors=self.connector_catalog(),
            zapier_direct=zapier_direct if isinstance(zapier_direct, dict) else {},
            n8n_workflows={},
            kali={},
        )
        return {
            "available": True,
            "executed": True,
            "secret_safe": True,
            "action": "agent_mesh_execute",
            "captured_at": captured_at,
            "summary": {
                "safe_execution_count": len(safe_executions),
                "failed_step_count": len(failed_steps),
                "skipped_high_risk_count": len(skipped_high_risk),
                "ready_capability_count": ready_count,
                "zapier_app_count": zapier_app_count,
                "zapier_action_count": zapier_action_count,
                "zapier_direct_oauth_connected": zapier_direct_connected,
                "zapier_direct_app_count": zapier_direct.get("app_count")
                if isinstance(zapier_direct, dict)
                else None,
                "zapier_direct_action_count": zapier_direct.get("action_count")
                if isinstance(zapier_direct, dict)
                else None,
                "zapier_direct_error": zapier_direct.get("error")
                if isinstance(zapier_direct, dict)
                else None,
                "integration_probe_count": len(integration_probes),
                "ready_integration_count": len(ready_integrations),
                "partial_integration_count": len(partial_integrations),
                "paper_trading_start_requested": start_primary_trading,
                "paper_trading_started": any(
                    step.get("tool") == "trading_start"
                    and isinstance(step.get("result"), dict)
                    and step["result"].get("executed")
                    for step in safe_executions
                ),
                "paper_trading_running": any(
                    step.get("tool") in {"trading_status", "trading_start"}
                    and isinstance(step.get("result"), dict)
                    and step["result"].get("running")
                    for step in safe_executions
                ),
                "paper_trading_advisor_refreshed": any(
                    step.get("tool") == "trading_strategy_refresh"
                    and isinstance(step.get("result"), dict)
                    and step["result"].get("executed")
                    for step in safe_executions
                ),
            },
            "execution_policy": {
                "mode": "safe_execute",
                "automatic_internal_execution": True,
                "approval_gated_steps_skipped": True,
                "external_writes_require_approval": True,
                "live_trading_requires_explicit_testnet_enablement": True,
                "live_security_testing_requires_approval": True,
            },
            "safe_executions": safe_executions,
            "skipped_high_risk": skipped_high_risk,
            "integration_probes": integration_probes,
            "next_actions": next_actions,
            "operator_prompt": prompt[:1000],
        }

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
        args: dict[str, Any],
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
        model_timeout_seconds = _bounded_float(
            args.get(
                "model_timeout_seconds",
                self.config.trading_advisory_timeout_seconds,
            ),
            default=self.config.trading_advisory_timeout_seconds,
            minimum=0.05,
            maximum=60.0,
        )
        advisor_model = _trading_advisor_model_client(model, self.config, args)
        advisory_model_id: str | None = None
        if advisor_model and advisor_model.available:
            try:
                raw = _complete_model_with_timeout(
                    advisor_model,
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
                    timeout_seconds=model_timeout_seconds,
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
                provider = str(getattr(advisor_model, "last_provider", "model"))[:120]
                advisory_model_id = str(
                    getattr(advisor_model, "last_model", None)
                    or getattr(advisor_model, "model", "")
                    or ""
                )[:160]
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
            "model_timeout_seconds": model_timeout_seconds,
            "advisory_model": advisory_model_id,
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
                    timeout=2,
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
        if self.config.n8n_api_key:
            try:
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
                if response.ok:
                    return {
                        "available": True,
                        "status_code": response.status_code,
                        "source": "rest_api",
                        "workflows": payload,
                    }
                api_error = f"n8n API returned HTTP {response.status_code}"
            except requests.RequestException as exc:
                api_error = f"n8n API request failed: {exc}"
        else:
            api_error = "N8N_API_KEY is not configured; using local CLI fallback"

        cli = self._n8n_cli_workflows()
        if cli["available"]:
            return {
                "available": True,
                "status_code": None,
                "source": "local_cli",
                "api_error": api_error,
                "workflows": cli["workflows"],
                "workflow_count": cli["workflow_count"],
            }
        return {
            "available": False,
            "status_code": None,
            "source": "local_cli",
            "api_error": api_error,
            "workflows": [],
            "workflow_count": 0,
            "error": cli["error"],
        }

    def _n8n_cli_workflows(self) -> dict[str, Any]:
        command = _n8n_cli_command()
        result = self._run([command, "list:workflow"], cwd=self.config.repo_root, timeout=30)
        if result["return_code"] != 0:
            return {
                "available": False,
                "workflow_count": 0,
                "workflows": [],
                "error": result["stderr"] or "n8n workflow CLI listing failed",
            }
        workflows: list[dict[str, str]] = []
        for raw_line in result["stdout"].splitlines():
            line = _strip_ansi(raw_line).strip()
            if not line or line.startswith("$ ") or line.lower().startswith("usage"):
                continue
            workflow_id, separator, name = line.partition("|")
            workflows.append(
                {
                    "id": workflow_id.strip(),
                    "name": name.strip() if separator else workflow_id.strip(),
                }
            )
        return {
            "available": True,
            "workflow_count": len(workflows),
            "workflows": workflows,
            "error": None,
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
            if requested == "n8n_workflows" and method == "GET":
                return self._n8n_connector_workflows_fallback(
                    profile,
                    method,
                    api_error=f"{type(exc).__name__}: connector request failed",
                    status_code=None,
                )
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
        if requested == "n8n_workflows" and method == "GET" and not response.ok:
            return self._n8n_connector_workflows_fallback(
                profile,
                method,
                api_error=f"Connector returned HTTP {response.status_code}",
                status_code=response.status_code,
            )
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

    def _n8n_connector_workflows_fallback(
        self,
        profile: dict[str, Any],
        method: str,
        *,
        api_error: str,
        status_code: int | None,
    ) -> dict[str, Any]:
        cli = self._n8n_cli_workflows()
        return {
            "profile": "n8n_workflows",
            "provider": profile.get("provider", "connector"),
            "method": method,
            "configured": True,
            "available": bool(cli["available"]),
            "executed": bool(cli["available"]),
            "execution_failed": False,
            "status_code": status_code,
            "source": "local_cli",
            "error": None if cli["available"] else cli["error"] or api_error,
            "api_error": api_error,
            "response": {
                "source": "local_cli",
                "workflow_count": cli["workflow_count"],
                "workflows": cli["workflows"],
            },
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
        apps = _combined_zapier_apps(inventory)
        return {
            "available": True,
            "path": str(path),
            "captured_at": inventory.get("captured_at"),
            "policy": inventory.get("policy", {}),
            "zapier_mcp_status": inventory.get("zapier_mcp_status", {}),
            "additional_zapier_mcp_sources": inventory.get(
                "additional_zapier_mcp_sources", []
            ),
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
        app = str(args.get("app") or "")
        try:
            return self.zapier.action_catalog(
                app,
                force=bool(args.get("refresh")),
            )
        except ZapierMCPError as exc:
            return self._zapier_action_catalog_fallback(app, str(exc))

    def _zapier_action_catalog_fallback(self, app: str, error: str) -> dict[str, Any]:
        status = self.zapier.status()
        base: dict[str, Any] = {
            "available": False,
            "connected": bool(status.get("connected")),
            "provider": "Zapier MCP",
            "source": "connected_tool_inventory_fallback",
            "live_available": False,
            "error": error,
            "apps": [],
            "app_count": 0,
            "action_count": 0,
        }
        if not self.config.tool_inventory_path.exists():
            return base
        try:
            inventory = json.loads(
                self.config.tool_inventory_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return base
        apps = _combined_zapier_apps(inventory)
        requested = app.strip().casefold()
        if requested:
            match = next(
                (
                    item
                    for item in apps
                    if str(item.get("app") or "").casefold() == requested
                ),
                None,
            )
            if not match:
                return base
            return {
                **base,
                "available": True,
                "app": match.get("app"),
                "app_count": 1,
                "action_count": int(match.get("action_count") or 0),
                "apps": [match],
            }
        return {
            **base,
            "available": bool(apps),
            "app_count": len(apps),
            "action_count": sum(int(item.get("action_count") or 0) for item in apps),
            "apps": apps,
        }

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
        if not shutil.which("wsl.exe"):
            return {
                "available": False,
                "status": "unavailable",
                "distro": self.config.kali_wsl_distro,
                "requested_commands": commands,
                "found": [],
                "found_commands": [],
                "missing_commands": commands,
                "execution_failed": False,
                "error": "wsl.exe is not installed or not on PATH",
                "command": ["wsl.exe", "-d", self.config.kali_wsl_distro],
                "return_code": 127,
                "stdout": "",
                "stderr": "",
            }
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

    def _hexstrike_lab_scan(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        target_url = _loopback_url(
            str(args.get("target_url") or args.get("target") or "http://127.0.0.1:3000")
        )
        parsed_target = urlparse(target_url)
        target_host = _loopback_host(
            str(args.get("target_host") or parsed_target.hostname or "127.0.0.1")
        )
        port = _safe_port(str(args.get("port") or parsed_target.port or "3000"))
        objective = str(args.get("objective") or "quick").strip().lower()
        if objective not in {"quick", "comprehensive", "stealth"}:
            objective = "quick"
        base_url = _loopback_url(str(args.get("hexstrike_url") or "http://127.0.0.1:8888"))

        health = self._hexstrike_request("GET", base_url, "/health", timeout=10)
        if not health.get("ok"):
            return {
                "available": False,
                "executed": False,
                "status": "unavailable",
                "target_url": target_url,
                "target_host": target_host,
                "port": port,
                "error": health.get("error") or health.get("body"),
                "hexstrike_status_code": health.get("status_code"),
                "execution_failed": False,
            }

        analysis = self._hexstrike_request(
            "POST",
            base_url,
            "/api/intelligence/analyze-target",
            {"target": target_url},
            timeout=30,
        )
        selected = self._hexstrike_request(
            "POST",
            base_url,
            "/api/intelligence/select-tools",
            {"target": target_url, "objective": objective},
            timeout=30,
        )
        nmap = self._hexstrike_request(
            "POST",
            base_url,
            "/api/tools/nmap",
            {
                "target": target_host,
                "scan_type": "-sT",
                "ports": port,
                "additional_args": "-T2 --max-retries 1 --host-timeout 15s",
                "use_recovery": False,
            },
            timeout=60,
        )

        profile = _json_path(analysis, "body", "target_profile")
        selected_tools = _json_path(selected, "body", "selected_tools")
        if not isinstance(profile, dict):
            profile = {}
        if not isinstance(selected_tools, list):
            selected_tools = []
        nmap_body = nmap.get("body") if isinstance(nmap.get("body"), dict) else {}
        nmap_stdout = str(nmap_body.get("stdout") or nmap_body.get("output") or "")
        return {
            "available": True,
            "executed": True,
            "status": "completed",
            "target_url": target_url,
            "target_host": target_host,
            "port": port,
            "objective": objective,
            "hexstrike": _hexstrike_health_summary(health.get("body")),
            "analysis": {
                "success": bool(_json_path(analysis, "body", "success")),
                "target_type": profile.get("target_type"),
                "risk_level": profile.get("risk_level"),
                "services": profile.get("services"),
            },
            "selected_tools": [
                _tool_name(item)
                for item in selected_tools[:12]
                if _tool_name(item)
            ],
            "nmap": {
                "success": bool(nmap_body.get("success", nmap.get("ok"))),
                "return_code": nmap_body.get("return_code", nmap_body.get("exit_code")),
                "timed_out": bool(nmap_body.get("timed_out", False)),
                "stdout_preview": "\n".join(nmap_stdout.splitlines()[:20]),
            },
            "execution_failed": False,
        }

    @staticmethod
    def _hexstrike_request(
        method: str,
        base_url: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: int,
    ) -> dict[str, Any]:
        try:
            response = requests.request(
                method,
                f"{base_url.rstrip('/')}{path}",
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text[:4000]
        return {
            "ok": response.ok,
            "status_code": response.status_code,
            "body": body,
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
            "sys.stdout.reconfigure(encoding='utf-8', errors='replace');"
            "sys.stderr.reconfigure(encoding='utf-8', errors='replace');"
            "sys.path.insert(0,'.');"
            "from core.orchestrator import FathiyaOrchestrator;"
            "r=FathiyaOrchestrator().run(sys.argv[1]);"
            "print(json.dumps({'final_answer':r.get('final_answer'),"
            "'analysis':r.get('analysis'),"
            "'session_id':r.get('session_id')},ensure_ascii=False,default=str))"
        )
        result = self._run(
            [sys.executable, "-c", code, question],
            cwd=core_root,
            timeout=90,
            env={
                "PYTHONIOENCODING": "utf-8",
                "PYTHONUTF8": "1",
            },
        )
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
    def _run(
        command: list[str],
        *,
        cwd: Path,
        timeout: int = 20,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=run_env,
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


def _loopback_url(raw: str) -> str:
    candidate = raw.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("HexStrike lab target must be an HTTP(S) loopback URL")
    _loopback_host(parsed.hostname)
    return candidate.rstrip("/")


def _loopback_host(raw: str) -> str:
    host = raw.strip().strip("[]").lower()
    if host in {"127.0.0.1", "localhost", "::1"}:
        return "127.0.0.1" if host in {"localhost", "::1"} else host
    raise ValueError("HexStrike lab scan is restricted to loopback targets")


def _safe_port(raw: str) -> str:
    port = raw.strip()
    if not re.fullmatch(r"\d{1,5}", port):
        raise ValueError("HexStrike lab scan requires a single numeric port")
    value = int(port)
    if value < 1 or value > 65535:
        raise ValueError("HexStrike lab scan port must be between 1 and 65535")
    return str(value)


def _json_path(payload: dict[str, Any], *keys: str) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _tool_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("name") or item.get("tool") or "").strip()
    return str(item).strip()


def _hexstrike_health_summary(body: Any) -> dict[str, Any]:
    if not isinstance(body, dict):
        return {"status": "unknown"}
    category_stats = body.get("category_stats")
    return {
        "status": body.get("status"),
        "version": body.get("version"),
        "all_essential_tools_available": body.get("all_essential_tools_available"),
        "total_tools_available": body.get("total_tools_available"),
        "total_tools_count": body.get("total_tools_count"),
        "category_stats": category_stats if isinstance(category_stats, dict) else {},
    }


def _bounded_float(
    value: Any,
    *,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _bounded_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _agent_mesh_requests_trading_start(prompt: str) -> bool:
    text = prompt.casefold()
    return any(
        term in text
        for term in (
            "fathiya_execution_os_mission_v1",
            "start_primary_trading",
            "start primary trading",
            "ابدأ وكيل التداول الورقي",
            "ابدأ وكيل التداول",
            "شغّل وكيل التداول الورقي",
            "شغل وكيل التداول الورقي",
            "تشغيل وكيل التداول الورقي",
            "ينبض بالثانية",
            "بنبض الثانية",
        )
    )


def _combined_zapier_apps(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def absorb(apps: Any, source: str) -> None:
        if not isinstance(apps, list):
            return
        for item in apps:
            if not isinstance(item, dict) or not item.get("app"):
                continue
            name = str(item["app"])
            existing = merged.setdefault(
                name,
                {
                    "app": name,
                    "action_count": 0,
                    "modes": [],
                    "sources": [],
                },
            )
            try:
                action_count = int(item.get("action_count", 0))
            except (TypeError, ValueError):
                action_count = 0
            existing["action_count"] = max(int(existing["action_count"]), action_count)
            modes = item.get("modes", [])
            if isinstance(modes, list):
                for mode in modes:
                    if isinstance(mode, str) and mode not in existing["modes"]:
                        existing["modes"].append(mode)
            if source and source not in existing["sources"]:
                existing["sources"].append(source)

    absorb(inventory.get("zapier_apps", []), "fathya_core_zapier")
    for source in inventory.get("additional_zapier_mcp_sources", []):
        if isinstance(source, dict):
            absorb(source.get("apps", []), str(source.get("name") or "zapier_mcp"))
    return sorted(merged.values(), key=lambda item: str(item.get("app", "")).casefold())


def _n8n_cli_command() -> str:
    discovered = shutil.which("n8n") or shutil.which("n8n.cmd")
    if discovered:
        return discovered
    windows_candidate = Path.home() / "AppData" / "Roaming" / "npm" / "n8n.cmd"
    if windows_candidate.exists():
        return str(windows_candidate)
    return "n8n.cmd" if os.name == "nt" else "n8n"


def _strip_ansi(value: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", value)


def _complete_model_with_timeout(
    model: ModelClient,
    system_prompt: str,
    user_prompt: str,
    *,
    timeout_seconds: float,
    json_mode: bool,
    max_new_tokens: int,
) -> str:
    results: queue.Queue[tuple[str, str | BaseException]] = queue.Queue(maxsize=1)

    def run() -> None:
        try:
            results.put(
                (
                    "ok",
                    model.complete(
                        system_prompt,
                        user_prompt,
                        json_mode=json_mode,
                        max_new_tokens=max_new_tokens,
                    ),
                ),
                block=False,
            )
        except BaseException as exc:  # pragma: no cover - re-raised by caller
            try:
                results.put(("error", exc), block=False)
            except queue.Full:
                pass

    thread = threading.Thread(
        target=run,
        name="fathiya-trading-advisor-refresh",
        daemon=True,
    )
    thread.start()
    try:
        status, payload = results.get(timeout=timeout_seconds)
    except queue.Empty as exc:
        raise TimeoutError("Trading strategy advisor timed out") from exc
    if status == "error":
        if isinstance(payload, BaseException):
            raise payload
        raise RuntimeError(str(payload))
    return str(payload)


def _trading_advisor_model_client(
    model: ModelClient | None,
    config: RuntimeConfig,
    args: dict[str, Any],
) -> ModelClient | None:
    model_override = str(
        args.get("model_override")
        or args.get("model")
        or config.trading_advisory_model
        or ""
    ).strip()
    if config.openrouter_api_key and model_override:
        candidate_override = args.get("model_candidates")
        if isinstance(candidate_override, str):
            fallback_models = tuple(
                item.strip() for item in candidate_override.split(",") if item.strip()
            )
        elif isinstance(candidate_override, list):
            fallback_models = tuple(
                str(item).strip() for item in candidate_override if str(item).strip()
            )
        else:
            fallback_models = config.trading_advisory_model_candidates
        return OpenRouterClient(
            config.openrouter_api_key,
            model_override,
            fallback_models,
        )
    return model


def _agent_mesh_next_actions(
    *,
    integration_probes: dict[str, dict[str, Any]],
    connectors: list[dict[str, Any]],
    zapier_direct: dict[str, Any],
    n8n_workflows: dict[str, Any],
    kali: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    def add(
        action_id: str,
        title: str,
        prompt: str,
        reason: str,
        *,
        ui_action: str = "task",
        settings_group: str | None = None,
        integration_id: str | None = None,
        action_path: str | None = None,
        action_label: str | None = None,
    ) -> None:
        action: dict[str, Any] = {
            "id": action_id,
            "title": title,
            "prompt": prompt,
            "reason": reason,
            "ui_action": ui_action,
        }
        if settings_group:
            action["settings_group"] = settings_group
        if integration_id:
            action["integration_id"] = integration_id
        if action_path:
            action["action_path"] = action_path
        if action_label:
            action["action_label"] = action_label
        actions.append(action)

    if integration_probes.get("openrouter", {}).get("status") != "ready":
        add(
            "configure_openrouter",
            "تفعيل OpenRouter",
            "integration probe: openrouter",
            "المهام الثقيلة تحتاج مفتاح OpenRouter محلي حتى يعمل التخطيط والتقييم بالنماذج.",
            ui_action="settings",
            settings_group="openrouter",
            integration_id="openrouter",
        )
    if integration_probes.get("huggingface_local", {}).get("status") != "ready":
        add(
            "enable_huggingface_local",
            "تفعيل Hugging Face المحلي",
            "integration probe: huggingface_local",
            "الاسترجاع والتوليد المحليين يخففان الاعتماد على الشبكة ويعطيان المحرك ذاكرة أقرب.",
            integration_id="huggingface_local",
        )
    if not zapier_direct.get("connected"):
        add(
            "connect_zapier_oauth",
            "ربط Zapier MCP المحلي",
            "integration probe: zapier_mcp",
            "مخزون Zapier متاح، لكن التنفيذ المباشر يحتاج OAuth محليًا بدل كلمات مرور في المحادثة.",
            ui_action="oauth",
            integration_id="zapier_mcp",
            action_path="/api/agent/oauth/zapier/start",
            action_label="ربط Zapier OAuth",
        )
    if not n8n_workflows.get("available"):
        add(
            "configure_n8n_api",
            "تفعيل قراءة n8n",
            "افحص n8n واعرض مساراته",
            "قراءة workflows تحتاج N8N_API_KEY حتى يستطيع المحرك توجيه الأتمتة بدل الاكتفاء بالصحة.",
            ui_action="settings",
            settings_group="n8n_local",
            integration_id="n8n_local",
        )
    missing_connector_env = sorted(
        {
            str(name)
            for connector in connectors
            for name in connector.get("missing_env", [])
            if name
        }
    )
    bridge_missing_env = [
        name
        for name in missing_connector_env
        if name
        in {
            "FATHIYA_CURSOR_AGENT_URL",
            "FATHIYA_MANUS_AGENT_URL",
            "FATHIYA_N8N_WEBHOOK_URL",
            "FATHIYA_ZAPIER_WEBHOOK_URL",
        }
    ]
    if bridge_missing_env:
        add(
            "configure_agent_bridges",
            "إكمال جسور Cursor وManus وZapier",
            "اعرض جاهزية جسور Cursor وManus وZapier ثم جهز الناقص",
            "بعض الموصلات التنفيذية تنتظر إعدادات محلية: "
            + ", ".join(bridge_missing_env[:8]),
            ui_action="settings",
            settings_group="local_execution_mesh",
            integration_id="local_execution_mesh",
        )
    if kali.get("status") != "active":
        add(
            "prepare_kali",
            "تجهيز Kali WSL",
            "افحص أدوات Kali الدفاعية",
            "وكيل الأمن يحتاج أدوات Kali جاهزة للفحص الدفاعي، مع بقاء الفحص الحي تحت الموافقة.",
            integration_id="kali_wsl",
        )
    if integration_probes.get("broker_testnet", {}).get("status") != "ready":
        add(
            "configure_testnet",
            "ربط Testnet للتداول",
            "integration probe: broker_testnet",
            "التنفيذ المالي الحقيقي يبقى مقفلًا؛ أول خطوة آمنة هي Testnet محلي مع مفاتيح غير مكشوفة.",
            ui_action="settings",
            settings_group="broker_testnet",
            integration_id="broker_testnet",
        )
    return actions


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


def _agent_mesh_step_evidence(result: dict[str, Any]) -> dict[str, Any]:
    tool = str(result.get("tool") or "")
    if tool in {"connector_profile", "n8n_status", "n8n_workflows"}:
        return _connector_result_evidence(result)
    if tool == "local_capability_inventory":
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "ready_count": result.get("ready_count"),
            "partial_count": result.get("partial_count"),
            "capability_count": result.get("capability_count"),
            "cached": result.get("cached"),
        }
    if tool == "connected_tool_inventory":
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "zapier_app_count": result.get("zapier_app_count"),
            "zapier_action_count": result.get("zapier_action_count"),
            "agent_provider_actions": result.get("agent_provider_actions"),
        }
    if tool == "zapier_action_catalog":
        apps = result.get("apps") if isinstance(result.get("apps"), list) else []
        actions = result.get("actions") if isinstance(result.get("actions"), list) else []
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "connected": result.get("connected"),
            "provider": result.get("provider"),
            "app": result.get("app"),
            "app_count": result.get("app_count"),
            "action_count": result.get("action_count"),
            "apps": apps[:12],
            "actions": actions[:12],
            "error": result.get("error"),
        }
    if tool == "connector_catalog":
        connectors = (
            result.get("profiles")
            if isinstance(result.get("profiles"), list)
            else result
            if isinstance(result, list)
            else []
        )
        return {
            "available": True,
            "executed": True,
            "profile_count": len(connectors),
            "configured_count": sum(
                1 for connector in connectors if connector.get("configured")
            ),
            "read_only_configured": [
                connector.get("name")
                for connector in connectors
                if connector.get("configured")
                and connector.get("read_only", True)
                and not connector.get("requires_approval")
            ],
        }
    if tool == "integration_probe":
        details = result.get("details") if isinstance(result.get("details"), dict) else {}
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "integration_id": result.get("integration_id"),
            "ok": result.get("ok"),
            "status": result.get("status"),
            "summary": result.get("summary"),
            "action": result.get("action"),
            "details": details,
        }
    if tool == "kali_tool_inventory":
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "status": result.get("status"),
            "distro": result.get("distro"),
            "found_commands": result.get("found_commands", []),
            "missing_commands": result.get("missing_commands", []),
            "error": result.get("error"),
        }
    if tool == "hexstrike_lab_scan":
        analysis = result.get("analysis") if isinstance(result.get("analysis"), dict) else {}
        nmap = result.get("nmap") if isinstance(result.get("nmap"), dict) else {}
        hexstrike = result.get("hexstrike") if isinstance(result.get("hexstrike"), dict) else {}
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "status": result.get("status"),
            "target_url": result.get("target_url"),
            "port": result.get("port"),
            "hexstrike_status": hexstrike.get("status"),
            "tool_count": hexstrike.get("total_tools_available"),
            "target_type": analysis.get("target_type"),
            "risk_level": analysis.get("risk_level"),
            "selected_tools": result.get("selected_tools", []),
            "nmap_success": nmap.get("success"),
            "error": result.get("error"),
        }
    if tool in {"trading_status", "trading_start", "trading_stop"}:
        trading = result.get("trading") if isinstance(result.get("trading"), dict) else {}
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "action": result.get("action"),
            "running": trading.get("running"),
            "symbol": trading.get("symbol"),
            "mode": trading.get("mode"),
            "latest_receipt_id": trading.get("latest_receipt_id"),
            "execution_cadence": trading.get("execution_cadence"),
            "cycle_target_seconds": trading.get("cycle_target_seconds"),
        }
    if tool == "trading_strategy_refresh":
        advisory = result.get("advisory") if isinstance(result.get("advisory"), dict) else {}
        return {
            "available": result.get("available"),
            "executed": result.get("executed"),
            "model_provider": result.get("model_provider"),
            "fallback": result.get("fallback"),
            "error_type": result.get("error_type"),
            "advisory": {
                "action": advisory.get("action"),
                "confidence": advisory.get("confidence"),
                "provider": advisory.get("provider"),
            },
            "live_execution_enabled": result.get("live_execution_enabled"),
        }
    if tool == "trading_testnet_status":
        testnet = result.get("testnet") if isinstance(result.get("testnet"), dict) else {}
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "action": result.get("action"),
            "configured": testnet.get("configured"),
            "execution_enabled": testnet.get("execution_enabled"),
            "real_funds_possible": testnet.get("real_funds_possible"),
        }
    return {
        key: result.get(key)
        for key in (
            "available",
            "executed",
            "execution_failed",
            "status",
            "status_code",
            "error",
            "action",
        )
        if key in result
    }
