# FATHIYA Apps/GPTs Routing Map Parsed Report v0

## Metadata

| Field | Value |
|-------|-------|
| Source file | `FATHIYA_Apps_GPTs_Routing_Map_v1.xlsx` |
| Canonical repo | `fathya-core/fathiya-core` |
| Baseline commit before task | `262f0516b75eb2f74023d862ad49983b56eef9e4` |
| Daily intake cycle | `daily-intake-cycle-001` |
| Source manifest | `knowledge/intake/daily/2026-05-17/source_manifest_batch_001.json` |
| Output routing map | `knowledge/routing/apps_gpts_routing_map_v1.json` |
| Output routing rules | `knowledge/routing/apps_gpts_routing_rules_v1.json` |
| Queue entry | `rt-2026-05-17-post-daily-intake-validation-routing-parse-v0` |
| Receipt | `receipt-2026-05-17-post-daily-intake-validation-routing-parse-v0` |

## Sheet Coverage

| Sheet | Range | Parsed row count | Output |
|-------|-------|------------------|--------|
| `Architecture_Principle` | `A1:A6` | 5 interpreted principle rows | Architecture principles and routing implications |
| `Apps_Full_Mapped` | `A1:I174` | 173 app rows | App role groups, trading relevance groups, category coverage |
| `GPTs_Full_Mapped` | `A1:K30` | 29 GPT rows | Risk groups, decision-blocked groups, GPT boundary rules |
| `Sample_Workflows` | `A1:F4` | 3 workflow rows | Trading Digest, Meeting to Tasks, Docs to Knowledge templates |

## Architecture Principle

The parse confirms the FATHIYA routing model:

1. **LLM/GPT = X transformation layer**: GPT transforms, analyzes, classifies, summarizes, extracts, and formats.
2. **Zapier/Make/n8n = Y->X->Z orchestration**: external orchestrators manage triggers, sequencing, delivery, and adapter calls.
3. **State/memory outside the model**: queues, receipts, logs, notes, tasks, files, vector memory, and workflow state live outside GPT sessions.
4. **Validation/logging/guardrails required**: every routed workflow needs explicit validation, logging, and forbidden-action boundaries.

## Apps Summary

### Role Groups

| Role group | Count | Routing interpretation |
|------------|-------|------------------------|
| Connector/Tool | 151 | Default adapter/connector lane; requires tool contracts and orchestrator-owned payload validation. |
| Connector + Notifications | 10 | Notification-capable connector lane; requires idempotency, delivery logging, and approval when messages leave the system. |
| State/Storage | 8 | External memory/state lane; suitable for notes, files, logs, task state, and retrieval memory. |
| Input/Output Docs | 2 | Document input/output lane; requires chunking and citations/source references where applicable. |
| Connector Dev/API | 2 | Engineering/API lane; requires schema validation and non-destructive test mode before live API mutation. |

### Trading Relevance

| Relevance | Count | Routing posture |
|-----------|-------|-----------------|
| Low / منخفضة | 138 | Standard non-trading routing with normal validation/logging. |
| Medium / متوسطة | 20 | Market-adjacent routing with no-execution language and receipt requirements. |
| High / عالية | 12 | Finance/trading-sensitive routing; analysis-only, decision-blocked, no direct trade recommendations. |
| Header / blank / not classified | 3 | Do not auto-route until classified. |

### Categories Present

The parsed category set includes services/tools, travel/leisure, design/media, productivity, market/finance, CRM/marketing, learning/lifestyle, dev/security, communication, files/storage, and payments.

## GPT Summary

### Risk Levels

| Risk level | Count | Default mode |
|------------|-------|--------------|
| منخفض | 10 | Assistive transformation |
| متوسط | 9 | Reviewed analysis |
| مرتفع | 4 | Guarded analysis only |
| مرتفع جدًا | 4 | Restricted analysis only |
| متغير | 2 | Context-dependent; classify before use |

### Decision Blocking

| Decision-blocked label | Count | Rule |
|------------------------|-------|------|
| نعم | 18 | GPT may transform/analyze but cannot decide or execute. |
| لا | 9 | GPT may assist within declared scope; side effects still require orchestrator validation and approvals. |
| حسب الضبط | 2 | Default to blocked until configuration explicitly defines the decision boundary. |

Trading-like and finance-like GPTs remain scenario/analysis-only. They must not become execution decision makers.

## Workflow Templates

### Trading Digest

- **Input**: market/conversation snapshot.
- **Orchestrator**: Make or n8n.
- **GPT transform**: JSON with `{bias,risk,scenarios,next_questions}`.
- **Guardrail**: no entry/exit recommendations, no order payloads, no trading execution.

### Meeting to Tasks

- **Input**: transcript.
- **Orchestrator**: Zapier or Make.
- **GPT transform**: meeting summary plus task extraction.
- **Output**: Notion tasks and Slack summary.
- **Guardrail**: idempotency and logging before downstream writes.

### Docs to Knowledge

- **Input**: docs/PDF.
- **Orchestrator**: n8n.
- **GPT transform**: extraction into structured notes.
- **Output**: Obsidian or Notion notes.
- **Guardrail**: chunking and citations/source references.

## Guardrails Captured

- No direct trading decisions.
- No hidden execution.
- No external webhooks, emails, trading, scans, credential access, or destructive actions from this parse task.
- GPT/LLM state and memory remain outside the model.
- Validation, logging, receipts, and guardrails are required.
- Trading and finance GPTs remain analysis/scenario-only unless a separate human-approved execution policy exists.

## Command Center Status

No dedicated low-risk routing status section exists in `src/lib/command-center.ts`. The Command Center data loader was not expanded in this task to avoid adding a new UI surface. Routing status is documented as a pending UI expansion in `apps_gpts_routing_rules_v1.json`.

## Limitations

- The original workbook is not committed in this repository.
- Concrete row-level app names and GPT names are not available in the supplied parse facts and were not inferred.
- The v1 artifacts encode sheet metadata, summary counts, role/risk groups, routing rules, workflows, and guardrails only.

## Next Recommended Task

Add a Command Center Routing Status panel that reads `knowledge/routing/apps_gpts_routing_map_v1.json` and `knowledge/routing/apps_gpts_routing_rules_v1.json`, showing parse status, guardrail status, and the three workflow templates without enabling any external side effects.
