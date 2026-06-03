# ADR-005: FATHIYA Agentic Operating System Plan v0

## Status

**Accepted** - 2026-06-03

## Context

The operator clarified that the active project is not only the Command Center UI. The larger objective is to build FATHIYA as an agentic operating system that coordinates multiple AI providers, OpenRouter model slots, authenticated tools, local-machine tools, and a shared knowledge base.

The core intent is:

- Use several models and providers as specialized agents, not as one generic assistant.
- Use OpenRouter and direct provider routes for fast, reasoning, critic, and structured-output work.
- Build a crypto/trading intelligence engine that can research, reason, criticize, simulate, and prepare decisions without issuing live trades until a separate execution policy exists.
- Build a security lab engine that can profile owned targets, map surfaces, plan reconnaissance, review evidence, and produce reports without live scanning or third-party probing until explicit authorization and scope exist.
- Make agents understand through retrieval, evals, failure cases, receipts, source references, and critic review instead of memorizing static prompts.
- Let automation tools such as Zapier, n8n, GitHub, browser automation, and local computer automation participate through explicit contracts and approval gates.

Existing FATHIYA artifacts already support this direction:

- `src/lib/ops/tasks.ts` defines the 5-layer / 16-task stack.
- `src/lib/llm/model-router.ts` and `src/lib/llm/openrouter.ts` define OpenRouter routing slots.
- `knowledge/registries/model_routing_registry_v0.json` defines model slot policy and no-direct-trading rules.
- `knowledge/cards/routing/kc-2026-05-17-apps-gpts-routing-v0.json` states that LLMs transform and reason while orchestration, state, logs, receipts, and guardrails live outside the model.
- ADR-002 permits internal build work without per-task approval.
- ADR-003 establishes staged operations with no hidden external execution.
- ADR-004 establishes MCP/API/deployment topology for future tool exposure.

## Decision

Adopt **FATHIYA Agentic Operating System Plan v0** as the canonical operating objective for the next build sequence.

FATHIYA will be organized as seven cooperating planes:

| Plane | Role | Primary artifacts |
|---|---|---|
| Knowledge / RAG Plane | Stores durable memory, source references, cards, corpora, receipts, and retrieval indexes outside the model. | `knowledge/`, T15, retrieval indexes |
| Model Routing Plane | Routes task classes to OpenRouter/provider slots and records receipts for meaningful calls. | `model-router.ts`, `openrouter.ts`, `model_routing_registry_v0.json` |
| Crypto Intelligence Plane | Builds catalyst scans, narrative analysis, thesis review, invalidation maps, watchlists, and paper/simulation outputs. | T12, T13, T14 |
| Security Lab Plane | Builds owned-scope target profiling, surface mapping, recon planning, evidence review, reporting, security evals, and routing. | T01, T02, T03, T04 |
| Account Orchestration Plane | Tracks provider accounts, profiles, readiness, draining/exhausted states, and fallback groups. | T05, T06, T07, T08 |
| Tool / Automation Plane | Uses Zapier, n8n, GitHub, browser, computer-use, MCP, and future adapters through contracts and approval gates. | operations contracts, Zapier control plane, MCP tools |
| Understanding / Evaluation Plane | Forces models to prove understanding through evals, critic review, failure library, source-backed outputs, and fail-closed behavior. | T02, T11, T14, T16 |

## Operating Principles

1. **Models are agents, not state stores.** State, memory, queues, logs, receipts, tasks, and source references stay outside the model.
2. **OpenRouter slots are capability lanes.** Fast, reasoning, critic, structured, and default slots are routed by task class and reviewed by quality gates where needed.
3. **Trading remains intelligence-first.** Crypto outputs may produce scenarios, signals, invalidations, risks, and watchlists. Live orders, portfolio mutations, direct buy/sell/long/short instructions, leverage, and target/stop instructions remain blocked until a separate execution-policy ADR and explicit runtime approval exist.
4. **Security remains authorization-first.** Security outputs may prepare and document owned-scope work. Live scanning, probing, exploitation, credential access, or third-party target activity remain blocked until formal scope and authorization exist.
5. **Tools are governed by contracts.** Zapier, n8n, browser, computer-use, GitHub, MCP, email, webhooks, and future adapters must be represented as read-only, staged, or approval-gated actions before they can affect external systems.
6. **Understanding beats memorization.** Every agent should retrieve sources, cite or reference the relevant internal artifact, pass eval cases, survive critic review, and fail closed when evidence is missing.
7. **Receipts are mandatory for meaningful work.** Internal build tasks, model calls with operational value, staged operations, and validations must leave runtime queue and receipt ledger evidence.

## Prioritized Build Sequence

### Phase 0 - Canonical objective

Create this ADR, audit report, runtime queue entry, receipt ledger entry, and individual receipt.

### Phase 1 - Account and profile foundation

Implement T05 and T06:

- `registry/accounts.schema.json`
- `registry/accounts.example.json`
- profile packs for security, crypto, research, and code

These are first because routing, fallbacks, cost control, and provider readiness depend on knowing which accounts exist and what they are allowed to do.

### Phase 2 - Provider capability and routing

Implement T03, T10, T13, and expand `model_routing_registry_v0.json`:

- security routing matrix
- crypto routing matrix
- competitive capability map
- provider fallback/failure rules
- task-to-slot mapping for security and crypto work

### Phase 3 - Evals and playbooks

Implement T01, T02, T12, and T14:

- security playbook and eval cases
- crypto intelligence playbook and eval cases
- no-trade and no-live-scan fail-closed cases
- evidence-missing and conflicting-signal cases

### Phase 4 - Knowledge corpus and prompt packs

Implement T11, T15, and T16:

- failure library
- internal corpus index
- router, reviewer, critic, synthesizer, report, and fail-closed prompt packs

### Phase 5 - Staged automation

Implement T04 and T08:

- n8n security workflow drafts
- Zapier account control plane drafts
- payload previews, approval records, rollback notes, and receipts

No live workflow activation happens in this phase.

### Phase 6 - Execution policy gates

Only after the above foundation exists, publish separate execution-policy ADRs for:

- paper trading and simulation
- live trading, if ever approved
- owned-security lab execution
- webhook/workflow activation
- message/email sending
- credential-reference handling

## Boundaries

This ADR does not approve:

- live trades or exchange actions
- portfolio changes
- direct trading commands
- live security scanning, probing, exploitation, or third-party target activity
- webhook calls or workflow activations
- email, chat, or notification sending
- credential access, rotation, or secret storage
- destructive actions
- bypassing browser, OS, or service safety gates

## Consequences

### Positive

- Restores the full project vision as a canonical architecture decision.
- Gives future agents a concrete build sequence instead of drifting into isolated UI work.
- Aligns OpenRouter, provider agents, Zapier/n8n, browser/computer tools, and GitHub operations under one operating model.
- Preserves safety boundaries while allowing aggressive internal build progress.

### Risks / Trade-offs

- The plan is broad. Risk is controlled by phasing and receipt-backed progress.
- Live execution remains blocked, so early work may feel like scaffolding. This is intentional until evals, policies, and approvals exist.
- Provider/account details must not be hard-coded until T05/T06 define schemas and safe references.

## References

- `src/lib/ops/tasks.ts`
- `src/lib/llm/model-router.ts`
- `src/lib/llm/openrouter.ts`
- `knowledge/registries/model_routing_registry_v0.json`
- `knowledge/cards/routing/kc-2026-05-17-apps-gpts-routing-v0.json`
- `knowledge/decisions/ADR_002_FATHIYA_AUTOPILOT_INTERNAL_BUILD_MODE.md`
- `knowledge/decisions/ADR_003_FATHIYA_OPERATIONS_AUTOPILOT_MODE.md`
- `knowledge/decisions/ADR_004_FATHIYA_DEPLOYMENT_ARCHITECTURE_MCP_SDK.md`
- `knowledge/runtime/runtime_queue_v0.json`
- `knowledge/runtime/receipt_ledger_v0.json`
