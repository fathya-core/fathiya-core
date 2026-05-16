# ADR-001: FATHIYA Monorepo as Canonical Repository

## Status

**Accepted** — 2026-05-16

## Context

The FATHIYA project evolved across two GitHub repositories:

| Repository | Organization | Role (historical) |
|---|---|---|
| `fathya-core/fathiya-core` | fathya-core | Core knowledge, runtime, registries, playbooks, Command Center UI |
| `fathya-project/fathiya-ops-console` | fathya-project | Ops Console front-end (Bolt-deployed) |

This split introduced ambiguity about which repository is the source of truth for architecture decisions, runtime state, and operational artifacts. It also risked divergence between the core backbone and the ops console, since they share the same runtime queue, receipt ledger, registries, and awareness state.

Key problems with maintaining two independent repositories:

1. **Split brain**: Two repositories claiming authority over overlapping operational surfaces.
2. **Drift**: Registries, queue schemas, and playbook references could diverge without a shared commit history.
3. **Duplication**: Knowledge artifacts, security scope maps, and target cards had to reference both repos as separate sources of truth.
4. **Coordination overhead**: PRs, branch chains, and architecture decisions had to be synchronized across two repos with different org owners.

## Decision

**Use `fathya-core/fathiya-core` as the single canonical repository for all FATHIYA architecture.**

Specifically:

1. **One system, one source of truth.** All knowledge, runtime, receipts, registries, playbooks, Command Center UI, and future ops console functionality live inside `fathya-core/fathiya-core`.
2. **The Command Center app in this repo is the active operational UI.** It is not a placeholder or stub — it is the authoritative implementation of PLAYBOOK_008.
3. **`fathya-project/fathiya-ops-console` becomes a legacy/external mirror.** It is not the source of truth. It may continue to exist as a deployment mirror or historical reference, but architectural authority flows from the monorepo.
4. **No deletion of the external repo.** The legacy repository is preserved as-is. It is simply demoted from "independent system" to "optional external deployment mirror."

## Consequences

### Positive

- Single PR chain for all architectural changes.
- Backbone artifacts (runtime queue, receipt ledger, registries, awareness state) have one canonical home.
- Security scope maps and target cards reference one primary repository.
- Reduced coordination overhead between organizations.
- Clear ownership model for future contributors and agents.

### Negative / Trade-offs

- The external Bolt-deployed ops console at `fathiya-ops-console-0jfl.bolt.host` may need a sync mechanism or redirect strategy if it continues to serve traffic.
- Contributors who previously worked in `fathya-project/fathiya-ops-console` must redirect to the monorepo.

### Neutral

- `fathya-project/fathiya-ops-console` is not deleted. It remains available as a historical archive or deployment mirror.
- This ADR does not prescribe a specific migration timeline for external deployments.

## References

- `knowledge/audit/FATHIYA_REPOSITORY_IDENTITY_MAP_v0.md` — Repository identity corrections
- `knowledge/reports/architecture/FATHIYA_OPERATING_BACKBONE_v0.md` — Operating backbone definition
- `knowledge/audit/FATHIYA_MONOREPO_CONSOLIDATION_REPORT_v0.md` — Migration state report
- Branch: `cursor/monorepo-consolidation-v0`
- Base: `cursor/repo-identity-correction-v0`
