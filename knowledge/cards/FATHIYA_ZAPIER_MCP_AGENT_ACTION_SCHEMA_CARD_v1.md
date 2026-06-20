# FATHIYA Zapier MCP Agent Action Schema Card v1

Captured: 2026-06-18

Purpose: teach FATHIYA how to prepare real delegated agent actions from the connected Zapier MCP inventory, even when the local direct OAuth gateway is not connected yet.

## Current State

- Zapier MCP inventory is available from the Codex-hosted connector: 22 apps and 126 enabled actions.
- Local direct Zapier MCP OAuth is not connected, so unattended local execution must use inventory-only planning until the operator reconnects OAuth.
- Read-only actions can be prepared automatically. External writes remain approval-gated.
- Never expose internal Zapier routing metadata or secrets in operator-facing receipts.

## Agent Providers

### Cursor

Use Cursor for delegated coding, repository inspection, implementation plans, and follow-up instructions.

Primary write action:

- Action: Launch Agent
- Tool name: cursor_launch_agent
- Required params: repository_url, prompt_text
- Optional params: model, images, webhook_url, repository_ref, webhook_secret, target_branch_name, target_auto_create_pr
- Defaults: repository_ref=main, target_auto_create_pr=false
- Gate: approval required before hosted execution

Read/check action:

- Action: Find Agent Status
- Required params: agent_id

### Manus

Use Manus for broader multi-step task execution, product/design review, and large cross-tool research tasks.

Primary write action:

- Action: Create Task
- Tool name: manus_create_task
- Required params: prompt, agent_profile, share_visibility
- Optional params: connectors, hide_in_task_list
- Defaults: agent_profile=manus-1.6, share_visibility=private
- Gate: approval required before hosted execution

Follow-up action:

- Action: Continue Task (Add a New Prompt)
- Required params: task_id, prompt

### Zapier Agents

Use Zapier Agents only when an operator-created Zapier Agent should run a bounded task.

- Action: Run Agent
- Tool name: agents_run_agent
- Required params: agent_id
- Optional params: agent_input_message, wait_for_response
- Default: wait_for_response=true
- Gate: approval required before hosted execution

## Supporting Apps

GitHub:

- Find Repository: required repo, optional owner.
- Create Issue: required repo, title, body; optional labels, assignee, milestone; approval required.

Gmail:

- Find Email: required query.
- Create Draft: required to, subject, body; approval required.

Netlify:

- Start Deploy: required site_id; approval required.

Zapier Tables:

- Find Records: required table_id; optional filter, limit.
- Create Record: required table_id, fields; approval required.

AI by Zapier:

- Extract Content From URL: required url, optional instructions.
- Search Content Across URLs: required query and urls, optional instructions.
- Analyze and Return Data: required content and instructions.
- Treat these as approval-gated writes because the Zapier connector exposes them as write actions.

## Routing Rule

When the operator asks FATHIYA to "use Cursor", "use Manus", "run an agent", or "delegate this", first call `agent_provider_action_prepare`. The result should produce a suggested task with missing parameters and the exact approval boundary. Only call a hosted write action after the operator confirms the final prepared action.
