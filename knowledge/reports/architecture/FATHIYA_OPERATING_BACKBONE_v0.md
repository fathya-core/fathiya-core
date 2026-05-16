# FATHIYA CORE — Operating Backbone v0

## Status
Backbone v0 after full corpus study and playbook consolidation.

## الحكم
FATHIYA is not a list of playbooks. FATHIYA is an operating layer.

The correct backbone is:

```text
Sources
→ Raw Archive
→ Corpus Intake
→ Classification
→ Artifact Selection
→ Runtime Queue
→ Policy / Approval Gate
→ Tool Contract Resolver
→ Adapter Router
→ Execution / Draft / Validation
→ Receipt Ledger
→ Awareness State Update
→ Command Center UI
```

## Why this exists
After studying the corpus, the strongest insight is that the value is not only in knowledge cards. The value is in orchestration:

- which agent acts
- which workflow applies
- which queue receives the task
- which tool contract governs the action
- which receipt proves the result
- which UI state shows what happened

## Core layers

### 1. Knowledge Vault
Canonical memory. Files are the source of truth.

Includes:
- raw archive
- cards
- reports
- schemas
- indexes
- graph
- audit records

### 2. FATHIYA Kernel
Decision and routing layer.

Responsibilities:
- classify input
- select artifact
- select queue
- check policy
- choose adapter
- require receipt
- update awareness state

### 3. Playbook Layer
Operational procedures.

Current chain:
- PLAYBOOK 001 — Corpus Intake
- PLAYBOOK 002 — Agent / Machine / Workflow Intake
- PLAYBOOK 003 — Runtime Queue & Receipt Ledger
- PLAYBOOK 004 — Tool Contract Resolver
- PLAYBOOK 005 — Scope & Authorization Preparation
- PLAYBOOK 006 — Crypto Radar & Signal Intake
- PLAYBOOK 007 — Daily Intake Automation
- PLAYBOOK 008 — Command Center UI Requirements
- PLAYBOOK 009 — Model Router & Cost-Aware Inference

### 4. Runtime Queue
Tracks work before and during routing.

Every task should end as:
- completed
- blocked
- failed
- needs_review
- waiting_approval

### 5. Receipt Ledger
Proof layer.

No meaningful action is complete without a receipt.

Receipts record:
- source request
- queue
- adapter
- input artifact
- output artifact
- status
- error
- approval reference
- next step

### 6. Registries
Structured operating memory.

Current registries:
- agent_registry_v0.json
- workflow_registry_v0.json
- tool_contract_registry_v0.json
- skill_registry_v0.json
- machine_task_registry_v0.json
- model_router_registry_v0.json
- approval_policy_registry_v0.json

### 7. Tool Contract Resolver
Prevents random execution.

Every adapter needs:
- allowed actions
- input schema
- output schema
- side effects
- approval requirement
- failure modes
- receipt requirement

### 8. Adapter Router
Execution arms.

Current connected adapters through Zapier:
- GitHub
- Cursor
- Manus
- Gmail
- Outlook
- Webhooks
- Files
- Code
- AI by Zapier
- RSS
- Zapier Tables
- Zapier Manager
- MCP Client
- Formatter
- Chrome Extension
- Zapier Forms
- Zapier Chatbots

Other project tools:
- n8n
- Gemini
- Perplexity
- DataCamp
- Kali WSL
- HexStrike AI
- private domain

### 9. Command Center UI
The app must show runtime state.

Core screens:
- Overview
- Runtime Queue
- Receipt Ledger
- Agents
- Playbooks
- Tool Contracts
- Daily Intake
- Crypto Radar
- Scope & Authorization
- Approval Queue

## Operating rules

### Rule 1 — Files are canonical
Database and UI are indexes over files.

### Rule 2 — Tools are arms, not the brain
Zapier, Cursor, Manus, GitHub, n8n, Gemini, and others execute or assist. They do not replace FATHIYA Kernel.

### Rule 3 — Queue before action
Every meaningful task must be routed.

### Rule 4 — Contract before tool
No adapter call without a tool contract or draft contract.

### Rule 5 — Receipt after outcome
Completed, failed, blocked, or approved work must leave a receipt.

### Rule 6 — UI must show state
If it matters, it must appear in Command Center.

## What is core vs application-specific

### Core backbone
- Corpus Intake
- Agent/Machine/Workflow Intake
- Runtime Queue
- Receipt Ledger
- Tool Contract Resolver
- Daily Intake
- Command Center UI
- Model Router

### Application domains
- Scope & Authorization / Security preparation
- Crypto Radar
- Future SOC / OSINT / DataCamp learning tracks

## Current risk
The project can drift if we keep adding playbooks without integrating them.

Correction:
- stop new playbook expansion temporarily
- validate backbone as one system
- create missing registries
- connect UI requirements to app implementation
- use Cursor for validation

## Immediate next actions

1. ~~Validate all playbook references.~~ Done — Backbone Validation v0.
2. ~~Create missing registry skeletons.~~ Done — all 7 registries exist.
3. ~~Generate Backbone validation report.~~ Done — FATHIYA_BACKBONE_VALIDATION_REPORT_v0.
4. ~~Ask Cursor Agent to verify consistency.~~ Done — automated validation pass.
5. Then decide: Command Center UI implementation or Memory Retrieval refresh.

## Decision
PLAYBOOK 010 is paused.

Next artifact is not another playbook.
Next artifact is:

```text
FATHIYA_BACKBONE_VALIDATION_REPORT_v0
```