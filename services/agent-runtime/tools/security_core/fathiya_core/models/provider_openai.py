"""
models/provider_openai.py — مزود OpenAI مجرّد (هيكل جاهز)

يوفر واجهة موحدة للتواصل مع OpenAI API.
هذا الملف هيكل جاهز للاستخدام المستقبلي.

الاستخدام:
    from models.provider_openai import OpenAIProvider

    provider = OpenAIProvider()
    result = provider.chat(messages, model_id="gpt-4o-mini")
"""

import time
import random
import requests
from typing import Optional, List, Dict, Any

from config.settings import settings


class OpenAIProvider:
    """
    مزود خدمة OpenAI — هيكل جاهز للتكامل المستقبلي.

    المميزات:
    - واجهة موحدة مع OpenRouterProvider
    - إعادة المحاولة التلقائية
    - دعم json_mode

    ملاحظة: يتطلب OPENAI_API_KEY في .env للتفعيل.
    """

    PROVIDER_NAME = "openai"
    BASE_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.openai_api_key
        # لا نرفع خطأ هنا — المزود اختياري

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
        model_id: str = "gpt-4o-mini",
        json_mode: bool = False,
        max_retries: int = 3,
        timeout: int = 60,
    ) -> str:
        """
        إرسال طلب محادثة إلى OpenAI.

        المعاملات:
            messages    — قائمة الرسائل (system + user)
            model_id    — معرّف النموذج
            json_mode   — تفعيل وضع JSON
            max_retries — الحد الأقصى لإعادة المحاولة
            timeout     — المهلة الزمنية بالثواني

        يرجع:
            محتوى الرد النصي (مقصوص الأطراف)
        """
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY is missing. "
                "Set it in .env or as an environment variable to use OpenAI provider."
            )

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
                        f"Unexpected OpenAI API response structure: {payload}"
                    ) from e

                return content.strip()

            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = (
                    e.response.status_code if e.response is not None else None
                )

                if status_code == 404:
                    raise ValueError(
                        f"Model not found on OpenAI: {model_id}"
                    ) from e

                if status_code == 429:
                    sleep_time = min(30, (2 ** attempt) + random.uniform(1.5, 4.0))
                else:
                    sleep_time = min(15, (2 ** attempt) + random.uniform(0.8, 2.0))

                if attempt < max_retries - 1:
                    time.sleep(sleep_time)
                else:
                    break

            except requests.exceptions.RequestException as e:
                last_error = e
                sleep_time = min(15, (2 ** attempt) + random.uniform(0.8, 2.0))

                if attempt < max_retries - 1:
                    time.sleep(sleep_time)
                else:
                    break

        raise ValueError(
            f"OpenAI API request failed after {max_retries} retries: {last_error}"
        )

    def chat_json(
        self,
        messages: List[Dict[str, str]],
        model_id: str = "gpt-4o-mini",
        max_retries: int = 3,
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
