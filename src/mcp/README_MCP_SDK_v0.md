# FATHIYA CORE — MCP SDK v0

## الهدف
تحويل مشروع FATHIYA CORE إلى MCP Server قابل للاستدعاء من Zapier وأي MCP Client.

## المبدأ
- MCP هو **adapter** فقط — ليس العقل.
- العقل هو: Knowledge Vault + FATHIYA Kernel + Quality Gates.
- كل tool في MCP يمثل عملية واحدة محددة.
- لا تنفيذ مباشر بدون Approval Queue.

---

## البنية

```text
src/mcp/
  server.ts              — MCP Server entry point
  tools/
    knowledge.ts         — Knowledge Vault tools
    intake.ts            — Daily Intake tools
    crypto.ts            — Crypto Intelligence tools
    signals.ts           — Signal Card tools
    retrieval.ts         — Retrieval Engine tools
    awareness.ts         — Awareness State tools
    quality-gate.ts      — Quality Gate tools
    approval-queue.ts    — Approval Queue tools
  schemas/
    knowledge-card.ts    — KnowledgeCard schema
    signal-card.ts       — SignalCard schema
    coin-card.ts         — CoinCard schema
    decision-card.ts     — DecisionCard schema
    tool-card.ts         — ToolCard schema
  utils/
    validator.ts         — Quality Gate validator
    formatter.ts         — Output formatter
    logger.ts            — MCP execution logger
  types.ts               — Shared MCP types
  config.ts              — MCP Server config
```

---

## Tools المتاحة

### Knowledge Tools
| Tool | الوصف |
|------|-------|
| `knowledge_search` | بحث في Knowledge Vault |
| `knowledge_get_card` | جلب بطاقة معرفة بالـ ID |
| `knowledge_create_card` | إنشاء بطاقة معرفة جديدة |
| `knowledge_list_cards` | قائمة البطاقات بالتصنيف |
| `knowledge_get_awareness_state` | جلب حالة الوعي الحالية |

### Crypto Tools
| Tool | الوصف |
|------|-------|
| `crypto_create_signal_card` | إنشاء Signal Card من خبر |
| `crypto_get_coin_card` | جلب بطاقة عملة |
| `crypto_list_watchlist` | قائمة المراقبة الحالية |
| `crypto_run_quality_gate` | تشغيل Quality Gate على مخرج |
| `crypto_get_narrative_map` | جلب خريطة السرديات |

### Intake Tools
| Tool | الوصف |
|------|-------|
| `intake_submit_raw` | إدخال محتوى خام |
| `intake_classify` | تصنيف محتوى |
| `intake_get_queue` | جلب قائمة الانتظار |

### Approval Queue Tools
| Tool | الوصف |
|------|-------|
| `queue_get_pending` | جلب العناصر المعلقة |
| `queue_approve` | الموافقة على عنصر |
| `queue_reject` | رفض عنصر |

---

## قواعد MCP

1. **لا تنفيذ مباشر** — كل action يمر بـ Approval Queue.
2. **Quality Gate إلزامي** — أي مخرج يمر بـ Quality Gate قبل الإرسال.
3. **لا أوامر تداول** — Crypto tools لا تنتج buy/sell/enter/exit.
4. **كل استدعاء له receipt** — يُسجَّل في knowledge/audit.
5. **Batching محدود** — max 10 items per MCP call.

---

## الاستخدام مع Zapier

```json
{
  "mcp_server_url": "https://your-domain/mcp",
  "tool": "knowledge_search",
  "params": {
    "query": "Bitcoin ETF narrative",
    "category": "crypto",
    "limit": 5
  }
}
```

---

## الحالة
- [x] Branch: `zapier/mcp-sdk-v0`
- [x] README
- [ ] server.ts
- [ ] tools/
- [ ] schemas/
- [ ] utils/
- [ ] config.ts
- [ ] types.ts
