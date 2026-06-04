from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from .config import RuntimeConfig


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
    def __init__(self, config: RuntimeConfig):
        self.config = config
        self._handlers: dict[str, ToolHandler] = {
            "tool_catalog": self._tool_catalog,
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
            "kali_tool_inventory": self._kali_tool_inventory,
            "security_core_plan": self._security_core_plan,
            "command_profile": self._command_profile,
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
            )
        }

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
            elif spec.name == "connector_profile":
                item["profiles"] = connector_profiles
                item["configured"] = any(
                    bool(profile.get("configured")) for profile in connector_profiles
                )
            elif spec.name == "connector_catalog":
                item["configured"] = bool(connector_profiles)
            elif spec.name == "n8n_webhook":
                item["configured"] = bool(self.config.n8n_webhook_url)
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

    def _tool_catalog(
        self,
        _prompt: str,
        _args: dict[str, Any],
        _context: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {"available": True, "tools": self.catalog()}

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
        }

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
