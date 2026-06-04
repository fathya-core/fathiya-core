from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests

from .config import RuntimeConfig


class ToolExecutor:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def execute(self, tool: str, prompt: str) -> dict[str, Any]:
        handlers = {
            "internal_echo": self._internal_echo,
            "repo_status": self._repo_status,
            "n8n_status": self._n8n_status,
            "connected_tool_inventory": self._connected_tool_inventory,
            "kali_tool_inventory": self._kali_tool_inventory,
            "security_core_plan": self._security_core_plan,
        }
        if tool not in handlers:
            raise ValueError(f"Tool is not allowlisted: {tool}")
        return handlers[tool](prompt)

    @staticmethod
    def _internal_echo(prompt: str) -> dict[str, Any]:
        return {
            "tool": "internal_echo",
            "executed": True,
            "message": "اكتمل إثبات التنفيذ الداخلي.",
            "prompt_excerpt": prompt[:240],
        }

    def _repo_status(self, _prompt: str) -> dict[str, Any]:
        result = self._run(["git", "status", "--short"], cwd=self.config.repo_root)
        return {
            "tool": "repo_status",
            "repo": str(self.config.repo_root),
            "clean": not bool(result["stdout"].strip()),
            **result,
        }

    def _n8n_status(self, _prompt: str) -> dict[str, Any]:
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
                        "tool": "n8n_status",
                        "available": True,
                        "endpoint": path,
                        "status_code": response.status_code,
                        "body": response.text[:500],
                        "version": version["stdout"].strip() or None,
                    }
                errors.append(f"{path}: HTTP {response.status_code}")
            except requests.RequestException as exc:
                errors.append(f"{path}: {exc}")
        return {"tool": "n8n_status", "available": False, "errors": errors}

    def _connected_tool_inventory(self, _prompt: str) -> dict[str, Any]:
        path = self.config.tool_inventory_path
        if not path.exists():
            return {
                "tool": "connected_tool_inventory",
                "available": False,
                "path": str(path),
                "error": "Connected tool inventory is missing",
            }
        inventory = json.loads(path.read_text(encoding="utf-8"))
        apps = inventory.get("zapier_apps", [])
        return {
            "tool": "connected_tool_inventory",
            "available": True,
            "path": str(path),
            "captured_at": inventory.get("captured_at"),
            "policy": inventory.get("policy", {}),
            "local_tools": inventory.get("local_tools", []),
            "zapier_app_count": len(apps),
            "zapier_action_count": sum(int(app.get("action_count", 0)) for app in apps),
            "zapier_apps": apps,
            "agent_provider_actions": inventory.get("agent_provider_actions", {}),
        }

    def _kali_tool_inventory(self, _prompt: str) -> dict[str, Any]:
        commands = ["nmap", "nuclei", "httpx", "subfinder", "git", "python3"]
        script = "command -v " + " ".join(commands) + " || true"
        result = self._run(
            ["wsl.exe", "-d", self.config.kali_wsl_distro, "--", "bash", "-lc", script],
            cwd=self.config.repo_root,
            timeout=30,
        )
        found = [line.strip() for line in result["stdout"].splitlines() if line.strip()]
        return {"tool": "kali_tool_inventory", "found": found, **result}

    def _security_core_plan(self, prompt: str) -> dict[str, Any]:
        core_root = (
            self.config.service_root / "tools" / "security_core" / "fathiya_core"
        ).resolve()
        code = (
            "import json,sys;"
            "sys.path.insert(0,'.');"
            "from core.orchestrator import FathiyaOrchestrator;"
            "r=FathiyaOrchestrator().run(sys.argv[1]);"
            "print(json.dumps({'final_answer':r.get('final_answer'),"
            "'analysis':r.get('analysis'),"
            "'session_id':r.get('session_id')},ensure_ascii=False,default=str))"
        )
        result = self._run([sys.executable, "-c", code, prompt], cwd=core_root, timeout=90)
        try:
            output = json.loads(result["stdout"])
        except json.JSONDecodeError:
            output = {"raw": result["stdout"][:8000]}
        return {"tool": "security_core_plan", "output": output, "stderr": result["stderr"]}

    @staticmethod
    def _run(command: list[str], *, cwd: Path, timeout: int = 20) -> dict[str, Any]:
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
            "stdout": completed.stdout[:10_000],
            "stderr": completed.stderr[:4_000],
        }
