# FATHIYA Daily Intake Workflow — Bootstrap Report v0

**Date:** 2026-05-16
**Status:** Scaffold complete
**ADR:** ADR-002 (FATHIYA Autopilot Internal Build Mode)
**Approval class:** `internal_autopilot`
**Branch:** `cursor/autopilot-internal-build-v0`

---

## Purpose

This report documents the initial scaffolding of the FATHIYA Daily Intake Workflow — a seven-stage pipeline that collects sources, archives raw material, classifies items, generates queue entries and receipts, updates the Command Center, and validates the build.

The workflow operates entirely within the non-execution boundaries defined by ADR-002.

## Scaffold Artifact

`knowledge/workflows/daily_intake_workflow_v0.json`

## Stages Defined

| Stage | ID | Purpose | Approval |
|---|---|---|---|
| Source Collection | S1 | Gather raw inputs from local repo and operator-provided files | No |
| Raw Archive | S2 | Persist raw material into knowledge/raw/ with provenance | No |
| Classification | S3 | Classify by domain, sensitivity, and target queue | No |
| Queue Entry | S4 | Append runtime queue entries for each classified item | No |
| Receipt Generation | S5 | Generate individual receipts and update ledger | No |
| Command Center Update | S6 | Update snapshot loader if new data sources added | No |
| Build & Lint Validation | S7 | Run npm run build and eslint | No |

## Non-Execution Boundaries

The following actions are explicitly forbidden within this workflow:

- Sending email or external messages
- Calling webhooks or activating external workflows
- Executing trades or portfolio mutations
- Scanning or probing external targets
- Accessing or rotating credentials
- Deleting or destroying data
- Deploying to production

Items that require external execution are routed to the Approval Queue with `waiting_approval` status and do not proceed without explicit operator approval.

## Sources Supported (v0)

| Source type | Location | Status |
|---|---|---|
| Operator source briefs | `knowledge/raw/` | Active |
| Crypto radar batches | `knowledge/crypto/radar/` | Active |
| Pending queue entries | `knowledge/runtime/runtime_queue_v0.json` | Active |
| External feeds | N/A | Future — requires adapter and separate policy |

## Validation Checklist

- [x] Workflow JSON is valid and parses without error
- [x] All seven stages defined with inputs, outputs, and boundary constraints
- [x] Non-execution boundary block present with explicit forbidden list
- [x] Approval class `internal_autopilot` referenced and present in registry
- [x] ADR-002 referenced as governing decision
- [x] No external API calls, webhooks, or side effects in scaffold

## Dependencies

- ADR-001: Canonical monorepo (all artifacts live in `fathya-core/fathiya-core`)
- ADR-002: Autopilot internal build mode (permits autonomous internal work)
- `approval_policy_registry_v0.json`: `internal_autopilot` class added
- `runtime_queue_v0.json`: Queue entry for this bootstrap task
- `receipt_ledger_v0.json`: Receipt for this bootstrap task

## Next Steps

1. Execute the first live daily intake cycle using operator-provided sources.
2. Implement adapter connectors for future external source channels (requires separate policy).
3. Add scheduled trigger via n8n or Zapier (requires Automation Queue approval).
4. Integrate with retrieval indexes for semantic search over archived sources.

## Blockers

| Blocker | Status |
|---|---|
| External source adapters (RSS, API, email) | Blocked — requires separate adapter policy |
| Scheduled triggers (n8n, Zapier) | Blocked — requires Automation Queue approval |
| Production deployment | Blocked — requires deployment policy |
