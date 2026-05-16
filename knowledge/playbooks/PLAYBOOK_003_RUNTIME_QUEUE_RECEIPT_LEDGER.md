# PLAYBOOK 003 — Runtime Queue & Receipt Ledger

## Status
Final v0.

## Purpose
Turn FATHIYA from a knowledge vault into an operating system by routing every actionable item through a queue and recording a receipt for every meaningful outcome.

## Why this exists
Cards and playbooks are not enough. FATHIYA needs runtime state:

- what is waiting
- what is running
- what is blocked
- what completed
- what failed
- what needs approval
- what proof exists

Without this layer, agents and tools act as loose helpers. With this layer, they become controlled operators.

## Trigger
Use this playbook when any task may become:

- agent work
- workflow execution
- GitHub write
- Cursor validation
- Manus research
- n8n/Zapier workflow
- model routing decision
- index rebuild
- artifact promotion
- approval-required action

## Core rule
No routed work should disappear.

Every routed task must end as one of:

```text
completed
blocked
failed
needs_review
waiting_approval
```

## Runtime Queue entry
Each queue entry requires:

```yaml
id:
timestamp:
source:
requested_by:
queue:
adapter:
mode:
input_artifact:
expected_output:
approval_required:
status:
receipt_path:
next_step:
```

## Queue selection

| Condition | Queue |
|---|---|
| source to card/index | Knowledge Queue |
| research/synthesis | Research Queue |
| repo/schema/validation | Engineering Queue |
| n8n/Zapier draft | Automation Queue |
| model/cost/context choice | Model Queue |
| external side effect | Approval Queue |
| routing/control decision | Hub |

## Status lifecycle

```text
draft
→ queued
→ running
→ completed
```

Blocked path:

```text
draft
→ queued
→ blocked
→ needs_context
```

Approval path:

```text
draft
→ waiting_approval
→ approved
→ running
→ completed
```

Failure path:

```text
running
→ failed
→ receipt_written
→ next_step_defined
```

## Receipt Ledger entry
Every receipt requires:

```yaml
receipt_id:
timestamp:
source_request:
queue:
adapter:
input_artifact:
output_artifact:
status:
error:
approval_reference:
next_step:
```

## Procedure

### Step 1 — Classify task
Determine whether the request is knowledge, research, engineering, automation, model routing, approval, or hub decision.

### Step 2 — Create queue entry
Write or update runtime queue with a pending entry.

### Step 3 — Check policy/approval
If external side effect exists, move to Approval Queue before execution.

External side effects include:
- GitHub write
- email send
- webhook call
- n8n activation
- public publication
- trading execution
- security testing against live target

### Step 4 — Assign adapter
Choose adapter from registry:
- FATHIYA Kernel
- Cursor Agent
- Manus AI
- GitHub
- Zapier MCP
- n8n
- Model Router

### Step 5 — Execute or draft
If approval is not required, run as draft/validation.
If approval is required, prepare payload preview first.

### Step 6 — Write receipt
No task is complete without a receipt.

### Step 7 — Update awareness state
Update current focus, completed artifacts, blockers, and next best action.

## Failure handling
If task fails:

1. Keep original queue entry.
2. Write receipt with `failed`.
3. Add exact error.
4. Add next step.
5. Do not retry blindly.

## Blocked handling
If missing input:

1. Mark `blocked`.
2. Specify missing artifact or context.
3. Record who/what can unblock.
4. Do not delete the task.

## Approval handling
If approval needed:

1. Create payload preview.
2. Create approval queue entry.
3. Wait for explicit command or approved policy.
4. Execute only after approval condition is satisfied.
5. Write execution receipt.

## Success definition
This playbook succeeds when:

- a queue entry exists
- correct queue is selected
- adapter is identified
- approval requirement is known
- output artifact is created or blocker is recorded
- receipt is written
- next step is clear

## Required files

```text
knowledge/runtime/runtime_queue_v0.json
knowledge/runtime/receipt_ledger_v0.json
knowledge/registries/agent_registry_v0.json
knowledge/registries/tool_contract_registry_v0.json
knowledge/registries/workflow_registry_v0.json
```

## Next playbook
PLAYBOOK 004 — Tool Contract Resolver