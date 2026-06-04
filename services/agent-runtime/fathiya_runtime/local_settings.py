from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


LOCAL_SETTINGS_GROUPS: dict[str, dict[str, Any]] = {
    "openrouter": {
        "name": "OpenRouter",
        "description": "نماذج التخطيط والتقييم الثقيلة.",
        "restart_required": False,
        "fields": (
            {
                "name": "OPENROUTER_API_KEY",
                "label": "API key",
                "kind": "secret",
                "required": True,
            },
            {
                "name": "OPENROUTER_MODEL",
                "label": "النموذج",
                "kind": "text",
                "required": False,
                "placeholder": "openrouter/auto",
            },
        ),
    },
    "supabase": {
        "name": "Supabase",
        "description": "قناة المهام الإنتاجية.",
        "restart_required": True,
        "fields": (
            {
                "name": "SUPABASE_URL",
                "label": "Project URL",
                "kind": "url",
                "required": True,
            },
            {
                "name": "SUPABASE_SERVICE_ROLE_KEY",
                "label": "Service role key",
                "kind": "secret",
                "required": True,
            },
        ),
    },
    "n8n_local": {
        "name": "n8n المحلي",
        "description": "قراءة وتشغيل مسارات n8n المحلية.",
        "restart_required": False,
        "fields": (
            {
                "name": "N8N_BASE_URL",
                "label": "العنوان المحلي",
                "kind": "url",
                "required": False,
                "placeholder": "http://127.0.0.1:5678",
            },
            {
                "name": "N8N_API_KEY",
                "label": "API key",
                "kind": "secret",
                "required": True,
            },
        ),
    },
    "broker_testnet": {
        "name": "Binance Spot Testnet",
        "description": "حساب تداول تجريبي فقط؛ التنفيذ الحقيقي غير مدعوم.",
        "restart_required": False,
        "fields": (
            {
                "name": "FATHIYA_TRADING_TESTNET_API_KEY",
                "label": "Testnet API key",
                "kind": "secret",
                "required": True,
            },
            {
                "name": "FATHIYA_TRADING_TESTNET_API_SECRET",
                "label": "Testnet API secret",
                "kind": "secret",
                "required": True,
            },
        ),
    },
}

_FIELD_TO_GROUP = {
    field["name"]: group_id
    for group_id, group in LOCAL_SETTINGS_GROUPS.items()
    for field in group["fields"]
}
_SIMPLE_VALUE = re.compile(r"^[^\r\n\x00]{1,4096}$")
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class LocalSettingsStore:
    """Persist an allowlisted set of operator credentials without returning values."""

    def __init__(self, path: Path):
        self.path = path.resolve()

    def load_into_environment(self, *, override: bool = False) -> None:
        for name, value in self._load_values().items():
            if override or not os.getenv(name):
                os.environ[name] = value

    def status(self) -> dict[str, Any]:
        stored = self._load_values()
        groups: list[dict[str, Any]] = []
        for group_id, definition in LOCAL_SETTINGS_GROUPS.items():
            fields = []
            for field in definition["fields"]:
                name = str(field["name"])
                source = (
                    "local_store"
                    if name in stored
                    else "environment"
                    if bool(os.getenv(name))
                    else "missing"
                )
                fields.append(
                    {
                        **field,
                        "configured": source != "missing",
                        "source": source,
                        "clearable": source == "local_store",
                    }
                )
            groups.append(
                {
                    "id": group_id,
                    "name": definition["name"],
                    "description": definition["description"],
                    "restart_required": definition["restart_required"],
                    "fields": fields,
                    "configured_count": sum(
                        bool(field["configured"]) for field in fields
                    ),
                }
            )
        return {
            "groups": groups,
            "security": {
                "values_returned": False,
                "allowlisted_fields_only": True,
                "storage_path": "ignored_local_runtime/operator-settings.json",
            },
        }

    def update_group(
        self,
        group_id: str,
        values: dict[str, Any],
        clear: list[Any],
    ) -> dict[str, Any]:
        definition = LOCAL_SETTINGS_GROUPS.get(group_id)
        if not definition:
            raise ValueError("Unknown local settings group")
        allowed = {str(field["name"]): field for field in definition["fields"]}
        if not isinstance(values, dict):
            raise ValueError("values must be an object")
        if not isinstance(clear, list):
            raise ValueError("clear must be an array")
        unknown = (set(values) | {str(name) for name in clear}) - set(allowed)
        if unknown:
            raise ValueError("Settings request contains fields outside the allowlist")

        existing = self._load_values()
        previous = dict(existing)
        updated_fields: list[str] = []
        cleared_fields: list[str] = []
        for name, raw_value in values.items():
            if not isinstance(raw_value, str):
                raise ValueError(f"{name} must be a string")
            clean = raw_value.strip()
            if not clean:
                continue
            self._validate_value(name, clean, str(allowed[name]["kind"]))
            existing[name] = clean
            os.environ[name] = clean
            updated_fields.append(name)
        for raw_name in clear:
            name = str(raw_name)
            old_value = existing.pop(name, None)
            if old_value is not None:
                cleared_fields.append(name)
            if old_value is not None and os.getenv(name) == old_value:
                os.environ.pop(name, None)

        self._save_values(existing)
        return {
            "group_id": group_id,
            "updated_fields": updated_fields,
            "cleared_fields": cleared_fields,
            "changed": existing != previous,
            "restart_required": bool(definition["restart_required"]),
            "settings": self.status(),
        }

    def _load_values(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        values = payload.get("values", {}) if isinstance(payload, dict) else {}
        if not isinstance(values, dict):
            return {}
        return {
            str(name): str(value)
            for name, value in values.items()
            if name in _FIELD_TO_GROUP and isinstance(value, str) and value
        }

    def _save_values(self, values: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "updated_at": datetime.now(UTC).isoformat(),
            "values": values,
        }
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        temporary.replace(self.path)
        try:
            self.path.chmod(0o600)
        except OSError:
            pass

    @staticmethod
    def _validate_value(name: str, value: str, kind: str) -> None:
        if not _SIMPLE_VALUE.fullmatch(value):
            raise ValueError(f"{name} contains invalid characters or is too long")
        if kind != "url":
            return
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{name} must be an HTTP(S) URL")
        if name == "N8N_BASE_URL" and parsed.hostname not in _LOOPBACK_HOSTS:
            raise ValueError("N8N_BASE_URL must point to a loopback host")
        if name == "SUPABASE_URL" and parsed.scheme != "https":
            raise ValueError("SUPABASE_URL must use HTTPS")
