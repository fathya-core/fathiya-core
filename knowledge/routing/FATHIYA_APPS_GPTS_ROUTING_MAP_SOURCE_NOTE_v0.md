# FATHIYA Apps & GPTs Routing Map — Source Note v0

## Status

**structured_parse_completed**

## Source File

`FATHIYA_Apps_GPTs_Routing_Map_v1.xlsx`

## Ingestion Cycle

Daily Intake Cycle 001 — 2026-05-17

## Purpose

This routing map defines how FATHIYA routes tasks and queries across different apps and GPT configurations. The original source is an Excel spreadsheet. The workbook was locally parsed in the operator session, and the supplied structured facts are now captured as machine-readable routing artifacts.

## Current State

The xlsx file was included in the operator-provided source batch for Daily Intake Cycle 001. It was initially registered in the source manifest with `ingestion_status: pending_structured_parse`. This follow-up task completes that pending state by integrating the operator-parsed sheet metadata, summary counts, routing rules, workflow templates, and guardrails.

## Intended Artifact

The structured artifacts are:

- `knowledge/routing/apps_gpts_routing_map_v1.json`
- `knowledge/routing/apps_gpts_routing_rules_v1.json`
- `knowledge/routing/FATHIYA_APPS_GPTS_ROUTING_MAP_PARSED_REPORT_v0.md`
- `knowledge/cards/routing/kc-2026-05-17-apps-gpts-routing-v0.json`

## Parsed Spreadsheet Facts Captured

- Sheets:
  - `Architecture_Principle`: `A1:A6`
  - `Apps_Full_Mapped`: `A1:I174`
  - `GPTs_Full_Mapped`: `A1:K30`
  - `Sample_Workflows`: `A1:F4`
- Row counts:
  - Apps: 173 app rows
  - GPTs: 29 GPT rows
  - Workflows: 3 workflow rows
- Architecture principle:
  - GPT/LLM is transformation/analysis layer X.
  - Zapier/Make/n8n are orchestration Y->X->Z.
  - State and memory live outside the model.
  - Validation, logging, and guardrails are required.
- App summaries:
  - Top role group: Connector/Tool (151 of 173).
  - Trading relevance: Low / منخفضة 138, Medium / متوسطة 20, High / عالية 12, plus 3 header/blank/not-classified rows.
- GPT summaries:
  - Risk levels: منخفض 10, متوسط 9, مرتفع 4, مرتفع جدًا 4, متغير 2.
  - Decision-blocked: نعم 18, لا 9, حسب الضبط 2.

## Next Steps

1. Expand the Command Center with a dedicated routing status section when UI scope is approved.
2. If the original xlsx is committed in a future source archive, run a row-level parser to add concrete app/GPT names without changing the v1 guardrails.
3. Attach tool contracts to any app row before activating external side-effect workflows.

## Boundary

This is a source tracking note plus completion marker. The structured artifacts use only the parsed spreadsheet facts supplied by the operator; concrete row-level app and GPT names were not inferred.

## Receipt

Source intake receipt: `receipt-2026-05-17-daily-intake-cycle-001`

Structured parse receipt: `receipt-2026-05-17-post-daily-intake-validation-routing-parse-v0`
