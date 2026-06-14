import os
import json
import re
import time
import random
import requests
from dotenv import load_dotenv
from pydantic import ValidationError
from schemas.framer_schema import FramedProblem

load_dotenv()


class ProblemFramer:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "nvidia/nemotron-3-super-120b-a12b:free"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing in .env")

    def _extract_json_object(self, text: str) -> dict:
        cleaned = text.strip()

        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        start = cleaned.find("{")
        if start == -1:
            raise ValueError(f"No JSON object found in model response: {text}")

        brace_count = 0
        end = None

        for i in range(start, len(cleaned)):
            char = cleaned[i]
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        if end is None:
            raise ValueError(f"Could not find a complete JSON object in model response: {text}")

        candidate = cleaned[start:end]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise ValueError(f"Model returned invalid JSON after cleaning: {candidate}") from e

    def _post_with_retry(self, headers: dict, data_template: dict) -> dict:
        last_error = None

        for attempt in range(5):
            try:
                data = dict(data_template)
                data["model"] = self.model

                response = requests.post(
                    self.url,
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()
                return response.json()

            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = e.response.status_code if e.response is not None else None

                if status_code == 404:
                    raise ValueError(f"Framer model not found on OpenRouter: {self.model}") from e

                if status_code == 429:
                    sleep_time = min(30, (2 ** attempt) + random.uniform(1.5, 4.0))
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

    def frame(self, user_input: str) -> FramedProblem:
        system_instruction = """
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

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_input}
            ],
            "response_format": {"type": "json_object"}
        }

        payload = self._post_with_retry(headers, data)

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected API response structure: {payload}") from e

        parsed_data = self._extract_json_object(content)

        try:
            validated_data = FramedProblem(**parsed_data)
        except ValidationError as e:
            raise ValueError(f"Response does not match FramedProblem schema: {e}") from e

        return validated_data