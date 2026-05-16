# PLAYBOOK 008 — Command Center UI Requirements

## Status
Final v0.

## Purpose
Define the Command Center UI requirements for FATHIYA so the system can be operated through visible state, queues, agents, playbooks, receipts, and approvals instead of hidden conversation context.

## Core rule
If the system has runtime state, the UI must show it.

## Why this exists
FATHIYA is no longer only a vault. It now has:
- Playbooks
- Runtime Queue
- Receipt Ledger
- Agent Registry
- Workflow Registry
- Tool Contract Registry
- Daily Intake
- Crypto Radar
- Scope/Authorization workflow

The Command Center is the control surface for these layers.

## Primary screens

### 1. Overview
Shows system status.

Required widgets:
- current focus
- active queue count
- blocked items
- latest receipts
- open PRs
- active agents
- next recommended action

### 2. Runtime Queue
Shows every queued, running, blocked, waiting approval, failed, and completed task.

Required columns:
- id
- timestamp
- source
- queue
- adapter
- mode
- expected output
- approval required
- status
- receipt path
- next step

### 3. Receipt Ledger
Shows proof of completed, failed, blocked, or approved work.

Required columns:
- receipt id
- timestamp
- queue
- adapter
- input artifact
- output artifact
- status
- error
- approval reference
- next step

### 4. Agents
Shows available agents and their role.

Required fields:
- agent id
- name
- role
- queue
- capabilities
- tools
- permissions
- status
- failure modes

### 5. Playbooks
Shows all playbooks and next chain.

Required fields:
- playbook id
- title
- status
- purpose
- required files
- next playbook
- last validation

### 6. Tool Contracts
Shows adapter boundaries.

Required fields:
- tool id
- adapter
- queue
- allowed actions
- side effects
- approval required
- receipt required
- failure modes
- status

### 7. Daily Intake
Shows ingestion pipeline.

Required fields:
- source
- captured count
- duplicates
- classified domains
- cards drafted
- blockers
- receipts
- next actions

### 8. Crypto Radar
Shows radar state, not trading execution.

Required fields:
- signal id
- asset or sector
- narrative
- catalyst
- timeframe
- risk factors
- invalidation
- confidence
- status

### 9. Scope & Authorization
Shows target preparation status.

Required fields:
- target id
- name
- policy URL
- scope status
- authorization status
- blocked reason
- next artifact
- receipt

### 10. Approval Queue
Shows actions that require explicit approval before external side effect.

Required fields:
- approval id
- requested action
- tool contract
- payload preview
- side effects
- rollback or recovery note
- requester
- status

## Navigation model
Recommended top navigation:
- Overview
- Queue
- Receipts
- Agents
- Playbooks
- Tools
- Intake
- Radar
- Scope
- Approvals

## UI principles
- state first
- no hidden execution
- every action has receipt
- every tool has contract
- every blocker has next step
- every queue item has owner or adapter
- every external action shows approval state

## Command actions
Allowed UI actions:
- create queue entry
- mark blocked
- attach receipt
- open source artifact
- launch Cursor validation
- create Manus research task
- draft GitHub file update
- generate daily report
- create signal card draft
- create target card draft

Approval-required UI actions:
- write to main branch
- send email
- call webhook
- activate workflow
- execute market action
- run target-specific external activity

## Data sources
The UI reads from:
- knowledge/runtime/runtime_queue_v0.json
- knowledge/runtime/receipt_ledger_v0.json
- knowledge/registries/agent_registry_v0.json
- knowledge/registries/workflow_registry_v0.json
- knowledge/registries/tool_contract_registry_v0.json
- knowledge/playbooks/
- knowledge/retrieval_index_summary.json
- knowledge/FATHIYA_AWARENESS_STATE.json

## Success definition
This playbook succeeds when the app can display current operational state and route the next action without depending on memory hidden in chat.

## Next playbook
PLAYBOOK 009 — Model Router & Cost-Aware Inference