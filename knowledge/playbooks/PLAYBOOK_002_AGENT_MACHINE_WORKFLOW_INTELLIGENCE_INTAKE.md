# PLAYBOOK 002 — Agent / Machine / Workflow Intelligence Intake

## Status
Final v0 after full corpus study.

## Purpose
Convert agent, machine, MCP, automation, coding-agent, workflow, and runtime material into operating-layer artifacts instead of generic knowledge cards.

## Why this exists
The corpus showed that FATHIYA cannot become strong by storing knowledge only. The next layer is a runtime intelligence layer that knows:

- which agent should handle a task
- which skill is being invoked
- which workflow pattern applies
- which machine task is required
- which tool contract governs action
- which receipt proves completion

## Trigger
Use this playbook when an input mentions or implies:

- agent / agentic / autonomous
- Claude Code / Cursor / Manus / Gemini
- MCP / tool server / tool use
- workflow / orchestration / pipeline
- automation / scripts / CLI
- memory / vector DB / agentic memory
- model routing / inference cost
- runtime / queue / receipts
- UI/API tool execution
- human-in-the-loop
- coding agent context files

## Output artifact selection

Do not default to Knowledge Card.

| Detected pattern | Output |
|---|---|
| actor/capability | Agent Card |
| reusable skill | Skill Card |
| multi-step pattern | Workflow Card |
| executable unit | Machine Task |
| tool boundary | Tool Contract |
| failure point | Failure Mode Card |
| system change | Architecture Impact Note |
| model choice/cost | Model Router Rule |
| memory change | Memory Layer Note |
| UI change | Command Center Requirement |

## Procedure

### Step 1 — Preserve source
Save source in raw archive and create a triage receipt.

### Step 2 — Detect operational unit
Ask:
- Is this about an agent?
- Is this about a skill?
- Is this about a workflow?
- Is this about a machine task?
- Is this about a tool contract?
- Is this about runtime state?
- Is this about memory?
- Is this about model routing?
- Is this about UI/command center?

### Step 3 — Extract effect
For each input, extract:

```yaml
affected_layer:
  - hub
  - agent_registry
  - skill_registry
  - workflow_registry
  - machine_task_registry
  - tool_contract_registry
  - runtime_queue
  - receipt_ledger
  - model_router
  - app_ui
```

### Step 4 — Create artifact
Create the strongest matching artifact.

Required shared fields:
```yaml
id:
title:
source:
detected_pattern:
affected_layer:
input_contract:
output_contract:
tools:
approval_required:
receipt_required:
failure_modes:
next_action:
status:
```

### Step 5 — Route
Queue routing:

| Pattern | Queue | Adapter |
|---|---|---|
| research/synthesis | Research Queue | Manus |
| code/repo validation | Engineering Queue | Cursor |
| workflow draft | Automation Queue | n8n/Zapier draft |
| external mutation | Approval Queue | relevant adapter |
| card/index update | Knowledge Queue | Vault/Cursor |
| model routing rule | Model Queue | Model Router |

### Step 6 — Receipt
Every run creates:
```yaml
receipt_id:
timestamp:
source_artifact:
created_artifact:
queue:
adapter:
status:
error:
next_step:
```

### Step 7 — Promote
Promotion conditions:
- repeated pattern
- clear input/output
- tool boundary known
- receipt possible
- failure modes known
- no missing context

## Stop conditions
Mark `needs_context` if:
- tool boundary is vague
- no output artifact can be determined
- external action is implied but not approved
- article is hype-only
- input is too corrupted
- security target/scope is missing
- cost/model routing is unknown

## Success definition
A successful run creates at least one of:
- Agent Card
- Skill Card
- Workflow Card
- Machine Task
- Tool Contract
- Runtime Queue Rule
- Receipt Schema Update
- Model Router Rule
- Architecture Impact Note

## Next playbook
PLAYBOOK 003 — Runtime Queue & Receipt Ledger