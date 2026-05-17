# FATHIYA Apps & GPTs Routing Map — Source Note v0

## Status

**pending_structured_parse**

## Source File

`FATHIYA_Apps_GPTs_Routing_Map_v1.xlsx`

## Ingestion Cycle

Daily Intake Cycle 001 — 2026-05-17

## Purpose

This routing map defines how FATHIYA routes tasks and queries across different apps and GPT configurations. The original source is an Excel spreadsheet that requires structured cell-by-cell extraction to produce a machine-readable JSON routing artifact.

## Current State

The xlsx file was included in the operator-provided source batch for Daily Intake Cycle 001. Raw spreadsheet cell parsing is not available in this intake cycle. The file has been registered in the source manifest with `ingestion_status: pending_structured_parse`.

## Intended Artifact

Once the spreadsheet is parsed, the structured artifact will be:

- `knowledge/routing/FATHIYA_APPS_GPTS_ROUTING_MAP_v0.json`
- Schema: array of routing entries, each with `app_name`, `gpt_config`, `task_types`, `routing_rules`, `priority`, and `notes`.

## Next Steps

1. Parse `FATHIYA_Apps_GPTs_Routing_Map_v1.xlsx` using a spreadsheet extraction tool in a future intake cycle.
2. Validate parsed data against the routing map schema.
3. Generate `FATHIYA_APPS_GPTS_ROUTING_MAP_v0.json` and link to the Command Center.
4. Update this source note status from `pending_structured_parse` to `completed`.

## Boundary

This is a source tracking note only. No data has been fabricated or inferred from the spreadsheet. The structured parse will occur when appropriate tooling is available.

## Receipt

`receipt-2026-05-17-daily-intake-cycle-001`
