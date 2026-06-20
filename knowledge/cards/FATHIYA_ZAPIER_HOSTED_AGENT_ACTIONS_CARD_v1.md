# FATHIYA Zapier Hosted Agent Actions Card v1

Captured: 2026-06-18

## Purpose

FATHIYA can see a hosted Zapier MCP inventory even while the local OAuth gateway
is not connected. Treat this as planning knowledge: the agent can choose the
right app/action shape, but local live execution still requires the Zapier OAuth
activation gate.

## Current Hosted Inventory

- Enabled apps: 22
- Enabled actions: 126
- High-value agent providers: GitHub, Cursor, Manus, Agents, AI by Zapier,
  Gmail, Microsoft Outlook, Netlify, Webhooks by Zapier, MCP Client by Zapier,
  Code by Zapier, Zapier Tables, Zapier Manager, Zapier Functions.

## Agent Provider Actions

### Cursor

Read:

- Find Agent Status
- Make API GET Request

Write or mutating:

- Launch Agent
- Add Followup Instruction to Agent
- Make API Mutating Request
- Delete Agent

Operational use: use Cursor for coding-agent handoffs, status checks, and
follow-up instructions after OAuth activation. Do not use delete or mutating
actions without an explicit approval gate.

### Manus

Read:

- Get Tasks

Write or mutating:

- Create Task
- Continue Task
- Get Task
- Update Task
- Delete Task

Operational use: use Manus for broad research/build task delegation after OAuth
activation. Treat create/update/continue as external writes.

### Agents

Write:

- Run Agent

Operational use: use Agents for one-shot Zapier-hosted agent execution only
after selecting the configured agent and passing the approval gate.

### GitHub

Read:

- Find Repository
- Find Issue
- Find Pull Request
- Find Branch
- Find User

Write:

- Create Pull Request
- Create Issue
- Create Comment
- Create or Update File

Operational use: prefer GitHub CLI for local authenticated repository reads and
safe local workflow. Use Zapier GitHub actions when the agent needs cross-app
automation or when the Zapier workflow is the target.

## Activation Gates

- Local Zapier OAuth is not live yet. Current local state is inventory-only.
- The local runtime should open `/api/agent/oauth/zapier/start` to activate live
  execution.
- Until activation succeeds, FATHIYA may plan actions and prepare parameters,
  but it must not claim that Zapier live execution has run from the local engine.

## Mastery Check

FATHIYA understands this card when it can answer:

1. Which Zapier apps are usable as agent providers?
2. Which actions are read-only versus mutating?
3. Why does hosted inventory not equal local live execution?
4. What gate must pass before Cursor, Manus, or Agents actions can execute from
   the local runtime?
