# FATHIYA Knowledge To Agent Runtime Map v1

## Purpose

This file connects the imported awareness/security corpus to FATHIYA runtime
behavior. It is a retrieval anchor for agents that need to decide what to do
with knowledge files before executing tools.

The important rule is simple: knowledge informs action, but the operator
boundary profile authorizes action once the operator defines it.

## Active Knowledge Artifacts

- Corpus manifest:
  `knowledge/intake/runtime/awareness_knowledge_roadmap_security_2026_05_15_manifest.json`
- Imported corpus registry:
  `knowledge/registries/imported_corpus_registry_v1.json`
- Comprehension map:
  `knowledge/reports/study/FATHIYA_AWARENESS_SECURITY_CORPUS_COMPREHENSION_MAP_v1.md`
- Agent learning cards:
  `knowledge/learning/FATHIYA_AWARENESS_SECURITY_AGENT_LEARNING_CARDS_v1.json`
- Comprehension evals:
  `knowledge/evaluations/FATHIYA_AWARENESS_SECURITY_COMPREHENSION_EVALS_v1.json`
- Pending operator boundary profile:
  `knowledge/policies/FATHIYA_OPERATOR_BOUNDARY_PROFILE_PENDING_v1.json`

## Runtime Routing

When a task mentions the imported knowledge files, awareness/security corpus,
agent learning, trading-agent policy, MCP tools, OSINT, detection engineering,
or security lab work, the runtime should retrieve the learning cards and evals
before choosing a tool.

The expected flow is:

```text
operator request
-> retrieve manifest / cards / evals
-> classify plane and risk
-> select playbook and tool contract
-> check operator boundary profile
-> execute only actions already covered by the current boundary
-> mark undefined sensitive actions as boundary_pending
-> write receipt with sources, allowed work, boundary-pending work, and evaluation
```

## Agent Priorities

1. The primary trading agent keeps running in its currently configured mode.
   Knowledge files improve policy, model critique, receipts, and secret hygiene;
   the operator boundary profile defines which trading modes and model authority
   levels are allowed later.
2. The security lab starts with target cards, owned-scope checks, lab design,
   telemetry mapping, and defensive detections. Live probing is treated as
   boundary_pending until scope and the operator boundary profile define it.
3. MCP, Zapier, n8n, and connector material becomes tool-governance knowledge.
   Connected tools do not imply permission by themselves; the operator boundary
   profile defines automation authority.
4. Comprehension is tested through transfer scenarios. The agent must explain
   what it can do, what still needs a boundary decision, and what evidence proves
   the boundary.

## Current Automatic Outputs

- learning cards;
- scenario evals;
- detection and telemetry checklists;
- owned-scope target-card drafts;
- architecture notes;
- read-only local inventory;
- currently configured trading status and strategy-advisory refresh;
- receipts that cite source paths.

## Operator Boundary Pending Outputs

The operator will define these later in
`knowledge/policies/FATHIYA_OPERATOR_BOUNDARY_PROFILE_PENDING_v1.json`.

Until that profile is completed, agents should mark sensitive or state-changing
actions as `boundary_pending` instead of inventing project-specific boundary
lists.

## Completion Standard

A knowledge task is complete only when the result includes:

- source paths or source IDs;
- the relevant learning card or eval;
- allowed action;
- boundary decision needed;
- risk or boundary reason;
- receipt or evidence path.
