# FATHIYA CC Extraction Pack

## الهدف
استخراج أنماط تشغيل عملية من `claude-code-main.zip` و`awesome-cc-oss-main.zip` وتحويلها إلى أشياء قابلة للزرع داخل FATHIYA CORE بدل نسخ المشروع كاملًا.

---

## الحكم السريع على الملفين

### 1) claude-code-main.zip
هذا هو المصدر المفيد فعليًا.
فيه بنية تشغيل واضحة:
- `.claude/commands/`
- `plugins/`
- `agents/`
- `hooks/`
- `examples/settings/`
- `examples/hooks/`
- `.github/workflows/`

**الاستنتاج:**
هذا ليس مجرد كود. هذا "نظام تشغيل مصغر" مبني على:
- أوامر
- وكلاء متخصصين
- Hooks حارسة
- إعدادات strict/lax
- workflows قابلة للتكرار

### 2) awesome-cc-oss-main.zip
قيمته أقل معماريًا.
هو أقرب إلى:
- فهرس
- تجميع موارد
- إشارات خارجية

**الاستنتاج:**
يُستخدم كمرجع ثانوي فقط، وليس كأساس بنيوي.

---

## ما الذي نأخذه فعليًا إلى FATHIYA CORE

## A) طبقة Plugins بدل تكديس المنطق في main.py

### الفكرة
بدل أن يكبر `main.py` ويتحول إلى عقدة عشوائية، يتم تقسيم النظام إلى وحدات مستقلة شبيهة بـ plugins.

### البنية المقترحة
```text
fathiya_core/
├── agents/
├── hooks/
├── commands/
├── plugins/
│   ├── review-loop/
│   ├── project-framing/
│   ├── feature-dev/
│   └── safety-guard/
├── core/
├── memory/
└── evals/
```

### لماذا هذا مهم
- إضافة قدرة جديدة بدون لمس القلب
- تعطيل/تجريب وحدة واحدة بدون كسر الباقي
- فصل التجارب عن النواة

---

## B) Hooks كطبقة حراسة حقيقية

### أهم شيء مستخرج
الريبو لا يعتمد فقط على prompts.
يعتمد أيضًا على hooks للأحداث.

### الأحداث المفيدة لفATHIYA
```text
SessionStart
PreToolUse
PostToolUse
Stop
```

### ترجمتها داخل مشروعك

#### 1. SessionStart
حقن قواعد الجلسة:
- ما هو الدور الحالي؟
- هل نحن في اختبار أم تنفيذ؟
- ما الحد الأقصى للحلقات؟

#### 2. PreToolUse
فلتر قبل الأداة:
- هل الوكيل سيستخدم أداة غير لازمة؟
- هل الطلب خارج الدور؟
- هل هذا تعديل خطر أو خطوة غير متوقعة؟

#### 3. PostToolUse
تسجيل ما حدث:
- ما الأداة المستخدمة؟
- ماذا تغيّر؟
- هل حصل فشل؟

#### 4. Stop
اعتراض الإنهاء المبكر:
- هل المهمة اكتملت فعلًا؟
- هل عندنا final artifact؟
- هل الحلقة خرجت قبل تحقق الشرط؟

### النتيجة
الـ hook هنا ليس زينة.
هو **طبقة ضبط سلوك**.

---

## C) وكلاء ضيقو الدور لا وكيل شامل

الريبو يثبت أن القوة ليست في Agent واحد عام.
بل في Agents ضيقي الدور مثل:
- code-explorer
- code-architect
- code-reviewer
- comment-analyzer
- silent-failure-hunter

### ما يعنيه هذا لك
أنت أصلًا على الطريق الصحيح:
- Framer
- Solver
- Evaluator

لكن التوسعة الصحيحة ليست:
> Agent أذكى يفعل كل شيء

بل:
> Agent أدق يملك دورًا واحدًا وحدودًا واضحة

### التوسعة المقترحة لاحقًا
```text
agents/
├── framer.py
├── solver.py
├── evaluator.py
├── revision_planner.py
├── failure_hunter.py
└── route_chooser.py
```

---

## D) Loop حقيقية بشروط إكمال لا تدوير فارغ

إضافة `ralph-wiggum` تعطي أهم درس:
الحلقة الذاتية لا تنجح إلا إذا كان عندها:
- شرط إكمال
- حد أقصى للتكرار
- اعتراض على الخروج الخاطئ
- مسار إلغاء

### ما يجب زرعه في فتحية
أي loop يجب أن تملك هذا العقد:

```json
{
  "goal": "produce_final_answer",
  "max_iterations": 2,
  "completion_criteria": [
    "answer_matches_user_request",
    "no_major_language_corruption",
    "evaluator_verdict_is_approve_or_revision_applied"
  ],
  "cancel_conditions": [
    "api_failure_repeated",
    "same_revision_repeated",
    "output_quality_degrades"
  ]
}
```

### الحكم
المشكلة عندك لم تكن غياب loop.
المشكلة كانت غياب **policy** للـ loop.

---

## E) إعدادات تشغيل متعددة: strict / lax / sandbox

وجود أمثلة مثل:
- `settings-strict.json`
- `settings-lax.json`
- `settings-bash-sandbox.json`

معناه أن التشغيل ليس mode واحد.

### ترجمتها داخل فتحية

#### discovery mode
مرن أكثر
- يسمح بالاستكشاف
- أسئلة أكثر
- نقد أوسع

#### execution mode
أشد
- لا توسع
- لا حشو
- لا خروج عن الدور
- output قصير ومحدد

#### sandbox mode
للاختبار
- منع الخطوات الخطرة
- منع الكتابة على ملفات أساسية
- تسجيل كل محاولة

### القرار
أنت تحتاج ملف state/mode لاحقًا، وليس فقط prompts مختلفة.

---

## F) الأوامر الجاهزة Command Layer

من الأشياء الذكية في الريبو:
وجود أوامر جاهزة مثل:
- commit
- commit-push-pr
- triage-issue
- code-review
- feature-dev

### ما يقابله داخل فتحية
بدل الاعتماد على سؤال حر كل مرة، تبني أوامر تشغيلية:

```text
/run:frame
/run:solve
/run:evaluate
/run:test-harness
/run:stability-check
/run:feature-plan
```

### الفائدة
- تقليل العشوائية
- إعادة إنتاج النتيجة
- تسهيل الاختبار

---

## G) Workflows وAutomation حول النظام لا داخله فقط

وجود `.github/workflows/` يدل أن النظام الناضج لا يكتفي بالوكلاء.
يبني حولهم:
- triage
- dedupe
- issue lifecycle
- sweep
- automated review

### ما يفيدك من هذا
حتى FATHIYA CORE لاحقًا يحتاج workflows خارجية مثل:
- تشغيل test harness على مجموعة أسئلة ثابتة
- تخزين نتائج agents
- اكتشاف التكرار في الإخفاقات
- مقارنة موديلين على نفس الحالة

---

## H) ما لا ننسخه

### لا تنسخ:
- نظام Claude نفسه
- بنية plugin كما هي
- workflows كما هي
- المجلدات حرفيًا

### انسخ فقط:
- الفكرة التشغيلية
- فصل الطبقات
- منطق hooks
- فكرة أوامر جاهزة
- مفهوم loop policy
- مفهوم modes

---

## ترجمة مباشرة إلى FATHIYA CORE

## النسخة القابلة للتنفيذ الآن

### 1. أضف مجلد hooks
```text
hooks/
├── session_start.py
├── pre_run_guard.py
├── post_run_logger.py
└── stop_guard.py
```

### 2. أضف policy للـ revision loop
```text
core/revision_policy.py
```

ويحتوي:
- max_iterations
- completion_criteria
- cancel_conditions

### 3. أضف command layer بسيطة
```text
commands/
├── run_frame.py
├── run_pipeline.py
└── run_tests.py
```

### 4. أضف modes
```text
config/runtime_modes.py
```

مثال:
- discovery
- execution
- sandbox

---

## أولويات التنفيذ المستخلصة

### أولوية 1
**Hooks + revision policy**

لأن مشكلتك الحالية تشغيلية لا معمارية فقط.

### أولوية 2
**Test harness ثابت**

لأنك تحتاج قياسًا لا انطباعًا.

### أولوية 3
**Command layer**

لمنع الفوضى في تشغيل الأجزاء.

### أولوية 4
**Pluginization لاحقًا**

بعد الاستقرار.

---

## قرار نهائي

ما خرج من الملفين ليس مشروعًا جاهزًا للنسخ.
الشيء المهم الذي خرج هو هذا:

> **FATHIYA CORE يجب أن يتطور من سلسلة Agents إلى نظام تشغيل صغير**

يعني:
- Agents
- Hooks
- Commands
- Modes
- Loop policy
- Test harness

هذا هو الاستخراج الحقيقي المفيد.

---

## الخطوة التالية المقترحة

أول شيء نبنيه من هذا الاستخراج:

### `core/revision_policy.py`
ثم بعده:
### `commands/run_tests.py`

لأنهما أقرب شيئين يحلان مشكلتك الحالية مباشرة.
