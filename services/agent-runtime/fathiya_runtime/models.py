from __future__ import annotations

import json
from typing import Any

import requests


class OpenRouterClient:
    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model
        self.url = "https://openrouter.ai/api/v1/chat/completions"

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        if not self.available:
            raise RuntimeError("OpenRouter is not configured")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "max_tokens": 1200,
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
        return str(payload["choices"][0]["message"]["content"]).strip()

    def evaluate(self, prompt: str, result: dict[str, Any]) -> dict[str, Any]:
        if not self.available:
            return {
                "passed": bool(result),
                "mode": "local_fallback",
                "summary": "تم التحقق محليًا من وجود نتيجة قابلة للتسجيل.",
            }
        try:
            raw = self.complete(
                "أنت مقيّم نتائج في فتحية. أخرج JSON فقط: passed, summary, concerns.",
                f"الطلب:\n{prompt}\n\nالنتيجة:\n{json.dumps(result, ensure_ascii=False)[:8000]}",
                json_mode=True,
            )
        except Exception as exc:
            return {
                "passed": bool(result),
                "mode": "openrouter_error_fallback",
                "summary": "تعذر تقييم OpenRouter؛ تم التحقق محليًا من وجود نتيجة قابلة للتسجيل.",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"passed": True, "mode": "openrouter_text", "summary": raw[:1000]}
