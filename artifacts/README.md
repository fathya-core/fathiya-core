# FATHIYA Artifacts

> القاعدة الحاكمة: **أي مهمة مع الاشتراكات المؤقتة يجب أن تنتج Artifact دائم هنا.**

أي مهمة في Ops Console لا تُغلق (`done`) إلا إذا انحط ملف نهائي تحت `artifacts/` وارتبط بالمهمة في `_index.json`.

## الهيكل

```
artifacts/
  _index.json          ← المصدر الرسمي لربط المهام بالـ artifacts
  registry/            ← T05  Account Registry
  profiles/            ← T06  Customization Profiles
  routing/             ← T03 / T13  Routing Matrices
  evals/               ← T02 / T14  Evals Libraries
  playbooks/           ← T01 / T12  Playbooks
  dossiers/            ← T09  Perplexity Dossiers
  corpus/              ← T15  Internal Corpus (RAG seed)
  prompts/             ← T16  Distilled Prompt Packs
  failures/            ← T11  Failure Library
  workflows/           ← T04 / T08  n8n / Zapier flows (exports)
  capability_map.json  ← T10
```

## كيف تُضاف artifact جديدة

1. احفظ الملف في المجلد المناسب (JSON للبيانات، MD للوثائق).
2. أضف مسار الملف إلى `_index.json` تحت `tasks[].artifacts[].path`.
3. حدّث `tasks[].status` إلى `done` إذا اكتملت كل الـ artifacts المتوقعة.

## مالكو المخرجات

| الكود | المالك الأساسي |
|---|---|
| Claude    | منهج، reviewer logic، routing policy، prompt distillation |
| GPT/Codex | schemas، bridge، validators، scripts، parsers |
| Perplexity| dossiers، market/security maps، vendor intelligence |
| Manus     | playbook surfaces، dashboards specs، operational packaging |
