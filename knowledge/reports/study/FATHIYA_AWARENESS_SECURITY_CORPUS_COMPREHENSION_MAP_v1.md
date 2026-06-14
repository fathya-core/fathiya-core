# FATHIYA Awareness/Security Corpus Comprehension Map v1

## Purpose

This map teaches FATHIYA agents how to use the imported
`awareness_knowledge_roadmap_security_2026_05_15` corpus as working knowledge,
not as memorized text. The corpus is evidence for retrieval, planning,
evaluation, lab design, defensive detection, and owned-scope preparation.

The primary operating goal remains an agentic execution system. The first
specialist is the paper-trading agent, which runs a one-second local prediction
and execution loop. Security material from this corpus protects the runtime,
tool contracts, connector design, and lab validation. Project-specific allowed
and disallowed boundaries are operator-owned and pending definition in
`knowledge/policies/FATHIYA_OPERATOR_BOUNDARY_PROFILE_PENDING_v1.json`.

## Canonical Corpus Anchors

- Manifest: `knowledge/intake/runtime/awareness_knowledge_roadmap_security_2026_05_15_manifest.json`
- Raw corpus root: `knowledge/raw/imports/awareness_knowledge_roadmap_security_2026_05_15`
- Ingest report: `knowledge/reports/study/FATHIYA_AWARENESS_SECURITY_CORPUS_INGEST_REPORT_v1.md`
- Operator bootstrap: `knowledge/runtime/FATHIYA_AGENT_COMPREHENSION_BOOTSTRAP_v1.md`
- Imported registry: `knowledge/registries/imported_corpus_registry_v1.json`

## Understanding Model

The agent must answer five questions before turning corpus knowledge into work:

1. What plane does this source affect: trading, knowledge/RAG, security lab,
   detection, tool automation, or evaluation?
2. Is the material reference-only, review-before-use, or execution-capable?
3. Is the target owned, local, simulated, testnet, or external/third-party?
4. Which tool contract, playbook, and operator boundary section apply?
5. What receipt will prove what happened, what was read, what was executed, and
   what still needs an operator boundary decision?

## Agentic AI, MCP, HexStrike, Cursor, Gemini

Relevant corpus examples include:

- `aks-023-ebb20c0481` - AI Agents: Complete Course
- `aks-024-fa11650a15` - AI Offensive Security: Practical Attacks Against LLM Agents
- `aks-036-17ee06ea20` - Burp Suite MCP + Gemini CLI
- `aks-052-a907516562` - HexStrike-AI as a red-team force multiplier
- `aks-055-8795310ba2` - HexStrike AI MCP setup patterns

FATHIYA should convert these into architecture checks: context boundaries,
prompt-injection resistance, tool-call validation, least privilege,
deterministic receipts, and reversible lab workflows. The agent may learn
orchestration patterns from the corpus, then route any tool authority question
through the operator boundary profile, Target Card, tool contract, and receipt.

## Security Lab And Owned-Scope Testing

Relevant corpus examples include:

- `aks-016-a200aff5dc` - Active Directory lab deployment
- `aks-017-65161270f6` - Active Directory penetration testing
- `aks-043-1eafb9e3b3` - HackerAI lab walkthrough
- `aks-020-82d02e1e14` and `aks-021-b6ce1a01ab` - HexStrike lab workflows

FATHIYA may use this material to build isolated labs, design checklists,
prepare benign validation plans, and map required logs. Live activity is
`boundary_pending` until the operator defines scope and authority in the
operator boundary profile.

## OSINT And Attack Surface

Relevant corpus examples include:

- `aks-053-9d248602d8` - HexStrike + Cursor for OSINT
- `aks-075-014193f6e9` - Shodan and HexStrike integration
- imported bug-bounty/recon sources under the same raw corpus root

FATHIYA can use these sources for owned-asset inventory, report templates,
privacy-preserving exposure maps, and passive research planning. External
lookups, personal-data handling, and active enumeration must be resolved through
the operator boundary profile.

## Detection Engineering And Threat Intelligence

Relevant corpus examples include:

- `aks-040-5040e233c8` - malicious insider detection engineering
- `aks-045-ba6dff6b94` - threat intelligence to detection engineering
- `aks-112-d91c2aa522` - solo SOC threat-intelligence stack

These are immediately useful for defensive detections, log-source maps,
incident-response templates, analyst workflows, test cases, and evaluation
rubrics. Defensive outputs are allowed when they stay inside owned systems,
synthetic data, or documented lab telemetry.

## Trading Agent Connection

The corpus is not a market-alpha source by default. It supports the trading
agent by improving runtime reliability:

- tool-call policy, connector hygiene, and secret handling;
- audit receipts for prediction, paper fills, and strategy updates;
- evaluation discipline so models explain decisions rather than memorize notes;
- security boundaries around broker/testnet credentials and automation.

The one-second trading loop may continue in the currently configured mode.
Testnet, broker-connected, or real-money trading boundaries are not inferred
from this corpus; they are defined later by the operator boundary profile.

## Boundary-Aware Execution Policy

Allowed automatically:

- read imported corpus files and manifest entries;
- produce learning cards, architecture notes, reports, rubrics, and lab plans;
- run read-only inventories of local tools, connectors, and owned runtime state;
- run the paper-trading loop and read paper-trading receipts.

Operator boundary pending:

- external webhooks or workflow activation;
- Kali, Burp, Nmap, Shodan, HexStrike, or similar live target use;
- credential handling, secrets, broker/testnet order placement, or any action
  that can change money, accounts, infrastructure, or third-party systems;
- deletion, persistence, destructive testing, or publication.

These are not a final boundary list. They are the areas the operator will
define later in
`knowledge/policies/FATHIYA_OPERATOR_BOUNDARY_PROFILE_PENDING_v1.json`.

## Comprehension Check

An acceptable agent answer must cite the manifest or imported raw paths,
classify at least one source from each major area, explain what is learned, and
name what boundary decision is still needed before execution. A stronger answer
also connects the corpus to FATHIYA's queue, operator boundary profile,
tool-contract, adapter, evaluation, and receipt flow.
