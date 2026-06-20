# FATHIYA Command Center v0

## Canonical Status

This is the **active Command Center app** for the FATHIYA monorepo. It lives inside the canonical repository `fathya-core/fathiya-core` and is the single source of truth for the FATHIYA operational UI. There is no separate ops console repository that supersedes this — `fathya-project/fathiya-ops-console` is a legacy external mirror only (see ADR-001).

## Purpose

This is the first Command Center v0 implementation for the validated FATHIYA Operating Backbone.

It adds a new app route:

- `/command-center`
- `/agent-tasks/`

The page is built on the existing TanStack Start + React + Vite app and is intended to surface the operating state defined in:

- `knowledge/reports/architecture/FATHIYA_OPERATING_BACKBONE_v0.md`
- `knowledge/playbooks/PLAYBOOK_008_COMMAND_CENTER_UI_REQUIREMENTS.md`

## Local Agent OS

Run the local FATHIYA operator with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start-fathiya.ps1 -Detached -RestartRuntime -RestartWeb -RuntimePythonPath "C:\Users\pc\Documents\Codex\2026-06-04\fathiya-agent-runtime-v1\services\agent-runtime\.venv\Scripts\python.exe" -StateRoot "C:\Users\pc\Documents\Codex\2026-06-04\fathiya-agent-runtime-v1\services\agent-runtime\runtime" -KnowledgeRoot "C:\Users\pc\Documents\Codex\2026-06-04\fathiya-agent-runtime-v1\knowledge" -ToolInventoryPath "C:\Users\pc\Documents\Codex\2026-06-04\fathiya-operator-lanes-ui\knowledge\runtime\connected_tool_inventory_v1.json"
```

Then open:

- `http://127.0.0.1:5180/agent-tasks/`
- `http://127.0.0.1:8765/api/agent/command-center`

Check the public domain wiring with:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\link-fathiya-domain.ps1 -Json
```

To attach `fathya-core.com` to the current Netlify site, set `NETLIFY_AUTH_TOKEN` and rerun:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\link-fathiya-domain.ps1 -Apply -ProvisionSsl
```

Expected DNS target:

- Apex `fathya-core.com`: Netlify-compatible A record.
- `www.fathya-core.com`: CNAME to `thriving-fenglisu-ef18b1.netlify.app`.

## Backbone mapping

The Backbone defines this chain:

```text
Sources
-> Runtime Queue
-> Policy / Approval Gate
-> Tool Contract Resolver
-> Execution / Draft / Validation
-> Receipt Ledger
-> Awareness State Update
-> Command Center UI
```

The Command Center route maps those layers into the following screens:

| Screen                | Backbone layer                              | Primary data source(s)                                                                                                                                                           |
| --------------------- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Overview              | Awareness State Update + validation summary | `knowledge/FATHIYA_AWARENESS_STATE.json`, `knowledge/audit/FATHIYA_BACKBONE_VALIDATION_REPORT_v0.json`                                                                           |
| Runtime Queue         | Runtime Queue                               | `knowledge/runtime/runtime_queue_v0.json`                                                                                                                                        |
| Receipt Ledger        | Receipt Ledger                              | `knowledge/runtime/receipt_ledger_v0.json`                                                                                                                                       |
| Agents                | Registries / routing operators              | `knowledge/registries/agent_registry_v0.json`, `knowledge/registries/workflow_registry_v0.json`                                                                                  |
| Playbooks             | Playbook Layer                              | `knowledge/playbooks/PLAYBOOK_*.md`, `knowledge/audit/FATHIYA_BACKBONE_VALIDATION_REPORT_v0.json`                                                                                |
| Tool Contracts        | Tool Contract Resolver                      | `knowledge/registries/tool_contract_registry_v0.json`                                                                                                                            |
| Daily Intake          | Intake loop / corpus routing                | `knowledge/retrieval_index_summary.json`, `knowledge/retrieval_validation_report.json`, `knowledge/FATHIYA_AWARENESS_STATE.json`                                                 |
| Crypto Radar          | Crypto Radar Mode                           | derived from `knowledge/playbooks/PLAYBOOK_006_CRYPTO_RADAR_SIGNAL_INTAKE.md`, `knowledge/retrieval_index_summary.json`, `knowledge/registries/approval_policy_registry_v0.json` |
| Scope & Authorization | Scope / Target preparation                  | derived from `knowledge/playbooks/PLAYBOOK_005_SCOPE_AUTHORIZATION_PREPARATION.md`                                                                                               |
| Approval Queue        | Policy / Approval Gate                      | derived from `knowledge/registries/approval_policy_registry_v0.json` plus `knowledge/registries/tool_contract_registry_v0.json`                                                  |

## Data-loading adapter

The adapter lives in:

- `src/lib/command-center.ts`

### How it works

The app does **not** call external services for Command Center data.

Instead, the adapter:

1. imports local JSON and markdown files from `knowledge/`
2. parses them into a normalized snapshot
3. feeds that snapshot into the `/command-center` route loader

This approach was chosen because it works cleanly inside the existing app stack and keeps the Command Center tied directly to the canonical file-backed Backbone artifacts.

### Canonical vs derived data

Some v0 screens still use derived data because no dedicated live dataset exists yet:

- `runtime_queue_v0.json` and `receipt_ledger_v0.json` now contain live entries populated through the Runtime Queue → Receipt Ledger lifecycle.
- There is no dedicated live dataset yet for:
  - Daily Intake batch rows
  - Crypto Radar signals
  - Scope/Authorization target cards
  - Approval Queue entries

For those screens, the adapter uses a **documented derived fallback**:

- Daily Intake mixes retrieval summary data with awareness state
- Crypto Radar renders policy-backed radar rows from PB006 + approval policy
- Scope & Authorization renders preparation lanes from PB005
- Approval Queue renders approval-policy lanes mapped to current tool contracts

These rows are explicitly labeled in the UI as `derived`.

## Main implementation files

- `src/lib/command-center.ts`
- `src/routes/command-center.tsx`
- `src/routes/index.tsx`

## Validation expectation

Use the existing project scripts:

- `npm run build`
- `npm run lint`

If the project stack changes later and local knowledge imports stop working, the adapter already exposes a mock-fallback mode so the page fails visibly instead of silently.
