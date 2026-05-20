# FATHIYA CORE — OpenRouter Model Routing Bootstrap Report v0

**Date:** 2026-05-18  
**Branch:** `zapier/mcp-sdk-v0`  
**Status:** Bootstrap Complete — Pending Deployment

---

## ما تم بناؤه

### 1. OpenRouter Provider Contract
**الملف:** `src/lib/llm/openrouter.ts`

| العنصر | الحالة |
|--------|-------|
| Env vars contract | ✅ بالاسم فقط — لا secrets |
| Multi-model support | ✅ 5 slots |
| Unified response | ✅ `OpenRouterResponse` |
| Receipt ID | ✅ `OR-{SLOT}-{TS}` |
| Error handling | ✅ missing key / HTTP error / fetch error |
| No Supabase | ✅ |

**Env vars required:**
```
OPENROUTER_API_KEY
OPENROUTER_BASE_URL
OPENROUTER_DEFAULT_MODEL
OPENROUTER_FAST_MODEL
OPENROUTER_REASONING_MODEL
OPENROUTER_CRITIC_MODEL
OPENROUTER_STRUCTURED_MODEL
```

### 2. Model Router
**الملف:** `src/lib/llm/model-router.ts`

| Task Class | Model Slot | الدور |
|-----------|-----------|------|
| `formatting` | fast | تنسيق نص |
| `knowledge_search` | fast | بحث واسترجاع |
| `intake_classification` | fast | تصنيف مدخلات |
| `crypto_analysis` | reasoning | تحليل سيناريوهات |
| `quality_gate` | critic | كشف أوامر تداول |
| `critic_review` | critic | مراجعة مخاطر |
| `structured_extraction` | structured | استخراج JSON |

### 3. Knowledge Registry
**الملف:** `knowledge/registries/model_routing_registry_v0.json`

- ✅ Task classes موثقة
- ✅ Model slots مع env vars
- ✅ Fallback rules
- ✅ Quality Gate rules
- ✅ Receipt requirement
- ✅ No direct trading decision rule

### 4. API Route — GET /api/mcp (Manifest)
**الملف:** `src/routes/api/mcp.ts`

GET يرجع:
```json
{
  "server": "fathiya-core-mcp",
  "version": "0.1.0",
  "supported_modes": {
    "webhook_dispatcher_v0": true,
    "mcp_protocol_full": false,
    "openrouter_model_routing": true
  },
  "tools": [...],
  "schemas": {...}
}
```

---

## تصحيح التسمية

### ما هو `/api/mcp` في v0

> **`/api/mcp` في v0 هو: Webhook-compatible tool endpoint**
> وليس MCP protocol كامل.

| الخاصية | v0 (webhook_dispatcher) | MCP Protocol كامل |
|---------|------------------------|-------------------|
| HTTP POST بـ JSON | ✅ | ✅ |
| Tool manifest (GET) | ✅ | ✅ |
| JSON-RPC 2.0 | ❌ | ✅ |
| Streamable HTTP | ❌ | ✅ |
| MCP Client by Zapier | ❌ | ✅ |
| Auth boundary | ❌ | ✅ |
| Tool discovery protocol | ❌ | ✅ |

### Future MCP Protocol Layer (v1)

```
GET  /api/mcp          → tool manifest + schemas
POST /api/mcp          → JSON-RPC 2.0 dispatcher
POST /api/mcp/stream   → Streamable HTTP (SSE)
```

**ما يحتاجه v1:**
- JSON-RPC 2.0 envelope: `{ jsonrpc, id, method, params }`
- Tool discovery: `tools/list` method
- Tool execution: `tools/call` method
- Auth: Bearer token / API key header
- Streamable HTTP: SSE for long-running tools
- MCP Client by Zapier compatibility

---

## Quality Gate — ما هو ممنوع

### ممنوع في كل مخرج
```
buy / sell / enter / exit / long / short
leverage
target price as instruction
stop loss as instruction
اشتري / بع / ادخل / اخرج
ضارب الآن / افتح صفقة / هدف سعري قطعي
```

### مسموح فقط
```
analysis / scenario / risk
invalidation_conditions
source_backed_signal_card
hypothesis / watchlist_item
signal_direction: supportive | negative | mixed | unclear | noise
```

---

## نتائج التحقق

| الفحص | الحالة | الملاحظة |
|------|-------|----------|
| TypeScript types | ✅ | لا any غير ضروري |
| No Supabase imports | ✅ | كل شيء من knowledge/ |
| No secret values in code | ✅ | env vars بالاسم فقط |
| Quality Gate on all outputs | ✅ | regex + LLM critic |
| Receipt ID on all LLM calls | ✅ | OR-{SLOT}-{TS} |
| JSON registry valid | ✅ | model_routing_registry_v0.json |
| No trading commands | ✅ | Quality Gate enforced |
| build check | ⚠️ | يحتاج deploy للتحقق الفعلي |
| eslint | ⚠️ | يحتاج Cursor/local run |

**البلوكرز الحالية:**
- `npm run build` و `eslint` يحتاجان بيئة محلية أو CI — لا يمكن تشغيلهما عبر GitHub API.
- التحقق الفعلي يتم بعد deploy على `app.fathya-core.com`.

---

## الخطوة التالية

1. Merge PR #26
2. Deploy على `app.fathya-core.com`
3. ربط Zapier Webhooks بـ `https://app.fathya-core.com/api/mcp`
4. ضبط env vars في deployment secrets
5. بناء Zap 1: Gmail → Intake
6. بناء Zap 2: RSS → Crypto Signal
7. v1: إضافة JSON-RPC 2.0 layer
