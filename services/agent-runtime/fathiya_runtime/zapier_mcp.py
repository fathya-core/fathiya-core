from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

import requests

from .config import RuntimeConfig


ZAPIER_AUTHORIZATION_ENDPOINT = "https://mcp.zapier.com/oauth/authorize"
ZAPIER_REGISTRATION_ENDPOINT = "https://mcp.zapier.com/api/v1/oauth/register"
ZAPIER_TOKEN_ENDPOINT = "https://mcp.zapier.com/api/v1/oauth/token"
ZAPIER_SCOPES = "openid profile email"
MCP_PROTOCOL_VERSION = "2025-06-18"


class ZapierMCPError(RuntimeError):
    pass


class ZapierTokenStore:
    def __init__(self, path: Path, environment_access_token: str = ""):
        self.path = path
        self.environment_access_token = environment_access_token.strip()

    def load(self) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    payload = raw
            except (OSError, json.JSONDecodeError):
                payload = {}
        if self.environment_access_token:
            payload["access_token"] = self.environment_access_token
            payload["token_source"] = "environment"
        return payload

    def save(self, payload: dict[str, Any]) -> None:
        if self.environment_access_token:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
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

    def status(self) -> dict[str, Any]:
        payload = self.load()
        expires_at = float(payload.get("expires_at") or 0)
        return {
            "connected": bool(payload.get("access_token")),
            "token_source": payload.get("token_source", "oauth_file"),
            "has_refresh_token": bool(payload.get("refresh_token")),
            "expires_at": expires_at or None,
            "expired": bool(expires_at and expires_at <= time.time()),
        }


class ZapierOAuthManager:
    def __init__(self, config: RuntimeConfig, token_store: ZapierTokenStore):
        self.config = config
        self.token_store = token_store
        self.pending: dict[str, dict[str, Any]] = {}

    def start(self, callback_url: str, return_to: str) -> str:
        credentials = self.token_store.load()
        client_id = str(credentials.get("client_id") or "")
        client_secret = str(credentials.get("client_secret") or "")
        if not client_id:
            registration = self._register(callback_url)
            client_id = str(registration.get("client_id") or "")
            client_secret = str(registration.get("client_secret") or "")
            if not client_id:
                raise ZapierMCPError("Zapier OAuth registration returned no client_id")
            credentials.update(
                {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": callback_url,
                    "registration_endpoint": ZAPIER_REGISTRATION_ENDPOINT,
                    "token_endpoint": ZAPIER_TOKEN_ENDPOINT,
                }
            )
            self.token_store.save(credentials)

        verifier = secrets.token_urlsafe(64)
        challenge = _base64url(hashlib.sha256(verifier.encode("ascii")).digest())
        state = secrets.token_urlsafe(32)
        self.pending[state] = {
            "callback_url": callback_url,
            "return_to": return_to,
            "verifier": verifier,
            "client_id": client_id,
            "client_secret": client_secret,
            "expires_at": time.time() + 600,
        }
        return f"{ZAPIER_AUTHORIZATION_ENDPOINT}?{urlencode({
            'response_type': 'code',
            'client_id': client_id,
            'redirect_uri': callback_url,
            'scope': ZAPIER_SCOPES,
            'state': state,
            'code_challenge': challenge,
            'code_challenge_method': 'S256',
            'resource': self.config.zapier_mcp_url,
        })}"

    def complete(self, code: str, state: str) -> str:
        pending = self.pending.pop(state, None)
        if not pending or float(pending["expires_at"]) <= time.time():
            raise ZapierMCPError("Zapier OAuth state is missing or expired")
        response = requests.post(
            ZAPIER_TOKEN_ENDPOINT,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": pending["callback_url"],
                "client_id": pending["client_id"],
                "client_secret": pending["client_secret"],
                "code_verifier": pending["verifier"],
                "resource": self.config.zapier_mcp_url,
            },
            timeout=30,
        )
        if not response.ok:
            raise ZapierMCPError(f"Zapier OAuth token exchange returned HTTP {response.status_code}")
        token = response.json()
        if not isinstance(token, dict) or not token.get("access_token"):
            raise ZapierMCPError("Zapier OAuth token exchange returned no access token")
        credentials = self.token_store.load()
        credentials.update(token)
        credentials.update(
            {
                "client_id": pending["client_id"],
                "client_secret": pending["client_secret"],
                "redirect_uri": pending["callback_url"],
                "token_endpoint": ZAPIER_TOKEN_ENDPOINT,
                "token_source": "oauth_file",
                "expires_at": time.time() + float(token.get("expires_in") or 3600),
            }
        )
        self.token_store.save(credentials)
        return str(pending["return_to"])

    @staticmethod
    def _register(callback_url: str) -> dict[str, Any]:
        response = requests.post(
            ZAPIER_REGISTRATION_ENDPOINT,
            json={
                "client_name": "FATHIYA Local Agent Runtime",
                "redirect_uris": [callback_url],
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
            timeout=30,
        )
        if not response.ok:
            raise ZapierMCPError(
                f"Zapier OAuth registration returned HTTP {response.status_code}"
            )
        payload = response.json()
        return payload if isinstance(payload, dict) else {}


class StreamableHttpMCPClient:
    def __init__(self, config: RuntimeConfig, token_store: ZapierTokenStore):
        self.config = config
        self.token_store = token_store
        self.session = requests.Session()
        self.session_id = ""
        self.request_id = 0

    def list_tools(self) -> list[dict[str, Any]]:
        result = self._rpc("tools/list", {})
        tools = result.get("tools", []) if isinstance(result, dict) else []
        return [item for item in tools if isinstance(item, dict)]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self._rpc("tools/call", {"name": name, "arguments": arguments})
        return result if isinstance(result, dict) else {"content": result}

    def _rpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.session_id:
            self._initialize()
        try:
            return self._request(method, params)
        except ZapierMCPError as exc:
            if "session" not in str(exc).lower():
                raise
            self.session_id = ""
            self._initialize()
            return self._request(method, params)

    def _initialize(self) -> None:
        result, response = self._request_with_response(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "fathiya-agent-runtime", "version": "0.1.0"},
            },
            include_session=False,
        )
        self.session_id = str(response.headers.get("Mcp-Session-Id") or "")
        self._notification("notifications/initialized", {})
        if not isinstance(result, dict):
            raise ZapierMCPError("Zapier MCP initialize returned an invalid result")

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        result, _response = self._request_with_response(method, params)
        return result

    def _request_with_response(
        self,
        method: str,
        params: dict[str, Any],
        *,
        include_session: bool = True,
    ) -> tuple[dict[str, Any], requests.Response]:
        self.request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }
        response = self._post(payload, include_session=include_session)
        message = _mcp_message(response)
        if isinstance(message.get("error"), dict):
            raise ZapierMCPError(str(message["error"].get("message") or "Zapier MCP error"))
        result = message.get("result")
        return (result if isinstance(result, dict) else {"value": result}), response

    def _notification(self, method: str, params: dict[str, Any]) -> None:
        self._post(
            {"jsonrpc": "2.0", "method": method, "params": params},
            include_session=bool(self.session_id),
            expect_body=False,
        )

    def _post(
        self,
        payload: dict[str, Any],
        *,
        include_session: bool,
        expect_body: bool = True,
    ) -> requests.Response:
        token = self._access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
        }
        if include_session and self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        response = self.session.post(
            self.config.zapier_mcp_url,
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code == 401 and self._refresh_access_token():
            headers["Authorization"] = f"Bearer {self._access_token()}"
            response = self.session.post(
                self.config.zapier_mcp_url,
                headers=headers,
                json=payload,
                timeout=60,
            )
        if not response.ok:
            raise ZapierMCPError(f"Zapier MCP returned HTTP {response.status_code}")
        if expect_body and not response.content:
            raise ZapierMCPError("Zapier MCP returned an empty response")
        return response

    def _access_token(self) -> str:
        token = str(self.token_store.load().get("access_token") or "")
        if not token:
            raise ZapierMCPError("Zapier MCP OAuth is not connected")
        return token

    def _refresh_access_token(self) -> bool:
        credentials = self.token_store.load()
        refresh_token = str(credentials.get("refresh_token") or "")
        client_id = str(credentials.get("client_id") or "")
        if not refresh_token or not client_id:
            return False
        response = requests.post(
            str(credentials.get("token_endpoint") or ZAPIER_TOKEN_ENDPOINT),
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": str(credentials.get("client_secret") or ""),
                "resource": self.config.zapier_mcp_url,
            },
            timeout=30,
        )
        if not response.ok:
            return False
        token = response.json()
        if not isinstance(token, dict) or not token.get("access_token"):
            return False
        credentials.update(token)
        credentials["expires_at"] = time.time() + float(token.get("expires_in") or 3600)
        self.token_store.save(credentials)
        return True


class ZapierMCPGateway:
    def __init__(
        self,
        config: RuntimeConfig,
        *,
        client_factory: Callable[[], StreamableHttpMCPClient] | None = None,
    ):
        self.config = config
        self.token_store = ZapierTokenStore(
            config.zapier_mcp_token_path,
            config.zapier_mcp_access_token,
        )
        self.oauth = ZapierOAuthManager(config, self.token_store)
        self._client_factory = client_factory or (
            lambda: StreamableHttpMCPClient(config, self.token_store)
        )
        self._client: StreamableHttpMCPClient | None = None
        self._catalog_cache: tuple[float, list[dict[str, Any]]] | None = None

    @property
    def configured(self) -> bool:
        return bool(self.token_store.status()["connected"])

    def status(self) -> dict[str, Any]:
        return {
            **self.token_store.status(),
            "provider": "Zapier MCP",
            "endpoint": self.config.zapier_mcp_url,
            "direct_execution": self.configured,
        }

    def start_oauth(self, callback_url: str, return_to: str) -> str:
        return self.oauth.start(callback_url, return_to)

    def complete_oauth(self, code: str, state: str) -> str:
        return self.oauth.complete(code, state)

    def action_catalog(self, app: str = "", *, force: bool = False) -> dict[str, Any]:
        if not self.configured:
            return {
                "available": False,
                "connected": False,
                "provider": "Zapier MCP",
                "error": "Zapier MCP OAuth is not connected",
                "apps": [],
                "action_count": 0,
            }
        apps = self._apps(force=force)
        if app.strip():
            app_entry, actions = self._actions_for_app(app)
            return {
                "available": True,
                "connected": True,
                "provider": "Zapier MCP",
                "app": app_entry["app"],
                "action_count": len(actions),
                "actions": [
                    {
                        "key": item.get("key"),
                        "name": item.get("name"),
                        "tool_name": item.get("tool_name"),
                        "mode": (
                            "read"
                            if "read" in str(item.get("tool") or "").casefold()
                            else "write"
                        ),
                    }
                    for item in actions
                ],
            }
        return {
            "available": True,
            "connected": True,
            "provider": "Zapier MCP",
            "app_count": len(apps),
            "action_count": sum(int(app.get("action_count", 0)) for app in apps),
            "apps": [
                {
                    "app": app.get("app"),
                    "action_count": int(app.get("action_count", 0)),
                }
                for app in apps
            ],
        }

    def action_requirement(self, app: str, action: str) -> dict[str, Any]:
        try:
            resolved = self.resolve_action(app, action)
        except Exception as exc:
            return {
                "required": True,
                "risk_class": "external",
                "reason": f"Zapier action could not be verified: {type(exc).__name__}",
            }
        write = resolved["mode"] != "read"
        return {
            "required": write,
            "risk_class": "external" if write else "internal_owned",
            "reason": (
                f"Zapier write action {resolved['app']}/{resolved['name']} requires approval"
                if write
                else ""
            ),
        }

    def resolve_action(self, app: str, action: str) -> dict[str, Any]:
        requested_app = app.strip().casefold()
        requested_action = action.strip().casefold()
        if not requested_app or not requested_action:
            raise ZapierMCPError("Zapier app and action are required")
        app_entry, actions = self._actions_for_app(app)
        selected_api = str(app_entry.get("selected_api") or "")
        resolved = next(
            (
                item
                for item in actions
                if requested_action
                in {
                    str(item.get("key") or "").casefold(),
                    str(item.get("name") or "").casefold(),
                    str(item.get("tool_name") or "").casefold(),
                }
            ),
            None,
        )
        if not resolved:
            fuzzy = [
                item
                for item in actions
                if any(
                    requested_action in candidate or candidate in requested_action
                    for candidate in (
                        str(item.get("key") or "").casefold(),
                        str(item.get("name") or "").casefold(),
                        str(item.get("tool_name") or "").casefold(),
                    )
                    if candidate
                )
            ]
            resolved = fuzzy[0] if len(fuzzy) == 1 else None
        if not resolved:
            raise ZapierMCPError(f"Zapier action is not enabled for {app}: {action}")
        executor = str(resolved.get("tool") or "")
        return {
            "app": str(app_entry.get("app") or app),
            "selected_api": selected_api,
            "key": str(resolved.get("key") or action),
            "name": str(resolved.get("name") or action),
            "tool_name": str(resolved.get("tool_name") or ""),
            "executor": executor,
            "mode": "read" if "read" in executor.casefold() else "write",
        }

    def execute_action(
        self,
        app: str,
        action: str,
        params: dict[str, Any],
        instructions: str,
        output: str,
    ) -> dict[str, Any]:
        resolved = self.resolve_action(app, action)
        executor = self._find_tool(
            "execute_zapier_read_action"
            if resolved["mode"] == "read"
            else "execute_zapier_write_action"
        )
        result = self._client_instance().call_tool(
            executor,
            {
                "selected_api": resolved["selected_api"],
                "action": resolved["key"],
                "instructions": instructions[:2_000],
                "output": output[:1_000],
                "params": params,
            },
        )
        return {
            "available": True,
            "executed": True,
            "provider": "Zapier MCP",
            "app": resolved["app"],
            "action": resolved["name"],
            "action_key": resolved["key"],
            "mode": resolved["mode"],
            "response": _safe_result(result),
        }

    def _apps(self, *, force: bool = False) -> list[dict[str, Any]]:
        if self._catalog_cache and not force and self._catalog_cache[0] > time.time():
            return self._catalog_cache[1]
        payload = self._call_list_enabled({})
        if not isinstance(payload, dict) or not isinstance(payload.get("apps"), list):
            raise ZapierMCPError("Zapier enabled-action inventory returned an invalid payload")
        apps = [item for item in payload["apps"] if isinstance(item, dict)]
        self._catalog_cache = (time.time() + 300, apps)
        return apps

    def _actions_for_app(self, app: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        requested_app = app.strip().casefold()
        apps = self._apps()
        app_entry = next(
            (item for item in apps if str(item.get("app") or "").casefold() == requested_app),
            None,
        )
        if not app_entry:
            raise ZapierMCPError(f"Zapier app is not enabled: {app}")
        selected_api = str(app_entry.get("selected_api") or "")
        payload = self._call_list_enabled({"selected_api": selected_api})
        entries = payload if isinstance(payload, list) else [payload]
        actions: list[dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, dict) and isinstance(entry.get("actions"), list):
                actions.extend(item for item in entry["actions"] if isinstance(item, dict))
        return app_entry, actions

    def _call_list_enabled(self, arguments: dict[str, Any]) -> Any:
        result = self._client_instance().call_tool(
            self._find_tool("list_enabled"),
            arguments,
        )
        return _result_payload(result)

    def _find_tool(self, purpose: str) -> str:
        tools = self._client_instance().list_tools()
        purpose = purpose.casefold()
        for item in tools:
            name = str(item.get("name") or "")
            description = str(item.get("description") or "")
            haystack = f"{name} {description}".casefold()
            if purpose == "execute_zapier_write_action":
                if "execute_zapier_write" in haystack or "execute a write or create action" in haystack:
                    return name
            elif purpose == "execute_zapier_read_action":
                if "execute_zapier_read" in haystack or "execute a search or read action" in haystack:
                    return name
            elif purpose in haystack:
                return name
        raise ZapierMCPError(f"Zapier MCP tool is unavailable: {purpose}")

    def _client_instance(self) -> StreamableHttpMCPClient:
        if self._client is None:
            self._client = self._client_factory()
        return self._client


def _mcp_message(response: requests.Response) -> dict[str, Any]:
    content_type = str(response.headers.get("Content-Type") or "")
    if "application/json" in content_type:
        payload = response.json()
        if isinstance(payload, dict):
            return payload
    for line in response.text.splitlines():
        if not line.startswith("data:"):
            continue
        try:
            payload = json.loads(line[5:].strip())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise ZapierMCPError("Zapier MCP response was not valid JSON or SSE")


def _result_payload(result: dict[str, Any]) -> Any:
    structured = result.get("structuredContent")
    if isinstance(structured, (dict, list)):
        return structured
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "text":
                continue
            text = str(item.get("text") or "")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
    return result


def _safe_result(value: Any) -> Any:
    if isinstance(value, dict):
        value = {
            str(key): _safe_result(item)
            for key, item in value.items()
            if not _sensitive_result_key(str(key))
        }
    elif isinstance(value, list):
        value = [_safe_result(item) for item in value[:200]]
    elif isinstance(value, str):
        try:
            nested = json.loads(value)
        except json.JSONDecodeError:
            nested = None
        value = _safe_result(nested) if isinstance(nested, (dict, list)) else value[:20_000]
    elif not isinstance(value, (str, int, float, bool, type(None))):
        value = str(value)[:20_000]
    text = json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= 20_000:
        return value
    return {"truncated": True, "preview": text[:20_000]}


def _sensitive_result_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return normalized == "selected_api" or any(
        term in normalized
        for term in ("access_token", "refresh_token", "authorization", "password", "secret", "api_key")
    )


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
