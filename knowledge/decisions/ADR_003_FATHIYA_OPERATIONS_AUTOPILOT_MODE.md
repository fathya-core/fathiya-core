# ADR-003: FATHIYA Operations Autopilot Mode

## Status

**Accepted** — 2026-05-16

## Context

FATHIYA's Internal Build Mode (established through PRs #5–#16) created the operating backbone: runtime queue, receipt ledger, registries, playbooks, policy layer, and Command Center UI. All work has been append-only knowledge assembly with no live external side effects.

The next evolution is **Operations Autopilot Mode** — enabling FATHIYA to represent, stage, preview, and govern real operational actions (webhooks, workflow activations, email sends, credential references, repository operations) without executing them live until formal scope and approval are confirmed.

Key requirements driving this decision:

1. **Explicit tool contracts**: Every external adapter must have a published contract describing inputs, outputs, side effects, approval class, and failure modes.
2. **Staged execution model**: All operations default to `staged` — payload previews and queue entries are created, but no live execution occurs until approval policy is satisfied.
3. **No hidden execution**: Every action that touches an external system must produce a receipt, a queue entry, and an audit trail visible in the Command Center.
4. **Credential safety**: Credentials are referenced by name only; secret values are never stored in knowledge artifacts or tool contracts.
5. **Rollback readiness**: Every staged operation includes a rollback note template describing how to reverse or neutralize the action if executed.
6. **Complementary to Internal Build Mode**: Operations Autopilot adds an operations layer alongside the existing build backbone. It does not replace or modify Internal Build Mode artifacts.

## Decision

**Expand FATHIYA from Internal Build Mode to Operations Autopilot Mode with explicit tool contracts, runtime records, and no hidden execution.**

Specifically:

1. **Operations policy classes** are added to the approval policy registry governing webhook staging, workflow activation staging, credential references, destructive action blocking, owned asset operations, and third-party activity blocking.
2. **Operations tool contracts** are published for Zapier Webhooks, Zapier Manager, n8n workflow activation, Gmail/Outlook send, and GitHub repo operations — all in `staged` or `planned` status.
3. **Operations queue scaffold** (`knowledge/operations/operations_autopilot_queue_v0.json`) tracks staged operations separately from the runtime queue, which continues to track routed build work.
4. **Rollback note template** (`knowledge/operations/rollback_note_template_v0.md`) standardizes rollback documentation for every staged operation.
5. **Runtime queue and receipt entries** are created for this bootstrap task following PLAYBOOK_003 conventions.
6. **Audit report** documents the bootstrap process, validation results, and boundary compliance.

### Operating Boundaries

- No live webhook calls, email sends, workflow activations, or trading executions in this PR.
- No credential secret values stored anywhere — only reference names.
- No destructive changes to existing backbone artifacts.
- All operations represented as `staged`, `planned`, or `dry_run_only`.
- Owned FATHIYA repos/assets may be documented and prepared but not mutated externally.
- Third-party activity is blocked unless formal scope is established.

## Consequences

### Positive

- FATHIYA can represent the full lifecycle of an operational action (plan → stage → preview → approve → execute → receipt → rollback) without executing prematurely.
- Every tool interaction is governed by a published contract — no hidden side effects.
- The Command Center can render staged operations, payload previews, and rollback notes alongside the existing runtime queue and receipt ledger.
- Operations Autopilot is complementary to Internal Build Mode — existing PRs, receipts, and registries are untouched.

### Negative / Trade-offs

- Staged operations are inert until approval policies are formalized and execution adapters are connected — this is intentional but means the operations layer starts as a framework, not a live system.
- Additional JSON artifacts increase the knowledge surface area that must be validated on each PR.

### Neutral

- This ADR does not prescribe when or how live execution will be enabled — that requires a separate execution-policy ADR.
- The operations queue is separate from the runtime queue to avoid confusion between build work and staged external operations.

## References

- `knowledge/decisions/ADR_001_FATHIYA_MONOREPO_CANONICAL_REPOSITORY.md` — Canonical repo decision
- `knowledge/registries/approval_policy_registry_v0.json` — Approval policy classes (extended by this ADR)
- `knowledge/registries/tool_contract_registry_v0.json` — Existing tool contracts (complemented by operations contracts)
- `knowledge/runtime/runtime_queue_v0.json` — Runtime queue (build work tracking)
- `knowledge/policies/FATHIYA_POLICY_LAYER_v0.md` — Policy layer definition
- Branch: `cursor/operations-autopilot-v0`
- Base: `main`
