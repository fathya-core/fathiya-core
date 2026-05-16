# FATHIYA Command Center Hardening Report v0

## Summary

| Field | Value |
|---|---|
| Date | 2026-05-16 |
| Branch | `cursor/command-center-hardening-v0` |
| Base Branch | `cursor/command-center-v0` |
| Predecessor PR | PR #6 — Add initial FATHIYA Command Center v0 |
| Predecessor Base | PR #5 — Validate Operating Backbone v0 |
| Framework | TanStack Start + React + Vite |
| Result | Command Center v0 hardened |

## What changed

### 1. Misleading fallback data removed

PR #6 included fabricated fallback rows for sections with no live dataset. This hardening pass replaced them with explicit empty states or clearly labeled `derived_from_backbone` rows.

| Section | PR #6 behavior | Hardened behavior |
|---|---|---|
| Crypto Radar | 2 fabricated signal rows (`derived`) | Empty state — no live signal-card dataset exists |
| Scope & Authorization | 2 hardcoded target rows (`derived`) | Empty state — no Target Cards or scope maps exist yet |
| Approval Queue | Policy-class rows labeled `derived` | Kept, relabeled `derived_from_backbone` with explicit description |
| Daily Intake row 2 | Backbone audit row labeled `derived` | Kept, relabeled `derived_from_backbone` |

### 2. Data provenance added per section

A new `sectionProvenance` field was added to `CommandCenterSnapshot`, providing for each UI section:

- `source_file` — the knowledge file(s) backing the section
- `data_status` — one of `live`, `empty`, `derived_from_backbone`, or `planned`
- `notes` — human-readable explanation of what the data represents

Provenance banners are rendered in the UI for every tab, color-coded by status.

### 3. Build lineage surfaced

A new `lineage` field was added to the snapshot, and a "Build lineage" card is rendered in the UI header area showing:

- PR #5 as the validated backbone checkpoint
- PR #6 as the Command Center layer built on it
- The base branch relationship

### 4. Removed derived source entry

The `sources` array no longer includes the misleading "Derived fallback lanes" entry that grouped PB005, PB006, and approval policy together as a single derived source. Each section now explains its own provenance independently.

### 5. Loader note updated

The `loaderNote` text was updated to reflect the hardened behavior: sections with no live data show explicit empty states rather than policy-aware fallback rows.

## Changed files

| File | Change |
|---|---|
| `src/lib/command-center.ts` | Added `DataProvenance` type, `sectionProvenance` and `lineage` to snapshot, replaced Crypto Radar and Scope Auth with empty arrays, relabeled sourceType values, removed derived source entry |
| `src/routes/command-center.tsx` | Added `ProvenanceBanner` component, lineage card in header, empty states for Crypto Radar and Scope Auth, provenance banners for all tabs, updated section descriptions |
| `knowledge/audit/FATHIYA_COMMAND_CENTER_HARDENING_REPORT_v0.md` | This file |

## Validation

### Commands run

```text
npm ci
npm run build
npx eslint src/lib/command-center.ts src/routes/command-center.tsx src/routes/index.tsx
```

### Results

| Command | Status | Notes |
|---|---|---|
| `npm run build` | PASS | Client + SSR build completed successfully |
| `npx eslint` (targeted) | PASS | All three changed files pass lint after prettier auto-fix |
| `npm run lint` | FAIL (pre-existing) | Repository-wide issues outside Command Center — not addressed per scope |

## Section data status summary

| Section | data_status | Source files | Notes |
|---|---|---|---|
| Overview | `live` | FATHIYA_AWARENESS_STATE.json, FATHIYA_BACKBONE_VALIDATION_REPORT_v0.json | Metrics from real files |
| Runtime Queue | `empty` | runtime_queue_v0.json | Queue catalog populated, queue_entries array empty |
| Receipt Ledger | `empty` | receipt_ledger_v0.json | Policy and fields populated, receipts array empty |
| Agents | `live` | agent_registry_v0.json, workflow_registry_v0.json | Real registry data |
| Playbooks | `live` | PLAYBOOK_*.md | Parsed from 9 markdown files |
| Tool Contracts | `live` | tool_contract_registry_v0.json, model_router_registry_v0.json | Real registry data |
| Daily Intake | `derived_from_backbone` | retrieval_index_summary.json, retrieval_validation_report.json | Row 1 canonical, row 2 derived audit |
| Crypto Radar | `planned` | — | No dataset exists; PB006 defines the process |
| Scope & Authorization | `planned` | — | No Target Cards exist; PB005 defines the process |
| Approval Queue | `derived_from_backbone` | approval_policy_registry_v0.json, tool_contract_registry_v0.json | Policy-class rows, not live requests |

## Remaining fallbacks

Two sections still use `derived_from_backbone` data:

1. **Daily Intake** — Row 1 is canonical (retrieval data). Row 2 summarizes backbone validation metrics and is labeled `derived_from_backbone`. This is intentional: the backbone validation report is a real file.

2. **Approval Queue** — Rows are derived from the approval policy registry. These represent real policy gates that exist in the backbone, not fabricated entries. Labeled `derived_from_backbone`.

## Empty states

Two sections now show explicit empty states:

1. **Crypto Radar** — Will populate when PB006 intake batches produce signal cards.
2. **Scope & Authorization** — Will populate when PB005 produces Target Cards and Scope Maps.

## Next steps

1. Write the first runtime queue entry to move Queue from `empty` to `live`.
2. Record the first receipt to move Receipt Ledger from `empty` to `live`.
3. Run the first PB006 intake batch to populate Crypto Radar.
4. Run PB005 preparation to produce the first Target Card for Scope & Authorization.
5. Promote the first live approval request to shift Approval Queue from `derived_from_backbone` to `live`.
6. Address repo-wide lint debt separately from Command Center hardening.
