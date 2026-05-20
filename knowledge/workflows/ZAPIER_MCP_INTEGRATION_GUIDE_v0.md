# FATHIYA CORE — Zapier MCP Integration Guide v0

## الفكرة

Zapier يتصل بـ `/api/mcp` عبر **Webhooks by Zapier**.
كل Zap يرسل `POST` بـ `{ tool, params }` — يستقبل `MCPToolResult`.

---

## البنية

```
Zapier Trigger (Gmail / RSS / Schedule / Webhook)
        ↓
  Formatter / Filter step
        ↓
  Webhooks by Zapier — POST /api/mcp
  { "tool": "...", "params": { ... } }
        ↓
  FATHIYA MCP Server
        ↓
  Quality Gate
        ↓
  MCPToolResult { success, data, receipt_id, requires_approval }
        ↓
  Zapier — إذا requires_approval = true:
    → GitHub: Create File (knowledge/raw/...)
    → أو Slack/Email notification
```

---

## الـ Endpoint

```
POST https://your-domain.com/api/mcp
Content-Type: application/json
```

---

## الـ Tools المتاحة

### 1. ping — تحقق من السيرفر
```json
{ "tool": "ping" }
```

### 2. knowledge_get_awareness_state — حالة الوعي
```json
{ "tool": "knowledge_get_awareness_state" }
```

### 3. knowledge_search — بحث
```json
{
  "tool": "knowledge_search",
  "params": {
    "query": "Bitcoin ETF",
    "category": "crypto",
    "limit": 5
  }
}
```

### 4. intake_submit_raw — إدخال محتوى خام
```json
{
  "tool": "intake_submit_raw",
  "params": {
    "content": "نص الخبر أو المقال...",
    "source": "gmail",
    "category": "crypto"
  }
}
```
المخرج:
```json
{
  "success": true,
  "data": {
    "id": "raw-abc123",
    "suggested_path": "knowledge/raw/2026-05-18/gmail/raw-abc123.md",
    "status": "pending_write",
    "note": "Use Zapier GitHub action to write to knowledge/raw/."
  },
  "requires_approval": true,
  "receipt_id": "MCP-INTAKE-ABC-XYZ"
}
```
ثم Zapier يستخدم **GitHub: Create File** بـ `suggested_path`.

### 5. crypto_create_signal_card — إنشاء Signal Card
```json
{
  "tool": "crypto_create_signal_card",
  "params": {
    "source": "Perplexity",
    "asset": "BTC",
    "sector": "Bitcoin",
    "what_changed": "SEC approved spot ETF options trading",
    "signal_direction": "supportive",
    "impact_score": 8,
    "confidence_score": 0.75,
    "hidden_risk": "Narrative exhaustion after initial pump",
    "invalidation_conditions": ["ETF outflows > 500M in 3 days"]
  }
}
```

### 6. quality_gate_check — فحص أي نص
```json
{
  "tool": "quality_gate_check",
  "params": { "text": "اشتري BTC الآن" }
}
```
المخرج:
```json
{ "passed": false, "reason": "Output became a direct trading command..." }
```

---

## نماذج Zaps

### Zap 1: Gmail → Intake
```
Trigger: Gmail — New Email (label: fathiya-intake)
Action 1: Webhooks — POST /api/mcp
  body: { tool: "intake_submit_raw", params: { content: {{body}}, source: "gmail" } }
Action 2: Filter — only if success = true
Action 3: GitHub — Create File
  path: {{data.suggested_path}}
  content: {{params.content}}
```

### Zap 2: RSS → Crypto Signal
```
Trigger: RSS — New Item (CoinDesk / Decrypt)
Action 1: Webhooks — POST /api/mcp
  body: { tool: "quality_gate_check", params: { text: {{title}} + {{summary}} } }
Action 2: Filter — only if passed = true
Action 3: Webhooks — POST /api/mcp
  body: { tool: "crypto_create_signal_card", params: { source: "rss", asset: "BTC", ... } }
Action 4: GitHub — Create File
  path: {{data.suggested_path}}
```

### Zap 3: Schedule → Awareness Check
```
Trigger: Schedule — Every day 9am
Action: Webhooks — POST /api/mcp
  body: { tool: "knowledge_get_awareness_state" }
```

---

## قواعد

- كل Zap يتحقق من `success: true` قبل الخطوة التالية.
- إذا `requires_approval: true` → لا تكتب مباشرة — أرسل للمراجعة أولاً.
- الكتابة لـ GitHub دائماً عبر **GitHub: Create File** action في Zapier.
- لا تستخدم Supabase — كل شيء في `knowledge/`.
- احتفظ بـ `receipt_id` في كل Zap للتدقيق.
