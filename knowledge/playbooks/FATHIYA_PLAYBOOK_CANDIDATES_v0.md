# FATHIYA CORE — Playbook Candidates v0

## Status
Draft candidates only. Not final operating playbooks.

## Rule
A candidate becomes a playbook only after context, output artifact, stop conditions, hub routing, and approval requirements are defined.

## Candidate 01 — Corpus Intake and Knowledge Conversion
Purpose: turn new inputs into structured knowledge.
Inputs: articles, notes, PDFs, markdown, extracted text, tool notes.
Outputs: raw archive, cleaned item, triage entry, knowledge card, graph relation updates.
Mode: Knowledge Mode.
Stop conditions: missing source, incomplete text, duplicate item, human review required.

## Candidate 02 — Target Preparation
Purpose: turn a program or project scope into a target card and preparation artifacts.
Inputs: program name, policy URL, allowed scope, forbidden scope, notes.
Outputs: target card, scope map, hypothesis list, report draft template.
Mode: Target-Specific Mode.
Required: policy URL and clear scope.

## Candidate 03 — Local Lab Card Builder
Purpose: convert technical detail records into local lab-only planning cards.
Inputs: detail holding record, tool card, local lab context.
Outputs: lab card, experiment plan, observation template.
Mode: Lab Mode.
Stop conditions: no local lab context or unclear ownership.

## Candidate 04 — Crypto Daily Radar
Purpose: convert market news into radar artifacts.
Inputs: crypto news, market notes, asset notes, macro signals.
Outputs: signal card, narrative card, risk card, watchlist draft.
Mode: Crypto Radar Mode.
Stop conditions: no source, unclear impact, direct trading command language.

## Candidate 05 — Tool Capability Mapping
Purpose: update the memory of tools and adapters.
Inputs: tool docs, MCP action list, Cursor result, Manus result, Zapier capability list.
Outputs: tool card, adapter card, routing rule, failure mode card.
Mode: Knowledge and Automation Mode.
Stop conditions: unknown permission, untested action, external change without approval.

## Candidate 06 — GitHub Vault Checkpoint
Purpose: save vault state through a branch and pull request.
Inputs: vault archive, manifest, branch name, commit notes.
Outputs: branch, commit, pull request, import manifest.
Mode: External Execution Mode.
Required: explicit command, separate branch, no automatic merge.

## Next
Pick one candidate, write final playbook steps, connect to Hub Queue, then assign adapter.