from __future__ import annotations

import json
from typing import Any, Protocol

import requests


class ModelClient(Protocol):
    model: str
    last_provider: str

    @property
    def available(self) -> bool: ...

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        max_new_tokens: int | None = None,
    ) -> str: ...

    def evaluate(self, prompt: str, result: dict[str, Any]) -> dict[str, Any]: ...


class OpenRouterClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.last_provider = "openrouter"

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        max_new_tokens: int | None = None,
    ) -> str:
        if not self.available:
            raise RuntimeError("OpenRouter is not configured")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": max_new_tokens or 1200,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        response = requests.post(
            self.url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://fathya-core.com",
                "X-Title": "FATHIYA Local Agent Runtime",
            },
            json=body,
            timeout=75,
        )
        response.raise_for_status()
        payload = response.json()
        self.last_provider = "openrouter"
        return str(payload["choices"][0]["message"]["content"]).strip()

    def evaluate(self, prompt: str, result: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return _local_result_check(result)
        try:
            raw = self.complete(
                "أنت مقيّم نتائج في فتحية. أخرج JSON فقط: passed, summary, concerns.",
                f"الطلب:\n{prompt}\n\nالنتيجة:\n{json.dumps(result, ensure_ascii=False)[:8000]}",
                json_mode=True,
            )
        except Exception as exc:
            return {
                **_local_result_check(result),
                "mode": "openrouter_error_fallback",
                "summary": "تعذر تقييم OpenRouter؛ تم التحقق محليًا من وجود نتيجة قابلة للتسجيل.",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }
        return _parse_evaluation(raw, "openrouter")


class LocalHuggingFaceClient:
    def __init__(
        self,
        enabled: bool,
        model: str,
        max_new_tokens: int,
        max_generation_seconds: float = 20.0,
    ):
        self.enabled = enabled
        self.model = model
        self.max_new_tokens = max_new_tokens
        self.max_generation_seconds = max_generation_seconds
        self.last_provider = "huggingface_local"
        self._tokenizer: Any = None
        self._model: Any = None

    @property
    def available(self) -> bool:
        return self.enabled

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        max_new_tokens: int | None = None,
    ) -> str:
        if not self.available:
            raise RuntimeError("Local Hugging Face generation is not enabled")
        self._load()
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        if json_mode:
            messages[0]["content"] += " Return one valid JSON object and no markdown."
        if hasattr(self._tokenizer, "apply_chat_template"):
            rendered = self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            rendered = f"System: {system}\nUser: {user}\nAssistant:"
        inputs = self._tokenizer(rendered, return_tensors="pt")
        generated = self._model.generate(
            **inputs,
            max_new_tokens=min(self.max_new_tokens, max_new_tokens or self.max_new_tokens),
            max_time=self.max_generation_seconds,
            do_sample=False,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        new_tokens = generated[0][inputs["input_ids"].shape[1] :]
        self.last_provider = "huggingface_local"
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def evaluate(self, prompt: str, result: dict[str, Any]) -> dict[str, Any]:
        try:
            raw = self.complete(
                "أنت مقيّم نتائج في فتحية. أخرج JSON فقط: passed, summary, concerns.",
                f"الطلب:\n{prompt}\n\nالنتيجة:\n{json.dumps(result, ensure_ascii=False)[:8000]}",
                json_mode=True,
            )
            return _parse_evaluation(raw, "huggingface_local")
        except Exception as exc:
            return {
                **_local_result_check(result),
                "mode": "huggingface_error_fallback",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(self.model)
        self._model = AutoModelForCausalLM.from_pretrained(self.model)
        self._model.eval()


class AgentModelRouter:
    def __init__(
        self,
        openrouter_api_key: str,
        openrouter_model: str,
        *,
        enable_local_generation: bool,
        local_model: str,
        local_max_new_tokens: int,
        enable_local_planning: bool = False,
        local_max_generation_seconds: float = 20.0,
    ):
        self.openrouter = OpenRouterClient(openrouter_api_key, openrouter_model)
        self.local = LocalHuggingFaceClient(
            enable_local_generation,
            local_model,
            local_max_new_tokens,
            local_max_generation_seconds,
        )
        self.enable_local_planning = enable_local_planning
        self.model = (
            self.openrouter.model
            if self.openrouter.available
            else f"local:{self.local.model}"
            if self.local.available
            else "local_deterministic"
        )
        self.last_provider = "not_run"
        self.last_error: str | None = None

    @property
    def available(self) -> bool:
        return self.openrouter.available or self.local.available

    def complete(
        self,
        system: str,
        user: str,
        *,
        json_mode: bool = False,
        max_new_tokens: int | None = None,
    ) -> str:
        errors: list[str] = []
        for client in (self.openrouter, self.local):
            if not client.available:
                continue
            try:
                result = client.complete(
                    system,
                    user,
                    json_mode=json_mode,
                    max_new_tokens=max_new_tokens,
                )
                self.last_provider = client.last_provider
                self.last_error = "; ".join(errors) or None
                return result
            except Exception as exc:
                errors.append(f"{client.last_provider}: {type(exc).__name__}: {str(exc)[:500]}")
        self.last_error = "; ".join(errors) or "No model provider is configured"
        raise RuntimeError(self.last_error)

    def plan_complete(self, system: str, user: str, *, json_mode: bool = True) -> str:
        errors: list[str] = []
        if self.openrouter.available:
            try:
                result = self.openrouter.complete(system, user, json_mode=json_mode)
                self.last_provider = self.openrouter.last_provider
                self.last_error = None
                return result
            except Exception as exc:
                errors.append(f"openrouter: {type(exc).__name__}: {str(exc)[:500]}")
        if self.enable_local_planning and self.local.available:
            try:
                result = self.local.complete(
                    system,
                    user,
                    json_mode=json_mode,
                    max_new_tokens=160,
                )
                self.last_provider = self.local.last_provider
                self.last_error = "; ".join(errors) or None
                return result
            except Exception as exc:
                errors.append(f"huggingface_local: {type(exc).__name__}: {str(exc)[:500]}")
        if self.local.available and not self.enable_local_planning:
            errors.append("local planning disabled; using deterministic planner")
        self.last_error = "; ".join(errors) or "No planning model provider is configured"
        raise RuntimeError(self.last_error)

    def synthesize(self, system: str, user: str) -> str:
        errors: list[str] = []
        if self.openrouter.available:
            try:
                result = self.openrouter.complete(
                    system,
                    user,
                    max_new_tokens=700,
                )
                self.last_provider = self.openrouter.last_provider
                self.last_error = None
                return result
            except Exception as exc:
                errors.append(f"openrouter: {type(exc).__name__}: {str(exc)[:500]}")
        if self.local.available:
            try:
                result = self.local.complete(
                    system,
                    user,
                    max_new_tokens=96,
                )
                self.last_provider = self.local.last_provider
                self.last_error = "; ".join(errors) or None
                return result
            except Exception as exc:
                errors.append(f"huggingface_local: {type(exc).__name__}: {str(exc)[:500]}")
        self.last_error = "; ".join(errors) or "No synthesis model provider is configured"
        raise RuntimeError(self.last_error)

    def evaluate(self, prompt: str, result: dict[str, Any]) -> dict[str, Any]:
        if self.openrouter.available:
            evaluation = self.openrouter.evaluate(prompt, result)
            self.last_provider = self.openrouter.last_provider
            if evaluation.get("mode") == "openrouter_error_fallback":
                self.last_error = (
                    f"openrouter: {evaluation.get('error_type')}: "
                    f"{str(evaluation.get('error', ''))[:500]}"
                )
            else:
                self.last_error = None
            return evaluation
        return {
            **_local_result_check(result),
            "mode": "local_deterministic_evaluation",
            "summary": "تم التحقق محليًا من وجود نتائج أدوات قابلة للتسجيل.",
        }


def _local_result_check(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "passed": bool(result),
        "mode": "local_fallback",
        "summary": "تم التحقق محليًا من وجود نتيجة قابلة للتسجيل.",
    }


def _parse_evaluation(raw: str, provider: str) -> dict[str, Any]:
    try:
        payload = _json_object(raw)
        if isinstance(payload, dict):
            payload.setdefault("mode", provider)
            return payload
    except (json.JSONDecodeError, ValueError):
        pass
    return {"passed": True, "mode": f"{provider}_text", "summary": raw[:1000]}


def _json_object(raw: str) -> dict[str, Any]:
    start = raw.find("{")
    if start < 0:
        raise ValueError("No JSON object found")
    payload, _end = json.JSONDecoder().raw_decode(raw[start:])
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object")
    return payload
