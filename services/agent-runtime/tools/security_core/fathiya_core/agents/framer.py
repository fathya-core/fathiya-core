"""
agents/framer.py — وكيل تحليل وتأطير المشكلات
يعيد تصدير المنطق الأصلي من domains/security/framer.py
للتوافق مع استيرادات orchestrator.py
"""

import os
import json
import re
import time
import random
import requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pydantic import ValidationError
from schemas.target_schema import FramedProblem

load_dotenv()


class ProblemFramer:
    def __init__(self) -> None:
        self.api_key: str = os.getenv("OPENROUTER_API_KEY", "")
        self.url: str = "https://openrouter.ai/api/v1/chat/completions"
        self.model: str = "nvidia/nemotron-3-super-120b-a12b:free"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing in .env")

    def _extract_json_object(self, text: str) -> Dict[str, Any]:
        """استخراج كائن JSON من رد النموذج مع تنظيف markdown fences"""
        cleaned: str = text.strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start: int = cleaned.find("{")
        if start == -1:
            raise ValueError(f"No JSON object found in model response: {text}")

        brace_count: int = 0
        end: Optional[int] = None

        for i in range(start, len(cleaned)):
            char: str = cleaned[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        if end is None:
            raise ValueError(f"Could not find a complete JSON object in model response: {text}")

        candidate: str = cleaned[start:end]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model returned invalid JSON after cleaning: {candidate}") from e

    def _post_with_retry(self, headers: Dict[str, str], data_template: Dict[str, Any]) -> Dict[str, Any]:
        """إرسال طلب API مع إعادة المحاولة (حتى 5 مرات)"""
        last_error: Optional[Exception] = None

        for attempt in range(5):
            try:
                data: Dict[str, Any] = dict(data_template)
                data["model"] = self.model

                response: requests.Response = requests.post(
                    self.url,
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code: Optional[int] = e.response.status_code if e.response is not None else None

                if status_code == 404:
                    raise ValueError(f"Framer model not found on OpenRouter: {self.model}") from e

                if status_code == 429:
                    sleep_time: float = min(30, (2 ** attempt) + random.uniform(1.5, 4.0))
                else:
                    sleep_time = min(15, (2 ** attempt) + random.uniform(0.8, 2.0))

                if attempt < 4:
                    time.sleep(sleep_time)
                else:
                    break

            except requests.exceptions.RequestException as e:
                last_error = e
                sleep_time = min(15, (2 ** attempt) + random.uniform(0.8, 2.0))

                if attempt < 4:
                    time.sleep(sleep_time)
                else:
                    break

        raise ValueError(f"Framer API request failed after retries: {last_error}")

    def _fallback_frame(self, reason: str) -> FramedProblem:
        return FramedProblem(
            problem_type="research",
            clarity_score=6,
            needs_research=True,
            needs_clarification=True,
            missing_information=[reason],
            handling_strategy="research_first",
            sub_tasks=[
                "Confirm authorized scope and stop conditions.",
                "Collect non-destructive evidence requirements.",
                "Avoid live probing until missing requirements are resolved.",
            ],
        )

    def frame(self, user_input: str) -> FramedProblem:
        """تأطير وتشخيص طبيعة المسألة — يرجع FramedProblem"""
        system_instruction: str = """
أنت 'كاشف ضبابية' في FATHIYA CORE.
مهمتك تشخيص طبيعة المسألة فقط.
ممنوع تقديم حلول أو نصائح.

أخرج JSON فقط.

الحقول المطلوبة:
problem_type
clarity_score
needs_research
needs_clarification
missing_information
handling_strategy
sub_tasks

القواعد الأساسية:

1) التفريق الحاسم:
- إذا كان السؤال عامًا (مثل: "أبي أسوي مشروع"):
  لا تجعله يحتاج توضيح
  needs_clarification = false
  handling_strategy = direct_execution

- إذا كان السؤال ناقص معلومات تمنع التنفيذ:
  needs_clarification = true
  handling_strategy = clarify_first

2) needs_research:
- true فقط إذا كانت الإجابة تحتاج معلومات خارج السؤال (بيانات، أخبار، أرقام)
- false في:
  - التعلم
  - المشاريع
  - الخطط
  - الأسئلة العامة

3) clarity_score:
- 1-3 = غامض جدًا
- 4-6 = متوسط
- 7-10 = واضح

4) handling_strategy:
- clarify_first → فقط إذا لا يمكن البدء بدون معلومات
- direct_execution → إذا يمكن إعطاء جواب أو اقتراح مبدئي
- research_first → فقط إذا يحتاج بحث خارجي
- analysis_then_execution → إذا يحتاج تحليل قبل الحل

5) sub_tasks:
- مراحل فهم فقط
- لا تكتب خطوات تنفيذ

6) اللغة:
- الحقول إنجليزية
- القيم التفسيرية عربية
- لا تستخدم أي لغة أخرى

أمثلة:

سؤال: "أبي أسوي مشروع"
→ needs_clarification = false
→ handling_strategy = direct_execution

سؤال: "أبي أبني تطبيق توصيل مثل هنقرستيشن"
→ needs_clarification = false
→ direct_execution

سؤال: "كيف أحلل بيانات شركة X في 2025"
→ needs_research = true
→ research_first

ممنوع:
- إضافة أي نص خارج JSON
- شرح إضافي
"""

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data: Dict[str, Any] = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            "response_format": {"type": "json_object"}
        }

        try:
            payload: Dict[str, Any] = self._post_with_retry(headers, data)
        except ValueError as e:
            return self._fallback_frame(str(e)[:240])

        try:
            content: str = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected API response structure: {payload}") from e

        try:
            parsed_data: Dict[str, Any] = self._extract_json_object(content)
        except ValueError as e:
            return self._fallback_frame(str(e)[:240])

        try:
            validated_data: FramedProblem = FramedProblem(**parsed_data)
        except ValidationError as e:
            return self._fallback_frame(f"Response does not match FramedProblem schema: {e}"[:240])

        return validated_data
