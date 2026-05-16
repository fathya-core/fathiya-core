# PLAYBOOK 001 — Corpus Intake & Knowledge Conversion

## Status
Final v0 playbook.

## Purpose
Convert any new knowledge input into structured FATHIYA Vault memory without losing raw source context.

## When to use
Use this when new material arrives:
- article
- report
- markdown
- PDF text
- tool note
- Cursor result
- Manus result
- news item
- course note

## Mode
Knowledge Mode.

## Inputs
- source file or text
- source URL when available
- source name
- captured timestamp
- optional domain hint

## Outputs
- raw archive item
- cleaned item
- triage record
- knowledge card candidate
- relation graph update candidate
- audit receipt

## Folder targets
- Raw source: `knowledge/raw/inbox/`
- Cleaned/triage artifacts: `knowledge/audit/`
- Approved cards: `knowledge/cards/`
- Relations: `knowledge/graph.json`
- Search indexes: `knowledge/search_index.json` and related indexes

## Procedure

### Step 1 — Preserve raw input
Save the original input first. Do not summarize before preserving.

Required metadata:
- raw_id
- source
- url if present
- captured_at
- extraction_quality
- original_path

### Step 2 — Clean
Create a cleaned representation.

Check:
- duplicate
- broken extraction
- missing source
- partial text
- language
- obvious category

### Step 3 — Triage
Assign:
- domain
- category
- sensitivity
- confidence
- actionability
- review_required

Triage decision options:
- card_now
- cluster_first
- store_only
- needs_review
- reject_noise

### Step 4 — Convert to card candidate
If selected, create a Knowledge Card candidate with:
- id
- title
- summary
- core idea
- why it matters
- tags
- source
- domain
- category
- sensitivity
- decision boundary

### Step 5 — Link
Add relation candidates:
- mentions
- supports
- contradicts
- requires
- affects
- derived_from
- produced_from

### Step 6 — Quality Gate
Before promotion, verify:
- source exists
- required fields exist
- no duplicate card
- relation IDs resolve or are declared as placeholders
- decision boundary exists
- status is draft or reviewed

### Step 7 — Update indexes
After card approval, rebuild or update:
- search_index.json
- domain_index.json
- sensitivity_index.json
- type_index.json
- graph_neighbors.json

### Step 8 — Receipt
Write an audit receipt containing:
- input path
- output paths
- cards created
- relations created
- warnings
- next action

## Stop conditions
Stop and mark `needs_review` if:
- source is missing
- content is too corrupted
- ownership or usage context is unclear
- the item should become a Lab/Target/Crypto-specific card but lacks context
- external execution would be required

## Hub routing
Queue: Knowledge Queue
Adapters:
- Local Vault
- Cursor Agent for validation
- Manus AI for deep synthesis when needed

Approval required:
- No for draft knowledge conversion
- Yes for external write, execution, or publication

## Success definition
A run is complete only when it produces at least one of:
- raw archive entry
- triage record
- card candidate
- relation update candidate
- audit receipt

## Next playbook
PLAYBOOK 002 — Agent / Machine / Workflow Intelligence Intake