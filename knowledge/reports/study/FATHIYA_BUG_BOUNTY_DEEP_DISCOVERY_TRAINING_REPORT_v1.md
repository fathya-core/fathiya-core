# FATHIYA Bug Bounty Deep Discovery Training Report v1

Status: deeper discovery training prepared
Date: 2026-06-14
Mode: authorized bug bounty and local lab only

## What This Adds

The previous bug bounty layer taught FATHIYA safe bug bounty behavior. This layer teaches deeper discovery behavior: finding simple and complex vulnerabilities, selecting the right tools, and asking for or collecting missing requirements before testing.

New artifacts:

- `knowledge/playbooks/FATHIYA_BUG_BOUNTY_DISCOVERY_PLAYBOOK_v1.json`
- `knowledge/playbooks/FATHIYA_BUG_BOUNTY_TOOL_ORCHESTRATION_MATRIX_v1.json`
- `knowledge/policies/FATHIYA_BUG_BOUNTY_REQUIREMENTS_INTAKE_v1.json`
- `knowledge/evaluations/FATHIYA_BUG_BOUNTY_DEEP_DISCOVERY_EVALS_v1.json`
- `knowledge/reports/study/FATHIYA_BUG_BOUNTY_DEEP_DISCOVERY_TRAINING_REPORT_v1.md`

## Core Upgrade

FATHIYA should now treat every bug bounty request as a requirements-and-discovery workflow:

1. Ask for or collect the program policy, scope, rate limits, and reporting channel.
2. Ask for test accounts, API docs, mobile artifacts, callback endpoint, and safe test data when needed.
3. Classify vulnerability classes by simple, medium, or complex discovery paths.
4. Use all relevant tools by phase: readiness, policy/docs collection, passive mapping, scoped active leads, manual validation, chain analysis, and report drafting.
5. Stop when scope, accounts, safe data, or approval are missing.

## Simple Vulnerability Coverage

The discovery playbook now covers:

- missing or weak security headers;
- exposed docs and OpenAPI descriptors;
- debug pages and version leakage;
- static files and backup exposure;
- CORS and cross-domain policy candidates;
- simple reflected/stored/client-side XSS paths;
- subdomain takeover candidate evidence.

## Complex Vulnerability Coverage

The discovery playbook now covers:

- IDOR/BOLA/BFLA and object-property authorization;
- business logic and workflow state flaws;
- OAuth/OIDC, JWT, and session lifecycle issues;
- WebSocket/realtime authorization;
- SSRF and server-side fetch behavior;
- file upload and content processing chains;
- GraphQL/API inventory and deprecated endpoint risks;
- injection/parser classes at a controlled, non-destructive validation level.

## Tool Mesh Coverage

The tool orchestration matrix maps runtime tools to bug bounty roles:

- `tool_catalog`, `local_capability_inventory`, `agent_mesh_audit`, and `integration_probe` for readiness.
- `web_fetch` and `knowledge_ingest_url` for policy and docs.
- `repo_search` and `github_repo_info` for owned-code evidence.
- `security_core_plan` for reasoning and validation planning.
- `kali_tool_inventory` and `hexstrike_lab_scan` for security lab readiness and loopback lab work.
- `n8n_workflows`, `n8n_webhook`, `zapier_action_catalog`, and `zapier_action` for approved workflow/report routing.
- `agent_delegate` for bounded reasoning/delegation with inherited scope constraints.
- `command_profile` for internal validation of this repo/runtime.

## Requirement Intake Behavior

If a request says "find all bugs" but lacks scope, FATHIYA should not scan. It should ask for:

- program policy or uploaded scope;
- target asset and asset type;
- allowed and disallowed tests;
- rate/noise limits;
- two authorized test accounts for auth/IDOR/business logic/WebSocket work;
- API docs/OpenAPI/Postman collection when relevant;
- controlled callback endpoint for SSRF when allowed;
- safe test data and redaction rules;
- report destination.

It may collect public policy/docs with `web_fetch` or `knowledge_ingest_url` only when the operator provides the source or the source is clearly a public official program page.

## Deep Understanding Target

The next runtime proof should verify that FATHIYA can:

- distinguish simple findings from complex chain hypotheses;
- decide which tools are relevant and which are blocked;
- ask for missing requirements in Arabic;
- produce a passive-only plan when scope is missing;
- use local labs and user-provided evidence without confusing them with public target approval;
- mark scanner results as leads until manually validated;
- draft reports only when evidence is complete.
