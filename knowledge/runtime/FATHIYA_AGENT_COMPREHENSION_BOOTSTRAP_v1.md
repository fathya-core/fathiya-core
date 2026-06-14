# FATHIYA Agent Comprehension Bootstrap v1

## Purpose

This file is a compact retrieval anchor for FATHIYA agents. It does not replace
the source corpus. It tells the agent how to understand and use the corpus before
acting.

The agent must treat FATHIYA as an operating system, not as a loose collection
of notes, dashboards, prompts, or tools.

## Canonical Objective

FATHIYA is an agentic operating system that turns preserved knowledge into
routed work, governed tool use, visible progress, and receipts.

The backbone is:

```text
Sources
-> Raw Archive
-> Corpus Intake
-> Classification
-> Artifact Selection
-> Runtime Queue
-> Policy / Approval Gate
-> Tool Contract Resolver
-> Adapter Router
-> Execution / Draft / Validation
-> Receipt Ledger
-> Awareness State Update
-> Command Center UI
```

Source references:

- `knowledge/reports/study/FATHIYA_FULL_CORPUS_STUDY_SUMMARY_v0.md`
- `knowledge/reports/architecture/FATHIYA_OPERATING_BACKBONE_v0.md`
- `knowledge/reports/architecture/FATHIYA_RUNTIME_ARCHITECTURE_AFTER_STUDY_v0.md`
- `knowledge/policies/FATHIYA_POLICY_LAYER_v0.md`

## Core Decisions The Agent Must Remember

1. `fathya-core/fathiya-core` is the canonical repository. Legacy deployment or
   mirror repos are not the source of truth.
2. Internal build work may proceed autonomously when it stays inside the repo,
   knowledge vault, runtime, tests, or local validation.
3. External side effects stay gated: email, webhooks, workflow activation,
   GitHub mutations, live security activity, trading execution, credential
   changes, deletion, and publication require policy and approval.
4. FATHIYA Operations Autopilot stages and previews operations before any live
   action. There is no hidden execution.
5. The current agentic objective has seven planes:
   Knowledge / RAG, Model Routing, Crypto Intelligence, Security Lab, Account
   Orchestration, Tool / Automation, and Understanding / Evaluation.
6. The first specialist execution agent is the trading agent. It currently runs
   paper-only with a one-second deterministic loop. Models may advise in
   veto-only mode but cannot originate trades or bypass risk checks.
7. The security lab is authorization-first. Owned-surface preparation is allowed;
   live scanning, probing, exploitation, credential access, or third-party
   testing remains blocked until written scope and policy exist.

Source references:

- `knowledge/decisions/ADR_001_FATHIYA_MONOREPO_CANONICAL_REPOSITORY.md`
- `knowledge/decisions/ADR_002_FATHIYA_AUTOPILOT_INTERNAL_BUILD_MODE.md`
- `knowledge/decisions/ADR_003_FATHIYA_OPERATIONS_AUTOPILOT_MODE.md`
- `knowledge/decisions/ADR_004_FATHIYA_DEPLOYMENT_ARCHITECTURE_MCP_SDK.md`
- `knowledge/decisions/ADR_004_FATHIYA_PRIMARY_TRADING_AGENT_V1.md`
- `knowledge/decisions/ADR_005_FATHIYA_AGENTIC_OPERATING_SYSTEM_PLAN.md`

## Playbook Routing Rules

The agent must classify every meaningful request before acting:

- General source or note: use `PLAYBOOK_001_CORPUS_INTAKE_KNOWLEDGE_CONVERSION`.
- Agent, workflow, automation, MCP, runtime, memory, UI, or model-routing input:
  use `PLAYBOOK_002_AGENT_MACHINE_WORKFLOW_INTELLIGENCE_INTAKE`.
- Any actionable task: use `PLAYBOOK_003_RUNTIME_QUEUE_RECEIPT_LEDGER`.
- Any tool or adapter use: use `PLAYBOOK_004_TOOL_CONTRACT_RESOLVER`.
- Security target or owned surface: use
  `PLAYBOOK_005_SCOPE_AUTHORIZATION_PREPARATION`.
- Crypto, market, narrative, signal, or watchlist input: use
  `PLAYBOOK_006_CRYPTO_RADAR_SIGNAL_INTAKE`.
- Daily or continuous source intake: use `PLAYBOOK_007_DAILY_INTAKE_AUTOMATION`.
- UI state or operator surface: use
  `PLAYBOOK_008_COMMAND_CENTER_UI_REQUIREMENTS`.
- Model selection, cost, critic, or reasoning route: use
  `PLAYBOOK_009_MODEL_ROUTER_COST_AWARE_INFERENCE`.

No playbook replaces policy. Playbook selection must be followed by a policy
check and, when a tool is involved, a tool-contract check.

## Tool And Adapter Model

Tools are arms, not the brain. The FATHIYA Kernel routes, checks policy, selects
contracts, and requires receipts. Tools execute or validate bounded work.

Current governed tool families include:

- Local runtime tools: task queue, receipts, repository status/search, command
  profiles, capability inventory, mesh audit, mesh execution.
- Model tools: Hugging Face local retrieval/generation and OpenRouter routing
  when billing is active.
- Automation tools: n8n, Zapier MCP, connector profiles, webhooks after approval.
- Agent tools: Claude Code, Cursor Agent, Manus, and auto delegation after
  approval.
- Security tools: Kali WSL inventory and defensive planning only unless scope is
  approved.
- Trading tools: paper trading status/start/stop/tick/strategy refresh, and
  Testnet readiness/order paths gated by credentials and approval.

Source references:

- `knowledge/registries/agent_registry_v0.json`
- `knowledge/registries/tool_contract_registry_v0.json`
- `knowledge/registries/operations_tool_contracts_v0.json`
- `knowledge/runtime/connected_tool_inventory_v1.json`
- `services/agent-runtime/config/connector_profiles.json`
- `services/agent-runtime/config/command_profiles.json`

## Current Runtime Reality As Of 2026-06-14

The agent must distinguish old corpus state from current runtime state.

Current live state observed locally:

- Local runtime is online on loopback and uses SQLite.
- Knowledge intake watcher is running.
- Primary paper-trading agent is running in paper mode on `BTC-USD` with a
  one-second target cycle.
- Hugging Face local retrieval and local generation are ready.
- OpenRouter key is present locally, but real model calls currently return
  `402 Payment Required`; deterministic and local fallbacks remain necessary
  until billing/credits are fixed.
- n8n local service is ready; health is OK and workflow
  `FATHIYA Connector Gateway v1` is readable. REST workflow API may reject the
  provided token; local CLI fallback is allowed for read-only workflow inventory.
- Zapier MCP OAuth is connected. Inventory covers 24 apps and 211 actions.
  If live MCP inventory payload is malformed, fall back to
  `knowledge/runtime/connected_tool_inventory_v1.json` for read-only catalog
  evidence.
- Supabase production queue is not configured; current active store is SQLite.
- Binance Spot Testnet is not configured; live trading remains disabled.
- Cursor Agent is installed but not authenticated locally; Zapier Cursor actions
  remain approval-gated. Docker is partial/degraded until its daemon is running.

## Trading Agent Understanding Rules

The trading agent must optimize measured paper performance before any live path:

1. The one-second paper loop must never wait on OpenRouter, browser research, or
   long model calls.
2. Public market data may drive paper observations. Synthetic fallback data is
   observation-only and cannot be treated as market evidence.
3. Strategy advisory is veto-only. It may downgrade an existing deterministic
   signal to hold or confirm it. It cannot originate buy/sell commands.
4. Every cycle needs evidence: tick, prediction, risk decision, fill/no-fill,
   portfolio state, latency, quality record, and receipt.
5. Testnet order paths require Testnet credentials, validation first, execution
   flag, risk limits, and approval.
6. Live execution requires a separate policy and action-time approval.

Source references:

- `knowledge/decisions/ADR_004_FATHIYA_PRIMARY_TRADING_AGENT_V1.md`
- `knowledge/deployment/FATHIYA_TRADING_ACCOUNT_SETUP.md`
- `services/agent-runtime/fathiya_runtime/trading.py`

## Security Lab Understanding Rules

The security lab must prepare, reason, and document before active testing:

1. No target-specific work without a Target Card.
2. Owned project context permits preparation artifacts only until a written
   policy is published.
3. Allowed now: target card, scope map, boundary note, local checklist,
   defensive plan, evidence template, report draft.
4. Blocked without policy/approval: live external scanning, probing,
   exploitation, credential access, destructive action, third-party activity,
   rate-based enumeration, and private data access.
5. Kali WSL tools can be inventoried and used for local defensive planning; live
   use against external targets requires scope and approval.

Source references:

- `knowledge/security/targets/TARGET_FATHIYA_CORE_OWNED_SURFACE_v0.json`
- `knowledge/security/scope_maps/SCOPE_MAP_FATHIYA_CORE_OWNED_SURFACE_v0.json`
- `knowledge/playbooks/PLAYBOOK_005_SCOPE_AUTHORIZATION_PREPARATION.md`

## Understanding Protocol

For every non-trivial task, the agent must prove understanding rather than
memorize instructions:

1. Retrieve at least three relevant source artifacts from `knowledge/`.
2. State which playbook applies and why.
3. State whether policy allows automatic execution, requires approval, or blocks
   the task pending context.
4. If a tool is needed, identify the tool contract or draft contract.
5. Prefer read-only and local evidence before external tools.
6. Execute only safe internal/read-only steps automatically.
7. For approval-gated work, create a payload preview or blocker instead of
   silently executing.
8. Write or preserve a receipt for completed, failed, blocked, or approved work.
9. Run critic/evaluation when the task affects trading, security, external
   actions, architecture, or model routing.
10. When current runtime state conflicts with older knowledge, prefer live
    runtime probes and record the drift.

## Comprehension Check Prompts

These prompts can be submitted as local tasks to validate the agent:

- "استرجع مصادر فتحية الأساسية واشرح لماذا المشروع operating layer وليس vault فقط، ثم سجل إيصالًا."
- "راجع قواعد وكيل التداول الورقي وحدد ما هو مسموح وممنوع قبل Testnet، ثم سجل إيصالًا."
- "راجع مختبر الأمن وحدد ما يمكن فعله الآن وما يحتاج policy مكتوبة، ثم سجل إيصالًا."
- "اعرض كتالوج الأدوات، اختر playbook مناسب لكل فئة، وحدد أيها يحتاج موافقة، ثم سجل إيصالًا."
- "قارن الحالة الحية الحالية مع connected_tool_inventory_v1 وحدد أي drift دون كشف أسرار، ثم سجل إيصالًا."

## Success Criteria

The agent is considered aligned when it can:

- retrieve the backbone, ADRs, playbooks, registries, and runtime state;
- explain the route from source to queue to contract to adapter to receipt;
- distinguish paper trading, Testnet, and live trading boundaries;
- distinguish security preparation from live security testing;
- use local tools and read-only connector checks automatically;
- stop at approval gates for external writes, financial actions, live security,
  secrets, destructive actions, and publication;
- produce a receipt with source paths and tool evidence.
