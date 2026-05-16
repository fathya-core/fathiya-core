# PLAYBOOK 005 — Scope & Authorization Preparation

## Status
Final v0.

## Purpose
Prepare any target, program, asset, or report context before planning, routing, documentation, or tool use.

## Core rule
No target-specific work without a Target Card.

## Target Card fields
- target_id
- name
- program
- policy_url
- authorized_scope
- forbidden_scope
- asset_types
- engagement_rules
- rate_limits
- data_handling
- reporting_channel
- allowed_artifacts
- forbidden_actions
- approval_required
- status

## Mode selection
- learning only: Knowledge Mode
- owned local app: Lab Mode
- sandbox or training environment: Lab Mode
- public program with written policy: Target-Specific Mode
- unclear ownership: blocked / needs_context
- third-party target without authorization: blocked

## Outputs
- Target Card
- Scope Map
- Asset Inventory
- Boundary Note
- Hypothesis List
- Evidence Template
- Report Draft Template
- Risk Note
- Queue Entry
- Receipt

## Procedure
1. Identify target context: target name, program name, policy URL, authorization, asset list, request goal.
2. Read policy: allowed assets, excluded assets, categories, rate limits, automation limits, data handling, reporting process, safe harbor language.
3. Build Target Card.
4. Build Scope Map: in_scope, out_of_scope, unknown_scope, requires_clarification.
5. Select artifact type.
6. Route through Runtime Queue.
7. Apply PLAYBOOK_004_TOOL_CONTRACT_RESOLVER before tool-assisted activity.
8. Write receipt.

## Stop conditions
Stop and mark blocked if policy URL is missing, authorization is missing, scope is unclear, ownership is unclear, request is outside allowed scope, external action lacks approval, or data handling rules are unknown.

## Success definition
This playbook succeeds when Target Card exists or blocker is recorded, scope is classified, policy status is known, queue route is selected, next artifact is clear, and receipt is written or planned.

## Required files
- knowledge/playbooks/PLAYBOOK_004_TOOL_CONTRACT_RESOLVER.md
- knowledge/runtime/runtime_queue_v0.json
- knowledge/runtime/receipt_ledger_v0.json
- knowledge/registries/tool_contract_registry_v0.json

## Next playbook
PLAYBOOK 006 — Crypto Radar & Signal Intake