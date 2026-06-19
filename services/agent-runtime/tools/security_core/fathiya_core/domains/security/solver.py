import os
import time
import random
import requests
from dotenv import load_dotenv

from schemas.framer_schema import FramedProblem

load_dotenv()


class ProblemSolver:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.url = "https://openrouter.ai/api/v1/chat/completions"

        # موديل واحد مستقر حاليًا في مشروعك
        self.model = "nvidia/nemotron-3-super-120b-a12b:free"

        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing in .env")

    def _post_with_retry(self, messages: list) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        last_error = None

        for attempt in range(5):
            try:
                data = {
                    "model": self.model,
                    "messages": messages
                }

                response = requests.post(
                    self.url,
                    headers=headers,
                    json=data,
                    timeout=60
                )
                response.raise_for_status()

                payload = response.json()

                try:
                    content = payload["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as e:
                    raise ValueError(f"Unexpected Solver API response structure: {payload}") from e

                return content.strip()

            except requests.exceptions.HTTPError as e:
                last_error = e
                status_code = e.response.status_code if e.response is not None else None

                if status_code == 404:
                    raise ValueError(f"Solver model not found on OpenRouter: {self.model}") from e

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

        raise ValueError(f"Solver API request failed after retries: {last_error}")

    def solve(self, user_input: str, framed_problem: FramedProblem) -> str:
        system_instruction = """
أنت Solver في FATHIYA CORE.
مهمتك: إنتاج الرد المناسب للمستخدم بناءً على:
1) السؤال الأصلي
2) تقرير التشخيص القادم من Framer

قواعد سلوكية أساسية:
- إذا لم يذكر المستخدم مستواه أو خبرته، فافترض أنه مبتدئ
- إذا كان الطلب عامًا، فابدأ بأبسط حل صالح وأقلها تعقيدًا
- لا تقفز مباشرة إلى تقنيات ثقيلة مثل React و Node.js و MongoDB إلا إذا طلب المستخدم ذلك أو ظهرت خبرته التقنية بوضوح
- إذا كان السؤال عن مشروع بشكل عام، فاقترح مشروعًا صغيرًا أو مشروعين كحد أقصى
- عند اقتراح مشروع، قدم شيئًا يمكن البدء به بسرعة وبأقل تعقيد ممكن
- فضّل المشاريع التي يمكن تنفيذها بأدوات بسيطة أو بتقنيات أساسية قبل اقتراح بنية احترافية كبيرة
- إذا كان المستخدم يبدو مبتدئًا، ففضّل:
  - مشروع صفحة بسيطة
  - أداة سطر أوامر بسيطة
  - مشروع Python صغير
  - مشروع HTML/CSS/JavaScript بسيط
- لا تفترض بنية شركات أو نشر أو قواعد بيانات أو مصادقة إلا إذا احتاجها الطلب فعلًا

إذا طلب المستخدم خطة زمنية:
- التزم بالمدة المطلوبة حرفيًا
- لا تتجاوز العدد المطلوب من الأيام
- لا تضف أيامًا خارج العدد المطلوب
- لا تحول الرد إلى درس نظري طويل

قواعد صارمة:
- لا تذكر JSON
- لا تذكر Framer
- لا تذكر handling_strategy
- لا تشرح النظام الداخلي
- قدّم ردًا مباشرًا وواضحًا ومفيدًا

قواعد صارمة جدًا للمخرج:
- التزم تمامًا بطلب المستخدم ولا توسع النطاق
- إذا طلب المستخدم خطة 30 يوم، فلا تتجاوز 30 يومًا
- لا تستخدم جداول
- لا تستخدم كلمات أو جمل بأي لغة غير العربية إلا للمصطلحات التقنية الضرورية مثل Python و pandas و NumPy
- لا تخلط العربية بلغات أخرى
- اجعل الرد منظمًا على شكل عناوين ونقاط قصيرة
- تجنب الحشو والشرح الطويل
- إذا كان السؤال مباشرًا، أجب مباشرة بدون مقدمات طويلة
- اجعل الإخراج عمليًا وقابلًا للتنفيذ

منطق التعامل:
- إذا كانت handling_strategy = clarify_first:
  لا تطرح أسئلة إضافية مباشرة
  بل قدّم للمستخدم اقتراحًا أوليًا بسيطًا أو خيارين مناسبين مبدئيًا
  ثم اختم بسطر قصير يفتح المجال للتخصيص إذا أراد
- إذا كانت handling_strategy = research_first:
  اشرح باختصار ماذا يجب البحث عنه أولًا، ثم أعطِ مسارًا أوليًا
- إذا كانت handling_strategy = direct_execution:
  أعطِ جوابًا مباشرًا ومنظمًا
- إذا كانت handling_strategy = analysis_then_execution:
  ابدأ بتحليل مختصر، ثم أعطِ الجواب العملي

قواعد خاصة باقتراح المشاريع:
- إذا قال المستخدم فقط "أبي أسوي مشروع" أو ما يشبهها، فلا تطلب منه تفاصيل أولًا
- أعطه اقتراحًا أوليًا مباشرًا منخفض التعقيد
- اجعل الاقتراح مناسبًا لشخص قد يكون في بداية التعلم
- مثال جيد:
  مشروع بسيط لإدارة المهام أو تتبع المصروفات أو منظم ملاحظات
- مثال سيئ:
  منصة كاملة بمكدس تقني ثقيل وبنية متعددة الطبقات من أول رد

الحد الأعلى للطول:
- اجعل الرد متوسط الطول
- لا تكتب أكثر مما يلزم لإنجاز الطلب

قواعد الأسلوب:
- اكتب بالعربية
- يسمح باستخدام المصطلحات التقنية الشائعة بالإنجليزية إذا كانت أوضح
- اجعل الرد منظمًا ومختصرًا ومفيدًا
"""

        framed_json = framed_problem.model_dump_json(indent=2)

        user_prompt = f"""
السؤال الأصلي:
{user_input}

تقرير التشخيص:
{framed_json}

الآن أنتج الرد المناسب للمستخدم.
"""

        return self._post_with_retry([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])

    def revise(self, user_input: str, original_answer: str, revision_note: str) -> str:
        system_instruction = """
أنت Solver في FATHIYA CORE.
مهمتك الآن: تعديل جواب سابق بناءً على ملاحظة مراجعة قصيرة.

قواعد صارمة:
- أصلح فقط المشاكل المذكورة في ملاحظة المراجع
- إذا كانت الملاحظة تقول إن الجواب تجاوز عدد الأيام المطلوب، فأعد كتابة الخطة بالعدد الصحيح فقط
- إذا كانت الملاحظة تقول إن هناك خلط لغات، فأخرج جوابًا عربيًا نظيفًا بالكامل
- لا تُبقِ أي كلمة من لغات أخرى إلا المصطلحات التقنية الضرورية مثل Python و pandas و NumPy
- إذا كانت الملاحظة تطلب جوابًا مباشرًا، فأعطِ جوابًا مباشرًا دون أسئلة توضيحية
- إذا كانت الملاحظة تطلب اقتراح مشروع، فاقترح مشروعًا بسيطًا مناسبًا لمبتدئ ما لم يذكر المستخدم خلاف ذلك
- لا تقفز إلى stack معقد إلا إذا كانت الملاحظة أو السؤال يبرران ذلك
- لا تغيّر المعنى الأساسي إلا إذا كانت الملاحظة تتطلب ذلك
- لا تذكر أنك تعدّل أو تراجع
- لا تذكر أي نظام داخلي
- لا تستخدم جداول
- اكتب الجواب النهائي فقط
- التزم بطلب المستخدم حرفيًا
- اجعل الجواب أوضح وأنظف من النسخة السابقة
"""

        user_prompt = f"""
طلب المستخدم:
{user_input}

الجواب السابق:
{original_answer}

ملاحظة المراجع:
{revision_note}

أعد كتابة الجواب بصيغته النهائية فقط.
"""

        return self._post_with_retry([
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_prompt}
        ])