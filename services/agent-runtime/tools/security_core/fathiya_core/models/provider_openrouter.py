"""
models/provider_openrouter.py — مزود OpenRouter مجرّد

يوفر واجهة موحدة للتواصل مع OpenRouter API.
يمكن استخدامه مباشرة أو عبر ModelRegistry.

الاستخدام:
    from models.provider_openrouter import OpenRouterProvider

    provider = OpenRouterProvider()
    result = provider.chat(messages, model_id="nvidia/nemotron-3-super-120b-a12b:free")
"""

import time
import random
import requests
from typing import Optional, List, Dict, Any

from config.settings import settings


class OpenRouterProvider:
    """
    مزود خدمة OpenRouter — يتعامل مع API بشكل مجرّد.

    المميزات:
    - إعادة المحاولة التلقائية مع تأخير تصاعدي
    - دعم json_mode
    - إدارة مركزية للترويسات والمهلة الزمنية
    """

    PROVIDER_NAME = "openrouter"
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openrouter_api_key
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing")

    @property
    def headers(self) -> dict:
        """ترويسات HTTP"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        model_id: str = "nvidia/nemotron-3-super-120b-a12b:free",
        json_mode: bool = False,
        max_retries: int = 5,
        timeout: int = 60,
    ) -> str:
        """
        إرسال طلب محادثة إلى OpenRouter.

        المعاملات:
            messages    — قائمة الرسائل (system + user)
            model_id    — معرّف النموذج
            json_mode   — تفعيل وضع JSON
            max_retries — الحد الأقصى لإعادة المحاولة
            timeout     — المهلة الزمنية بالثواني

        يرجع:
            محتوى الرد النصي (مقصوص الأطراف)
        """
        data: Dict[str, Any] = {
            "model": model_id,
            "messages": messages,
        }

        if json_mode:
            data["response_format"] = {"type": "json_object"}

        last_error = None

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.BASE_URL,
                    headers=self.headers,
                    json=data,
                    timeout=timeout,
                )
                response.raise_for_status()

                payload = response.json()

                try:
                    content = payload["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as e:
                    raise ValueError(
                        f"Unexpected API response structure: {payload}"
                    ) from e

                return content.strip()

            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = (
                    e.response.status_code if e.response is not None else None
                )

                # خطأ 404 = النموذج غير موجود — لا فائدة من إعادة المحاولة
                if status_code == 404:
                    raise ValueError(
                        f"Model not found on OpenRouter: {model_id}"
                    ) from e

                # خطأ 429 = تجاوز حد الطلبات — تأخير أطول
                if status_code == 429:
                    sleep_time = min(
                        settings.retry.rate_limit_delay,
                        (2 ** attempt) + random.uniform(1.5, 4.0),
                    )
                else:
                    sleep_time = min(
                        settings.retry.max_delay / 2,
                        (2 ** attempt) + random.uniform(
                            settings.retry.jitter_min,
                            settings.retry.jitter_max,
                        ),
                    )

                if attempt < max_retries - 1:
                    time.sleep(sleep_time)
                else:
                    break

            except requests.exceptions.RequestException as e:
                last_error = e
                sleep_time = min(
                    settings.retry.max_delay / 2,
                    (2 ** attempt) + random.uniform(
                        settings.retry.jitter_min,
                        settings.retry.jitter_max,
                    ),
                )

                if attempt < max_retries - 1:
                    time.sleep(sleep_time)
                else:
                    break

        raise ValueError(
            f"OpenRouter API request failed after {max_retries} retries: {last_error}"
        )

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        model_id: str = "nvidia/nemotron-3-super-120b-a12b:free",
        max_retries: int = 5,
        timeout: int = 60,
    ) -> str:
        """اختصار لـ chat() مع تفعيل json_mode"""
        return self.chat(
            messages=messages,
            model_id=model_id,
            json_mode=True,
            max_retries=max_retries,
            timeout=timeout,
        )

    def is_available(self) -> bool:
        """التحقق من توفر مفتاح API"""
        return bool(self.api_key)
