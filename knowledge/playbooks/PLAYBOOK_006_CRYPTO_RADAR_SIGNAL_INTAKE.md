# PLAYBOOK 006 — Crypto Radar & Signal Intake

## Status
Final v0.

## Purpose
Convert crypto news, market notes, protocol updates, narratives, and asset observations into structured radar artifacts without turning them into direct financial commands.

## Core rule
FATHIYA can create radar, signals, narratives, watchlists, risk notes, and paper-simulation artifacts. It does not output direct buy/sell/enter/exit instructions as an automated command.

## Trigger
Use this playbook when input involves crypto news, asset narrative, protocol update, token unlock, exchange listing, on-chain signal, macro event, market regime note, DeFi/RWA/stablecoin/L2 narrative, portfolio observation, or paper trading idea.

## Outputs
- Signal Card
- Narrative Card
- Risk Card
- Watchlist Draft
- Market Regime Note
- Catalyst Timeline
- Invalidation Note
- Paper Simulation Plan
- Queue Entry
- Receipt

## Signal Card fields
- signal_id
- title
- asset_or_sector
- source
- timeframe
- narrative
- catalyst
- observed_data
- risk_factors
- invalidation_conditions
- confidence
- actionability
- status

## Mode selection
- education/research: Knowledge Mode
- news monitoring: Crypto Radar Mode
- watchlist building: Crypto Radar Mode
- paper simulation: Paper Simulation Mode
- real execution: Approval Queue and separate execution policy required

## Procedure
1. Preserve source: save source, timestamp, URL, and extraction quality before interpretation.
2. Classify market object: asset, sector, protocol, macro factor, narrative, catalyst, risk event, liquidity event, or technical regime note.
3. Extract signal components: what changed, why it matters, affected assets/sectors, timeframe, evidence, uncertainty, risk, and invalidation.
4. Create artifact: Signal Card, Narrative Card, Risk Card, Watchlist Draft, or Paper Simulation Plan.
5. Route through Runtime Queue: Knowledge Queue, Research Queue, Model Queue, or Approval Queue.
6. Apply PLAYBOOK_004_TOOL_CONTRACT_RESOLVER before using external APIs, webhooks, exchange tools, portfolio tools, or automation.
7. Write receipt for signal card creation, narrative update, risk note, watchlist update, paper simulation note, or blocked execution request.

## Stop conditions
Stop and mark blocked or needs_review if source is missing, market object is unclear, signal has no catalyst or timeframe, risk/invalidation is missing, request becomes direct financial execution, external execution lacks policy and approval, or data is stale/contradictory.

## Watchlist Draft fields
- watchlist_id
- name
- assets
- sectors
- reason
- catalysts
- monitoring_window
- risk_notes
- source_cards
- status

## Paper Simulation fields
- simulation_id
- thesis
- asset_or_sector
- entry_condition_hypothesis
- invalidation_condition
- observation_window
- metrics_to_track
- expected_learning
- status

## Success definition
This playbook succeeds when source is preserved, signal/narrative/risk is classified, artifact is created or blocker is recorded, risk and invalidation are captured, queue route is selected, and receipt is written or planned.

## Required files
- knowledge/playbooks/PLAYBOOK_004_TOOL_CONTRACT_RESOLVER.md
- knowledge/runtime/runtime_queue_v0.json
- knowledge/runtime/receipt_ledger_v0.json
- knowledge/registries/tool_contract_registry_v0.json

## Next playbook
PLAYBOOK 007 — Daily Intake Automation