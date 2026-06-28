from __future__ import annotations

import json
import html
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
from urllib.parse import urljoin, urlparse

import requests

from .config import RuntimeConfig
from .learning import build_learning_session, make_learning_source
from .medium_intel import build_medium_intelligence_report
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

EXCLUDED_TOOL_NAMES = {"agent_delegate"}
EXCLUDED_CAPABILITY_IDS = {"claude_code"}
EXCLUDED_INTEGRATION_IDS = {"supabase"}
EXCLUDED_AGENT_PROVIDER_APPS = {"cursor", "manus"}


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
            "github_codespaces_inventory": self._github_codespaces_inventory,
            "github_codespaces_agent": self._github_codespaces_agent,
            "web_fetch": self._web_fetch,
            "production_site_audit": self._production_site_audit,
            "knowledge_ingest_url": self._knowledge_ingest_url,
            "learning_bootstrap": self._learning_bootstrap,
            "medium_intelligence_pipeline": self._medium_intelligence_pipeline,
            "n8n_status": self._n8n_status,
            "n8n_workflows": self._n8n_workflows,
            "n8n_webhook": self._n8n_webhook,
            "connector_catalog": self._connector_catalog,
            "connector_profile": self._connector_profile,
            "connected_tool_inventory": self._connected_tool_inventory,
            "agent_provider_probe": self._agent_provider_probe,
            "agent_provider_action_prepare": self._agent_provider_action_prepare,
            "integration_probe": self._integration_probe,
            "openrouter_model_strategy": self._openrouter_model_strategy,
            "zapier_action_catalog": self._zapier_action_catalog,
            "zapier_action_details": self._zapier_action_details,
            "zapier_action_preflight": self._zapier_action_preflight,
            "zapier_action": self._zapier_action,
            "kali_tool_inventory": self._kali_tool_inventory,
            "hexstrike_lab_scan": self._hexstrike_lab_scan,
            "bug_bounty_static_review": self._bug_bounty_static_review,
            "bug_bounty_draft_gate": self._bug_bounty_draft_gate,
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
                    "openrouter_model_strategy",
                    "Read the OpenRouter routing strategy: cheap-first planning, Fusion deep research, advisor escalation, and safety guardrail models.",
                    "models",
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
                    "github_codespaces_inventory",
                    "List GitHub Codespaces visible to the authenticated gh account without executing remote commands.",
                    "github",
                    inputs=("limit",),
                ),
                ToolSpec(
                    "github_codespaces_agent",
                    "Prepare the GitHub Codespaces engineering agent with inventory, target selection, and a remote execution handoff plan without running remote commands.",
                    "github",
                    inputs=("objective", "mode", "target_repository", "limit"),
                ),
                ToolSpec(
                    "web_fetch",
                    "Fetch a public or operator-provided HTTP(S) source for evidence.",
                    "research",
                    inputs=("url",),
                ),
                ToolSpec(
                    "production_site_audit",
                    "Run a read-only public-domain audit for FATHIYA routes, identity signals, and production/local routing gaps.",
                    "deployment",
                    inputs=("base_url", "routes"),
                ),
                ToolSpec(
                    "knowledge_ingest_url",
                    "Fetch an HTTP(S) report and persist it in the local knowledge intake.",
                    "knowledge",
                    read_only=False,
                    inputs=("url",),
                ),
                ToolSpec(
                    "learning_bootstrap",
                    "Convert courses, training posts, writeups, and local notes into learning cards, quiz questions, and a mastery report.",
                    "knowledge",
                    read_only=False,
                    inputs=("source_urls", "source_paths", "source_text", "title", "objective"),
                ),
                ToolSpec(
                    "medium_intelligence_pipeline",
                    "Collect Medium security writeups at scale and gate them into learning-only, needs-evidence, dedupe-hold, or report-candidate queues.",
                    "knowledge",
                    read_only=False,
                    inputs=("source_urls", "source_paths", "source_text", "max_items", "fetch_live", "title"),
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
                    "agent_provider_probe",
                    "Inspect a Zapier-backed agent provider such as Agents, ChatGPT, Apify, or Netlify and return exact inventory/read/write actions plus OAuth readiness.",
                    "connectors",
                    inputs=("provider", "refresh"),
                ),
                ToolSpec(
                    "agent_provider_action_prepare",
                    "Prepare an exact Zapier-backed provider action from a provider, requested action, and objective without executing external writes.",
                    "connectors",
                    inputs=("provider", "action", "objective", "params", "refresh"),
                ),
                ToolSpec(
                    "zapier_action_catalog",
                    "Read the live Zapier MCP app and action catalog through local OAuth.",
                    "connectors",
                    inputs=("app", "refresh"),
                ),
                ToolSpec(
                    "zapier_action_details",
                    "Read required parameters and a safe JSON template for one exact Zapier MCP action.",
                    "connectors",
                    inputs=("app", "action"),
                ),
                ToolSpec(
                    "zapier_action_preflight",
                    "Validate an exact Zapier MCP action request against live or inventory metadata without executing it.",
                    "connectors",
                    inputs=("app", "action", "params", "instructions"),
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
                    "bug_bounty_static_review",
                    "Review an authorized public/local repository with static-only checks, or create a passive website-intake report for an HTTP(S) target URL without active scanning or submission.",
                    "security",
                    inputs=("program", "program_url", "repo_url", "target_path", "scope_note", "focus"),
                ),
                ToolSpec(
                    "bug_bounty_draft_gate",
                    "Validate a local Bugcrowd static-review draft and upload the verified draft decision inside FATHIYA without external submission.",
                    "security",
                    read_only=False,
                    inputs=("program", "report_path", "repo_path", "destination"),
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
            if spec.name in EXCLUDED_TOOL_NAMES:
                continue
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
        if integration_id in EXCLUDED_INTEGRATION_IDS:
            raise ValueError(f"Integration is excluded in this FATHIYA build: {integration_id}")
        if integration_id == "local_execution_mesh":
            result = self._local_capability_inventory("", {}, [])
            ready_count = int(result.get("ready_count") or 0)
            capability_count = int(result.get("capability_count") or 0)
            partial_count = int(result.get("partial_count") or 0)
            core_ready_count = int(result.get("core_ready_count") or ready_count)
            core_capability_count = int(
                result.get("core_capability_count") or capability_count
            )
            optional_attention_count = int(result.get("optional_attention_count") or 0)
            ok = bool(
                core_capability_count and core_ready_count == core_capability_count
            )
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "partial" if ready_count else "needs_setup",
                summary=(
                    f"{core_ready_count} من {core_capability_count} بوابات التنفيذ الأساسية جاهزة"
                    + (
                        f" و{optional_attention_count} اختيارية تحتاج انتباه."
                        if optional_attention_count
                        else "."
                    )
                ),
                checked_at=checked_at,
                action="local_capability_inventory",
                details={
                    "ready_count": ready_count,
                    "partial_count": partial_count,
                    "capability_count": capability_count,
                    "core_ready_count": core_ready_count,
                    "core_capability_count": core_capability_count,
                    "optional_attention_count": optional_attention_count,
                },
            )
        if integration_id == "huggingface_local":
            retrieval = bool(self.config.enable_hf_retrieval)
            generation = bool(self.config.enable_local_generation)
            planning = bool(self.config.enable_local_planning)
            ok = retrieval or generation or planning
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "needs_setup",
                summary=(
                    "النماذج المحلية مفعلة للاسترجاع أو التوليد أو التخطيط."
                    if ok
                    else "النماذج المحلية غير مفعلة في إعدادات المشغّل."
                ),
                checked_at=checked_at,
                action="configuration_check",
                details={
                    "retrieval_enabled": retrieval,
                    "generation_enabled": generation,
                    "planning_enabled": planning,
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
                    "research_model": self.config.openrouter_research_model,
                    "safety_model": self.config.openrouter_safety_model,
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
                    "network_call": False,
                    "cost_incurred": False,
                },
            )
        if integration_id == "github_codespaces":
            result = self._github_codespaces_inventory("", {"limit": 10}, [])
            available = bool(result.get("available"))
            installed = bool(result.get("installed"))
            codespace_count = int(result.get("codespace_count") or 0)
            active_count = int(result.get("active_codespace_count") or 0)
            return _integration_probe_payload(
                integration_id,
                ok=available,
                status="ready" if available else "partial" if installed else "needs_setup",
                summary=(
                    f"GitHub Codespaces متصل؛ {codespace_count} مساحة ظاهرة و{active_count} نشطة."
                    if available
                    else "GitHub CLI موجود ويحتاج scope codespace: gh auth refresh -h github.com -s codespace"
                    if installed
                    else "GitHub CLI غير مثبت أو غير ظاهر للمشغل المحلي."
                ),
                checked_at=checked_at,
                action="github_codespaces_inventory",
                details={
                    "installed": installed,
                    "authenticated": bool(result.get("authenticated")),
                    "auth_state": result.get("auth_state"),
                    "missing_scope": result.get("missing_scope"),
                    "operator_action_required": bool(
                        result.get("operator_action_required")
                    ),
                    "codespace_count": codespace_count,
                    "active_codespace_count": active_count,
                    "execution_mode": result.get("execution_mode"),
                    "required_scope": "codespace",
                    "auth_command": result.get("auth_command")
                    or "gh auth refresh -h github.com -s codespace",
                    "requires_approval_for_remote_execution": True,
                    "codespaces": result.get("codespaces", []),
                    "error": result.get("error"),
                },
            )
        if integration_id == "n8n_local":
            status_result = self._n8n_status("", {}, [])
            ok = bool(status_result.get("available"))
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
                action="n8n_status",
                details={
                    "status_available": bool(status_result.get("available")),
                    "status_source": status_result.get("source"),
                    "version": status_result.get("version"),
                    "error": status_result.get("error"),
                },
            )
        if integration_id == "kali_wsl":
            result = self._kali_tool_inventory("", {}, [])
            found = result.get("found_commands")
            missing = result.get("missing_commands")
            found_commands = found if isinstance(found, list) else []
            missing_commands = missing if isinstance(missing, list) else []
            available = bool(result.get("available"))
            ok = available and not missing_commands
            missing_summary = ", ".join(str(item) for item in missing_commands)
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status="ready" if ok else "partial" if available else "needs_setup",
                summary=(
                    f"Kali WSL جاهز وفيه {len(found_commands)} أدوات أمنية أساسية."
                    if ok
                    else f"Kali WSL متاح جزئيًا؛ الأدوات الناقصة: {missing_summary or 'غير محددة'}."
                    if available
                    else "تعذر الوصول إلى Kali WSL."
                ),
                checked_at=checked_at,
                action="kali_tool_inventory",
                details={
                    "distro": result.get("distro"),
                    "found_commands": found_commands,
                    "missing_commands": missing_commands,
                    "status": result.get("status"),
                    "error": result.get("error"),
                },
            )
        if integration_id == "zapier_mcp":
            status = self.zapier.status()
            inventory = self._connected_tool_inventory("", {}, [])
            connected = bool(status.get("connected"))
            app_count = int(inventory.get("zapier_app_count") or 0)
            action_count = int(inventory.get("zapier_action_count") or 0)
            direct_catalog = self._zapier_action_catalog("", {"refresh": False}, [])
            live_available = bool(
                direct_catalog.get("live_available", direct_catalog.get("available"))
            )
            needs_reconnect = bool(direct_catalog.get("needs_reconnect"))
            direct_ready = bool(connected and live_available and not needs_reconnect)
            inventory_ready = bool(app_count > 0)
            ok = bool(direct_ready and inventory_ready)
            return _integration_probe_payload(
                integration_id,
                ok=ok,
                status=(
                    "ready"
                    if ok
                    else "partial"
                    if connected or inventory_ready
                    else "needs_setup"
                ),
                summary=(
                    f"Zapier OAuth المباشر جاهز، والمخزون يعرض {app_count} تطبيقًا و{action_count} إجراء."
                    if ok
                    else f"مخزون Zapier يعرض {app_count} تطبيقًا و{action_count} إجراء، لكن OAuth المباشر يحتاج إعادة ربط."
                    if connected and needs_reconnect
                    else "Zapier OAuth المحلي متصل وجاهز للتنفيذ، لكن مخزون التطبيقات والإجراءات فارغ أو غير متزامن."
                    if direct_ready
                    else f"مخزون Zapier يعرض {app_count} تطبيقًا و{action_count} إجراء، لكن OAuth المحلي المباشر لم يكتمل."
                    if inventory_ready
                    else "Zapier MCP غير جاهز بعد؛ اربط OAuth المحلي أو فعّل التطبيقات داخل Zapier MCP."
                ),
                checked_at=checked_at,
                action="oauth_status_and_inventory",
                details={
                    "direct_oauth_connected": connected,
                    "direct_live_available": live_available,
                    "needs_reconnect": needs_reconnect,
                    "inventory_available": inventory_ready,
                    "auth_state": direct_catalog.get("auth_state"),
                    "refresh_recommended": bool(
                        direct_catalog.get("refresh_recommended")
                        or status.get("refresh_recommended")
                    ),
                    "last_refresh_error": (
                        direct_catalog.get("last_refresh_error")
                        or status.get("last_refresh_error")
                    ),
                    "last_refresh_status_code": (
                        direct_catalog.get("last_refresh_status_code")
                        or status.get("last_refresh_status_code")
                    ),
                    "last_refresh_at": status.get("last_refresh_at"),
                    "app_count": app_count,
                    "action_count": action_count,
                    "endpoint": status.get("endpoint"),
                    "error": direct_catalog.get("error"),
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

        github = self._probe_cli("gh", ("--version",), auth_args=("auth", "status"))
        github.update(
            {
                "id": "github_cli",
                "name": "GitHub CLI",
                "execution_mode": "local_cli",
                "requires_approval": False,
            }
        )
        codespaces_status = self._github_codespaces_inventory("", {"limit": 10}, [])
        github_codespaces = {
            "id": "github_codespaces",
            "name": "GitHub Codespaces",
            "installed": bool(codespaces_status.get("installed")),
            "available": bool(codespaces_status.get("available")),
            "status": str(codespaces_status.get("status") or "unavailable"),
            "execution_mode": "github_codespaces_remote_dev",
            "requires_approval": True,
            "required_for_core": False,
            "optional": True,
            "optional_reason": (
                "Remote development capacity is an upgrade path; local agents "
                "continue running without a Codespace."
            ),
            "codespace_count": int(codespaces_status.get("codespace_count") or 0),
            "active_codespace_count": int(
                codespaces_status.get("active_codespace_count") or 0
            ),
            "authenticated": bool(codespaces_status.get("authenticated")),
            "auth_state": codespaces_status.get("auth_state"),
            "missing_scope": codespaces_status.get("missing_scope"),
            "operator_action_required": bool(
                codespaces_status.get("operator_action_required")
            ),
            "auth_command": codespaces_status.get("auth_command"),
            "error": codespaces_status.get("error"),
        }
        docker = self._probe_docker()
        docker.update(
            {
                "required_for_core": False,
                "optional": True,
                "optional_reason": "Only needed for containerized helper tasks; FATHIYA can execute local agents without it.",
            }
        )
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
            "required_for_core": False,
            "optional": True,
            "optional_reason": (
                "Zapier live OAuth unlocks connected apps, while inventory and "
                "local tools remain usable before OAuth is refreshed."
            ),
        }
        hugging_face_ready = (
            self.config.enable_hf_retrieval
            or self.config.enable_local_generation
            or self.config.enable_local_planning
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
            github,
            github_codespaces,
            docker,
            n8n,
            kali,
            zapier,
            hugging_face,
            openrouter,
            trading_agent,
        ]
        capabilities = [
            capability
            for capability in capabilities
            if str(capability.get("id") or "") not in EXCLUDED_CAPABILITY_IDS
        ]
        for capability in capabilities:
            capability.setdefault("required_for_core", True)
            capability.setdefault("optional", not bool(capability["required_for_core"]))
        ready_count = sum(
            item.get("status") in {"active", "ready"} for item in capabilities
        )
        core_capabilities = [
            item for item in capabilities if bool(item.get("required_for_core"))
        ]
        optional_capabilities = [
            item for item in capabilities if not bool(item.get("required_for_core"))
        ]
        core_ready_count = sum(
            item.get("status") in {"active", "ready"} for item in core_capabilities
        )
        result = {
            "available": True,
            "captured_at": datetime.now(UTC).isoformat(),
            "ready_count": ready_count,
            "core_ready_count": core_ready_count,
            "core_capability_count": len(core_capabilities),
            "optional_capability_count": len(optional_capabilities),
            "optional_attention_count": sum(
                item.get("status") in {"partial", "degraded", "unavailable"}
                for item in optional_capabilities
            ),
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
        if integration_id in EXCLUDED_INTEGRATION_IDS:
            raise ValueError(f"integration_probe is excluded for {integration_id}")
        return self.integration_probe(integration_id)

    def _openrouter_model_strategy(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "tool": "openrouter_model_strategy",
            "available": True,
            "configured": bool(self.config.openrouter_api_key),
            "network_call": False,
            "cost_incurred": False,
            "source": (
                "OpenRouter mid-June 2026 email: Fusion, Advisor, Subagent, "
                "Models API, and new model recap."
            ),
            "strategy": {
                "default_planning": {
                    "mode": "local_first_openrouter_escalation",
                    "primary_model": f"local:{self.config.local_model}",
                    "fallback_models": list(
                        dict.fromkeys(
                            [self.config.openrouter_model, *self.config.openrouter_model_candidates]
                        )
                    ),
                    "reason": (
                        "Use the local Hugging Face model for routine planning and synthesis; "
                        "escalate to OpenRouter only when the local route fails or the task needs "
                        "deeper advisor/research judgment."
                    ),
                },
                "trading_advisor": {
                    "mode": "advisor_veto_only",
                    "primary_model": self.config.trading_advisory_model,
                    "fallback_models": list(self.config.trading_advisory_model_candidates),
                    "server_tool_features": [
                        "multiple_named_advisors",
                        "memory_across_requests",
                        "streaming",
                    ],
                    "reason": (
                        "A stronger/agentic model may confirm or veto paper signals, "
                        "but cannot originate orders."
                    ),
                },
                "deep_research": {
                    "mode": "fusion_on_demand",
                    "model": self.config.openrouter_research_model,
                    "invocation_modes": [
                        "direct_model_slug",
                        "server_tool_from_current_model",
                    ],
                    "panel_limit": 8,
                    "web_search_default": True,
                    "judge_behavior": [
                        "map_model_agreement",
                        "map_model_conflict",
                        "surface_unique_catches",
                        "surface_shared_blind_spots",
                    ],
                    "not_for": [
                        "majority_vote",
                        "default_coding_agent",
                        "general_chat",
                    ],
                    "use_when": [
                        "research-heavy learning tasks",
                        "multi-source bug-bounty dedupe review",
                        "fresh market/regulatory comparison",
                    ],
                    "avoid_when": [
                        "one-second trading loop",
                        "routine coding-agent planning",
                        "simple chat or status checks",
                    ],
                },
                "safety_guardrail": {
                    "model": self.config.openrouter_safety_model,
                    "use_when": [
                        "pre/post-checking model output",
                        "screening high-impact automation prompts",
                        "normalizing risky tool requests before execution gates",
                    ],
                },
                "mid_june_model_recap": {
                    "source_date": "2026-06-17",
                    "default_route_change": "none_keep_local_first",
                    "free_or_eval_candidates": [
                        {
                            "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
                            "role": "large_free_evaluation_fallback",
                            "notes": "550B open-weight model; use as an evaluation fallback, not a one-second loop model.",
                        },
                        {
                            "model": "nvidia/nemotron-3.5-content-safety:free",
                            "role": "safety_guardrail",
                            "notes": "Free moderation/checking layer, not a general planner.",
                        },
                        {
                            "model": "nex-agi/nex-n2-pro:free",
                            "role": "agentic_free_advisor_candidate",
                            "notes": "Low-risk candidate for bounded advisor experiments.",
                        },
                    ],
                    "paid_candidates_operator_opt_in": [
                        {
                            "model": "qwen/qwen3.7-plus",
                            "role": "low_cost_1m_context_workhorse",
                            "price_per_million_tokens": {
                                "input_usd": 0.32,
                                "output_usd": 1.28,
                            },
                        },
                        {
                            "model": "moonshotai/kimi-k2.7-code",
                            "role": "long_context_coding_agent",
                            "context_tokens": 262000,
                            "price_per_million_tokens": {
                                "input_usd": 0.74,
                                "output_usd": 3.50,
                            },
                        },
                    ],
                },
                "server_tools_pattern": {
                    "advisor": {
                        "use": "Consult a stronger model only when the cheap path is stuck.",
                        "features": [
                            "multiple_named_advisors",
                            "memory_across_requests",
                            "streaming",
                        ],
                    },
                    "subagent": {
                        "use": "Delegate bounded routine subtasks to a smaller worker model.",
                    },
                    "fusion": {
                        "use": "Fan out deep research to a panel and synthesize agreement, conflict, and unique evidence.",
                        "invocation_modes": [
                            "direct_model_slug",
                            "server_tool_from_current_model",
                        ],
                    },
                },
                "cost_controls": {
                    "optimize_for": "cost_per_correct_answer",
                    "routing": [
                        "cheap_or_free_first",
                        "advisor_only_on_uncertainty",
                        "subagent_for_bounded_routine_work",
                        "fusion_only_for_research_heavy_questions",
                        "openrouter_default_load_balancing_for_provider_selection",
                    ],
                    "paid_route_controls": [
                        ":floor provider shortcut when a paid route is explicitly allowed",
                        ":nitro provider shortcut only when paid low-latency routing is explicitly allowed",
                        "max_price cap before raising model quality",
                        "Models API filters for price, modality, context, provider, and benchmark metadata",
                    ],
                    "auto_router_policy": (
                        "Research/benchmark candidate only; do not replace the local-first "
                        "planner without an explicit operator routing change."
                    ),
                },
            },
        }

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
            "github_codespaces",
            "n8n_local",
            "kali_wsl",
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
        hosted_sources = connected_inventory.get("additional_zapier_mcp_sources", [])
        if not isinstance(hosted_sources, list):
            hosted_sources = []
        hosted_zapier_available = any(
            isinstance(source, dict)
            and source.get("name") == "codex_hosted_zapier_mcp"
            and isinstance(source.get("apps"), list)
            and len(source.get("apps", [])) > 0
            for source in hosted_sources
        )
        zapier_inventory_available = zapier_app_count > 0 and zapier_action_count > 0
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
            zapier_inventory={
                "available": zapier_inventory_available,
                "hosted_available": hosted_zapier_available,
                "app_count": zapier_app_count,
                "action_count": zapier_action_count,
            },
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
            "zapier_inventory_available": zapier_inventory_available,
            "zapier_hosted_available": hosted_zapier_available,
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
                "integration probe: github_codespaces",
                "شغّل وكيل GitHub Codespaces للهدف الهندسي",
                "zapier action: <app>/<action> params:{...}",
                "حضّر مهمة GitHub Codespaces أو n8n أو Zapier MCP مع إيصال واضح",
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
        n8n_status_result = run_safe("n8n_status", "قراءة صحة n8n المحلي")
        n8n_workflows_result = run_safe("n8n_workflows", "قراءة workflows n8n المحلية")
        codespaces_agent = run_safe(
            "github_codespaces_agent",
            "تجهيز وكيل GitHub Codespaces الهندسي دون تنفيذ أوامر بعيدة",
            {
                "objective": prompt[:500],
                "mode": "read_only_audit",
                "limit": 10,
            },
        )
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
            "github_codespaces",
            "n8n_local",
            "kali_wsl",
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
                    "details": _agent_mesh_probe_details(probe_result.get("details")),
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
        zapier_direct_live_available = (
            bool(zapier_direct.get("live_available", zapier_direct.get("available")))
            if isinstance(zapier_direct, dict)
            else False
        )
        hosted_sources = (
            connected_inventory.get("additional_zapier_mcp_sources", [])
            if isinstance(connected_inventory, dict)
            else []
        )
        if not isinstance(hosted_sources, list):
            hosted_sources = []
        hosted_zapier_available = any(
            isinstance(source, dict)
            and source.get("name") == "codex_hosted_zapier_mcp"
            and isinstance(source.get("apps"), list)
            and len(source.get("apps", [])) > 0
            for source in hosted_sources
        )
        zapier_inventory_available = bool(
            (zapier_app_count or 0) > 0 and (zapier_action_count or 0) > 0
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
            zapier_inventory={
                "available": zapier_inventory_available,
                "hosted_available": hosted_zapier_available,
                "app_count": zapier_app_count,
                "action_count": zapier_action_count,
            },
            n8n_workflows=n8n_workflows_result
            if isinstance(n8n_workflows_result, dict)
            else {},
            kali={},
        )
        activation_plan = _agent_mesh_activation_plan(
            integration_probes=integration_probes,
            next_actions=next_actions,
            skipped_high_risk=skipped_high_risk,
        )
        operator_status = _agent_mesh_operator_status(
            safe_executions=safe_executions,
            failed_steps=failed_steps,
            skipped_high_risk=skipped_high_risk,
            integration_probes=integration_probes,
            zapier_inventory_available=zapier_inventory_available,
            zapier_direct_live_available=zapier_direct_live_available,
        )
        execution_command_center = _agent_mesh_execution_command_center(
            prompt=prompt,
            safe_executions=safe_executions,
            integration_probes=integration_probes,
            next_actions=next_actions,
            activation_plan=activation_plan,
            skipped_high_risk=skipped_high_risk,
            connected_inventory=connected_inventory
            if isinstance(connected_inventory, dict)
            else {},
            zapier_direct=zapier_direct if isinstance(zapier_direct, dict) else {},
            n8n_workflows=n8n_workflows_result
            if isinstance(n8n_workflows_result, dict)
            else {},
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
                "zapier_inventory_available": zapier_inventory_available,
                "zapier_hosted_available": hosted_zapier_available,
                "zapier_direct_oauth_connected": zapier_direct_connected,
                "zapier_direct_live_available": zapier_direct_live_available,
                "zapier_direct_needs_reconnect": bool(
                    zapier_direct.get("needs_reconnect")
                    if isinstance(zapier_direct, dict)
                    else False
                ),
                "zapier_direct_app_count": zapier_direct.get("app_count")
                if isinstance(zapier_direct, dict)
                else None,
                "zapier_direct_action_count": zapier_direct.get("action_count")
                if isinstance(zapier_direct, dict)
                else None,
                "zapier_direct_error": zapier_direct.get("error")
                if isinstance(zapier_direct, dict)
                else None,
                "codespaces_agent_status": codespaces_agent.get("status")
                if isinstance(codespaces_agent, dict)
                else None,
                "codespaces_agent_ready": codespaces_agent.get("agent_ready")
                if isinstance(codespaces_agent, dict)
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
            "activation_plan": activation_plan,
            "operator_status": operator_status,
            "execution_command_center": execution_command_center,
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
        raise ValueError(
            "agent_delegate is excluded in this FATHIYA build; use GitHub Codespaces, "
            "Zapier MCP, n8n, VS Code, Genspark Claw, or Bolt routes instead."
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
        if not target.exists() and str(args.get("path") or "").replace("\\", "/").startswith("audit/"):
            target = self._bounded_repo_path(f"knowledge/{args.get('path')}")
        if not target.exists():
            return {
                "query": query,
                "path": str(target),
                "matched": False,
                "execution_failed": False,
                "error": f"repo_search path does not exist: {target}",
                "command": None,
                "return_code": 1,
                "stdout": "",
                "stderr": "",
            }
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

    def _github_codespaces_inventory(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            limit = max(1, min(25, int(args.get("limit", 10))))
        except (TypeError, ValueError) as exc:
            raise ValueError("github_codespaces_inventory limit must be numeric") from exc
        executable = shutil.which("gh")
        if not executable:
            return {
                "installed": False,
                "available": False,
                "status": "unavailable",
                "authenticated": False,
                "codespace_count": 0,
                "active_codespace_count": 0,
                "codespaces": [],
                "execution_failed": False,
                "error": "GitHub CLI is not installed",
            }

        result = self._run(
            [
                executable,
                "codespace",
                "list",
                "--limit",
                str(limit),
                "--json",
                "name,displayName,repository,state,lastUsedAt",
            ],
            cwd=self.config.repo_root,
            timeout=45,
        )
        codespaces: list[dict[str, Any]] = []
        if result["return_code"] == 0:
            try:
                payload = json.loads(result["stdout"] or "[]")
            except json.JSONDecodeError:
                payload = []
            if isinstance(payload, list):
                for item in payload[:limit]:
                    if not isinstance(item, dict):
                        continue
                    repository = item.get("repository")
                    if isinstance(repository, dict):
                        repo_name = (
                            repository.get("nameWithOwner")
                            or repository.get("fullName")
                            or repository.get("name")
                        )
                    else:
                        repo_name = repository
                    name = str(item.get("displayName") or item.get("name") or "").strip()
                    state = str(item.get("state") or "unknown").strip()
                    codespaces.append(
                        {
                            "name": name[:160],
                            "repository": str(repo_name or "").strip()[:200],
                            "state": state,
                            "last_used_at": item.get("lastUsedAt"),
                        }
                    )
        active_count = sum(
            1
            for item in codespaces
            if str(item.get("state") or "").casefold()
            in {"active", "available", "running", "ready"}
        )
        available = result["return_code"] == 0
        stderr = str(result.get("stderr") or "")
        missing_scope = "codespace" if "needs the \"codespace\" scope" in stderr else ""
        needs_login = any(
            marker in stderr.casefold()
            for marker in (
                "gh auth login",
                "not logged",
                "failed to log in",
                "token in keyring is invalid",
                "to get started with github cli",
            )
        )
        auth_command = (
            "gh auth login -h github.com -p https -s repo,workflow,read:org,gist,codespace -w"
            if needs_login
            else "gh auth refresh -h github.com -s codespace"
            if missing_scope
            else None
        )
        auth_state = (
            "ready"
            if available
            else "missing_scope"
            if missing_scope
            else "not_logged_in"
            if needs_login
            else "unauthorized_or_unavailable"
            if result["return_code"] != 0
            else "unknown"
        )
        return {
            "installed": True,
            "available": available,
            "status": "active" if active_count else "ready" if available else "partial",
            "authenticated": available,
            "auth_state": auth_state,
            "missing_scope": missing_scope or None,
            "auth_command": auth_command,
            "operator_action_required": bool(missing_scope or needs_login),
            "codespace_count": len(codespaces),
            "active_codespace_count": active_count,
            "codespaces": codespaces,
            "execution_mode": "github_codespaces_remote_dev",
            "requires_approval": True,
            "read_only_inventory": True,
            "probe_failed": result["return_code"] != 0,
            "execution_failed": False,
            "error": stderr or None,
            "return_code": result["return_code"],
            "stdout": "",
            "stderr": stderr,
        }

    def _github_codespaces_agent(
        self,
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        objective = str(args.get("objective") or prompt or "").strip()[:1000]
        mode = str(args.get("mode") or "read_only_audit").strip()[:80]
        target_repository = str(
            args.get("target_repository") or args.get("repository") or ""
        ).strip()
        inventory = self._github_codespaces_inventory(
            "",
            {"limit": args.get("limit", 10)},
            context,
        )
        codespaces = (
            inventory.get("codespaces")
            if isinstance(inventory.get("codespaces"), list)
            else []
        )
        active_states = {"active", "available", "running", "ready"}
        target_key = target_repository.casefold()

        def matches_target(item: dict[str, Any]) -> bool:
            if not target_key:
                return True
            repository = str(item.get("repository") or "").casefold()
            name = str(item.get("name") or "").casefold()
            return target_key in repository or target_key in name

        matching = [item for item in codespaces if matches_target(item)]
        active_matching = [
            item
            for item in matching
            if str(item.get("state") or "").casefold() in active_states
        ]
        active_any = [
            item
            for item in codespaces
            if str(item.get("state") or "").casefold() in active_states
        ]
        selected = (
            active_matching[0]
            if active_matching
            else matching[0]
            if matching
            else active_any[0]
            if active_any
            else codespaces[0]
            if codespaces
            else None
        )
        installed = bool(inventory.get("installed"))
        available = bool(inventory.get("available"))
        agent_ready = bool(available and selected)
        blockers: list[str] = []
        if not installed:
            blockers.append("GitHub CLI غير مثبت أو غير ظاهر للمشغل المحلي.")
        elif not available:
            if inventory.get("auth_state") == "missing_scope":
                blockers.append(
                    "GitHub CLI يحتاج صلاحية Codespaces: gh auth refresh -h github.com -s codespace"
                )
            else:
                blockers.append("تعذر قراءة GitHub Codespaces من gh CLI.")
        elif not codespaces:
            blockers.append("لا توجد Codespaces ظاهرة للحساب المصادق.")
        elif target_repository and not matching:
            blockers.append(f"لا توجد Codespace مطابقة للمستودع: {target_repository}")

        selected_name = str(selected.get("name") or "") if selected else ""
        selected_repo = str(selected.get("repository") or "") if selected else ""
        dispatch_plan = [
            {
                "step": "inventory",
                "description": "قراءة Codespaces المتاحة عبر gh دون تنفيذ أوامر بعيدة.",
                "done": True,
            },
            {
                "step": "target",
                "description": (
                    f"استخدام Codespace: {selected_name} ({selected_repo})."
                    if selected
                    else "انتظار Codespace جاهزة أو صلاحية gh codespace."
                ),
                "done": bool(selected),
            },
            {
                "step": "remote_readiness",
                "description": (
                    "المرحلة التالية: تشغيل أوامر قراءة فقط داخل Codespace مثل git status واختبارات محددة بعد موافقة تشغيل بعيدة."
                ),
                "done": False,
            },
        ]
        return {
            "available": available or installed,
            "executed": True,
            "secret_safe": True,
            "action": "github_codespaces_agent_readiness",
            "status": "ready"
            if agent_ready
            else "partial"
            if installed
            else "needs_setup",
            "agent_ready": agent_ready,
            "mode": mode,
            "objective": objective,
            "target_repository": target_repository or selected_repo or None,
            "selected_codespace": selected,
            "codespace_count": inventory.get("codespace_count"),
            "active_codespace_count": inventory.get("active_codespace_count"),
            "authenticated": bool(inventory.get("authenticated")),
            "auth_state": inventory.get("auth_state"),
            "missing_scope": inventory.get("missing_scope"),
            "auth_command": inventory.get("auth_command"),
            "operator_action_required": bool(inventory.get("operator_action_required")),
            "remote_commands_executed": False,
            "requires_approval_for_remote_execution": True,
            "dispatch_plan": dispatch_plan,
            "next_prompt": (
                "شغّل وكيل GitHub Codespaces قراءة فقط: افحص git status والاختبارات المناسبة داخل Codespace ثم سجل إيصالًا."
            ),
            "blockers": blockers,
            "inventory_error": inventory.get("error"),
            "execution_failed": False,
        }

    def _web_fetch(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        url = self._requested_url(prompt, args)
        return self._fetch_url(url)

    def _production_site_audit(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        base_url = _production_base_url(prompt, args)
        routes = _production_audit_routes(args)
        captured_at = datetime.now(UTC).isoformat()
        headers = {
            "User-Agent": "FATHIYA-production-audit/1.0 read-only",
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        }
        checks: list[dict[str, Any]] = []
        for route in routes:
            url = urljoin(base_url.rstrip("/") + "/", route.lstrip("/"))
            started = time.monotonic()
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=8,
                    allow_redirects=True,
                )
                elapsed_ms = int((time.monotonic() - started) * 1000)
                text = response.text[:200_000]
                signals = _production_content_signals(text)
                checks.append(
                    {
                        "route": route,
                        "url": url,
                        "final_url": response.url,
                        "ok": bool(response.ok),
                        "status_code": response.status_code,
                        "elapsed_ms": elapsed_ms,
                        "content_type": response.headers.get("content-type"),
                        "character_count": len(response.text),
                        "title": _html_title(text),
                        "signals": signals,
                        "secret_safe": True,
                    }
                )
            except requests.RequestException as exc:
                checks.append(
                    {
                        "route": route,
                        "url": url,
                        "ok": False,
                        "status_code": None,
                        "elapsed_ms": int((time.monotonic() - started) * 1000),
                        "error": f"{type(exc).__name__}: {str(exc)[:240]}",
                        "signals": _production_content_signals(""),
                        "secret_safe": True,
                    }
                )

        reachable = any(bool(check.get("ok")) for check in checks)
        root_ok = any(check.get("route") == "/" and check.get("ok") for check in checks)
        agent_tasks_ok = any(
            str(check.get("route") or "").rstrip("/") == "/agent-tasks"
            and check.get("ok")
            for check in checks
        )
        identity_signal = any(
            check.get("signals", {}).get("fathiya_identity") for check in checks
        )
        focused_console_signal = any(
            check.get("signals", {}).get("focused_operator_console")
            for check in checks
        )
        command_signal = any(
            check.get("signals", {}).get("command_center") for check in checks
        )
        public_matches_local = bool(
            reachable
            and agent_tasks_ok
            and identity_signal
            and (focused_console_signal or command_signal)
        )
        if public_matches_local:
            status = "ready"
            summary = "الإنتاج يعرض مسار فتحية التشغيلي وفيه إشارات الهوية والأوامر."
        elif reachable:
            status = "partial"
            summary = (
                "الدومين يرد، لكن لا يوجد إثبات كاف أن صفحة فتحية التشغيلية "
                "الجديدة منشورة ومربوطة مثل المحلي."
            )
        else:
            status = "not_reachable"
            summary = "الدومين أو المسارات العامة لا ترد بنجاح من هذا المشغّل."

        next_actions = _production_audit_next_actions(
            root_ok=root_ok,
            agent_tasks_ok=agent_tasks_ok,
            identity_signal=identity_signal,
            focused_console_signal=focused_console_signal,
            command_signal=command_signal,
        )
        return {
            "available": True,
            "executed": True,
            "secret_safe": True,
            "read_only": True,
            "network_call": True,
            "base_url": base_url,
            "captured_at": captured_at,
            "status": status,
            "summary": summary,
            "public_matches_local": public_matches_local,
            "route_count": len(checks),
            "reachable_route_count": sum(1 for check in checks if check.get("ok")),
            "signals": {
                "root_ok": root_ok,
                "agent_tasks_ok": agent_tasks_ok,
                "fathiya_identity": identity_signal,
                "focused_operator_console": focused_console_signal,
                "command_center": command_signal,
                "local_api_bridge": True,
            },
            "checks": checks,
            "next_actions": next_actions,
        }

    def _knowledge_ingest_url(
        self,
        prompt: str,
        args: dict[str, Any],
        context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        fetched = self._web_fetch(prompt, args, context)
        if not fetched["ok"]:
            return {
                "ingested": False,
                "source": fetched["url"],
                "status_code": fetched["status_code"],
                "content_type": fetched["content_type"],
                "characters": 0,
                "warning": "source_fetch_failed",
                "error": fetched.get("error")
                or f"Cannot ingest URL with HTTP {fetched['status_code']}",
                "execution_failed": False,
            }
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

    def _learning_bootstrap(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sources = []
        errors: list[str] = []
        for url in _value_list(args.get("source_urls")) or re.findall(
            r"https?://[^\s`'\"<>]+",
            prompt,
        ):
            fetched = self._fetch_url(str(url))
            if fetched.get("ok"):
                sources.append(
                    make_learning_source(
                        str(url),
                        str(fetched.get("text") or ""),
                        url=str(fetched.get("url") or url),
                    )
                )
            else:
                errors.append(f"{url}: HTTP {fetched.get('status_code')}")

        for path_ref in _value_list(args.get("source_paths")):
            path = self._resolve_learning_source_path(str(path_ref))
            if not path:
                errors.append(f"{path_ref}: source path not found")
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{path_ref}: {type(exc).__name__}")
                continue
            sources.append(
                make_learning_source(
                    path.name,
                    text,
                    url=str(path),
                )
            )

        source_text = str(args.get("source_text") or "").strip()
        if source_text:
            sources.append(
                make_learning_source(
                    str(args.get("source_name") or "operator-source-text"),
                    source_text,
                )
            )

        if not sources:
            default_source = (
                self.config.sqlite_path.parent
                / "bugcrowd-work"
                / "FATHIYA_TRAINING_CORPUS_BOOTSTRAP_2026-06-16.md"
            )
            if default_source.exists():
                sources.append(
                    make_learning_source(
                        default_source.name,
                        default_source.read_text(encoding="utf-8"),
                        url=str(default_source),
                    )
                )
            else:
                sources.append(
                    make_learning_source(
                        "operator-learning-request",
                        prompt,
                    )
                )

        result = build_learning_session(
            self.config.knowledge_root / "learning",
            sources,
            title=str(args.get("title") or "Fathiya bug bounty learning bootstrap"),
            objective=str(
                args.get("objective")
                or "Teach Fathiya how to learn from DataCamp, training posts, Medium writeups, and triage feedback."
            ),
        )
        return {
            "available": True,
            "executed": True,
            "mode": "meta_learning_bootstrap",
            "errors": errors,
            **result,
        }

    def _medium_intelligence_pipeline(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        source_paths: list[Path] = []
        errors: list[str] = []
        for path_ref in _value_list(args.get("source_paths")):
            path = self._resolve_learning_source_path(str(path_ref))
            if path:
                source_paths.append(path)
            else:
                errors.append(f"{path_ref}: source path not found")
        source_urls = _value_list(args.get("source_urls")) or re.findall(
            r"https?://[^\s`'\"<>،]+",
            prompt,
        )
        fetch_live_raw = args.get("fetch_live", True)
        fetch_live = not (
            isinstance(fetch_live_raw, str)
            and fetch_live_raw.strip().casefold() in {"0", "false", "no", "off"}
        ) and bool(fetch_live_raw)
        try:
            max_items = int(args.get("max_items") or _prompt_field(prompt, "max_items") or 200)
        except (TypeError, ValueError):
            max_items = 200
        result = build_medium_intelligence_report(
            self.config.knowledge_root,
            source_urls=[str(url) for url in source_urls],
            source_text=str(args.get("source_text") or ""),
            source_paths=source_paths,
            title=str(args.get("title") or "FATHIYA Medium daily intelligence"),
            max_items=max_items,
            fetch_live=fetch_live,
        )
        if errors:
            result["errors"] = [*errors, *result.get("errors", [])]
        return result

    def _resolve_learning_source_path(self, value: str) -> Path | None:
        if not value.strip():
            return None
        raw = Path(value.strip().strip("`'\""))
        candidates = [raw] if raw.is_absolute() else []
        candidates.extend(
            [
                self.config.knowledge_root / raw,
                self.config.service_root / raw,
                self.config.repo_root / raw,
                self.config.sqlite_path.parent / raw,
            ]
        )
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if (
                resolved.is_file()
                and resolved.suffix.lower() in {".md", ".txt", ".json", ".csv"}
                and resolved.name.lower() not in {".env", ".env.local"}
            ):
                return resolved
        return None

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
                        "source": "http_health",
                        "endpoint": path,
                        "status_code": response.status_code,
                        "body": response.text[:500],
                        "version": version["stdout"].strip() or None,
                    }
                errors.append(f"{path}: HTTP {response.status_code}")
            except requests.RequestException as exc:
                errors.append(f"{path}: {exc}")
        command = _n8n_cli_command()
        version = self._run([command, "--version"], cwd=self.config.repo_root, timeout=10)
        if version.get("return_code") == 0:
            return {
                "available": True,
                "source": "local_cli",
                "version": str(version.get("stdout") or "").strip() or None,
                "errors": errors,
                "http_health_available": False,
            }
        errors.append(version.get("stderr") or "n8n CLI version check failed")
        return {"available": False, "errors": errors, "source": "unavailable"}

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
        refresh = bool(_args.get("refresh"))
        quick = bool(_args.get("quick"))
        inventory = json.loads(path.read_text(encoding="utf-8"))
        apps = _combined_zapier_apps(inventory)
        if quick and not self._capability_cache and not refresh:
            live_capabilities = {
                "available": True,
                "captured_at": None,
                "capabilities": [],
                "cached": True,
                "quick": True,
            }
        else:
            live_capabilities = self._local_capability_inventory(
                "",
                {"refresh": refresh},
                [],
            )
        local_tools = _merge_live_local_tools(
            inventory.get("local_tools", []),
            live_capabilities.get("capabilities", []),
        )
        agent_provider_actions = _visible_agent_provider_actions(
            inventory.get("agent_provider_actions", {})
        )
        return {
            "available": True,
            "quick": quick,
            "path": str(path),
            "captured_at": inventory.get("captured_at"),
            "live_captured_at": live_capabilities.get("captured_at"),
            "policy": inventory.get("policy", {}),
            "zapier_mcp_status": inventory.get("zapier_mcp_status", {}),
            "additional_zapier_mcp_sources": inventory.get(
                "additional_zapier_mcp_sources", []
            ),
            "local_tools": local_tools,
            "zapier_app_count": len(apps),
            "zapier_action_count": sum(int(app.get("action_count", 0)) for app in apps),
            "zapier_apps": apps,
            "agent_provider_actions": agent_provider_actions,
            "direct_zapier_mcp": self.zapier.status(),
        }

    def _agent_provider_probe(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        provider = str(args.get("provider") or args.get("app") or "").strip()
        inventory = self._connected_tool_inventory(
            "",
            {"refresh": bool(args.get("refresh")), "quick": True},
            [],
        )
        action_sets = inventory.get("agent_provider_actions")
        if not isinstance(action_sets, dict):
            action_sets = {}
        direct = (
            inventory.get("direct_zapier_mcp")
            if isinstance(inventory.get("direct_zapier_mcp"), dict)
            else {}
        )
        live_available = bool(direct.get("connected") and direct.get("direct_execution"))
        providers: list[dict[str, Any]] = []
        requested = provider.casefold()
        for app, action_set in action_sets.items():
            if not isinstance(action_set, dict):
                continue
            app_name = str(app).strip()
            if provider and app_name.casefold() != requested:
                continue
            read_actions = _string_list(action_set.get("read"))
            write_actions = _string_list(action_set.get("approval_gated_write"))
            catalog = self._zapier_action_catalog("", {"app": app_name}, [])
            catalog_actions = catalog.get("actions") if isinstance(catalog, dict) else []
            providers.append(
                {
                    "app": app_name,
                    "available": True,
                    "status": "ready" if live_available else "inventory_only",
                    "execution_mode": (
                        "live_zapier_mcp"
                        if live_available
                        else "inventory_only_until_oauth"
                    ),
                    "inventory_only": not live_available,
                    "read_count": len(read_actions),
                    "write_count": len(write_actions),
                    "total_actions": len(read_actions) + len(write_actions),
                    "read_actions": read_actions,
                    "write_actions": write_actions,
                    "catalog_actions": catalog_actions if isinstance(catalog_actions, list) else [],
                    "catalog_source": catalog.get("source") if isinstance(catalog, dict) else None,
                    "catalog_live_available": bool(catalog.get("live_available"))
                    if isinstance(catalog, dict)
                    else False,
                    "requires_oauth": not live_available,
                    "oauth_action_path": None if live_available else "/api/agent/oauth/zapier/start",
                    "next_step": (
                        f"{app_name} جاهز للتنفيذ عبر Zapier MCP؛ استخدم إجراء قراءة أو بوابة موافقة للكتابة."
                        if live_available
                        else f"{app_name} ظاهر في مخزون Zapier، لكن التنفيذ الحي ينتظر ربط OAuth المحلي."
                    ),
                }
            )
        if provider and not providers:
            return {
                "tool": "agent_provider_probe",
                "available": False,
                "provider": provider,
                "status": "not_found",
                "execution_mode": "missing_from_inventory",
                "providers": sorted(str(app) for app in action_sets),
                "error": "Agent provider is not visible in the connected tool inventory",
            }
        providers.sort(
            key=lambda item: (
                0 if item.get("status") == "ready" else 1,
                -int(item.get("total_actions") or 0),
                str(item.get("app") or "").casefold(),
            )
        )
        return {
            "tool": "agent_provider_probe",
            "available": bool(providers),
            "provider": provider or None,
            "status": "ready" if live_available else "inventory_only",
            "execution_mode": "live_zapier_mcp" if live_available else "inventory_only_until_oauth",
            "inventory_available": bool(action_sets),
            "live_available": live_available,
            "requires_oauth": not live_available,
            "oauth_action_path": None if live_available else "/api/agent/oauth/zapier/start",
            "provider_count": len(providers),
            "read_action_count": sum(int(item.get("read_count") or 0) for item in providers),
            "write_action_count": sum(int(item.get("write_count") or 0) for item in providers),
            "providers": providers,
            "next_step": (
                "اختر مزودًا وإجراء قراءة/كتابة من Zapier MCP."
                if live_available
                else "اربط Zapier OAuth المحلي لتحويل المزودين من مخزون إلى تنفيذ حي."
            ),
        }

    def _zapier_provider_info_from_catalog(
        self,
        provider: str,
        *,
        refresh: bool = False,
    ) -> dict[str, Any] | None:
        try:
            catalog = self._zapier_action_catalog(
                "",
                {"app": provider, "refresh": refresh},
                [],
            )
        except Exception:
            return None
        actions = catalog.get("actions") if isinstance(catalog.get("actions"), list) else []
        if not catalog.get("available") or not actions:
            return None
        read_actions: list[str] = []
        write_actions: list[str] = []
        for action in actions:
            if not isinstance(action, dict):
                continue
            name = str(action.get("name") or action.get("key") or "").strip()
            if not name:
                continue
            if str(action.get("mode") or "write") == "read":
                read_actions.append(name)
            else:
                write_actions.append(name)
        live_available = bool(catalog.get("live_available", catalog.get("connected")))
        app_name = str(catalog.get("app") or provider)
        return {
            "app": app_name,
            "available": True,
            "status": "ready" if live_available else "inventory_only",
            "execution_mode": (
                "live_zapier_mcp" if live_available else "inventory_only_until_oauth"
            ),
            "inventory_only": not live_available,
            "read_count": len(read_actions),
            "write_count": len(write_actions),
            "total_actions": len(read_actions) + len(write_actions),
            "read_actions": read_actions,
            "write_actions": write_actions,
            "catalog_actions": actions,
            "catalog_source": catalog.get("source"),
            "catalog_live_available": live_available,
            "requires_oauth": not live_available,
            "oauth_action_path": None if live_available else "/api/agent/oauth/zapier/start",
            "next_step": (
                f"{app_name} جاهز للتنفيذ عبر Zapier MCP؛ استخدم إجراء قراءة أو بوابة موافقة للكتابة."
                if live_available
                else f"{app_name} ظاهر في كتالوج Zapier، لكن التنفيذ الحي ينتظر ربط OAuth المحلي."
            ),
        }

    def _agent_provider_action_prepare(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        provider = str(args.get("provider") or args.get("app") or "").strip()
        if not provider:
            raise ValueError("agent_provider_action_prepare requires provider")
        action_hint = str(args.get("action") or args.get("action_hint") or "").strip()
        objective = str(args.get("objective") or prompt).strip()
        params = args.get("params")
        if not isinstance(params, dict):
            params = {}
        probe = self._agent_provider_probe(
            "",
            {"provider": provider, "refresh": bool(args.get("refresh"))},
            [],
        )
        providers = probe.get("providers") if isinstance(probe.get("providers"), list) else []
        provider_info = providers[0] if providers and isinstance(providers[0], dict) else None
        if not provider_info:
            provider_info = self._zapier_provider_info_from_catalog(
                provider,
                refresh=bool(args.get("refresh")),
            )
        if not provider_info:
            return {
                "tool": "agent_provider_action_prepare",
                "available": False,
                "provider": provider,
                "status": "not_found",
                "error": "Provider is not visible in the connected tool inventory or Zapier live catalog",
                "probe": probe,
            }
        selected = _select_agent_provider_action(provider_info, action_hint, objective)
        if not selected:
            return {
                "tool": "agent_provider_action_prepare",
                "available": False,
                "provider": provider_info.get("app") or provider,
                "status": "no_matching_action",
                "execution_mode": provider_info.get("execution_mode"),
                "requires_oauth": provider_info.get("requires_oauth"),
                "read_actions": provider_info.get("read_actions", []),
                "write_actions": provider_info.get("write_actions", []),
                "error": "No suitable provider action matched the objective",
            }
        app_name = str(provider_info.get("app") or provider)
        action_name = str(selected.get("name") or selected.get("action") or "")
        selected = self._enrich_zapier_selected_action(app_name, action_name, selected)
        mode = str(selected.get("mode") or "write")
        instructions = objective or f"Run {app_name} / {action_name} from FATHIYA."
        param_plan = _agent_provider_param_plan(selected, params)
        prepared_params = (
            param_plan.get("params")
            if isinstance(param_plan.get("params"), dict)
            else dict(params)
        )
        suggested_prompt = "\n".join(
            [
                f"Zapier action: {app_name} / {action_name}",
                (
                    "نفذ إجراء قراءة آمن من Zapier MCP عبر مشغل فتحية، ثم سجل التقدم والإيصال."
                    if mode == "read"
                    else "حضّر إجراء Zapier خارجي عبر مشغل فتحية وبوابة المخاطر، ولا ترسل أو تعدل شيئًا خارج الحساب قبل موافقة صريحة داخل المهمة."
                ),
                f"instructions: {instructions}",
                (
                    "param_status: ready"
                    if param_plan["ready"]
                    else "param_status: missing_required_params"
                ),
                f"required_params:{json.dumps(param_plan['required_params'], ensure_ascii=False)}",
                f"provided_params:{json.dumps(param_plan['provided_params'], ensure_ascii=False)}",
                f"missing_params:{json.dumps(param_plan['missing_params'], ensure_ascii=False)}",
                f"params:{json.dumps(prepared_params, ensure_ascii=False, sort_keys=True)}",
            ]
        )
        live_available = bool(
            probe.get("live_available")
            or provider_info.get("catalog_live_available")
            or provider_info.get("status") == "ready"
        )
        requires_approval = mode != "read"
        requires_oauth = bool(provider_info.get("requires_oauth", not live_available))
        return {
            "tool": "agent_provider_action_prepare",
            "available": True,
            "provider": app_name,
            "status": "prepared",
            "execution_mode": probe.get("execution_mode"),
            "live_available": live_available,
            "requires_oauth": requires_oauth,
            "requires_approval": requires_approval,
            "oauth_action_path": probe.get("oauth_action_path"),
            "selected_action": selected,
            "param_plan": param_plan,
            "params_ready": bool(param_plan["ready"]),
            "required_params": param_plan["required_params"],
            "optional_params": param_plan["optional_params"],
            "provided_params": param_plan["provided_params"],
            "missing_params": param_plan["missing_params"],
            "defaulted_params": param_plan["defaulted_params"],
            "zapier_action_args": {
                "app": app_name,
                "action": action_name,
                "params": prepared_params,
                "instructions": instructions,
            },
            "suggested_task": {
                "title": f"{'قراءة' if mode == 'read' else 'تشغيل'} {app_name}: {action_name}",
                "prompt": suggested_prompt,
            },
            "can_execute_now": live_available and not requires_approval and bool(param_plan["ready"]),
            "next_step": (
                f"أكمل الحقول المطلوبة أولًا: {', '.join(param_plan['missing_params'])}."
                if param_plan["missing_params"]
                else (
                "نفذ مهمة Zapier المقترحة الآن؛ الإجراء قراءة ولا يحتاج موافقة."
                if live_available and not requires_approval
                else "اربط Zapier OAuth المحلي أولًا، ثم نفذ المهمة المقترحة."
                if requires_oauth
                else "المهمة المقترحة جاهزة، وستمر عبر بوابة الموافقة قبل أي كتابة خارجية."
                )
            ),
        }

    def _enrich_zapier_selected_action(
        self,
        app_name: str,
        action_name: str,
        selected: dict[str, Any],
    ) -> dict[str, Any]:
        if not app_name or not action_name:
            return selected
        try:
            details = self._zapier_action_details(
                "",
                {"app": app_name, "action": action_name},
                [],
            )
        except Exception:
            return selected
        params = details.get("params") if isinstance(details.get("params"), list) else []
        required = _string_list(details.get("required_keys"))
        optional = [
            str(param.get("key") or "").strip()
            for param in params
            if isinstance(param, dict)
            and str(param.get("key") or "").strip()
            and str(param.get("key") or "").strip() not in required
        ]
        enriched = dict(selected)
        if required:
            enriched["required_params"] = required
        if optional:
            enriched["optional_params"] = optional
        for key in ("key", "tool_name", "mode"):
            if details.get(key) and not enriched.get(key):
                enriched[key] = details.get(key)
        return enriched

    def _zapier_action_catalog(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        app = str(args.get("app") or "")
        try:
            catalog = self.zapier.action_catalog(
                app,
                force=bool(args.get("refresh")),
            )
            if not catalog.get("available") and not catalog.get("apps"):
                return self._zapier_action_catalog_fallback(
                    app,
                    str(catalog.get("error") or "Zapier MCP live catalog is unavailable"),
                )
            return catalog
        except ZapierMCPError as exc:
            return self._zapier_action_catalog_fallback(app, str(exc))

    def _zapier_action_details(
        self,
        _prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        app = str(args.get("app") or "").strip()
        action = str(args.get("action") or "").strip()
        if not app or not action:
            raise ValueError("zapier_action_details requires app and action")
        return self.zapier.action_details(app, action)

    def _zapier_action_preflight(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        app = str(args.get("app") or "").strip()
        action = str(args.get("action") or "").strip()
        params = args.get("params")
        if not app or not action:
            raise ValueError("zapier_action_preflight requires app and action")
        if not isinstance(params, dict):
            params = {}
        catalog = self._zapier_action_catalog("", {"app": app}, [])
        actions = catalog.get("actions") if isinstance(catalog.get("actions"), list) else []
        selected = next(
            (
                item
                for item in actions
                if isinstance(item, dict)
                and _norm_action_name(str(item.get("name") or item.get("key") or ""))
                == _norm_action_name(action)
            ),
            None,
        )
        if not selected:
            return {
                "available": False,
                "connected": bool(catalog.get("connected")),
                "live_available": bool(catalog.get("live_available")),
                "inventory_available": bool(catalog.get("inventory_available")),
                "app": app,
                "action": action,
                "params_ready": False,
                "missing_params": [],
                "error": "Zapier action is not visible in the live or inventory catalog",
                "catalog_source": catalog.get("source"),
            }
        param_plan = _agent_provider_param_plan(selected, params)
        mode = str(selected.get("mode") or "write")
        requires_approval = mode != "read"
        live_available = bool(catalog.get("live_available"))
        requires_oauth = not live_available
        suggested_prompt = "\n".join(
            [
                f"Zapier action: {catalog.get('app') or app} / {selected.get('name') or action}",
                f"instructions: {str(args.get('instructions') or prompt)[:1200]}",
                (
                    "param_status: ready"
                    if param_plan["ready"]
                    else "param_status: missing_required_params"
                ),
                f"required_params:{json.dumps(param_plan['required_params'], ensure_ascii=False)}",
                f"provided_params:{json.dumps(param_plan['provided_params'], ensure_ascii=False)}",
                f"missing_params:{json.dumps(param_plan['missing_params'], ensure_ascii=False)}",
                f"params:{json.dumps(param_plan['params'], ensure_ascii=False, sort_keys=True)}",
            ]
        )
        return {
            "available": True,
            "connected": bool(catalog.get("connected")),
            "live_available": live_available,
            "inventory_available": bool(catalog.get("inventory_available")),
            "app": catalog.get("app") or app,
            "action": selected.get("name") or action,
            "selected_action": selected,
            "mode": mode,
            "requires_oauth": requires_oauth,
            "requires_approval": requires_approval,
            "oauth_action_path": "/api/agent/oauth/zapier/start" if requires_oauth else None,
            "params_ready": bool(param_plan["ready"]),
            "param_plan": param_plan,
            "required_params": param_plan["required_params"],
            "optional_params": param_plan["optional_params"],
            "provided_params": param_plan["provided_params"],
            "missing_params": param_plan["missing_params"],
            "defaulted_params": param_plan["defaulted_params"],
            "zapier_action_args": {
                "app": catalog.get("app") or app,
                "action": selected.get("name") or action,
                "params": param_plan["params"],
                "instructions": str(args.get("instructions") or prompt),
            },
            "suggested_task": (
                {
                    "title": f"تنفيذ Zapier: {catalog.get('app') or app} / {selected.get('name') or action}",
                    "prompt": suggested_prompt,
                }
                if param_plan["ready"]
                else None
            ),
            "can_execute_now": live_available and not requires_approval and bool(param_plan["ready"]),
            "next_step": (
                f"أكمل الحقول المطلوبة أولًا: {', '.join(param_plan['missing_params'])}."
                if param_plan["missing_params"]
                else "اربط Zapier OAuth المحلي أولًا، ثم نفذ الإجراء بعد الموافقة."
                if requires_oauth
                else "الإجراء جاهز للتنفيذ وسيخضع لبوابة الموافقة."
                if requires_approval
                else "الإجراء قراءة جاهز للتنفيذ الآن."
            ),
            "catalog_source": catalog.get("source"),
            "auth_state": catalog.get("auth_state"),
            "error": catalog.get("error"),
        }

    def _zapier_action_catalog_fallback(self, app: str, error: str) -> dict[str, Any]:
        status = self.zapier.status()
        last_refresh_error = str(status.get("last_refresh_error") or "")
        needs_reconnect = bool(
            status.get("connected")
            and (
                "401" in error
                or last_refresh_error in {"http_400", "http_401", "invalid_token_payload"}
            )
        )
        base: dict[str, Any] = {
            "available": False,
            "connected": bool(status.get("connected")),
            "provider": "Zapier MCP",
            "source": "connected_tool_inventory_fallback",
            "inventory_available": False,
            "live_available": False,
            "needs_reconnect": needs_reconnect,
            "refresh_recommended": bool(status.get("refresh_recommended")),
            "last_refresh_error": status.get("last_refresh_error"),
            "last_refresh_status_code": status.get("last_refresh_status_code"),
            "auth_state": (
                "reconnect_required"
                if needs_reconnect
                else "refresh_recommended"
                if status.get("refresh_recommended")
                else "connected_but_live_catalog_failed"
                if status.get("connected")
                else "not_connected"
            ),
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
                "inventory_available": True,
                "app": match.get("app"),
                "app_count": 1,
                "action_count": int(match.get("action_count") or 0),
                "actions": _zapier_inventory_action_samples(inventory, str(match.get("app") or "")),
                "apps": [match],
            }
        return {
            **base,
            "available": bool(apps),
            "inventory_available": bool(apps),
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
        timed_out = "timed out" in str(result.get("stderr") or "").lower()
        try:
            output = json.loads(result["stdout"])
        except json.JSONDecodeError:
            output = {"raw": result["stdout"][:8000]}
        if timed_out:
            output = {
                **output,
                "fallback": "security_core_timeout",
                "final_answer": (
                    "انتهت مهلة نواة الأمن المحلية؛ تم تسجيل ذلك كتحذير غير قاتل "
                    "حتى لا يسقط استيعاب المعرفة بالكامل."
                ),
                "question": question[:500],
            }
        return {
            "output": output,
            "execution_failed": result["return_code"] != 0 and not timed_out,
            "timed_out": timed_out,
            "error": result["stderr"] or None,
            "stderr": result["stderr"],
        }

    def _bug_bounty_static_review(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        workspace = self.config.sqlite_path.parent / "bugcrowd-work" / "static-review"
        repos_root = workspace / "repos"
        reports_root = workspace / "reports"
        repos_root.mkdir(parents=True, exist_ok=True)
        reports_root.mkdir(parents=True, exist_ok=True)

        repo_url = _prompt_field(prompt, "repo_url") or str(args.get("repo_url") or "").strip()
        platform = str(args.get("platform") or _prompt_field(prompt, "platform") or "").strip()
        program_url = str(
            args.get("program_url") or _prompt_field(prompt, "program_url") or ""
        ).strip()
        if not repo_url and _looks_like_github_repo_url(program_url):
            repo_url = program_url
        target_path = str(args.get("target_path") or _prompt_field(prompt, "target_path") or "").strip()
        program = (
            str(args.get("program") or _prompt_field(prompt, "program") or "").strip()
            or "Authorized Bugcrowd program"
        )
        scope_note = str(args.get("scope_note") or _prompt_field(prompt, "scope_note") or "").strip()
        knowledge_path = str(
            args.get("knowledge_path") or _prompt_field(prompt, "knowledge_path") or ""
        ).strip()
        if platform:
            scope_note = _append_scope_note(scope_note, f"platform={platform}")
        if program_url and program_url.casefold() != "auto":
            scope_note = _append_scope_note(scope_note, f"program_url={program_url}")
        if knowledge_path:
            scope_note = _append_scope_note(scope_note, f"knowledge_path={knowledge_path}")
        focus = str(args.get("focus") or _prompt_field(prompt, "focus") or prompt).strip()[:500]

        clone_result: dict[str, Any] | None = None
        if (
            not repo_url
            and _looks_like_http_url(program_url)
            and not _looks_like_github_repo_url(program_url)
            and _is_default_static_target_path(target_path)
        ):
            intake = self._passive_web_target_intake(program_url)
            report = _render_passive_web_target_report(
                program=program,
                program_url=program_url,
                scope_note=scope_note,
                focus=focus,
                intake=intake,
            )
            timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            report_slug = _slug(f"{program}-web-intake")[:90] or "bug-bounty-web-intake"
            report_path = reports_root / f"{timestamp}-{report_slug}.md"
            report_path.write_text(report, encoding="utf-8")
            return {
                "available": True,
                "executed": True,
                "mode": "web_url_passive_intake",
                "deliverable_type": "company_web_intake_report",
                "source_status": "no_source_repository",
                "safety": {
                    "live_scan": False,
                    "passive_http_fetch": True,
                    "external_submission": False,
                    "destructive_actions": False,
                },
                "program": program,
                "platform": platform or None,
                "program_url": program_url,
                "knowledge_path": knowledge_path or None,
                "repo_url": None,
                "repo_path": None,
                "scope_note": scope_note,
                "focus": focus,
                "candidate_count": 0,
                "top_candidates": [],
                "evidence_count": len(intake.get("observations", [])),
                "intake_summary": intake.get("summary"),
                "company_report_ready": bool(
                    (intake.get("summary") or {}).get("company_ready")
                    if isinstance(intake.get("summary"), dict)
                    else False
                ),
                "submission_gate": "not_vulnerability_submission",
                "report_path": str(report_path),
                "report_title": f"تقرير حضور ويب أولي لـ {program}",
                "clone": None,
                "external_upload_recommended": False,
            }
        if repo_url:
            owner, name = _github_repo_parts(repo_url)
            repo_path = repos_root / f"{owner}__{name}"
            if repo_path.exists():
                clone_result = {
                    "return_code": 0,
                    "stdout": "repository already exists; reused local checkout",
                    "stderr": "",
                    "command": [],
                }
            else:
                clone_result = self._run(
                    ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
                    cwd=repos_root,
                    timeout=180,
                )
                if clone_result["return_code"] != 0:
                    return {
                        "available": False,
                        "executed": False,
                        "mode": "static_read_only",
                        "repo_url": repo_url,
                        "execution_failed": True,
                        "error": clone_result["stderr"] or "git clone failed",
                        "clone": clone_result,
                    }
        else:
            repo_path = self._bug_bounty_target_path(target_path or ".")
            owner = repo_path.parent.name or "local"
            name = repo_path.name or "repository"

        candidates = self._static_review_candidates(repo_path)
        report = _render_static_bug_bounty_report(
            program=program,
            repo_url=repo_url or str(repo_path),
            repo_path=repo_path,
            scope_note=scope_note,
            focus=focus,
            candidates=candidates,
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        report_slug = _slug(f"{program}-{owner}-{name}")[:90] or "bug-bounty-static-review"
        report_path = reports_root / f"{timestamp}-{report_slug}.md"
        report_path.write_text(report, encoding="utf-8")

        top_candidates = candidates[:5]
        return {
            "available": True,
            "executed": True,
            "mode": "static_read_only",
            "safety": {
                "live_scan": False,
                "external_submission": False,
                "destructive_actions": False,
            },
            "program": program,
            "platform": platform or None,
            "program_url": None if program_url.casefold() == "auto" else program_url or None,
            "knowledge_path": knowledge_path or None,
            "repo_url": repo_url or None,
            "repo_path": str(repo_path),
            "scope_note": scope_note,
            "focus": focus,
            "candidate_count": len(candidates),
            "top_candidates": top_candidates,
            "report_path": str(report_path),
            "report_title": (
                top_candidates[0]["title"]
                if top_candidates
                else f"Static review notes for {program}"
            ),
            "clone": clone_result,
        }

    def _bug_bounty_draft_gate(
        self,
        prompt: str,
        args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        workspace = self.config.sqlite_path.parent / "bugcrowd-work" / "static-review"
        reports_root = workspace / "reports"
        drafts_root = workspace / "draft-gates"
        drafts_root.mkdir(parents=True, exist_ok=True)

        report_path = str(
            args.get("report_path") or _prompt_field(prompt, "report_path") or ""
        ).strip()
        report_path_overridden = False
        if report_path:
            report = Path(report_path)
        else:
            report = _latest_bug_bounty_static_report(reports_root)
        report = report.resolve()
        if not report.exists() or not report.is_file():
            if _can_fallback_to_latest_static_report(report_path):
                program_hint = str(
                    args.get("program") or _prompt_field(prompt, "program") or ""
                ).strip()
                report = _latest_bug_bounty_static_report(reports_root, program_hint)
                report_path_overridden = True
            else:
                raise ValueError("report_path must be an existing local report file")
        if reports_root.resolve() not in report.parents:
            if _can_fallback_to_latest_static_report(report_path):
                program_hint = str(
                    args.get("program") or _prompt_field(prompt, "program") or ""
                ).strip()
                report = _latest_bug_bounty_static_report(reports_root, program_hint)
                report_path_overridden = True
            else:
                raise ValueError("report_path must stay inside runtime bugcrowd-work reports")

        report_text = report.read_text(encoding="utf-8", errors="replace")
        program = (
            str(args.get("program") or _prompt_field(prompt, "program") or "").strip()
            or _field_from_static_report(report_text, "Program")
            or "Authorized Bugcrowd program"
        )
        requested_repo_path = str(
            args.get("repo_path") or _prompt_field(prompt, "repo_path") or ""
        ).strip()
        repo_path_overridden = False
        passive_web_report = _static_report_is_passive_web_intake(report_text)
        if _static_report_has_no_source_repository(report_text):
            repo = None
            if passive_web_report:
                validation = [
                    {
                        "id": "passive-web-intake-company-report",
                        "status": "company_report_ready",
                        "decision": "internal_company_report_only",
                        "reason": (
                            "The report is a bounded passive website intake. It is ready as "
                            "an internal/company web-presence report, not as an external "
                            "Bugcrowd/HackerOne vulnerability submission."
                        ),
                        "evidence": [],
                    }
                ]
            else:
                validation = [
                    {
                        "id": "source-repository-required",
                        "status": "not_submission_ready",
                        "decision": "no_source_repository",
                        "reason": (
                            "The operator provided a website URL without a source repository. "
                            "FATHIYA did not review the canonical target code and will not turn "
                            "local project heuristics into an external vulnerability report."
                        ),
                        "evidence": [],
                    }
                ]
        else:
            inferred_repo = _repo_path_from_static_report(report_text)
            if requested_repo_path:
                requested_repo = Path(requested_repo_path).resolve()
                try:
                    repo = self._validated_bug_bounty_repo_path(requested_repo, workspace)
                except ValueError:
                    repo = self._validated_bug_bounty_repo_path(inferred_repo, workspace)
                    repo_path_overridden = True
            else:
                repo = self._validated_bug_bounty_repo_path(inferred_repo, workspace)
            validation = self._validate_bug_bounty_draft(repo, report_text)
        external_ready = any(item["status"] == "submission_ready" for item in validation)
        company_report_ready = any(
            item["status"] == "company_report_ready" for item in validation
        )
        verdict = (
            "submission_ready"
            if external_ready
            else "company_report_ready"
            if company_report_ready
            else "not_submission_ready"
        )
        draft_text = _render_bug_bounty_draft_gate(
            program=program,
            report_path=report,
            repo_path=repo,
            validation=validation,
            verdict=verdict,
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        draft_path = drafts_root / f"{timestamp}-{_slug(program) or 'bugcrowd'}-draft-gate.md"
        draft_path.write_text(draft_text, encoding="utf-8")

        return {
            "available": True,
            "executed": True,
            "mode": "verified_draft_gate",
            "program": program,
            "report_path": str(report),
            "report_path_overridden": report_path_overridden,
            "repo_path": str(repo) if repo is not None else None,
            "repo_path_overridden": repo_path_overridden,
            "draft_path": str(draft_path),
            "draft_uploaded_inside_fathiya": True,
            "external_upload_performed": False,
            "external_upload_recommended": external_ready,
            "verdict": verdict,
            "deliverable_type": (
                "company_web_intake_report" if company_report_ready else "bug_bounty_draft_gate"
            ),
            "company_report_ready": company_report_ready,
            "validated_findings": validation,
            "safety": {
                "live_scan": False,
                "external_submission": False,
                "destructive_actions": False,
            },
        }

    def _validated_bug_bounty_repo_path(self, repo: Path, workspace: Path) -> Path:
        repo = repo.resolve()
        if not repo.exists() or not repo.is_dir():
            raise ValueError("repo_path must be an existing local repository directory")
        allowed_repos_root = (workspace / "repos").resolve()
        if allowed_repos_root not in repo.parents and repo != self.config.repo_root.resolve():
            raise ValueError("repo_path must stay inside runtime bugcrowd-work repos or the canonical repo")
        return repo

    def _passive_web_target_intake(self, program_url: str) -> dict[str, Any]:
        root = self._fetch_url(program_url)
        final_url = str(root.get("url") or program_url)
        parsed = urlparse(final_url)
        origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else program_url.rstrip("/")
        observations: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []
        for label, url in (
            ("home", final_url),
            ("robots.txt", urljoin(origin + "/", "robots.txt")),
            ("sitemap.xml", urljoin(origin + "/", "sitemap.xml")),
            ("manifest.json", urljoin(origin + "/", "manifest.json")),
            ("security.txt", urljoin(origin + "/", ".well-known/security.txt")),
        ):
            fetched = root if label == "home" else self._fetch_url(url)
            checks.append(
                {
                    "label": label,
                    "url": fetched.get("url") or url,
                    "ok": bool(fetched.get("ok")),
                    "status_code": fetched.get("status_code"),
                    "content_type": fetched.get("content_type") or "",
                    "characters": len(str(fetched.get("text") or "")),
                    "error": fetched.get("error"),
                }
            )
        home_text = str(root.get("text") or "")
        home_headers = root.get("headers") if isinstance(root.get("headers"), dict) else {}
        html_info = _extract_html_page_intel(home_text, final_url)
        security_headers = _summarize_security_headers(home_headers)
        if root.get("ok"):
            observations.append(
                {
                    "type": "http_homepage",
                    "label": "الصفحة الرئيسية استجابت",
                    "detail": f"HTTP {root.get('status_code')} · {root.get('content_type') or 'content-type غير معروف'}",
                }
            )
        else:
            observations.append(
                {
                    "type": "http_homepage_error",
                    "label": "تعذر جلب الصفحة الرئيسية",
                    "detail": str(root.get("error") or f"HTTP {root.get('status_code')}"),
                }
            )
        for key, label in (
            ("title", "عنوان الصفحة"),
            ("description", "وصف الصفحة"),
            ("canonical", "الرابط canonical"),
            ("generator", "مولد/منصة ظاهرة"),
        ):
            value = html_info.get(key)
            if value:
                observations.append({"type": key, "label": label, "detail": value})
        if html_info.get("app_links"):
            observations.append(
                {
                    "type": "app_links",
                    "label": "روابط تطبيقات محتملة",
                    "detail": "; ".join(html_info["app_links"][:6]),
                }
            )
        if html_info.get("external_domains"):
            observations.append(
                {
                    "type": "external_domains",
                    "label": "نطاقات خارجية ظاهرة",
                    "detail": ", ".join(html_info["external_domains"][:12]),
                }
            )
        for header_name, present in security_headers["presence"].items():
            observations.append(
                {
                    "type": "security_header",
                    "label": f"Security header: {header_name}",
                    "detail": "موجود" if present else "غير ظاهر في الرد الأولي",
                }
            )
        for check in checks[1:]:
            observations.append(
                {
                    "type": "well_known_resource",
                    "label": check["label"],
                    "detail": (
                        f"HTTP {check['status_code']} · {check['content_type']}"
                        if check["status_code"] is not None
                        else str(check.get("error") or "لا توجد استجابة")
                    ),
                }
            )
        summary = _classify_passive_web_presence(root, html_info, checks)
        return {
            "captured_at": datetime.now(UTC).isoformat(),
            "program_url": program_url,
            "final_url": final_url,
            "origin": origin,
            "checks": checks,
            "html": html_info,
            "security_headers": security_headers,
            "observations": observations,
            "summary": summary,
        }

    def _validate_bug_bounty_draft(
        self,
        repo_path: Path,
        report_text: str = "",
    ) -> list[dict[str, Any]]:
        candidates = _candidate_ids_from_static_report(report_text)
        if not candidates:
            candidates = [str(item.get("id") or "") for item in self._static_review_candidates(repo_path)]

        seen: set[str] = set()
        validation: list[dict[str, Any]] = []
        for candidate_id in candidates:
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            if candidate_id == "command-execution-sink":
                validation.append(self._validate_command_execution_candidate(repo_path))
            elif candidate_id == "ssrf-review-candidate":
                validation.append(self._validate_ssrf_candidate(repo_path))
            elif candidate_id == "xss-html-sink":
                validation.append(self._validate_xss_candidate(repo_path))
            elif candidate_id == "open-redirect-candidate":
                validation.append(self._validate_open_redirect_candidate(repo_path))
            elif candidate_id == "tls-or-jwt-validation-disabled":
                validation.append(self._validate_tls_jwt_candidate(repo_path))
            elif candidate_id == "path-traversal-candidate":
                validation.append(self._validate_path_traversal_candidate(repo_path))
            elif candidate_id == "archive-extraction-candidate":
                validation.append(self._validate_archive_extraction_candidate(repo_path))
            elif candidate_id == "deserialization-candidate":
                validation.append(self._validate_deserialization_candidate(repo_path))
            elif candidate_id == "codegen-injection-candidate":
                validation.append(self._validate_codegen_injection_candidate(repo_path))
            elif candidate_id == "android-deeplink-candidate":
                validation.append(self._validate_android_deeplink_candidate(repo_path))
            elif candidate_id == "webview-unsafe-config-candidate":
                validation.append(self._validate_webview_config_candidate(repo_path))
            elif candidate_id == "webview-js-string-injection-candidate":
                validation.append(self._validate_webview_js_string_candidate(repo_path))
            elif candidate_id == "ios-url-scheme-candidate":
                validation.append(self._validate_ios_url_scheme_candidate(repo_path))

        if validation:
            return validation
        return [
            {
                "id": "no-static-candidate-confirmed",
                "status": "not_submission_ready",
                "decision": "no_candidate",
                "reason": "The static review report did not contain a recognizable candidate that can be promoted to a Bugcrowd submission.",
                "evidence": [],
            }
        ]

    def _validate_command_execution_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"child_process\.(exec|execSync)|subprocess\.(Popen|run|call)|\bos\.system\b|shell\s*=\s*True|Runtime\.getRuntime\(\)\.exec",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        production_evidence = [
            row
            for row in evidence
            if not _path_has_any(row.get("path"), ("test", "tests", "devops", "scripts"))
        ]
        fixed_argument_evidence = [
            row
            for row in production_evidence
            if re.search(r"subprocess\.run\(\s*\[[^\]]+]", str(row.get("text") or ""))
        ]
        if production_evidence and not fixed_argument_evidence:
            decision = "needs_input_boundary_trace"
            reason = (
                "Command execution sinks exist in source code, but this bounded pass did not "
                "prove attacker-controlled arguments reach the command boundary."
            )
        elif production_evidence:
            decision = "fixed_argument_or_local_admin_path"
            reason = (
                "The source-level command execution evidence appears to use fixed argument "
                "arrays or local admin/helper flows; no attacker-controlled command fragment was proven."
            )
        else:
            decision = "test_or_devops_only"
            reason = (
                "Command execution matches were limited to tests, scripts, or developer tooling in this pass."
            )
        return {
            "id": "command-execution-sink",
            "status": "not_submission_ready",
            "decision": decision,
            "reason": reason,
            "evidence": evidence[:8],
        }

    def _validate_ssrf_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"requests\.(get|post|put)|axios\.(get|post)|Net::HTTP|http\.Get|URLSession|NSURLSession|transformTargetUrl|targetBaseUrl|fetchWithAuth|proxyPath",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        source_evidence = [
            row
            for row in evidence
            if not _path_has_any(row.get("path"), ("test", "tests", "docs", "examples"))
        ]
        fixed_endpoint_evidence = _production_static_rows(
            self._static_rg_scoped(
                repo_path,
                r"endpoint\.baseURL|relativeTo:\s*endpoint\.baseURL|baseURL\s*[:=]|case\s+production|case\s+sandbox|apiPath",
                exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
            )
        )
        if source_evidence and fixed_endpoint_evidence:
            decision = "fixed_or_sdk_configured_endpoint"
            reason = (
                "Network client usage exists, but this pass traced it to fixed or SDK-configured "
                "endpoint construction rather than an attacker-controlled upstream URL."
            )
        elif source_evidence:
            decision = "needs_controlled_url_source"
            reason = (
                "Server-side HTTP usage exists, but this pass did not prove that an attacker "
                "can control the upstream URL or reach internal network targets."
            )
        else:
            decision = "test_or_docs_only"
            reason = (
                "SSRF-like HTTP client matches were limited to tests, docs, or non-production examples in this pass."
            )
        return {
            "id": "ssrf-review-candidate",
            "status": "not_submission_ready",
            "decision": decision,
            "reason": reason,
            "evidence": (source_evidence or evidence)[:8],
            "source_trace": fixed_endpoint_evidence[:5] if fixed_endpoint_evidence else [],
        }

    def _validate_xss_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"dangerouslySetInnerHTML|innerHTML\s*=|insertAdjacentHTML|v-html|bypassSecurityTrustHtml|html_safe|mark_safe",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        source_evidence = [
            row
            for row in evidence
            if not _path_has_any(row.get("path"), ("test", "tests", "docs", "examples"))
        ]
        if source_evidence:
            decision = "needs_taint_proof"
            reason = (
                "HTML sink evidence exists in source code, but this pass did not prove an "
                "attacker-controlled value reaches the sink without encoding."
            )
        else:
            decision = "docs_or_test_only"
            reason = (
                "HTML-sink matches are in generated documentation, examples, or tests, and no source-path attacker-controlled sink was confirmed."
            )
        return {
            "id": "xss-html-sink",
            "status": "not_submission_ready",
            "decision": decision,
            "reason": reason,
            "evidence": evidence[:8],
        }

    def _validate_open_redirect_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"toSafeRedirect|returnTo\s*=|return_to|next_url|redirect\(|redirect_to|window\.location|location\.href",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        mitigation_evidence = [
            row
            for row in evidence
            if re.search(
                r"toSafeRedirect|same-origin|origin|allowlist|logged_out|clear_session",
                str(row.get("text") or ""),
                re.IGNORECASE,
            )
        ]
        if mitigation_evidence:
            decision = "downgraded_by_mitigation_or_fixed_destination"
            reason = (
                "Redirect-like code paths appear to use a sanitizer, same-origin check, or fixed "
                "destination; no attacker-controlled external redirect target was proven."
            )
        else:
            decision = "needs_external_destination_proof"
            reason = (
                "Redirect-like code paths were found, but this pass did not prove attacker control "
                "of an external destination with security impact."
            )
        return {
            "id": "open-redirect-candidate",
            "status": "not_submission_ready",
            "decision": decision,
            "reason": reason,
            "evidence": evidence[:8],
        }

    def _validate_tls_jwt_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"rejectUnauthorized\s*:\s*false|verify\s*=\s*False|verify_signature.*False|algorithms\s*=\s*\[?['\"]none",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        return {
            "id": "tls-or-jwt-validation-disabled",
            "status": "not_submission_ready",
            "decision": "needs_reachable_production_default",
            "reason": (
                "Potential disabled TLS or JWT validation requires proof that the setting is "
                "reachable in production defaults and affects an in-scope security boundary."
            ),
            "evidence": evidence[:8],
        }

    def _validate_path_traversal_candidate(self, repo_path: Path) -> dict[str, Any]:
        return self._validate_static_source_candidate(
            repo_path,
            "path-traversal-candidate",
            r"\bPath\.of\b|\bPaths\.get\b|new\s+File\s*\(|\bFile\s*\(|\bresolve\s*\(|\bnormalize\s*\(|canonicalPath|toRealPath|FileInputStream|FileOutputStream",
            source_decision="needs_attacker_controlled_path_trace",
            source_reason=(
                "File path construction or file IO evidence exists in source code, but this pass "
                "did not prove attacker-controlled path segments bypass a base-directory boundary."
            ),
            low_signal_decision="test_or_docs_only",
            low_signal_reason=(
                "Path traversal-like matches were limited to tests, docs, fixtures, or examples in this pass."
            ),
        )

    def _validate_archive_extraction_candidate(self, repo_path: Path) -> dict[str, Any]:
        return self._validate_static_source_candidate(
            repo_path,
            "archive-extraction-candidate",
            r"ZipInputStream|ZipFile|ZipEntry|TarArchiveInputStream|untar|unzip|extractTo|extract\(",
            source_decision="needs_zip_slip_trace",
            source_reason=(
                "Archive extraction evidence exists in source code, but this pass did not prove "
                "attacker-supplied archive entries can escape the extraction directory."
            ),
            low_signal_decision="test_or_docs_only",
            low_signal_reason=(
                "Archive extraction matches were limited to tests, docs, fixtures, or examples in this pass."
            ),
        )

    def _validate_deserialization_candidate(self, repo_path: Path) -> dict[str, Any]:
        return self._validate_static_source_candidate(
            repo_path,
            "deserialization-candidate",
            r"ObjectInputStream|readObject\(|pickle\.loads|yaml\.load\(|XMLDecoder|XStream|Kryo\(",
            source_decision="needs_untrusted_payload_trace",
            source_reason=(
                "Deserializer evidence exists in source code, but this pass did not prove untrusted "
                "attacker payloads reach the deserialization boundary."
            ),
            low_signal_decision="test_or_docs_only",
            low_signal_reason=(
                "Deserialization matches were limited to tests, docs, fixtures, or examples in this pass."
            ),
        )

    def _validate_codegen_injection_candidate(self, repo_path: Path) -> dict[str, Any]:
        return self._validate_static_source_candidate(
            repo_path,
            "codegen-injection-candidate",
            r"JavaPoet|KotlinPoet|writeTo\(|emitCode|Mustache|Freemarker|Velocity|Handlebars",
            source_decision="needs_untrusted_schema_or_template_trace",
            source_reason=(
                "Code-generation or templating evidence exists in source code, but this pass did "
                "not prove attacker-controlled schema/template content becomes executable or unsafe output."
            ),
            low_signal_decision="test_or_docs_only",
            low_signal_reason=(
                "Code-generation or templating matches were limited to tests, docs, fixtures, or examples in this pass."
            ),
        )

    def _validate_android_deeplink_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"android:exported|intent-filter|ACTION_VIEW|BROWSABLE|getQueryParameter|Uri\.parse|NavDeepLink",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        source_evidence = _production_static_rows(evidence)
        exported_true = any(
            re.search(r"android:exported\s*=\s*['\"]true", str(row.get("text") or ""), re.IGNORECASE)
            for row in source_evidence
        )
        exported_false = any(
            re.search(r"android:exported\s*=\s*['\"]false", str(row.get("text") or ""), re.IGNORECASE)
            for row in source_evidence
        )
        if not source_evidence:
            decision = "test_or_docs_only"
            reason = "Android deep link matches were limited to tests, docs, fixtures, or examples in this pass."
        elif exported_false and not exported_true:
            decision = "non_exported_or_server_supplied_flow"
            reason = (
                "Android intent/deep-link evidence exists, but the manifest evidence is non-exported "
                "and this pass did not prove attacker-controlled parameters cross an auth/payment boundary."
            )
        else:
            decision = "needs_untrusted_deeplink_trace"
            reason = (
                "Android deep link or intent-routing evidence exists, but this pass did not prove "
                "an exported route accepts attacker-controlled parameters that cross an auth/payment boundary."
            )
        return {
            "id": "android-deeplink-candidate",
            "status": "not_submission_ready",
            "decision": decision,
            "reason": reason,
            "evidence": source_evidence[:8] if source_evidence else evidence[:8],
        }

    def _validate_webview_config_candidate(self, repo_path: Path) -> dict[str, Any]:
        return self._validate_static_source_candidate(
            repo_path,
            "webview-unsafe-config-candidate",
            r"addJavascriptInterface|setJavaScriptEnabled\(\s*true|setAllowFileAccess\(\s*true|setAllowUniversalAccessFromFileURLs\(\s*true|loadDataWithBaseURL|loadUrl\(",
            source_decision="needs_untrusted_content_trace",
            source_reason=(
                "WebView-sensitive configuration evidence exists, but this pass did not prove "
                "untrusted web content can invoke a privileged bridge or load local files."
            ),
            low_signal_decision="test_or_docs_only",
            low_signal_reason=(
                "WebView-sensitive matches were limited to tests, docs, fixtures, or examples in this pass."
            ),
        )

    def _validate_webview_js_string_candidate(self, repo_path: Path) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            r"evaluateJavascript\(|evaluateJavaScript\(",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        source_evidence = _production_static_rows(evidence)
        interpolation_evidence = [
            row
            for row in source_evidence
            if re.search(
                r"openCheckout\(['\"]|postMessageToCheckout\(['\"]|evaluateJavaScript.*#\(",
                str(row.get("text") or ""),
                re.IGNORECASE,
            )
        ]
        merchant_callback_evidence = self._static_rg_scoped(
            repo_path,
            r"didCommenceCheckout|shippingAddressDidChange|shippingOptionDidChange|CheckoutV2Handler|TokenResult|typealias\s+Token\s*=\s*String",
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        merchant_callback_evidence = _production_static_rows(merchant_callback_evidence)
        if not source_evidence:
            decision = "debug_or_test_only"
            reason = (
                "WebView evaluateJavascript matches were limited to debug, docs, tests, fixtures, or examples in this pass."
            )
            local_repro = None
        elif interpolation_evidence and merchant_callback_evidence:
            decision = "locally_reproducible_but_merchant_controlled_source"
            reason = (
                "A single-quoted JavaScript interpolation pattern can be broken locally if a token "
                "or callback value contains a single quote, but the traced source is a merchant SDK "
                "callback/handler. This is not submission-ready without an external attacker-controlled source."
            )
            local_repro = _webview_js_single_quote_repro()
        else:
            decision = "needs_untrusted_js_string_trace"
            reason = (
                "WebView evaluateJavascript usage exists, but this pass did not prove untrusted "
                "data can break out of the JavaScript string context or invoke a privileged bridge."
            )
            local_repro = None
        result = {
            "id": "webview-js-string-injection-candidate",
            "status": "not_submission_ready",
            "decision": decision,
            "reason": reason,
            "evidence": (interpolation_evidence or source_evidence or evidence)[:8],
        }
        if local_repro:
            result["local_repro"] = local_repro
            result["source_trace"] = merchant_callback_evidence[:5]
        return result

    def _validate_ios_url_scheme_candidate(self, repo_path: Path) -> dict[str, Any]:
        return self._validate_static_source_candidate(
            repo_path,
            "ios-url-scheme-candidate",
            r"CFBundleURLSchemes|openURL|canOpenURL|application\\(_:open|WKWebView|evaluateJavaScript|loadHTMLString",
            source_decision="needs_untrusted_url_scheme_trace",
            source_reason=(
                "iOS URL scheme or WebView evidence exists, but this pass did not prove "
                "attacker-controlled input crosses an authentication, account, or payment boundary."
            ),
            low_signal_decision="test_or_docs_only",
            low_signal_reason=(
                "iOS URL scheme/WebView matches were limited to tests, docs, fixtures, or examples in this pass."
            ),
        )

    def _validate_static_source_candidate(
        self,
        repo_path: Path,
        candidate_id: str,
        query: str,
        *,
        source_decision: str,
        source_reason: str,
        low_signal_decision: str,
        low_signal_reason: str,
    ) -> dict[str, Any]:
        evidence = self._static_rg_scoped(
            repo_path,
            query,
            exclude_substrings=("node_modules", "dist", "build", "vendor", ".git"),
        )
        source_evidence = _production_static_rows(evidence)
        return {
            "id": candidate_id,
            "status": "not_submission_ready",
            "decision": source_decision if source_evidence else low_signal_decision,
            "reason": source_reason if source_evidence else low_signal_reason,
            "evidence": (source_evidence or evidence)[:8],
        }

    def _static_rg_scoped(
        self,
        repo_path: Path,
        query: str,
        *,
        include_globs: tuple[str, ...] = (),
        exclude_substrings: tuple[str, ...] = (),
    ) -> list[dict[str, Any]]:
        if not shutil.which("rg"):
            return []
        command = [
            "rg",
            "-n",
            "--ignore-case",
            "--max-count",
            "40",
        ]
        for glob in include_globs:
            command.extend(["--glob", glob])
        command.extend(["--", query, "."])
        result = self._run(command, cwd=repo_path, timeout=45)
        if result["return_code"] not in {0, 1}:
            return []
        rows = _parse_rg_lines(result["stdout"])
        if exclude_substrings:
            lowered_exclusions = tuple(item.casefold() for item in exclude_substrings)
            rows = [
                row
                for row in rows
                if not any(
                    excluded in str(row.get("path", "")).casefold()
                    for excluded in lowered_exclusions
                )
            ]
        return rows

    def _static_review_candidates(self, repo_path: Path) -> list[dict[str, Any]]:
        patterns = [
            {
                "id": "xss-html-sink",
                "title": "Potential HTML injection sink requires taint review",
                "vrt": "Client-Side Injection > Cross-Site Scripting (XSS)",
                "severity": "P3/P4 until exploitability is proven",
                "query": (
                    r"dangerouslySetInnerHTML|innerHTML\s*=|insertAdjacentHTML|"
                    r"v-html|bypassSecurityTrustHtml|html_safe|mark_safe"
                ),
                "why": "HTML sinks can become XSS when attacker-controlled values reach them without encoding.",
            },
            {
                "id": "command-execution-sink",
                "title": "Potential command execution sink requires input-boundary review",
                "vrt": "Server-Side Injection > Command Injection",
                "severity": "P2/P3 if user-controlled input reaches the sink",
                "query": (
                    r"child_process\.(exec|execSync)|subprocess\.(Popen|run|call)|"
                    r"\bos\.system\b|shell\s*=\s*True|Runtime\.getRuntime\(\)\.exec"
                ),
                "why": "Command execution sinks can become command injection when arguments include untrusted data.",
            },
            {
                "id": "open-redirect-candidate",
                "title": "Potential open redirect or unsafe navigation sink",
                "vrt": "Unvalidated Redirects and Forwards",
                "severity": "P4/P3 depending on auth or token impact",
                "query": r"res\.redirect|redirect_to|window\.location|location\.href|return_to|next_url",
                "why": "Redirect sinks need allowlist validation when they process user-controlled destinations.",
            },
            {
                "id": "tls-or-jwt-validation-disabled",
                "title": "Potential disabled TLS/JWT validation",
                "vrt": "Cryptographic Weakness",
                "severity": "P2/P3 if reachable in production defaults",
                "query": (
                    r"rejectUnauthorized\s*:\s*false|verify\s*=\s*False|"
                    r"verify_signature.*False|algorithms\s*=\s*\[?['\"]none"
                ),
                "why": "Disabled transport or token validation can break authentication or confidentiality.",
            },
            {
                "id": "ssrf-review-candidate",
                "title": "Potential server-side fetch boundary requires SSRF review",
                "vrt": "Server-Side Injection > Server-Side Request Forgery (SSRF)",
                "severity": "P3/P2 if user-controlled URL reaches internal networks",
                "query": r"requests\.(get|post|put)|axios\.(get|post)|Net::HTTP|http\.Get|URLSession|NSURLSession",
                "why": "Server-side HTTP clients need URL allowlists and internal-address protections.",
            },
            {
                "id": "path-traversal-candidate",
                "title": "Potential path traversal or unsafe file path boundary",
                "vrt": "Server-Side Injection > Path Traversal",
                "severity": "P3/P2 if attacker-controlled paths cross a trust boundary",
                "query": (
                    r"\bPath\.of\b|\bPaths\.get\b|new\s+File\s*\(|\bFile\s*\(|\bresolve\s*\(|\bnormalize\s*\(|"
                    r"canonicalPath|toRealPath|FileInputStream|FileOutputStream"
                ),
                "why": "File path construction needs base-directory validation when untrusted path fragments are accepted.",
            },
            {
                "id": "archive-extraction-candidate",
                "title": "Potential unsafe archive extraction boundary",
                "vrt": "Server-Side Injection > Path Traversal",
                "severity": "P3/P2 if attacker-supplied archives can write outside the extraction root",
                "query": r"ZipInputStream|ZipFile|ZipEntry|TarArchiveInputStream|untar|unzip|extractTo|extract\(",
                "why": "Archive extraction needs canonical path checks to prevent Zip Slip style traversal.",
            },
            {
                "id": "deserialization-candidate",
                "title": "Potential unsafe deserialization boundary",
                "vrt": "Server-Side Injection > Insecure Deserialization",
                "severity": "P2/P1 if untrusted payloads reach a dangerous deserializer",
                "query": r"ObjectInputStream|readObject\(|pickle\.loads|yaml\.load\(|XMLDecoder|XStream|Kryo\(",
                "why": "Deserialization of untrusted payloads can lead to object injection or code execution.",
            },
            {
                "id": "codegen-injection-candidate",
                "title": "Potential code generation or template injection boundary",
                "vrt": "Server-Side Injection > Code Injection",
                "severity": "P3/P2 if untrusted schemas/templates affect generated executable output",
                "query": (
                    r"JavaPoet|KotlinPoet|writeTo\(|emitCode|"
                    r"Mustache|Freemarker|Velocity|Handlebars"
                ),
                "why": "Code generation and template rendering need escaping when fed by untrusted schemas or templates.",
            },
            {
                "id": "android-deeplink-candidate",
                "title": "Potential Android deep link or exported intent boundary",
                "vrt": "Broken Access Control > Insecure Direct Object Reference (IDOR)",
                "severity": "P3/P2 if an exported route crosses auth, account, or payment boundaries",
                "query": (
                    r"android:exported|intent-filter|ACTION_VIEW|BROWSABLE|getQueryParameter|"
                    r"Uri\.parse|NavDeepLink"
                ),
                "why": "Deep links and exported intents need strict validation when parameters affect sensitive workflows.",
            },
            {
                "id": "webview-unsafe-config-candidate",
                "title": "Potential unsafe WebView bridge or local-file configuration",
                "vrt": "Client-Side Injection > WebView Injection",
                "severity": "P2/P1 if untrusted content can reach a privileged bridge or local files",
                "query": (
                    r"addJavascriptInterface|setJavaScriptEnabled\(\s*true|setAllowFileAccess\(\s*true|"
                    r"setAllowUniversalAccessFromFileURLs\(\s*true|loadDataWithBaseURL|loadUrl\("
                ),
                "why": "WebView bridge and file settings can become critical when exposed to attacker-controlled content.",
            },
            {
                "id": "webview-js-string-injection-candidate",
                "title": "Potential WebView JavaScript string injection boundary",
                "vrt": "Client-Side Injection > WebView Injection",
                "severity": "P2/P1 if untrusted data escapes into privileged WebView JavaScript",
                "query": r"evaluateJavascript\(",
                "why": "evaluateJavascript calls need JavaScript-context escaping when they interpolate data into executable strings.",
            },
            {
                "id": "ios-url-scheme-candidate",
                "title": "Potential iOS URL scheme or WebView input boundary",
                "vrt": "Broken Access Control > Improper Authorization",
                "severity": "P3/P2 if URL-controlled input crosses auth, account, or payment boundaries",
                "query": (
                    r"CFBundleURLSchemes|openURL|canOpenURL|application\\(_:open|"
                    r"WKWebView|evaluateJavaScript|loadHTMLString"
                ),
                "why": "iOS schemes and WebViews need strict input validation for account, payment, and auth flows.",
            },
        ]
        candidates: list[dict[str, Any]] = []
        for pattern in patterns:
            matches = self._static_rg(repo_path, pattern["query"])
            production_matches = _production_static_rows(matches)
            if not production_matches:
                continue
            evidence = production_matches[:8]
            candidates.append(
                {
                    "id": pattern["id"],
                    "title": pattern["title"],
                    "vrt": pattern["vrt"],
                    "severity": pattern["severity"],
                    "why": pattern["why"],
                    "match_count": len(production_matches),
                    "low_signal_match_count": len(matches) - len(production_matches),
                    "evidence": evidence,
                }
            )
        candidates.sort(key=lambda item: (item["severity"], -int(item["match_count"])))
        return candidates

    def _static_rg(self, repo_path: Path, query: str) -> list[dict[str, Any]]:
        if shutil.which("rg"):
            result = self._run(
                [
                    "rg",
                    "-n",
                    "--ignore-case",
                    "--max-count",
                    "40",
                    "--glob",
                    "!**/{node_modules,dist,build,vendor,.git}/**",
                    "--",
                    query,
                    ".",
                ],
                cwd=repo_path,
                timeout=45,
            )
            if result["return_code"] not in {0, 1}:
                return []
            return _parse_rg_lines(result["stdout"])
        result = self._run(
            ["git", "grep", "-n", "-I", "-E", query],
            cwd=repo_path,
            timeout=45,
        )
        if result["return_code"] not in {0, 1}:
            return []
        return _parse_rg_lines(result["stdout"])

    def _bug_bounty_target_path(self, requested: str) -> Path:
        target = Path(requested)
        if not target.is_absolute():
            target = self.config.repo_root / target
        target = target.resolve()
        allowed_roots = [
            self.config.repo_root.resolve(),
            (self.config.sqlite_path.parent / "bugcrowd-work").resolve(),
        ]
        if not any(target == root or root in target.parents for root in allowed_roots):
            raise ValueError("Static review target must stay inside the repo or runtime bugcrowd-work")
        if not target.exists() or not target.is_dir():
            raise ValueError("Static review target_path must be an existing directory")
        return target

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
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "FATHIYA-Agent-Runtime/1.0"},
                timeout=30,
                allow_redirects=True,
                stream=True,
            )
        except requests.RequestException as exc:
            return {
                "ok": False,
                "url": url,
                "status_code": None,
                "content_type": "",
                "truncated": False,
                "text": "",
                "execution_failed": False,
                "error": f"{type(exc).__name__}: {exc}",
            }
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
        public_headers = {
            str(key).lower(): str(value)[:500]
            for key, value in response.headers.items()
            if str(key).lower() not in {"set-cookie", "cookie", "authorization"}
        }
        return {
            "ok": response.ok,
            "url": response.url,
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "headers": public_headers,
            "truncated": size >= 200_000,
            "text": raw.decode(encoding, errors="replace"),
            "execution_failed": False,
            "error": None,
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


def _is_visible_agent_provider_app(app: str) -> bool:
    normalized = app.strip().casefold()
    return bool(normalized) and normalized not in EXCLUDED_AGENT_PROVIDER_APPS


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _has_action_param_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _agent_provider_param_plan(
    selected_action: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    required = _string_list(selected_action.get("required_params"))
    optional = _string_list(selected_action.get("optional_params"))
    defaults = (
        dict(selected_action.get("defaults"))
        if isinstance(selected_action.get("defaults"), dict)
        else {}
    )
    prepared_params = dict(params)
    defaulted: dict[str, Any] = {}
    known_params = set(required) | set(optional)
    for key, value in defaults.items():
        param_name = str(key).strip()
        if not param_name or (known_params and param_name not in known_params):
            continue
        if not _has_action_param_value(prepared_params.get(param_name)):
            prepared_params[param_name] = value
            defaulted[param_name] = value
    missing = [
        param
        for param in required
        if not _has_action_param_value(prepared_params.get(param))
    ]
    provided = sorted(
        str(key)
        for key, value in prepared_params.items()
        if _has_action_param_value(value)
    )
    return {
        "ready": not missing,
        "params": prepared_params,
        "required_params": required,
        "optional_params": optional,
        "provided_params": provided,
        "missing_params": missing,
        "defaulted_params": defaulted,
        "dynamic_properties_depends_on": _string_list(
            selected_action.get("dynamic_properties_depends_on")
        ),
    }


def _select_agent_provider_action(
    provider_info: dict[str, Any],
    action_hint: str,
    objective: str,
) -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    catalog_actions = (
        provider_info.get("catalog_actions")
        if isinstance(provider_info.get("catalog_actions"), list)
        else []
    )
    by_name: dict[str, dict[str, Any]] = {}
    for item in catalog_actions:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("key") or "").strip()
        if name:
            by_name[_norm_action_name(name)] = item
    for mode, key in (("read", "read_actions"), ("write", "write_actions")):
        for action in _string_list(provider_info.get(key)):
            catalog_item = by_name.get(_norm_action_name(action), {})
            candidates.append(
                {
                    "name": action,
                    "key": catalog_item.get("key"),
                    "tool_name": catalog_item.get("tool_name"),
                    "mode": catalog_item.get("mode") or mode,
                    "inventory_only": bool(catalog_item.get("inventory_only", True)),
                    "required_params": _string_list(
                        catalog_item.get("required_params")
                    ),
                    "optional_params": _string_list(
                        catalog_item.get("optional_params")
                    ),
                    "dynamic_properties_depends_on": _string_list(
                        catalog_item.get("dynamic_properties_depends_on")
                    ),
                    "defaults": (
                        dict(catalog_item.get("defaults"))
                        if isinstance(catalog_item.get("defaults"), dict)
                        else {}
                    ),
                    "notes": str(catalog_item.get("notes") or "").strip(),
                }
            )
    if not candidates:
        return None
    text = f"{action_hint}\n{objective}".casefold()
    app = str(provider_info.get("app") or "").casefold()

    def score(candidate: dict[str, Any]) -> int:
        name = str(candidate.get("name") or "")
        normalized = _norm_action_name(name)
        value = 0
        if action_hint and _norm_action_name(action_hint) == normalized:
            value += 100
        if action_hint and _norm_action_name(action_hint) in normalized:
            value += 70
        if name.casefold() in text:
            value += 60
        if "delete" in normalized or "حذف" in text and "delete" in normalized:
            value -= 80
        if any(term in text for term in ("launch", "run", "start", "execute", "شغل", "شغّل", "تشغيل", "نفذ", "ابدأ")):
            if any(term in normalized for term in ("launch", "run", "start", "create", "send prompt", "conversation")):
                value += 45
        if any(term in text for term in ("create", "new", "task", "انشئ", "أنشئ", "مهمة")):
            if any(term in normalized for term in ("create", "task", "launch", "run")):
                value += 35
        if any(term in text for term in ("continue", "follow", "followup", "كمل", "تابع")):
            if any(term in normalized for term in ("continue", "followup", "add followup", "update")):
                value += 45
        if any(term in text for term in ("status", "find", "get", "read", "افحص", "حالة", "اقرأ")):
            if any(term in normalized for term in ("status", "find", "get", "make api get")):
                value += 40
        if app == "agents" and normalized == "run agent":
            value += 30
        if "netlify" in app and normalized == "start deploy":
            value += 30
        if "apify" in app and normalized == "run actor":
            value += 20
        if "chatgpt" in app and normalized in {"send prompt", "conversation"}:
            value += 20
        if str(candidate.get("mode")) == "read":
            value += 2
        return value

    selected = max(candidates, key=score)
    if score(selected) <= 0:
        return candidates[0]
    return selected


def _norm_action_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _visible_agent_provider_actions(actions: Any) -> dict[str, Any]:
    if not isinstance(actions, dict):
        return {}
    return {
        str(app): action_set
        for app, action_set in actions.items()
        if _is_visible_agent_provider_app(str(app))
    }


def _combined_zapier_apps(inventory: dict[str, Any]) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}

    def absorb(apps: Any, source: str) -> None:
        if not isinstance(apps, list):
            return
        for item in apps:
            if not isinstance(item, dict) or not item.get("app"):
                continue
            name = str(item["app"])
            if not _is_visible_agent_provider_app(name):
                continue
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


def _zapier_inventory_action_samples(
    inventory: dict[str, Any],
    app: str,
) -> list[dict[str, Any]]:
    requested = app.strip().casefold()
    if not requested:
        return []
    actions: list[dict[str, Any]] = []

    def absorb_schemas(schemas: Any) -> None:
        if not isinstance(schemas, dict):
            return
        for schema_app, action_defs in schemas.items():
            if str(schema_app).strip().casefold() != requested:
                continue
            if not isinstance(action_defs, list):
                continue
            for item in action_defs:
                if not isinstance(item, dict):
                    continue
                action_name = str(item.get("name") or "").strip()
                if not action_name:
                    continue
                key = str(item.get("key") or "").strip()
                slug = re.sub(r"[^a-z0-9]+", "_", action_name.casefold()).strip("_")
                mode_text = str(item.get("mode") or "").casefold()
                mode = "read" if mode_text == "read" else "write"
                tool_name = str(item.get("tool_name") or "").strip()
                params = item.get("params")
                action: dict[str, Any] = {
                    "key": key or slug or action_name,
                    "name": action_name,
                    "tool_name": tool_name
                    or f"inventory_only:{key or slug or action_name}",
                    "mode": mode,
                    "inventory_only": True,
                    "inventory_schema": True,
                    "required_params": _string_list(item.get("required_params")),
                    "optional_params": _string_list(item.get("optional_params")),
                    "dynamic_properties_depends_on": _string_list(
                        item.get("dynamic_properties_depends_on")
                    ),
                }
                if isinstance(params, list):
                    action["params"] = params
                defaults = item.get("defaults")
                if isinstance(defaults, dict):
                    action["defaults"] = defaults
                notes = str(item.get("notes") or "").strip()
                if notes:
                    action["notes"] = notes
                actions.append(action)

    def absorb(samples: Any) -> None:
        if not isinstance(samples, dict):
            return
        for sample_app, action_sets in samples.items():
            if str(sample_app).strip().casefold() != requested:
                continue
            if not isinstance(action_sets, dict):
                continue
            for sample_mode, names in action_sets.items():
                if not isinstance(names, list):
                    continue
                mode = "read" if str(sample_mode).casefold() == "read" else "write"
                for name in names:
                    if not isinstance(name, str) or not name.strip():
                        continue
                    action_name = name.strip()
                    key = re.sub(r"[^a-z0-9]+", "_", action_name.casefold()).strip("_")
                    actions.append(
                        {
                            "key": key or action_name,
                            "name": action_name,
                            "tool_name": f"inventory_only:{key or action_name}",
                            "mode": mode,
                            "inventory_only": True,
                        }
                    )

    absorb(inventory.get("action_samples"))
    absorb_schemas(inventory.get("action_schemas"))
    for source in inventory.get("additional_zapier_mcp_sources", []):
        if isinstance(source, dict):
            absorb(source.get("action_samples"))
            absorb_schemas(source.get("action_schemas"))
    deduped: dict[tuple[str, str], dict[str, Any]] = {}
    for action in actions:
        key = (str(action["name"]).casefold(), str(action["mode"]))
        existing = deduped.get(key)
        has_schema = bool(
            action.get("inventory_schema")
            or action.get("params")
            or action.get("required_params")
            or action.get("optional_params")
            or action.get("dynamic_properties_depends_on")
        )
        existing_has_schema = bool(
            existing
            and (
                existing.get("inventory_schema")
                or existing.get("params")
                or existing.get("required_params")
                or existing.get("optional_params")
                or existing.get("dynamic_properties_depends_on")
            )
        )
        if existing is None or (has_schema and not existing_has_schema):
            deduped[key] = action
    return list(deduped.values())


def _merge_live_local_tools(
    inventory_tools: Any,
    live_capabilities: Any,
) -> list[dict[str, Any]]:
    static_tools = [
        dict(item)
        for item in inventory_tools
        if isinstance(item, dict)
        and _is_visible_agent_provider_app(str(item.get("app") or ""))
    ]
    static_by_app = {
        str(item.get("app") or "").casefold(): item
        for item in static_tools
    }
    capability_names = {
        "github_cli": "GitHub CLI",
        "github_codespaces": "GitHub Codespaces",
        "docker": "Docker",
        "n8n": "n8n",
        "kali_wsl": "Kali Linux WSL",
        "zapier_mcp": "Zapier MCP",
        "huggingface_local": "Hugging Face",
        "openrouter": "OpenRouter",
        "trading_primary": "Primary Trading Agent",
    }
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    if isinstance(live_capabilities, list):
        for capability in live_capabilities:
            if not isinstance(capability, dict):
                continue
            capability_id = str(capability.get("id") or "").strip()
            app = capability_names.get(capability_id) or str(
                capability.get("name") or capability_id or ""
            ).strip()
            if not _is_visible_agent_provider_app(app):
                continue
            key = app.casefold()
            existing = static_by_app.get(key, {})
            live = {
                **existing,
                "app": app,
                "id": capability_id or existing.get("id"),
                "status": capability.get("status", existing.get("status")),
                "available": capability.get("available", existing.get("available")),
                "installed": capability.get("installed", existing.get("installed")),
                "authenticated": capability.get(
                    "authenticated",
                    existing.get("authenticated"),
                ),
                "version": capability.get("version", existing.get("version")),
                "execution_mode": capability.get(
                    "execution_mode",
                    existing.get("execution_mode"),
                ),
                "requires_approval": capability.get(
                    "requires_approval",
                    existing.get("requires_approval"),
                ),
                "runtime_live": True,
            }
            for optional_key in (
                "daemon_running",
                "tool_count",
                "missing_tool_count",
                "symbol",
                "live_execution_enabled",
                "testnet_configured",
                "testnet_execution_enabled",
                "zapier_ready",
            ):
                if optional_key in capability:
                    live[optional_key] = capability[optional_key]
            if capability_id == "openrouter":
                live["note"] = (
                    "OPENROUTER_API_KEY موجود محليًا؛ التخطيط والتقييم بالنماذج الثقيلة جاهزان عند طلب الوكيل."
                    if live.get("available")
                    else existing.get("note")
                )
            if capability_id == "huggingface_local":
                live["note"] = (
                    "النماذج المحلية مفعلة للاسترجاع أو التوليد داخل المشغّل."
                    if live.get("available")
                    else existing.get("note")
                )
            merged.append(live)
            seen.add(key)
    for item in static_tools:
        key = str(item.get("app") or "").casefold()
        if key not in seen:
            merged.append({**item, "runtime_live": False})
    return merged


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


def _prompt_field(prompt: str, field: str) -> str:
    match = re.search(
        rf"^[^\S\r\n]*{re.escape(field)}[^\S\r\n]*:[^\S\r\n]*([^\r\n]*)$",
        prompt,
        re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def _append_scope_note(current: str, note: str) -> str:
    clean = note.strip()
    if not clean:
        return current
    if not current:
        return clean
    if clean in current:
        return current
    return f"{current}; {clean}"


def _value_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        return [
            item.strip()
            for item in re.split(r"[\n,]+", stripped)
            if item.strip()
        ]
    return [str(value).strip()] if str(value).strip() else []


def _looks_like_github_repo_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    parts = [part for part in parsed.path.split("/") if part]
    return host in {"github.com", "www.github.com"} and len(parts) >= 2


def _github_repo_parts(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url)
    host = (parsed.hostname or "").casefold()
    if parsed.scheme not in {"http", "https"} or host not in {"github.com", "www.github.com"}:
        raise ValueError("bug_bounty_static_review only clones https://github.com repositories")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub repository URL must include owner and repository")
    owner = re.sub(r"[^A-Za-z0-9_.-]+", "-", parts[0]).strip("-")
    name = re.sub(r"[^A-Za-z0-9_.-]+", "-", parts[1].removesuffix(".git")).strip("-")
    if not owner or not name:
        raise ValueError("GitHub repository owner and name are required")
    return owner, name


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()


def _parse_rg_lines(value: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in value.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        path, line_no, text = parts
        if len(text.strip()) < 3:
            continue
        rows.append(
            {
                "path": path,
                "line": line_no,
                "text": text.strip()[:500],
            }
        )
    return rows


def _field_from_static_report(report_text: str, field: str) -> str:
    match = re.search(
        rf"^\s*-\s*{re.escape(field)}\s*:\s*(.+?)\s*$",
        report_text,
        re.IGNORECASE | re.MULTILINE,
    )
    return match.group(1).strip() if match else ""


def _latest_bug_bounty_static_report(reports_root: Path, program_hint: str = "") -> Path:
    reports = sorted(
        reports_root.glob("*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not reports:
        raise ValueError("No local Bugcrowd static-review report was found")
    hint_slug = _slug(program_hint)
    if hint_slug:
        for report in reports:
            if hint_slug in report.name:
                return report.resolve()
    return reports[0].resolve()


def _can_fallback_to_latest_static_report(report_path: str) -> bool:
    if not report_path:
        return True
    requested = Path(report_path)
    if not requested.is_absolute():
        return True
    placeholder_names = {
        "static_review_draft.md",
        "static-review-draft.md",
        "static_review_report.md",
        "static-review-report.md",
        "static_report.md",
        "static-report.md",
        "report.md",
        "draft.md",
    }
    return requested.name.casefold() in placeholder_names


def _looks_like_http_url(value: str) -> bool:
    if not value:
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_default_static_target_path(value: str) -> bool:
    clean = (value or "").strip().replace("\\", "/").rstrip("/")
    return clean in {"", "."}


def _static_report_has_no_source_repository(report_text: str) -> bool:
    return bool(
        re.search(
            r"^\s*-\s*Source repository status\s*:\s*no_source_repository\s*$",
            report_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )


def _static_report_is_passive_web_intake(report_text: str) -> bool:
    return bool(
        re.search(
            r"^\s*-\s*Mode\s*:\s*web URL passive intake\.?\s*$",
            report_text,
            re.IGNORECASE | re.MULTILINE,
        )
    )


def _extract_html_page_intel(text: str, page_url: str) -> dict[str, Any]:
    html_text = text[:200_000]
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html_text, re.IGNORECASE | re.DOTALL)
    title = _clean_html_value(title_match.group(1)) if title_match else ""
    description = ""
    generator = ""
    canonical = ""
    for tag in re.findall(r"<meta\b[^>]*>", html_text, re.IGNORECASE):
        attrs = _html_tag_attrs(tag)
        name = str(attrs.get("name") or attrs.get("property") or "").casefold()
        content = str(attrs.get("content") or "").strip()
        if not content:
            continue
        if name in {"description", "og:description", "twitter:description"} and not description:
            description = _clean_html_value(content)
        elif name == "generator" and not generator:
            generator = _clean_html_value(content)
    app_links: list[str] = []
    external_domains: set[str] = set()
    page_host = (urlparse(page_url).hostname or "").casefold()
    for tag in re.findall(r"<link\b[^>]*>", html_text, re.IGNORECASE):
        attrs = _html_tag_attrs(tag)
        rel = str(attrs.get("rel") or "").casefold()
        href = str(attrs.get("href") or "").strip()
        if not href:
            continue
        absolute = urljoin(page_url, href)
        if "canonical" in rel and not canonical:
            canonical = absolute
        if any(term in rel for term in ("manifest", "apple-touch-icon", "alternate")):
            app_links.append(absolute)
    for raw in re.findall(r"""(?:href|src)\s*=\s*["']([^"']+)["']""", html_text, re.IGNORECASE):
        absolute = urljoin(page_url, raw.strip())
        parsed = urlparse(absolute)
        host = (parsed.hostname or "").casefold()
        if not host:
            continue
        if host != page_host and not host.endswith(f".{page_host}"):
            external_domains.add(host)
        if any(marker in absolute.casefold() for marker in ("play.google.com", "apps.apple.com", "itunes.apple.com", ".apk")):
            app_links.append(absolute)
    deduped_app_links = []
    seen_links: set[str] = set()
    for link in app_links:
        if link not in seen_links:
            seen_links.add(link)
            deduped_app_links.append(link)
    return {
        "title": title,
        "description": description,
        "generator": generator,
        "canonical": canonical,
        "app_links": deduped_app_links[:20],
        "external_domains": sorted(external_domains)[:40],
    }


def _html_tag_attrs(tag: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for match in re.finditer(
        r"""([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""",
        tag,
    ):
        key = match.group(1).casefold()
        value = next(group for group in match.groups()[1:] if group is not None)
        attrs[key] = html.unescape(value.strip())
    return attrs


def _clean_html_value(value: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", value)
    clean = html.unescape(clean)
    return " ".join(clean.split())[:500]


def _summarize_security_headers(headers: dict[str, str]) -> dict[str, Any]:
    required = [
        "content-security-policy",
        "strict-transport-security",
        "x-content-type-options",
        "x-frame-options",
        "referrer-policy",
        "permissions-policy",
    ]
    lower = {str(key).casefold(): str(value) for key, value in headers.items()}
    return {
        "presence": {name: bool(lower.get(name)) for name in required},
        "values": {name: lower.get(name, "")[:300] for name in required if lower.get(name)},
    }


def _classify_passive_web_presence(
    root: dict[str, Any],
    html_info: dict[str, Any],
    checks: list[dict[str, Any]],
) -> dict[str, Any]:
    ok_checks = [check for check in checks if check.get("ok")]
    signals = []
    gaps = []
    if root.get("ok"):
        signals.append("الصفحة الرئيسية تستجيب عبر HTTP(S).")
    else:
        gaps.append("تعذر جلب الصفحة الرئيسية من خلال فحص GET واحد.")
    if html_info.get("title") or html_info.get("description"):
        signals.append("توجد بيانات تعريف مرئية يمكن استخدامها لتقييم هوية الموقع.")
    else:
        gaps.append("لا توجد بيانات title/description كافية في العينة الأولى.")
    if html_info.get("app_links"):
        signals.append("ظهرت روابط تطبيقات أو manifest يمكن مراجعتها يدويًا.")
    else:
        gaps.append("لم تظهر روابط متجر تطبيقات أو APK في الصفحة الأولى.")
    if any(str(check.get("label")) == "robots.txt" and check.get("ok") for check in ok_checks):
        signals.append("robots.txt متاح، وقد يساعد في فهم البنية العامة.")
    if any(str(check.get("label")) == "sitemap.xml" and check.get("ok") for check in ok_checks):
        signals.append("sitemap.xml متاح، وقد يساعد في تحديد صفحات المراجعة.")
    confidence = "low"
    if root.get("ok") and len(signals) >= 3:
        confidence = "medium"
    if root.get("ok") and html_info.get("title") and html_info.get("description") and len(ok_checks) >= 3:
        confidence = "medium-high"
    return {
        "classification": "needs_manual_business_verification",
        "confidence": confidence,
        "signals": signals,
        "gaps": gaps,
        "company_ready": bool(root.get("ok")),
    }


def _repo_path_from_static_report(report_text: str) -> Path:
    match = re.search(
        r"^\s*-\s*Local path\s*:\s*`?(.+?)`?\s*$",
        report_text,
        re.IGNORECASE | re.MULTILINE,
    )
    if not match:
        raise ValueError("Could not infer repo_path from the static review report")
    return Path(match.group(1).strip()).resolve()


def _candidate_ids_from_static_report(report_text: str) -> list[str]:
    title_to_id = (
        ("command execution", "command-execution-sink"),
        ("server-side request forgery", "ssrf-review-candidate"),
        ("ssrf", "ssrf-review-candidate"),
        ("html injection", "xss-html-sink"),
        ("cross-site scripting", "xss-html-sink"),
        ("xss", "xss-html-sink"),
        ("open redirect", "open-redirect-candidate"),
        ("unsafe navigation", "open-redirect-candidate"),
        ("disabled tls", "tls-or-jwt-validation-disabled"),
        ("jwt validation", "tls-or-jwt-validation-disabled"),
        ("path traversal", "path-traversal-candidate"),
        ("unsafe file path", "path-traversal-candidate"),
        ("archive extraction", "archive-extraction-candidate"),
        ("zip slip", "archive-extraction-candidate"),
        ("deserialization", "deserialization-candidate"),
        ("code generation", "codegen-injection-candidate"),
        ("template injection", "codegen-injection-candidate"),
        ("android deep link", "android-deeplink-candidate"),
        ("exported intent", "android-deeplink-candidate"),
        ("javascript string", "webview-js-string-injection-candidate"),
        ("evaluatejavascript", "webview-js-string-injection-candidate"),
        ("webview", "webview-unsafe-config-candidate"),
        ("url scheme", "ios-url-scheme-candidate"),
        ("ios", "ios-url-scheme-candidate"),
    )
    ids: list[str] = []
    for match in re.finditer(
        r"^###\s+Candidate\s+\d+\s*:\s*(.+?)\s*$",
        report_text,
        re.IGNORECASE | re.MULTILINE,
    ):
        title = match.group(1).casefold()
        candidate_id = next(
            (mapped for needle, mapped in title_to_id if needle in title),
            "",
        )
        if candidate_id and candidate_id not in ids:
            ids.append(candidate_id)
    return ids


def _path_has_any(path: Any, needles: tuple[str, ...]) -> bool:
    normalized = str(path or "").replace("\\", "/").casefold()
    parts = [part for part in normalized.split("/") if part]
    return any(
        needle.casefold() in parts or f".{needle.casefold()}." in normalized
        for needle in needles
    )


def _is_low_signal_static_path(path: Any) -> bool:
    normalized = str(path or "").replace("\\", "/").casefold()
    parts = [part for part in normalized.split("/") if part]
    low_signal_terms = (
        "test",
        "tests",
        "testdata",
        "fixture",
        "fixtures",
        "docs",
        "doc",
        "example",
        "examples",
        "sample",
        "samples",
        "benchmark",
        "benchmarks",
        "gradle",
        "buildsrc",
        "debug",
        ".github",
    )
    return any(
        part in low_signal_terms
        or part.endswith("test")
        or part.endswith("tests")
        or part.endswith(".gradle")
        or part.endswith(".gradle.kts")
        or part.endswith(".md")
        or "testdata" in part
        or "-test" in part
        or "-tests" in part
        for part in parts
    )


def _production_static_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if not _is_low_signal_static_path(row.get("path"))]


def _webview_js_single_quote_repro() -> dict[str, Any]:
    json_text = (
        '{"token":"tok\');window.__FATHIYA_PROOF=1;//",'
        '"locale":"en_US","environment":"sandbox"}'
    )
    script = f"openCheckout('{json_text}');"
    return {
        "kind": "local_static_string_context_probe",
        "breaks_single_quoted_js": "');" in script,
        "sample_payload": json_text,
        "sample_script": script,
        "limitation": (
            "This proves the JavaScript string context is fragile, not that an external "
            "attacker controls the token or callback value."
        ),
    }


def _render_static_bug_bounty_report(
    *,
    program: str,
    repo_url: str,
    repo_path: Path,
    scope_note: str,
    focus: str,
    candidates: list[dict[str, Any]],
) -> str:
    top = candidates[0] if candidates else None
    title = (
        str(top["title"])
        if top
        else f"Static-only review notes for {program}"
    )
    lines = [
        f"# {title}",
        "",
        "## Review boundary",
        "",
        "- Mode: static source review only.",
        "- No live target scanning was performed.",
        "- No external submission was made by FATHIYA.",
        f"- Program: {program}",
        f"- Repository/source: {repo_url}",
        f"- Local path: `{repo_path}`",
    ]
    if scope_note:
        lines.append(f"- Scope note: {scope_note}")
    if focus:
        lines.append(f"- Operator focus: {focus}")
    lines.extend(["", "## Candidate summary", ""])
    if not candidates:
        lines.extend(
            [
                "No reportable candidate was identified by the static heuristics in this pass.",
                "This is not proof that the target is secure; it only means this bounded review did not produce a submission-ready finding.",
            ]
        )
    for index, candidate in enumerate(candidates, start=1):
        lines.extend(
            [
                f"### Candidate {index}: {candidate['title']}",
                "",
                f"- Suggested VRT: {candidate['vrt']}",
                f"- Suggested priority: {candidate['severity']}",
                f"- Match count: {candidate['match_count']}",
                f"- Low-signal docs/tests matches filtered: {candidate.get('low_signal_match_count', 0)}",
                f"- Why it matters: {candidate['why']}",
                "",
                "Evidence:",
            ]
        )
        for evidence in candidate.get("evidence", []):
            if not isinstance(evidence, dict):
                continue
            lines.append(
                f"- `{evidence.get('path')}:{evidence.get('line')}` - "
                f"{evidence.get('text')}"
            )
        lines.extend(
            [
                "",
                "Validation needed before submission:",
                "- Confirm this code path is in the Bugcrowd authorized scope.",
                "- Trace whether attacker-controlled input reaches the sink.",
                "- Reproduce impact safely without live scanning outside the program rules.",
                "- Remove or downgrade the candidate if exploitability cannot be proven.",
                "",
            ]
        )
    lines.extend(
        [
            "## Submission gate",
            "",
            "Do not submit this draft until a human operator confirms scope, exploitability, impact, and program-specific rules.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_static_bug_bounty_no_source_report(
    *,
    program: str,
    program_url: str,
    scope_note: str,
    focus: str,
) -> str:
    lines = [
        f"# No source-backed static finding for {program}",
        "",
        "## Review boundary",
        "",
        "- Mode: static source review gate.",
        "- Source repository status: no_source_repository",
        "- No live target scanning was performed.",
        "- No external submission was made by FATHIYA.",
        f"- Program: {program}",
        f"- Program URL: {program_url}",
        "- Repository/source: not provided",
        "- Local path: not available",
    ]
    if scope_note:
        lines.append(f"- Scope note: {scope_note}")
    if focus:
        lines.append(f"- Operator focus: {focus}")
    lines.extend(
        [
            "",
            "## Result",
            "",
            "FATHIYA did not produce a submission-ready vulnerability report from this static pass.",
            "A website URL alone is not a source repository. The engine therefore did not review the local FATHIYA repository as a substitute target.",
            "",
            "## Required Next Evidence",
            "",
            "- Provide an in-scope source repository, mobile package, API collection, or exact authorized test surface.",
            "- Or run a separate passive/live-approved evidence task under the program rules.",
            "- Do not submit findings based on unrelated local project heuristics.",
            "",
            "## Submission gate",
            "",
            "Not submission ready. No external upload is recommended from this report.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_passive_web_target_report(
    *,
    program: str,
    program_url: str,
    scope_note: str,
    focus: str,
    intake: dict[str, Any],
) -> str:
    summary = intake.get("summary") if isinstance(intake.get("summary"), dict) else {}
    html_info = intake.get("html") if isinstance(intake.get("html"), dict) else {}
    security_headers = (
        intake.get("security_headers")
        if isinstance(intake.get("security_headers"), dict)
        else {}
    )
    checks = intake.get("checks") if isinstance(intake.get("checks"), list) else []
    observations = (
        intake.get("observations")
        if isinstance(intake.get("observations"), list)
        else []
    )
    lines = [
        f"# تقرير حضور ويب أولي لـ {program}",
        "",
        "## حدود التقرير",
        "",
        "- Mode: web URL passive intake.",
        "- Deliverable type: company_web_intake_report.",
        "- Source repository status: no_source_repository",
        "- No vulnerability exploitation was performed.",
        "- No credentialed login, account creation, purchase, or app download was performed.",
        "- لم يتم إنشاء حساب، أو تسجيل دخول، أو شراء، أو تنزيل تطبيق ضمن هذا المرور.",
        "- No destructive or high-volume scanning was performed.",
        "- No external submission was made by FATHIYA.",
        f"- Program: {program}",
        f"- Program URL: {program_url}",
        f"- Final URL observed: {intake.get('final_url') or program_url}",
        "- Repository/source: not provided",
        "- Local path: not available",
    ]
    if scope_note:
        lines.append(f"- Scope note: {scope_note}")
    if focus:
        lines.append(f"- Operator focus: {focus}")
    lines.extend(
        [
            "",
            "## الخلاصة التنفيذية",
            "",
            (
                "هذا التقرير يعطي صورة أولية عن حضور الموقع وملفاته العامة، وليس تقرير ثغرة جاهزًا للرفع. "
                "النتيجة تصلح كبداية تواصل أو تحقق تجاري/تقني مع الجهة، لكنها لا تكفي وحدها لإثبات أثر أمني."
            ),
            "",
            f"- التصنيف الأولي: {summary.get('classification', 'needs_manual_business_verification')}",
            f"- الثقة: {summary.get('confidence', 'low')}",
            f"- قابلية التسليم للشركة كتقرير حضور أولي: {'نعم' if summary.get('company_ready') else 'بحاجة لإعادة جلب/تحقق يدوي'}",
            "- قرار فتحية: جاهز كتقرير شركة أولي داخلي، وغير جاهز كبلاغ ثغرة خارجي.",
            "",
            "## أدلة الصفحة الأولى",
            "",
            f"- العنوان: {html_info.get('title') or 'غير ظاهر في العينة'}",
            f"- الوصف: {html_info.get('description') or 'غير ظاهر في العينة'}",
            f"- canonical: {html_info.get('canonical') or 'غير ظاهر'}",
            f"- generator/platform: {html_info.get('generator') or 'غير ظاهر'}",
        ]
    )
    app_links = html_info.get("app_links") if isinstance(html_info.get("app_links"), list) else []
    lines.extend(["", "## روابط تطبيقات أو Manifest محتملة", ""])
    if app_links:
        for link in app_links[:10]:
            lines.append(f"- {link}")
    else:
        lines.append("- لم تظهر روابط تطبيقات أو manifest واضحة في الصفحة الأولى.")
    external_domains = (
        html_info.get("external_domains")
        if isinstance(html_info.get("external_domains"), list)
        else []
    )
    lines.extend(["", "## نطاقات خارجية ظاهرة في الصفحة", ""])
    if external_domains:
        for domain in external_domains[:16]:
            lines.append(f"- {domain}")
    else:
        lines.append("- لم تظهر نطاقات خارجية كافية في العينة الأولى.")
    lines.extend(["", "## الملفات العامة التي تم جلبها", ""])
    for check in checks:
        lines.append(
            f"- {check.get('label')}: HTTP {check.get('status_code')} · "
            f"{check.get('content_type') or check.get('error') or 'لا توجد تفاصيل'} · "
            f"{check.get('characters', 0)} chars"
        )
    presence = (
        security_headers.get("presence")
        if isinstance(security_headers.get("presence"), dict)
        else {}
    )
    lines.extend(["", "## رؤوس أمان ظاهرة في الرد الأولي", ""])
    if presence:
        for name, present in presence.items():
            lines.append(f"- {name}: {'موجود' if present else 'غير ظاهر'}")
    else:
        lines.append("- لم يتم التقاط رؤوس كافية.")
    lines.extend(["", "## إشارات إيجابية", ""])
    signals = summary.get("signals") if isinstance(summary.get("signals"), list) else []
    if signals:
        for signal in signals:
            lines.append(f"- {signal}")
    else:
        lines.append("- لا توجد إشارات كافية من العينة الأولى.")
    lines.extend(["", "## نواقص تمنع الحكم النهائي", ""])
    gaps = summary.get("gaps") if isinstance(summary.get("gaps"), list) else []
    if gaps:
        for gap in gaps:
            lines.append(f"- {gap}")
    else:
        lines.append("- لا توجد نواقص رئيسية من فحص GET الأولي، لكن يلزم تحقق يدوي داخل الحساب/التطبيق إن كان مصرحًا.")
    lines.extend(["", "## سجل الملاحظات الخام", ""])
    for item in observations[:24]:
        if not isinstance(item, dict):
            continue
        lines.append(f"- {item.get('label')}: {item.get('detail')}")
    lines.extend(
        [
            "",
            "## هل هذا تقرير ثغرة قابل للرفع؟",
            "",
            "لا. لا توجد ثغرة مثبتة أو أثر أمني موثق في هذا المرور. التقرير الحالي هو تقرير حضور ويب أولي يساعد على تحديد هل الهدف يستحق مراجعة أعمق وما الأدلة الناقصة.",
            "",
            "## الخطوة التالية المقترحة",
            "",
            "- إذا المطلوب تقرير شركة: استخدم هذا التقرير كمسودة أولى، ثم أضف لقطات شاشة يدوية من الصفحة، صفحة التواصل، وسياسات الخدمة عند تجهيز نسخة الإرسال.",
            "- إذا المطلوب Bugcrowd/HackerOne: وفّر نطاقًا مصرحًا واضحًا أو مستودع مصدر أو API collection، ثم شغّل مراجعة ثابتة/ديناميكية ضمن القواعد.",
            "- إذا المطلوب تقييم هل الموقع spam: يلزم تحقق يدوي من الهوية القانونية، سجل النطاق، طرق الدفع، سياسة الخصوصية، التطبيق الرسمي، ومراجعات المستخدمين.",
            "",
            "## Submission gate",
            "",
            "Not submission ready. No external vulnerability upload is recommended from this report.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _render_bug_bounty_draft_gate(
    *,
    program: str,
    report_path: Path,
    repo_path: Path | None,
    validation: list[dict[str, Any]],
    verdict: str,
) -> str:
    lines = [
        f"# Bugcrowd Draft Gate - {program}",
        "",
        "## Decision",
        "",
        f"- Verdict: {verdict}",
        "- External Bugcrowd upload performed: no",
        "- Live target testing performed: no",
        "- Draft uploaded inside FATHIYA: yes",
        f"- Source static report: `{report_path}`",
        f"- Reviewed repository: `{repo_path}`" if repo_path else "- Reviewed repository: not available",
        "",
        "## Validation Results",
        "",
    ]
    for item in validation:
        lines.extend(
            [
                f"### {item['id']}",
                "",
                f"- Status: {item['status']}",
                f"- Decision: {item['decision']}",
                f"- Reason: {item['reason']}",
                "",
                "Evidence:",
            ]
        )
        evidence = item.get("evidence", [])
        if evidence:
            for row in evidence:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- `{row.get('path')}:{row.get('line')}` - {row.get('text')}"
                )
        else:
            lines.append("- No confirming evidence found in this bounded pass.")
        lines.append("")
        local_repro = item.get("local_repro")
        if isinstance(local_repro, dict):
            lines.extend(
                [
                    "Local static repro:",
                    f"- Kind: {local_repro.get('kind')}",
                    f"- Breaks single-quoted JS: {local_repro.get('breaks_single_quoted_js')}",
                    f"- Sample payload: `{local_repro.get('sample_payload')}`",
                    f"- Limitation: {local_repro.get('limitation')}",
                    "",
                ]
            )
        source_trace = item.get("source_trace")
        if isinstance(source_trace, list) and source_trace:
            lines.append("Source trace:")
            for row in source_trace:
                if not isinstance(row, dict):
                    continue
                lines.append(
                    f"- `{row.get('path')}:{row.get('line')}` - {row.get('text')}"
                )
            lines.append("")
    lines.extend(["## Upload Gate", ""])
    if verdict == "company_report_ready":
        lines.extend(
            [
                "Company-report gate: ready as an internal/company web-intake report.",
                "Do not upload this as an external Bugcrowd/HackerOne vulnerability report; it does not claim a proven exploit.",
                "Next acceptable step: add manual screenshots and business-identity evidence if the operator wants a polished company-facing PDF or message.",
            ]
        )
    else:
        lines.extend(
            [
                "Do not upload this as an external Bugcrowd vulnerability report yet. The current evidence is a verified internal draft gate, not a submission-ready exploit proof.",
                "Next acceptable step: find a candidate with a source-level attacker-controlled path and a safe proof inside the program rules, then rerun this gate.",
            ]
        )
    return "\n".join(lines).strip() + "\n"


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
    zapier_inventory: dict[str, Any] | None = None,
    n8n_workflows: dict[str, Any],
    kali: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    zapier_inventory = zapier_inventory or {}

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
    if (
        not zapier_direct.get("connected")
        or zapier_direct.get("needs_reconnect")
        or zapier_direct.get("live_available") is False
    ):
        inventory_note = (
            f"المخزون المستضاف ظاهر وفيه {zapier_inventory.get('app_count')} تطبيقًا "
            f"و{zapier_inventory.get('action_count')} إجراء؛ OAuth المحلي مطلوب للتنفيذ المحلي غير المراقب."
            if zapier_inventory.get("available")
            else "مخزون Zapier لم يظهر بعد؛ اربط OAuth المحلي حتى يستطيع المحرك قراءة وتنفيذ الإجراءات."
        )
        add(
            "connect_zapier_oauth",
            "ربط Zapier MCP المحلي",
            "integration probe: zapier_mcp",
            inventory_note,
            ui_action="oauth",
            integration_id="zapier_mcp",
            action_path="/api/agent/oauth/zapier/start",
            action_label="ربط Zapier OAuth",
        )
    codespaces_status = integration_probes.get("github_codespaces", {}).get("status")
    if codespaces_status != "ready":
        add(
            "authorize_github_codespaces",
            "تفعيل GitHub Codespaces",
            "integration probe: github_codespaces",
            "وكيل Codespaces يحتاج صلاحية gh codespace. شغّل: gh auth refresh -h github.com -s codespace",
            integration_id="github_codespaces",
        )
    else:
        add(
            "run_codespaces_agent",
            "تشغيل وكيل Codespaces",
            "شغّل وكيل GitHub Codespaces للهدف الهندسي",
            "Codespaces جاهز كبيئة هندسية بعيدة، والوكيل يقدر يجهز خطة تشغيل قراءة فقط مع إيصال.",
            integration_id="github_codespaces",
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
            "FATHIYA_N8N_WEBHOOK_URL",
            "FATHIYA_ZAPIER_WEBHOOK_URL",
        }
    ]
    if bridge_missing_env:
        add(
            "configure_agent_bridges",
            "إكمال جسور Zapier وn8n",
            "اعرض جاهزية جسور Zapier وn8n ثم جهز الناقص",
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


def _agent_mesh_probe_details(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed_keys = {
        "auth_state",
        "missing_scope",
        "operator_action_required",
        "auth_command",
        "required_scope",
        "codespace_count",
        "active_codespace_count",
        "configured",
        "active_store",
        "restart_required",
        "app_count",
        "action_count",
        "needs_reconnect",
        "refresh_recommended",
        "last_refresh_error",
        "last_refresh_status_code",
        "direct_live_available",
        "webhook_bridge_ready",
        "provider",
        "environment",
        "symbol",
        "testnet_execution_enabled",
        "live_execution_enabled",
        "real_funds_possible",
        "tool_count",
        "missing_tool_count",
        "execution_mode",
    }
    details: dict[str, Any] = {}
    for key in sorted(allowed_keys):
        if key not in value:
            continue
        item = value.get(key)
        if item is None or item == "" or item == [] or item == {}:
            continue
        details[key] = item
    return details


def _agent_mesh_execution_command_center(
    *,
    prompt: str,
    safe_executions: list[dict[str, Any]],
    integration_probes: dict[str, dict[str, Any]],
    next_actions: list[dict[str, Any]],
    activation_plan: dict[str, Any],
    skipped_high_risk: list[dict[str, Any]],
    connected_inventory: dict[str, Any],
    zapier_direct: dict[str, Any],
    n8n_workflows: dict[str, Any],
) -> dict[str, Any]:
    ready_integrations = sorted(
        integration_id
        for integration_id, probe in integration_probes.items()
        if isinstance(probe, dict) and bool(probe.get("ok"))
    )
    partial_integrations = sorted(
        integration_id
        for integration_id, probe in integration_probes.items()
        if isinstance(probe, dict)
        and not bool(probe.get("ok"))
        and str(probe.get("status") or "") in {"partial", "needs_setup", "needs_operator"}
    )
    ready_commands = _agent_mesh_ready_commands(
        prompt=prompt,
        ready_integrations=ready_integrations,
        connected_inventory=connected_inventory,
        zapier_direct=zapier_direct,
        n8n_workflows=n8n_workflows,
    )
    operator_queue = _agent_mesh_operator_queue(
        next_actions=next_actions,
        activation_plan=activation_plan,
        skipped_high_risk=skipped_high_risk,
    )
    executed_tools = [
        {
            "tool": str(item.get("tool") or ""),
            "description": str(item.get("description") or ""),
            "status": _execution_step_status(item),
        }
        for item in safe_executions[:16]
        if isinstance(item, dict) and item.get("tool")
    ]
    routable_tools = _agent_mesh_routable_tools(
        safe_executions=safe_executions,
        connected_inventory=connected_inventory,
        zapier_direct=zapier_direct,
    )
    return {
        "mode": "fathiya_execution_command_center_v1",
        "secret_safe": True,
        "objective": "execute_with_local_models_openrouter_and_connected_tools",
        "operator_authority": {
            "internal_and_read_only": "execute_now_without_waiting",
            "connected_app_reads": "prepare_and_execute_when_oauth_is_live",
            "connected_app_writes": "queue_as_operator_approved_external_effect",
            "real_money": "testnet_first",
            "live_security": "authorized_scope_first",
        },
        "model_stack": {
            "local_huggingface": "retrieval_light_generation_and_memory_grounding",
            "openrouter": "planning_routing_evaluation_and_heavy_reasoning",
            "fallback": "deterministic_local_execution_when_models_fail",
        },
        "summary": {
            "executed_now_count": len(executed_tools),
            "ready_command_count": len(ready_commands),
            "operator_queue_count": len(operator_queue),
            "routable_tool_count": len(routable_tools),
            "ready_integration_count": len(ready_integrations),
            "partial_integration_count": len(partial_integrations),
        },
        "ready_integrations": ready_integrations,
        "partial_integrations": partial_integrations,
        "executed_now": executed_tools,
        "ready_commands": ready_commands,
        "operator_queue": operator_queue,
        "routable_tools": routable_tools,
    }


def _agent_mesh_operator_status(
    *,
    safe_executions: list[dict[str, Any]],
    failed_steps: list[dict[str, Any]],
    skipped_high_risk: list[dict[str, Any]],
    integration_probes: dict[str, dict[str, Any]],
    zapier_inventory_available: bool,
    zapier_direct_live_available: bool,
) -> dict[str, Any]:
    ready_integrations = sorted(
        integration_id
        for integration_id, probe in integration_probes.items()
        if isinstance(probe, dict) and bool(probe.get("ok"))
    )
    activation_required = sorted(
        integration_id
        for integration_id, probe in integration_probes.items()
        if isinstance(probe, dict)
        and not bool(probe.get("ok"))
        and str(probe.get("status") or "") in {"partial", "needs_setup", "needs_operator"}
    )
    executed_tool_names = [
        str(step.get("tool") or "")
        for step in safe_executions
        if isinstance(step, dict) and step.get("tool")
    ]
    executed_count = len(executed_tool_names)
    state = (
        "executed_with_warnings"
        if executed_count and failed_steps
        else "executed_now"
        if executed_count
        else "prepared_only"
    )
    paper_trading_running = any(
        step.get("tool") in {"trading_status", "trading_start"}
        and isinstance(step.get("result"), dict)
        and bool(step["result"].get("running"))
        for step in safe_executions
    )
    model_route_ready = {
        "huggingface_local": "huggingface_local" in ready_integrations,
        "openrouter": "openrouter" in ready_integrations,
    }
    local_tool_route_ready = {
        "n8n_local": "n8n_local" in ready_integrations,
        "kali_wsl": "kali_wsl" in ready_integrations,
        "github_codespaces": "github_codespaces" in ready_integrations,
    }
    headline = (
        f"نفذت فتحية {executed_count} خطوة محلية الآن."
        if executed_count
        else "فتحية جهزت خطة التنفيذ لكنها لم تنفذ خطوة محلية بعد."
    )
    if activation_required:
        headline += f" بقي {len(activation_required)} بوابات ترقية لا توقف التنفيذ المحلي."
    return {
        "mode": "fathiya_operator_status_v1",
        "state": state,
        "can_execute_now": bool(executed_count),
        "headline": headline,
        "executed_tool_count": executed_count,
        "executed_tools": executed_tool_names[:16],
        "failed_step_count": len(failed_steps),
        "ready_integration_count": len(ready_integrations),
        "activation_required_count": len(activation_required),
        "ready_integrations": ready_integrations,
        "activation_required_integrations": activation_required,
        "paper_trading_running": paper_trading_running,
        "model_route_ready": model_route_ready,
        "local_tool_route_ready": local_tool_route_ready,
        "zapier_inventory_available": zapier_inventory_available,
        "zapier_live_execution_available": zapier_direct_live_available,
        "high_impact_followup_count": len(skipped_high_risk),
        "local_execution_not_blocked_by_upgrades": True,
        "next_step": (
            "اكتب الهدف التالي في الطلب المباشر؛ سيستخدم المحرك المعرفة والنماذج والأدوات الجاهزة."
            if executed_count
            else "شغل agent_mesh_execute أو أصلح اتصال العامل المحلي ثم أعد الطلب."
        ),
        "secret_safe": True,
    }


def _agent_mesh_ready_commands(
    *,
    prompt: str,
    ready_integrations: list[str],
    connected_inventory: dict[str, Any],
    zapier_direct: dict[str, Any],
    n8n_workflows: dict[str, Any],
) -> list[dict[str, Any]]:
    commands: list[dict[str, Any]] = []

    def add(
        command_id: str,
        title: str,
        command_prompt: str,
        *,
        tool: str = "agent_mesh_execute",
        lane: str = "execution",
        execution_mode: str = "local_task",
        reason: str = "",
        args: dict[str, Any] | None = None,
    ) -> None:
        commands.append(
            {
                "id": command_id,
                "title": title,
                "tool": tool,
                "lane": lane,
                "execution_mode": execution_mode,
                "prompt": command_prompt,
                "reason": reason,
                "args": _secret_safe_args(args or {}),
                "ui_action": "task",
            }
        )

    add(
        "execute_internal_mesh_now",
        "تشغيل شبكة فتحية الداخلية الآن",
        "agent mesh execute:\nنفذ شبكة فتحية المحلية: معرفة، نماذج، Zapier MCP، n8n، Kali، Codespaces، وتداول ورقي. سجل ما عمل وما ينتظر أثرًا خارجيًا.",
        reason="المحرك يستطيع تنفيذ الفحوصات والقراءات والأدوات المحلية الآن.",
    )
    add(
        "learn_then_execute",
        "استيعاب معرفة ثم تنفيذ",
        "knowledge execution mission:\nFATHIYA_KNOWLEDGE_EXECUTION_V1\nاستوعب ملفات وتقارير المعرفة الجديدة، اختبر الفهم، ثم نفذ الأدوات المحلية المناسبة وسجل إيصالًا.",
        lane="knowledge",
        reason="المعرفة لا تبقى تحليلًا؛ تتحول إلى اختيار أدوات وخطوات تشغيل.",
    )
    if "openrouter" in ready_integrations:
        add(
            "refresh_openrouter_strategy",
            "تحديث توجيه النماذج عبر OpenRouter",
            "افحص استراتيجية OpenRouter للنماذج المجانية والقوية، ثم اربطها بمسارات التخطيط والتقييم والتداول الورقي.",
            tool="openrouter_model_strategy",
            lane="models",
            reason="OpenRouter جاهز للتخطيط والتقييم الثقيل.",
        )
    if "huggingface_local" in ready_integrations:
        add(
            "run_local_knowledge_grounding",
            "تشغيل الذاكرة المحلية",
            "استرجع المعرفة المحلية المرتبطة بالهدف الحالي، ثم اقترح تنفيذًا بالأدوات المناسبة بدل تلخيص فقط.",
            lane="knowledge",
            reason="Hugging Face المحلي جاهز للذاكرة والاسترجاع.",
        )
    add(
        "start_paper_trading_second_loop",
        "تشغيل وكيل التداول الورقي بنبض الثانية",
        "شغّل وكيل التداول الورقي بنبض الثانية، حدّث مستشار الاستراتيجية، وسجل جودة التنبؤ والتنفيذ.",
        tool="trading_start",
        lane="trading",
        reason="التداول الورقي مسموح كتنفيذ محلي لا يستخدم أموالًا حقيقية.",
    )
    add(
        "run_bug_bounty_static_pipeline",
        "تشغيل صيد ثغرات ساكن ومصرح",
        "bug bounty static review:\nاستخدم المعرفة وKali عند اللزوم داخل الحدود المصرحة، واصنع draft داخلي بدليل عملي وقابلية dedupe.",
        tool="bug_bounty_static_review",
        lane="bug_bounty",
        reason="صيد الثغرات يبدأ بمراجعة ساكنة ودليل داخلي قبل أي أثر خارجي.",
    )
    if "kali_wsl" in ready_integrations:
        add(
            "refresh_kali_inventory",
            "فحص أدوات Kali المتاحة",
            "اعرض أدوات Kali الدفاعية الجاهزة واختر المناسب للهدف الحالي دون فحص حي غير مصرح.",
            tool="kali_tool_inventory",
            lane="bug_bounty",
            reason="Kali جاهز كمستودع أدوات محلي.",
        )
    if "n8n_local" in ready_integrations or n8n_workflows.get("available"):
        add(
            "inspect_n8n_workflows",
            "قراءة مسارات n8n القابلة للتشغيل",
            "اعرض مسارات n8n المحلية وحدد أي workflow يخدم تنفيذ فتحية القادم.",
            tool="n8n_workflows",
            lane="automation",
            reason="n8n جاهز كجسر أتمتة محلي.",
        )
    if bool(zapier_direct.get("live_available")):
        for provider in _agent_provider_names(connected_inventory)[:5]:
            add(
                f"prepare_{_slug(provider)}_agent_action",
                f"تحضير إجراء {provider}",
                (
                    f"Zapier agent provider: {provider}\n"
                    "اختر أفضل إجراء قراءة أو كتابة للهدف الحالي، حضر الحقول المطلوبة، "
                    "ولا ترسل أثرًا خارجيًا إلا كبوابة اعتماد."
                ),
                tool="agent_provider_action_prepare",
                lane="connected_apps",
                execution_mode="zapier_mcp_prepare",
                reason="Zapier MCP حي ويمكنه تحضير أفعال تطبيقات الذكاء والأتمتة.",
                args={"provider": provider, "objective": prompt[:400]},
            )
    return commands[:12]


def _agent_mesh_operator_queue(
    *,
    next_actions: list[dict[str, Any]],
    activation_plan: dict[str, Any],
    skipped_high_risk: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(item: dict[str, Any]) -> None:
        key = str(item.get("id") or item.get("prompt") or item.get("title") or "")
        if not key or key in seen:
            return
        seen.add(key)
        queue.append(item)

    for action in next_actions[:12]:
        if not isinstance(action, dict):
            continue
        add(
            {
                "id": action.get("id"),
                "title": action.get("title"),
                "state": "needs_setup_or_oauth",
                "prompt": action.get("prompt"),
                "reason": action.get("reason"),
                "ui_action": action.get("ui_action", "task"),
                "settings_group": action.get("settings_group"),
                "integration_id": action.get("integration_id"),
                "action_path": action.get("action_path"),
                "action_label": action.get("action_label"),
            }
        )
    entries = activation_plan.get("entries") if isinstance(activation_plan, dict) else []
    if isinstance(entries, list):
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("state") == "ready":
                continue
            action = entry.get("next_action") if isinstance(entry.get("next_action"), dict) else {}
            add(
                {
                    "id": action.get("id") or entry.get("integration_id"),
                    "title": action.get("title") or entry.get("integration_id"),
                    "state": "activation_required",
                    "prompt": action.get("prompt"),
                    "reason": action.get("reason") or entry.get("summary"),
                    "ui_action": action.get("ui_action", "task"),
                    "settings_group": action.get("settings_group"),
                    "integration_id": entry.get("integration_id"),
                    "action_path": action.get("action_path"),
                    "action_label": action.get("action_label"),
                }
            )
    for item in skipped_high_risk[:12]:
        if not isinstance(item, dict):
            continue
        tool = str(item.get("tool") or "external_effect")
        add(
            {
                "id": f"approve_{tool}_{len(queue)}",
                "title": f"اعتماد أثر خارجي: {tool}",
                "state": "operator_approval_required",
                "tool": tool,
                "risk_class": item.get("risk_class"),
                "reason": item.get("reason") or item.get("description"),
                "ui_action": "task",
            }
        )
    return [item for item in queue if item.get("title")][:16]


def _agent_mesh_routable_tools(
    *,
    safe_executions: list[dict[str, Any]],
    connected_inventory: dict[str, Any],
    zapier_direct: dict[str, Any],
) -> list[dict[str, Any]]:
    tools: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(name: str, lane: str, mode: str, *, ready: bool = True) -> None:
        if not name or name in seen:
            return
        seen.add(name)
        tools.append({"name": name, "lane": lane, "mode": mode, "ready": ready})

    for step in safe_executions:
        if isinstance(step, dict):
            add(str(step.get("tool") or ""), "executed_now", "local")
    for name, lane in (
        ("learning_bootstrap", "knowledge"),
        ("openrouter_model_strategy", "models"),
        ("trading_start", "trading"),
        ("trading_strategy_refresh", "trading"),
        ("bug_bounty_static_review", "bug_bounty"),
        ("kali_tool_inventory", "bug_bounty"),
        ("n8n_workflows", "automation"),
        ("github_codespaces_agent", "engineering"),
        ("agent_provider_action_prepare", "connected_apps"),
        ("zapier_action_preflight", "connected_apps"),
    ):
        add(name, lane, "ready_command")
    live_zapier = bool(zapier_direct.get("live_available"))
    for provider in _agent_provider_names(connected_inventory)[:8]:
        add(provider, "agent_provider", "zapier_mcp", ready=live_zapier)
    return tools[:32]


def _agent_provider_names(inventory: dict[str, Any]) -> list[str]:
    actions = inventory.get("agent_provider_actions")
    if not isinstance(actions, dict):
        return []
    preferred = ["ChatGPT (OpenAI)", "Agents", "Apify", "Netlify"]
    names = [name for name in preferred if name in actions and not _hidden_agent_provider_name(name)]
    names.extend(
        sorted(
            str(name)
            for name in actions
            if str(name) not in names and not _hidden_agent_provider_name(str(name))
        )
    )
    return names


def _hidden_agent_provider_name(name: str) -> bool:
    return False


def _production_base_url(prompt: str, args: dict[str, Any]) -> str:
    raw = str(args.get("base_url") or args.get("url") or "").strip()
    if not raw:
        match = re.search(r"https?://[^\s<>'\"،]+", prompt, re.IGNORECASE)
        raw = match.group(0).rstrip(").,]") if match else "https://fathya-core.com"
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "https://fathya-core.com"
    return f"{parsed.scheme}://{parsed.netloc}"


def _production_audit_routes(args: dict[str, Any]) -> list[str]:
    raw_routes = _value_list(args.get("routes"))
    if not raw_routes:
        raw_routes = ["/", "/agent-tasks", "/command-center", "/ai-console"]
    routes: list[str] = []
    for route in raw_routes:
        value = str(route or "").strip()
        if not value:
            continue
        if value.startswith("http://") or value.startswith("https://"):
            parsed = urlparse(value)
            value = parsed.path or "/"
        if not value.startswith("/"):
            value = f"/{value}"
        if value not in routes:
            routes.append(value)
    return routes[:8] or ["/", "/agent-tasks"]


def _html_title(text: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    return title[:160] if title else None


def _production_content_signals(text: str) -> dict[str, Any]:
    folded = text.casefold()
    title = (_html_title(text) or "").casefold()
    fathiya_identity = any(
        term in folded
        for term in (
            "fathiya",
            "fathya",
            "فتحية",
            "فتحيه",
            "المنصة السيادية الذكية",
            "المنصه السياديه الذكيه",
        )
    )
    agent_tasks = any(
        term in folded
        for term in (
            "agent-tasks",
            "agent tasks",
            "fathiya ops console",
            "fathiya_command_center",
            "command-center",
        )
    )
    focused_operator_console = any(
        term in folded
        for term in (
            "وكيل التداول",
            "صيد الثغرات",
            "المعرفة والتقارير",
            "محرك الوكلاء",
            "جسور الأدوات",
            "التداول",
        )
    )
    command_center = "command center" in folded or "command-center" in folded or "command center" in title
    return {
        "fathiya_identity": fathiya_identity,
        "agent_tasks": agent_tasks,
        "focused_operator_console": focused_operator_console,
        "command_center": command_center,
        "vite_react_shell": "vite" in folded or "react" in folded,
        "title": _html_title(text),
    }


def _production_audit_next_actions(
    *,
    root_ok: bool,
    agent_tasks_ok: bool,
    identity_signal: bool,
    focused_console_signal: bool,
    command_signal: bool,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not root_ok:
        actions.append(
            {
                "id": "fix_domain_root",
                "title": "إصلاح جذر الدومين",
                "reason": "جذر fathya-core.com لا يرد بنجاح؛ راجع DNS أو الاستضافة.",
                "owner": "deployment",
            }
        )
    if not agent_tasks_ok:
        actions.append(
            {
                "id": "publish_agent_tasks_route",
                "title": "نشر مسار /agent-tasks",
                "reason": "مسار لوحة فتحية غير مثبت على الإنتاج؛ انشر build الحالي أو أضف rewrite للـ SPA.",
                "owner": "deployment",
            }
        )
    if not identity_signal:
        actions.append(
            {
                "id": "publish_fathiya_identity",
                "title": "نشر هوية فتحية",
                "reason": "الإنتاج لا يعرض إشارات كافية لاسم فتحية/المنصة السيادية الذكية.",
                "owner": "frontend",
            }
        )
    if not focused_console_signal and not command_signal:
        actions.append(
            {
                "id": "publish_focused_console",
                "title": "نشر واجهة التشغيل المركزة",
                "reason": "الإنتاج لا يثبت وجود أقسام التداول وصيد الثغرات والمعرفة والأدوات.",
                "owner": "frontend",
            }
        )
    return actions or [
        {
            "id": "monitor_production",
            "title": "مراقبة الإنتاج",
            "reason": "الإنتاج يطابق الإشارات المطلوبة؛ استمر بالمراقبة وتشغيل مهام إثبات دورية.",
            "owner": "runtime",
        }
    ]


def _execution_step_status(item: dict[str, Any]) -> str:
    result = item.get("result")
    if isinstance(result, dict) and result.get("execution_failed"):
        return "failed"
    if isinstance(result, dict) and result.get("available") is False:
        return "unavailable"
    return "executed"


def _secret_safe_args(args: dict[str, Any]) -> dict[str, Any]:
    redacted_keys = {"payload", "params", "token", "api_key", "secret", "password", "key"}
    return {
        key: ("[redacted]" if key.lower() in redacted_keys else value)
        for key, value in args.items()
    }


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_") or "provider"


def _agent_mesh_activation_plan(
    *,
    integration_probes: dict[str, dict[str, Any]],
    next_actions: list[dict[str, Any]],
    skipped_high_risk: list[dict[str, Any]],
) -> dict[str, Any]:
    action_by_integration = {
        str(action.get("integration_id")): action
        for action in next_actions
        if isinstance(action, dict) and action.get("integration_id")
    }
    ordered_ids = [
        "huggingface_local",
        "openrouter",
        "zapier_mcp",
        "n8n_local",
        "kali_wsl",
        "github_codespaces",
        "broker_testnet",
        "local_execution_mesh",
    ]
    entries: list[dict[str, Any]] = []
    ready_count = 0
    activation_required_count = 0

    for integration_id in ordered_ids:
        probe = integration_probes.get(integration_id)
        if not isinstance(probe, dict):
            continue
        status = str(probe.get("status") or "unknown")
        action = action_by_integration.get(integration_id, {})
        state = "ready" if probe.get("ok") or status == "ready" else "activation_required"
        if state == "ready":
            ready_count += 1
        else:
            activation_required_count += 1
        entry: dict[str, Any] = {
            "id": integration_id,
            "integration_id": integration_id,
            "status": status,
            "state": state,
            "summary": probe.get("summary"),
            "probe_action": probe.get("action"),
            "secret_safe": True,
            "details": probe.get("details") if isinstance(probe.get("details"), dict) else {},
        }
        if action and state != "ready":
            entry["next_action"] = {
                key: action.get(key)
                for key in (
                    "id",
                    "title",
                    "prompt",
                    "reason",
                    "ui_action",
                    "settings_group",
                    "action_path",
                    "action_label",
                )
                if action.get(key)
            }
        entries.append(entry)

    approval_gated = [
        {
            "tool": item.get("tool"),
            "description": item.get("description"),
            "risk_class": item.get("risk_class"),
            "reason": item.get("reason"),
        }
        for item in skipped_high_risk[:10]
        if isinstance(item, dict)
    ]
    return {
        "mode": "agent_activation_plan_v1",
        "secret_safe": True,
        "ready_count": ready_count,
        "activation_required_count": activation_required_count,
        "approval_gated_count": len(skipped_high_risk),
        "entries": entries,
        "approval_gated": approval_gated,
    }


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
    if tool == "agent_provider_probe":
        providers = result.get("providers") if isinstance(result.get("providers"), list) else []
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "provider": result.get("provider"),
            "status": result.get("status"),
            "execution_mode": result.get("execution_mode"),
            "requires_oauth": result.get("requires_oauth"),
            "provider_count": result.get("provider_count"),
            "read_action_count": result.get("read_action_count"),
            "write_action_count": result.get("write_action_count"),
            "providers": [
                {
                    "app": provider.get("app"),
                    "status": provider.get("status"),
                    "read_count": provider.get("read_count"),
                    "write_count": provider.get("write_count"),
                    "catalog_actions": provider.get("catalog_actions", [])[:8],
                }
                for provider in providers[:8]
                if isinstance(provider, dict)
            ],
            "next_step": result.get("next_step"),
        }
    if tool == "agent_provider_action_prepare":
        selected = (
            result.get("selected_action")
            if isinstance(result.get("selected_action"), dict)
            else {}
        )
        suggested = (
            result.get("suggested_task")
            if isinstance(result.get("suggested_task"), dict)
            else {}
        )
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "provider": result.get("provider"),
            "status": result.get("status"),
            "execution_mode": result.get("execution_mode"),
            "live_available": result.get("live_available"),
            "requires_oauth": result.get("requires_oauth"),
            "oauth_action_path": result.get("oauth_action_path"),
            "requires_approval": result.get("requires_approval"),
            "selected_action": {
                key: selected.get(key)
                for key in ("name", "key", "mode", "tool_name", "inventory_only")
                if key in selected
            },
            "suggested_task_title": suggested.get("title"),
            "can_execute_now": result.get("can_execute_now"),
            "next_step": result.get("next_step"),
            "error": result.get("error"),
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
    if tool == "zapier_action_details":
        params = result.get("params") if isinstance(result.get("params"), list) else []
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "connected": result.get("connected"),
            "provider": result.get("provider"),
            "app": result.get("app"),
            "action": result.get("action"),
            "action_key": result.get("action_key"),
            "mode": result.get("mode"),
            "required_keys": result.get("required_keys", []),
            "param_template": result.get("param_template", {}),
            "params": params[:20],
            "requires_approval": result.get("requires_approval"),
        }
    if tool == "zapier_action_preflight":
        selected = (
            result.get("selected_action")
            if isinstance(result.get("selected_action"), dict)
            else {}
        )
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "app": result.get("app"),
            "action": result.get("action"),
            "mode": result.get("mode"),
            "live_available": result.get("live_available"),
            "requires_oauth": result.get("requires_oauth"),
            "requires_approval": result.get("requires_approval"),
            "params_ready": result.get("params_ready"),
            "missing_params": result.get("missing_params", []),
            "provided_params": result.get("provided_params", []),
            "selected_action": {
                key: selected.get(key)
                for key in ("name", "key", "mode", "tool_name", "inventory_only")
                if key in selected
            },
            "next_step": result.get("next_step"),
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
    if tool == "github_codespaces_agent":
        selected = (
            result.get("selected_codespace")
            if isinstance(result.get("selected_codespace"), dict)
            else {}
        )
        return {
            "available": result.get("available"),
            "executed": result.get("executed", True),
            "status": result.get("status"),
            "agent_ready": result.get("agent_ready"),
            "mode": result.get("mode"),
            "target_repository": result.get("target_repository"),
            "selected_codespace": {
                key: selected.get(key)
                for key in ("name", "repository", "state", "last_used_at")
                if key in selected
            },
            "codespace_count": result.get("codespace_count"),
            "active_codespace_count": result.get("active_codespace_count"),
            "remote_commands_executed": result.get("remote_commands_executed"),
            "requires_approval_for_remote_execution": result.get(
                "requires_approval_for_remote_execution"
            ),
            "blockers": result.get("blockers", []),
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
