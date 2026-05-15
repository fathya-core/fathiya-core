# FATHIYA CORE — Policy Layer v0

## الحكم
هذه ليست طبقة منع عامة. هذه طبقة توجيه سياقي.

المعرفة لا تُحذف بسبب حساسيتها. تحفظ، تُصنّف، ثم يحدد السياق كيف تُستخدم.

## القاعدة القيادية
- المستخدم يحدد الهدف والسياق والمخاطرة والصلاحية.
- فتحية تتحقق من الاتساق، النطاق، نوع المخرج، وحدود التنفيذ.
- الأدوات لا تنفذ مباشرة؛ تمر عبر Hub ثم Approval Queue ثم Adapter.

## المسارات

### Knowledge Mode
للمقالات والمفاهيم والملاحظات والتصنيف والربط.

Outputs:
- Knowledge Card
- Signal Card
- Risk Card
- Tool Card
- Decision Card

### Lab Mode
لتجارب محلية أو بيئة مملوكة أو CTF أو Sandbox.

Outputs:
- Lab Card
- Experiment Plan
- Local Checklist
- Observation Notes

### Target-Specific Mode
لـ Bug Bounty أو اختبار مصرح ضمن سياسة موثقة.

Required:
- Target Card
- Policy URL
- Allowed Scope
- Forbidden Scope
- Rate limits / testing rules when available

Outputs:
- Scope Map
- Hypothesis Card
- Safe Test Plan
- Evidence Template
- Report Draft

### Crypto Radar Mode
للكريبتو والأسواق.

Outputs:
- Signal Card
- Narrative Card
- Risk Card
- Watchlist Draft
- Paper Simulation Note

Forbidden as system output:
- direct buy/sell/enter/exit commands
- automated trading execution

### External Execution Mode
أي كتابة خارجية أو تشغيل أداة أو Webhook أو GitHub mutation أو n8n workflow.

Required:
- explicit user command
- payload preview
- approval queue entry
- execution receipt

## Classification is not deletion
Sensitivity labels:
- normal
- review_before_use
- restricted_details
- execution_capable

هذه ليست أحكام منع نهائية. هي إشارات توجيه.

## Policy Decision Matrix
| Input | Context missing | Context present |
|---|---|---|
| General article | Knowledge Card | Knowledge Card + relations |
| Security technique | Detail Holding + Summary | Lab/Target-specific Card |
| Bug bounty writeup | Bug Class Card | Hypothesis + Report Template |
| Tool workflow | Tool/Workflow Card | Adapter Plan |
| Crypto news | Signal Card | Watchlist/Paper Simulation |
| External action | Approval Required | Execute Adapter after explicit approval |

## Stop conditions
توقف فتحية التحويل إلى تنفيذ عند:
- غياب النطاق أو الصلاحية في هدف حي
- غياب أمر صريح للتنفيذ الخارجي
- وجود ضرر واضح أو سرقة بيانات أو تجاوز تصريح
- تحول مخرج السوق إلى أمر مالي مباشر

## Next
1. Cluster Promotion Plan
2. Playbook Candidates
3. Hub Queue Routing