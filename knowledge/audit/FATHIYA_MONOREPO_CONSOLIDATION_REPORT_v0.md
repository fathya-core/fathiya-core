# FATHIYA Monorepo Consolidation Report v0

## Date

2026-05-16

## Branch

`cursor/monorepo-consolidation-v0` → base `cursor/repo-identity-correction-v0`

## Current State

### Before this consolidation

The FATHIYA project had two repositories:

| Repository | Role | Status |
|---|---|---|
| `fathya-core/fathiya-core` | Core monorepo: knowledge vault, runtime, registries, playbooks, Command Center UI, backbone | Active, primary development |
| `fathya-project/fathiya-ops-console` | External Ops Console front-end (Bolt-deployed at `fathiya-ops-console-0jfl.bolt.host`) | Active, separate app |

Both repositories were referenced as independent systems in:

- Target Card (`TARGET_FATHIYA_CORE_OWNED_SURFACE_v0.json`)
- Scope Map (`SCOPE_MAP_FATHIYA_CORE_OWNED_SURFACE_v0.json`)
- Repository Identity Map (`FATHIYA_REPOSITORY_IDENTITY_MAP_v0.md`)

### After this consolidation

| Repository | Role | Status |
|---|---|---|
| `fathya-core/fathiya-core` | **Canonical monorepo** — all FATHIYA architecture | **Single source of truth** |
| `fathya-project/fathiya-ops-console` | Legacy external mirror | **Not source of truth** |

## Why Monorepo Is Chosen

1. **Eliminate split brain.** Two repositories claiming authority over overlapping surfaces (runtime, registries, UI) creates ambiguity and drift risk.
2. **Single PR chain.** Architecture decisions, backbone changes, and operational artifacts share one commit history.
3. **Command Center already exists here.** The core repo already contains the active Command Center implementation (`/command-center` route, `src/lib/command-center.ts`, `src/routes/command-center.tsx`). There is no reason for a separate ops console.
4. **Registry and runtime coherence.** The runtime queue, receipt ledger, registries, and awareness state are all file-backed artifacts in the knowledge directory. Having the UI in the same repo means it reads canonical data directly.
5. **Scope simplification.** Security scope maps, target cards, and audit artifacts reference one primary repository instead of coordinating across two orgs.

## What Happens to `fathya-project/fathiya-ops-console`

| Action | Description |
|---|---|
| **Not deleted** | The repository is preserved as-is. No branches or repos are removed. |
| **Demoted** | It is no longer the source of truth for any FATHIYA architecture. |
| **Mirror status** | It may continue to serve as an optional deployment mirror or historical reference. |
| **No sync obligation** | The monorepo does not have an obligation to push changes to the external repo. |
| **External deployment** | The Bolt deployment at `fathiya-ops-console-0jfl.bolt.host` is noted as a legacy external mirror in the Target Card and Scope Map. |

## Artifacts Changed

| File | Change |
|---|---|
| `knowledge/decisions/ADR_001_FATHIYA_MONOREPO_CANONICAL_REPOSITORY.md` | Created — formal ADR for the monorepo decision |
| `knowledge/audit/FATHIYA_REPOSITORY_IDENTITY_MAP_v0.md` | Updated — reflects canonical monorepo, legacy mirror distinction |
| `knowledge/audit/FATHIYA_MONOREPO_CONSOLIDATION_REPORT_v0.md` | Created — this report |
| `knowledge/security/targets/TARGET_FATHIYA_CORE_OWNED_SURFACE_v0.json` | Updated — ops console entries marked as `legacy_external_mirror` |
| `knowledge/security/scope_maps/SCOPE_MAP_FATHIYA_CORE_OWNED_SURFACE_v0.json` | Updated — ops console entries marked as `legacy_external_mirror` |
| `README_COMMAND_CENTER_v0.md` | Updated — documents this as the active canonical Command Center |
| `knowledge/runtime/runtime_queue_v0.json` | Updated — queue entry for monorepo consolidation |
| `knowledge/runtime/receipt_ledger_v0.json` | Updated — receipt for monorepo consolidation |
| `knowledge/runtime/receipts/receipt-2026-05-16-fathiya-monorepo-consolidation-v0.json` | Created — individual receipt file |

## Next Steps

1. Validate that all future artifacts, PRs, and playbook references treat `fathya-core/fathiya-core` as the single source of truth.
2. If the Bolt deployment at `fathiya-ops-console-0jfl.bolt.host` continues to serve traffic, consider adding a redirect or deprecation notice.
3. Future ops console features should be developed inside the monorepo app structure, not in the external repo.
4. Update any external documentation, onboarding materials, or contributor guides that reference two separate systems.
5. Do not delete `fathya-project/fathiya-ops-console` — it remains available as a historical archive.

## Governing ADR

ADR-001: `knowledge/decisions/ADR_001_FATHIYA_MONOREPO_CANONICAL_REPOSITORY.md`
