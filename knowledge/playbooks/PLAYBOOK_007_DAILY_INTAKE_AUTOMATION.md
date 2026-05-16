# PLAYBOOK 007 — Daily Intake Automation

## Status
Final v0.

## Purpose
Run a daily intake loop that collects new sources, preserves them, classifies them, routes them through FATHIYA queues, and produces cards, reports, blockers, or receipts.

## Core rule
Daily intake does not execute external actions by default. It drafts, classifies, routes, and records receipts.

## Trigger
Use this playbook for recurring intake from:
- RSS
- Gmail
- Outlook
- saved links
- uploaded files
- Zapier Forms
- Chrome extension captures
- Perplexity or Manus research outputs
- Cursor reports
- market notes
- security articles
- workflow/tooling articles

## Outputs
- Raw Archive Item
- Intake Batch
- Triage Table
- Knowledge Card Candidate
- Agent/Workflow Artifact Candidate
- Crypto Signal Candidate
- Scope/Authorization Candidate
- Queue Entry
- Receipt
- Daily Intake Report

## Intake source fields
- source_id
- source_type
- source_name
- source_url
- captured_at
- extraction_quality
- raw_path
- owner
- status

## Procedure

### Step 1 — Collect
Pull or receive new items from connected sources. Preserve raw content first.

### Step 2 — Deduplicate
Check against prior source URLs, titles, hashes, and card IDs.

### Step 3 — Classify domain
Classify each item into one or more:
- agent_machine_workflow
- security_scope
- crypto_radar
- automation_tooling
- data_skill
- product_interface
- general_knowledge

### Step 4 — Select playbook
Route by domain:
- general source: PLAYBOOK_001
- agent/workflow/tooling: PLAYBOOK_002
- queue/receipt item: PLAYBOOK_003
- adapter/tool action: PLAYBOOK_004
- target/scope item: PLAYBOOK_005
- crypto/market item: PLAYBOOK_006

### Step 5 — Create queue entries
Each selected item gets a runtime queue entry with expected output and receipt path.

### Step 6 — Produce artifacts
Allowed outputs:
- draft card
- triage entry
- signal card
- workflow card
- tool contract draft
- blocker note
- daily report

### Step 7 — Write receipts
Every intake batch writes a receipt with counts, outputs, blockers, and next action.

### Step 8 — Update indexes
After accepted cards or artifacts, update or schedule update for search, domain, sensitivity, type, and graph indexes.

## Stop conditions
Stop or mark item needs_review if:
- source is missing
- content extraction is broken
- item is duplicate
- domain is unclear
- output artifact cannot be selected
- external action would be required
- policy/approval context is missing

## Daily report fields
- report_id
- date
- sources_checked
- raw_items_added
- duplicates
- cards_created
- artifacts_created
- blockers
- queue_entries
- receipts
- next_actions

## Automation boundaries
Allowed automatically:
- collect
- preserve raw
- classify
- draft artifacts
- create queue entries
- write receipts
- draft reports

Requires approval:
- sending email
- calling webhooks
- activating n8n workflows
- writing to main branch
- executing market actions
- target-specific external activity

## Success definition
This playbook succeeds when daily intake produces a batch report, all items are either routed or blocked with reason, and no item disappears without receipt.

## Required files
- knowledge/runtime/runtime_queue_v0.json
- knowledge/runtime/receipt_ledger_v0.json
- knowledge/registries/workflow_registry_v0.json
- knowledge/playbooks/PLAYBOOK_001_CORPUS_INTAKE_KNOWLEDGE_CONVERSION.md
- knowledge/playbooks/PLAYBOOK_002_AGENT_MACHINE_WORKFLOW_INTELLIGENCE_INTAKE.md
- knowledge/playbooks/PLAYBOOK_006_CRYPTO_RADAR_SIGNAL_INTAKE.md

## Next playbook
PLAYBOOK 008 — Command Center UI Requirements