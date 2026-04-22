

# FATHIYA Ops Console — لوحة استنزاف الاشتراكات

سي عمر، الهدف: نبني هيكل **Ops Console** فاضي يعرض الـ 16 مهمة كاملة من الـ Task Stack، ويقرأ من ملفات `artifacts/` حقيقية. كل مهمة تنغلق = artifact دائم يُحفظ في المشروع. الواجهة + الملفات يكبروا مع بعض.

## 1. الفلسفة المعمارية

- **Source of Truth = ملفات JSON/MD داخل `artifacts/`** (مش الـ DB، مش in-memory). أي شي ينتجه Claude/GPT/Perplexity/Manus ينحط هنا.
- **الواجهة = قارئ + متتبع حالة فقط** في هذه المرحلة. ما تكتب لـ artifacts من المتصفح (يجي لاحقًا عبر server functions).
- **القاعدة الحاكمة محفوظة كـ memory**: أي مهمة تُغلق بدون artifact = لا تُحسب done.

## 2. هيكل الملفات

```text
artifacts/
  _index.json                    ← سجل كل المهام والـ artifacts المرتبطة
  registry/
    accounts.schema.json         ← مهمة 5
    accounts.example.json
  profiles/
    FATHIYA_SECURITY_BASE.json   ← مهمة 6
    FATHIYA_CRYPTO_BASE.json
    FATHIYA_RESEARCH_BASE.json
    FATHIYA_CODE_BASE.json
  routing/
    security.matrix.json         ← مهمة 3
    crypto.matrix.json           ← مهمة 13
  evals/
    security.cases.json          ← مهمة 4
    crypto.cases.json            ← مهمة 14
  playbooks/
    security.surface.md          ← مهمة 1
    crypto.intelligence.md       ← مهمة 12
  dossiers/                      ← مهمة 9 (Perplexity output)
  corpus/                        ← مهمة 15 (RAG seed)
  prompts/                       ← مهمة 16
  failures/
    failure_library.json         ← مهمة 11
  capability_map.json            ← مهمة 10
```

كل ملف = artifact دائم. الـ `_index.json` يربط المهمة بالـ artifact:

```json
{
  "tasks": [
    {
      "id": "T05",
      "code": "ACCT_REGISTRY",
      "layer": "B",
      "title": "Account Registry Schema",
      "owners": ["GPT"],
      "status": "todo",
      "priority": 1,
      "artifacts": ["registry/accounts.schema.json"],
      "depends_on": []
    }
  ]
}
```

## 3. مخطط الواجهة (Ops Console)

```text
┌─ FATHIYA Ops Console ──────────────────────────┐
│ [Layers: A B C D E]   [Owner: All ▾]   [⟳]    │
├────────────────────────────────────────────────┤
│ ▾ A. Security Ops Layer            (0/4 done) │
│   ▢ T01  Security Playbook Surface   Manus+GPT│
│   ▢ T02  Security Evals Library      Claude   │
│   ▢ T03  Security Routing Matrix     Claude ★ │
│   ▢ T04  n8n Security Operational    GPT      │
│ ▾ B. Account Orchestration                    │
│   ▣ T05  Account Registry Schema     GPT  ★★★ │
│   ▢ T06  Customization Profiles Pack Claude★★ │
│   ...                                         │
└────────────────────────────────────────────────┘
```

عناصر التفاعل:
- **بطاقة مهمة قابلة للطي** (Collapsible) فيها: العنوان، الـ owners (Badges)، الحالة (todo/in_progress/done)، قائمة الـ artifacts المتوقعة، زر "Open Artifact" لكل ملف.
- **شريط جانبي (Sheet)** يفتح عند الضغط على المهمة: يعرض الـ description كامل + المخرج المتوقع + dependencies + أي artifact موجود (preview للـ JSON/MD).
- **Progress bar أعلى كل Layer** يحسب done/total.
- **فلترة سريعة**: حسب Layer (Tabs)، حسب Owner (Claude/GPT/Perplexity/Manus)، حسب Priority.
- **شارة ★** للأولويات المباشرة (T05, T06, T03, T02, T15, T12).
- **شريط علوي**: عداد إجمالي + "Subscriptions Drain Mode" مفعّل (تذكير بصري بالقاعدة الحاكمة).

## 4. الـ 16 مهمة كما ستظهر

| # | كود | Layer | المالك | أولوية مباشرة |
|---|---|---|---|---|
| T01 | SEC_PLAYBOOK | A | Manus+GPT+Claude | |
| T02 | SEC_EVALS | A | Claude+GPT | ★ |
| T03 | SEC_ROUTING | A | Claude→GPT | ★ |
| T04 | SEC_N8N | A | GPT+n8n+Manus | |
| T05 | ACCT_REGISTRY | B | GPT | ★★★ |
| T06 | ACCT_PROFILES | B | Claude→GPT | ★★ |
| T07 | ACCT_VALIDATOR | B | GPT+Claude | |
| T08 | ACCT_ZAPIER | B | Zapier+GPT+Claude | |
| T09 | INTEL_DOSSIERS | C | Perplexity | |
| T10 | INTEL_CAPMAP | C | Claude+Perplexity→GPT | |
| T11 | INTEL_FAILURES | C | Claude+Perplexity+GPT | |
| T12 | CRYPTO_PLAYBOOK | D | Claude+Perplexity+Manus | ★ |
| T13 | CRYPTO_ROUTING | D | Claude→GPT | |
| T14 | CRYPTO_EVALS | D | Claude+GPT | |
| T15 | CORPUS | E | GPT+Perplexity+Claude | ★ |
| T16 | PROMPTS | E | Claude→GPT | |

## 5. مكونات الكود الجديدة

```text
src/routes/
  index.tsx                  ← يصير Ops Console (يستبدل الـ placeholder)
src/components/ops/
  TaskCard.tsx               ← بطاقة مهمة قابلة للطي
  LayerSection.tsx           ← قسم طبقة + progress
  TaskDetailSheet.tsx        ← Sheet جانبي للتفاصيل
  ArtifactPreview.tsx        ← عرض JSON/MD (read-only)
  StatusBadge.tsx
  OwnerBadges.tsx
src/lib/ops/
  tasks.ts                   ← types + الـ static seed للـ 16 مهمة
  artifacts.ts               ← helpers لقراءة الملفات
artifacts/
  _index.json                ← يُولّد من tasks.ts seed
  README.md                  ← القاعدة الحاكمة + كيف تُضاف artifacts
```

## 6. تفاصيل تقنية

- **Stack**: TanStack Start + shadcn (Card, Collapsible, Sheet, Tabs, Badge, Progress, ScrollArea) — كلها موجودة.
- **القراءة**: الـ seed الأولي ينحط داخل `src/lib/ops/tasks.ts` كـ TypeScript const عشان نضمن type safety. لاحقًا (مش الحين) نضيف `createServerFn` يقرأ من `artifacts/` على القرص.
- **RTL**: الواجهة عربية، نضيف `dir="rtl"` على الـ root container + `lang="ar"` (نحتفظ بـ `lang="en"` على الـ html ونغيّر للـ ar).
- **Theme**: نخلي الـ default dark (يلائم طابع "بارد/سيادي"). نفعّل `<html className="dark">` في `__root.tsx`.
- **بدون DB، بدون auth** في هذه المرحلة — مجرد واجهة + ملفات. لما نحتاج كتابة من المتصفح أو مزامنة بين أجهزة، نضيف Lovable Cloud لاحقًا.

## 7. ما سأنفذه عند الموافقة

1. أنشئ `artifacts/_index.json` + `artifacts/README.md` + 4 ملفات profile فاضية كـ stubs (T06).
2. أنشئ `src/lib/ops/tasks.ts` فيه الـ 16 مهمة كاملة بالـ metadata (owners, priority, layer, expected artifacts, dependencies).
3. أبني المكونات (`TaskCard`, `LayerSection`, `TaskDetailSheet`, `ArtifactPreview`, `StatusBadge`, `OwnerBadges`).
4. أستبدل `src/routes/index.tsx` بالـ Ops Console.
5. أفعّل dark mode + RTL في `__root.tsx`.
6. أحفظ القاعدة الحاكمة في memory (`mem://core/ops-console-rule`): "كل مهمة في Ops Console لا تُغلق إلا بـ artifact دائم تحت `artifacts/`".

النتيجة: واجهة شغّالة فورًا تعرض كل الـ Task Stack، وهيكل ملفات جاهز يستقبل مخرجات Claude/Perplexity/Manus/GPT بمجرد ما تبدأ تستنزف الاشتراكات.

