# PLAYBOOK 004 — Tool Contract Resolver

## Status
Final v0.

## Purpose
Resolve which tool or adapter is allowed to handle a task, what inputs it needs, what outputs it must return, what side effects it may create, and what receipt proves completion.

## Why this exists
FATHIYA has many powerful tools:

- GitHub
- Cursor Agent
- Manus AI
- Zapier MCP
- n8n
- Webhooks
- Email tools
- Files tools
- Model providers
- Local machine tools

Power without contracts becomes chaos. This playbook turns tools into governed adapters.

## Trigger
Use this playbook when a task requires or implies:

- tool selection
- API action
- adapter call
- GitHub write
- Cursor agent launch
- Manus research task
- webhook
- n8n workflow
- file generation
- email send/draft
- model routing
- external side effect

## Core rule
No tool is called without a contract.

A valid tool contract defines:

```yaml
tool_id:
name:
adapter:
queue:
allowed_actions:
input_schema:
output_schema:
side_effects:
approval_required:
receipt_required:
failure_modes:
status:
```

## Resolution procedure

### Step 1 — Identify intent
Classify the requested operation:

| Intent | Example adapter |
|---|---|
| repo write / validation | GitHub / Cursor |
| research synthesis | Manus |
| workflow draft | n8n / Zapier |
| external HTTP call | Webhooks |
| file generation | Files by Zapier / local |
| email operation | Gmail / Outlook |
| model choice | Model Router |
| knowledge update | Vault / Cursor |

### Step 2 — Locate contract
Find matching contract in:

```text
knowledge/registries/tool_contract_registry_v0.json
```

If no contract exists, create a draft Tool Contract before execution.

### Step 3 — Validate input contract
Before calling the adapter, confirm required fields exist.

Examples:

GitHub file write requires:
```yaml
repo:
branch:
path:
content:
commit_message:
```

Cursor launch requires:
```yaml
repository_url:
repository_ref:
target_branch_name:
prompt_text:
target_auto_create_pr:
```

### Step 4 — Check side effects
Classify side effect:

| Side effect | Approval |
|---|---|
| local draft | not required |
| research task | not required unless external publication |
| branch write | required |
| PR creation | required |
| webhook call | required |
| email send | required |
| n8n activation | required |
| trading execution | required |
| live target action | required |

### Step 5 — Route through queue
Select queue:

- Knowledge Queue
- Research Queue
- Engineering Queue
- Automation Queue
- Model Queue
- Approval Queue
- Hub

Write or update runtime queue entry.

### Step 6 — Build payload preview
For approval-required operations, create:

```yaml
payload_preview:
  tool_id:
  adapter:
  action:
  input_summary:
  side_effects:
  expected_output:
  rollback_or_recovery:
```

### Step 7 — Execute or block
Execute only when:

- contract exists
- input schema is satisfied
- side effects are understood
- approval requirement is satisfied
- receipt path is defined

Otherwise mark blocked.

### Step 8 — Write receipt
Every adapter call writes a receipt:

```yaml
receipt_id:
timestamp:
tool_id:
adapter:
action:
input_artifact:
output_artifact:
status:
error:
approval_reference:
next_step:
```

## Failure handling
If tool fails:

1. Do not retry blindly.
2. Record exact error.
3. Classify failure mode.
4. Write failed receipt.
5. Define next step.

## Missing contract handling
If no tool contract exists:

1. Create draft Tool Contract.
2. Mark task as `blocked_missing_contract`.
3. Add required inputs/outputs.
4. Add side effect classification.
5. Return to queue after contract review.

## Conflict handling
If multiple tools can do the same job:

Choose by priority:

1. lowest side effect
2. most observable output
3. strongest receipt
4. lowest cost
5. most reversible
6. most direct adapter

## Success definition
This playbook succeeds when:

- tool is selected or blocked with reason
- contract exists or draft contract is created
- input/output schema is known
- approval need is known
- queue entry exists
- receipt is written or planned
- next step is clear

## Required files

```text
knowledge/registries/tool_contract_registry_v0.json
knowledge/runtime/runtime_queue_v0.json
knowledge/runtime/receipt_ledger_v0.json
knowledge/playbooks/PLAYBOOK_003_RUNTIME_QUEUE_RECEIPT_LEDGER.md
```

## Next playbook
PLAYBOOK 005 — Security Target Preparation