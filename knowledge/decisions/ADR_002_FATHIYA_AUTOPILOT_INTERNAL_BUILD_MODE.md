# ADR-002: FATHIYA Autopilot Internal Build Mode

## Status

**Accepted** — 2026-05-16

## Context

After PR #16 was merged into `main` and post-merge sanity passed, the FATHIYA system reached a stable baseline: canonical monorepo confirmed (ADR-001), runtime queue and receipt ledger populated, Command Center rendering live data, and all JSON artifacts valid.

The operator granted explicit permission for continued internal system building without waiting for per-task approval, subject to boundaries.

Two categories of work exist:

| Category | Examples | Approval needed? |
|---|---|---|
| **Internal build** | Repo docs, schemas, JSON artifacts, runtime queue entries, receipt ledger entries, Command Center improvements, local build/lint validation, internal workflow scaffolds, draft adapters, reports | No — may proceed autonomously |
| **External side-effect** | Sending email, calling webhooks, activating external workflows, trading/exchange/portfolio actions, live security scanning/testing/probing, credential access, destructive actions, third-party target activity | Yes — blocked until separate explicit policy or runtime approval |

Without a formal decision record, every agent session would re-negotiate these boundaries, adding overhead and risking inconsistency.

## Decision

**Establish an "Autopilot Internal Build Mode" that allows autonomous progression of internal, non-externally-visible work within `fathya-core/fathiya-core`, while preserving approval gates for all external side effects.**

Specifically:

1. **Internal build work may proceed without per-task approval.** This includes: adding or updating knowledge artifacts (decisions, playbooks, registries, schemas, reports, audit records), appending runtime queue entries and receipt ledger entries, creating or updating workflow scaffolds and draft adapters, improving Command Center code and documentation, running local build and lint validation, and creating branches and pull requests within the canonical repo.

2. **External side-effect gates remain enforced.** No agent or autopilot session may: send email or messages to external recipients, call webhooks or activate n8n/Zapier workflows with live side effects, execute trades or portfolio mutations, perform live security scanning or probing against any target, access or rotate credentials, perform destructive operations (delete repos, drop tables, etc.), or interact with third-party systems beyond Git/Cursor repo operations.

3. **The `internal_autopilot` approval class is added to the approval policy registry.** This class has `requires_approval: false` and is limited to the internal build scope defined above.

4. **Every autonomous build task still generates a runtime queue entry and receipt.** Traceability is not relaxed — only the approval gate is.

5. **Overnight or unattended operation is permitted within these boundaries.** An operator note documents what can proceed and what remains blocked.

## Consequences

### Positive

- Agents can make continuous progress on internal scaffolding without idle time waiting for approval.
- The approval policy registry gains a formal class that codifies existing practice.
- All work remains traceable through queue entries and receipts.
- External safety boundaries are explicitly preserved and documented.

### Negative / Trade-offs

- Risk of scope creep if future agents interpret "internal build" too broadly. Mitigated by the explicit exclusion list and the approval registry gate.
- Operator must review accumulated changes periodically to catch drift.

### Neutral

- This ADR does not change the approval requirements for any existing approval class.
- External execution policies (market, webhook, email, security) remain independently gated.

## References

- `knowledge/decisions/ADR_001_FATHIYA_MONOREPO_CANONICAL_REPOSITORY.md` — Canonical repo decision
- `knowledge/registries/approval_policy_registry_v0.json` — Approval class registry (updated by this ADR)
- `knowledge/policies/FATHIYA_POLICY_LAYER_v0.md` — Policy layer
- `knowledge/runtime/runtime_queue_v0.json` — Runtime queue
- `knowledge/runtime/receipt_ledger_v0.json` — Receipt ledger
- PR #16 — Post-merge sanity baseline
- Branch: `cursor/autopilot-internal-build-v0`
