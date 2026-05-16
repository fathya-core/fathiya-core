# FATHIYA Repository Identity Map v0

## Purpose

Canonical reference for FATHIYA project repository identities. Establishes `fathya-core/fathiya-core` as the single canonical monorepo and source of truth for all FATHIYA architecture.

## Canonical Repository

| Role | GitHub Path | URL | Status |
|---|---|---|---|
| **Canonical monorepo** | `fathya-core/fathiya-core` | https://github.com/fathya-core/fathiya-core | **Active — single source of truth** |

All knowledge, runtime, receipts, registries, playbooks, Command Center UI, and ops console functionality live inside this monorepo.

## Legacy / External Mirror

| Role | GitHub Path | URL | Status |
|---|---|---|---|
| Legacy external app | `fathya-project/fathiya-ops-console` | https://github.com/fathya-project/fathiya-ops-console | **Legacy — not source of truth** |

`fathya-project/fathiya-ops-console` is preserved as a historical reference and optional deployment mirror. It is not the source of truth for any FATHIYA architecture decisions, runtime state, or operational artifacts. See ADR-001 for the full rationale.

## Corrections applied

| Incorrect reference | Correct reference | Where corrected |
|---|---|---|
| `fathya-core/fathiya-ops-console` | `fathya-project/fathiya-ops-console` | Target Card, Scope Map |
| Two independent systems / split repos | One canonical monorepo | ADR-001, Identity Map v0 update, Consolidation Report |

## Key facts

- The canonical monorepo is `fathya-core/fathiya-core`. This is the single source of truth for all FATHIYA architecture.
- The ops console functionality belongs inside the monorepo app structure, not in a separate repository.
- `fathya-project/fathiya-ops-console` exists as a legacy/external mirror only. It must not be treated as an independent system or source of truth.
- `fathya-project/fathiya-core` does not exist and must not be referenced.
- `fathya-core/fathiya-ops-console` does not exist and must not be referenced.
- The PR chain lives in `fathya-core/fathiya-core`.

## PR chain host

All PR chain branches (`cursor/scope-auth-and-pr-chain-v0`, etc.) live in the canonical monorepo `fathya-core/fathiya-core`.

## Governing ADR

- ADR-001: `knowledge/decisions/ADR_001_FATHIYA_MONOREPO_CANONICAL_REPOSITORY.md`

## Created

- Date: 2026-05-16
- Trigger: Repository identity correction task
- Branch: `cursor/repo-identity-correction-v0`
- Base: `cursor/scope-auth-and-pr-chain-v0`

## Updated

- Date: 2026-05-16
- Trigger: Monorepo consolidation — ADR-001 accepted
- Branch: `cursor/monorepo-consolidation-v0`
- Base: `cursor/repo-identity-correction-v0`
