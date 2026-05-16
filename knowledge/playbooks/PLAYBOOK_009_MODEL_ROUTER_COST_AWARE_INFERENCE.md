# PLAYBOOK 009 — Model Router & Cost-Aware Inference

## Status
Final v0.

## Purpose
Route each FATHIYA task to the right model or reasoning layer based on task type, context size, risk, cost, latency, and required output quality.

## Core rule
Do not use the strongest model for every task. Use the smallest sufficient model that can safely produce the required artifact.

## Why this exists
FATHIYA uses multiple intelligence layers:
- FATHIYA Kernel
- ChatGPT reasoning
- Gemini
- Manus AI
- Perplexity-style research
- Cursor Agent
- local scripts
- future specialized models

Without routing, cost rises, context gets wasted, and low-risk tasks consume high-risk resources.

## Trigger
Use this playbook when a request involves:
- model selection
- long context reading
- source-heavy research
- code validation
- schema generation
- daily intake classification
- crypto signal synthesis
- architecture decisions
- security scope review
- cost-sensitive automation

## Routing dimensions
Each task is scored across:
- task_type
- context_size
- reasoning_depth
- freshness_requirement
- source_requirement
- execution_risk
- cost_budget
- latency_need
- output_artifact
- confidence_requirement

## Model lanes

### Lane 1 — Simple Classification
For tagging, routing, dedupe hints, and short summaries.

Use when:
- low risk
- small context
- structured output
- no external action

Outputs:
- classification label
- queue recommendation
- draft metadata

### Lane 2 — Structured Drafting
For cards, schemas, queue entries, receipts, and playbook drafts.

Use when:
- artifact format is known
- source is already preserved
- moderate context

Outputs:
- Knowledge Card
- Workflow Card
- Tool Contract Draft
- Receipt Draft

### Lane 3 — Deep Reasoning
For architecture, policy, conflict resolution, and high-impact decisions.

Use when:
- system design changes
- multiple constraints conflict
- high confidence needed
- downstream automation depends on result

Outputs:
- architecture decision
- policy update
- runtime change
- promotion decision

### Lane 4 — Research Synthesis
For multi-source research and external source comparison.

Use when:
- source freshness matters
- source attribution matters
- comparison is required

Adapters:
- Manus AI
- Perplexity/Gemini as supporting sources when available

Outputs:
- research brief
- source map
- comparison report

### Lane 5 — Engineering Validation
For repo, schema, code, build, and file consistency checks.

Adapters:
- Cursor Agent
- local scripts

Outputs:
- validation report
- patch
- PR
- test result

### Lane 6 — Human Approval / Policy Gate
For external side effects or high-impact actions.

Use when:
- writing to main
- sending email
- calling webhook
- activating workflow
- executing market action
- target-specific external activity

Outputs:
- payload preview
- approval entry
- execution receipt

## Routing procedure

### Step 1 — Classify task
Determine:
- task type
- expected artifact
- queue
- adapter need
- approval need

### Step 2 — Estimate context size
Classify context:
- tiny
- small
- medium
- large
- corpus-scale

### Step 3 — Determine risk
Risk levels:
- low: draft/classification only
- medium: repo or system artifact update
- high: external side effect or policy-sensitive output
- critical: irreversible or financially/security sensitive action

### Step 4 — Select lane
Pick the lowest lane that can satisfy the required confidence.

### Step 5 — Route
Write model routing decision into runtime queue entry.

### Step 6 — Receipt
Record:
- selected lane
- selected adapter/model
- reason
- confidence
- fallback
- cost note

## Fallback rules
If output fails:
1. reduce task scope
2. retrieve narrower context
3. escalate one lane
4. call specialist adapter
5. write blocked receipt if still unresolved

## Cost controls
Prefer:
- cached indexes before full corpus reading
- summaries before raw corpus
- targeted retrieval before global context
- local validation before agent launch
- draft-only mode before external action

## Stop conditions
Stop and mark blocked if:
- task requires unavailable source freshness
- model cannot access needed context
- expected output is undefined
- approval need is unresolved
- cost is disproportionate to value
- execution risk exceeds current policy

## Success definition
This playbook succeeds when every model-assisted task records why a model/lane was selected, what artifact is expected, whether approval is required, and where the receipt lives.

## Required files
- knowledge/runtime/runtime_queue_v0.json
- knowledge/runtime/receipt_ledger_v0.json
- knowledge/registries/agent_registry_v0.json
- knowledge/registries/tool_contract_registry_v0.json
- knowledge/playbooks/PLAYBOOK_003_RUNTIME_QUEUE_RECEIPT_LEDGER.md

## Next playbook
PLAYBOOK 010 — Memory Retrieval & Index Refresh