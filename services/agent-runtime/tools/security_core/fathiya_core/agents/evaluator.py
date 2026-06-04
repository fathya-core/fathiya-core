"""
agents/evaluator.py — وكيل تقييم جودة الردود
يعيد بناء المنطق الأصلي من domains/security/evaluator.py
للتوافق مع استيرادات orchestrator.py
"""

import os
import json
import re
import time
import requests
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal

load_dotenv()


class EvaluationResult(BaseModel):
    """نتيجة التقييم — verdict + reason + revision_note"""
    verdict: Literal["approve", "revise"]
    reason: str
    revision_note: str


class ResponseEvaluator:
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

    def evaluate(self, user_input: str, solver_answer: str) -> EvaluationResult:
        """تقييم جواب الـ Solver — يرجع EvaluationResult"""
        system_instruction: str = """
أنت Evaluator صارم في FATHIYA CORE.
مهمتك: فحص جواب الـ Solver قبل اعتماده.

أخرج JSON فقط بهذه الحقول:
verdict
reason
revision_note

القواعد:
- verdict must be one of: approve, revise
- reason: شرح قصير جدًا بالعربية
- revision_note: ملاحظة تنفيذية محددة جدًا تصف ما يجب إصلاحه
- إذا كان verdict=approve فاجعل revision_note فارغة
- ممنوع verdict=revise مع revision_note فارغة

اختر revise فورًا إذا وجد واحد أو أكثر من التالي:
1) خلط لغات غير ضروري أو كلمات غريبة من لغات أخرى
2) مخالفة واضحة لطلب المستخدم (مثل 30 يوم وتحولت إلى 40 أو 70)
3) حشو أو تطويل واضح
4) وجود جداول أو تنسيق ثقيل بلا حاجة
5) رد غير مباشر بينما الطلب مباشر
6) خطة أو قائمة غير منضبطة أو فيها تكرار أو ضعف هيكلة
7) بقاء شوائب مثل كلمات غير عربية أو غير تقنية داخل نص عربي

اختر approve فقط إذا:
- الرد مناسب مباشرة لطلب المستخدم
- منظم وواضح
- خالٍ من خلط اللغات غير الضروري
- ملتزم بالمدة أو العدد أو القيود المذكورة
- لا يحتاج تعديل جوهري

قواعد مهمة:
- المصطلحات التقنية الشائعة فقط مسموحة بالإنجليزية مثل Python و pandas و NumPy و CSV
- أي كلمات فرنسية/إسبانية/صينية/يابانية/روسية/كورية داخل الرد العربي تعتبر خللًا
- إذا كان طلب المستخدم يحتوي على مدة أو عدد، افحص الالتزام به بدقة
- إذا طلب المستخدم خطة 30 يومًا، فأي تجاوز لهذا العدد = revise
- revision_note يجب أن تكون قابلة للتنفيذ مباشرة بواسطة Solver

أمثلة revision_note جيدة:
- "أعد كتابة الجواب بالعربية النظيفة فقط، واحذف أي كلمات من لغات أخرى غير المصطلحات التقنية الضرورية."
- "اختصر الخطة لتلتزم بـ30 يومًا فقط، ولا تتجاوز اليوم 30."
- "حوّل الرد إلى نقاط قصيرة وواضحة بدون حشو."
- "أجب مباشرة بدل طرح أسئلة إضافية."

لا تذكر أنك Evaluator.
لا تشرح النظام الداخلي.
"""

        user_prompt: str = f"""
طلب المستخدم:
{user_input}

جواب الـ Solver:
{solver_answer}

راجع الجواب الآن وأخرج JSON فقط.
"""

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"}
        }

        payload: Optional[Dict[str, Any]] = None

        for attempt in range(3):
            try:
                response: requests.Response = requests.post(self.url, headers=headers, json=data, timeout=40)
                response.raise_for_status()
                payload = response.json()
                break
            except requests.exceptions.RequestException as e:
                if attempt < 2:
                    time.sleep(2)
                else:
                    raise ValueError(f"Evaluator API request failed after 3 attempts: {e}") from e

        try:
            content: str = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError(f"Unexpected API response structure: {payload}") from e

        parsed: Dict[str, Any] = self._extract_json_object(content)
        return EvaluationResult(**parsed)
