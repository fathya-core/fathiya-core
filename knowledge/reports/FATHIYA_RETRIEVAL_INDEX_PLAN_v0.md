# FATHIYA CORE — Retrieval Index Plan v0

## الهدف
تحويل الـ Vault من ملفات محفوظة إلى ذاكرة قابلة للاسترجاع.

## المبدأ
Files are canonical. Indexes are rebuildable.

## v0 Retrieval
- `knowledge/index.json`
- `knowledge/graph.json`
- file paths
- card ids
- domain tags
- sensitivity labels
- batch ids

## v1 Retrieval
- local search script
- JSON validation
- markdown metadata extraction
- graph neighbor lookup
- duplicate detection

## v2 Retrieval
- Supabase/Postgres
- pgvector
- hybrid search
- recency weighting
- source confidence weighting

## Index Fields
Each searchable item should expose:
- id
- title
- type
- domain
- category
- sensitivity
- source
- path
- summary
- tags
- related_nodes
- updated_at

## First Retrieval Tasks
1. Build `knowledge/search_index.json` from all card JSON files.
2. Build `knowledge/domain_index.json` grouped by domain.
3. Build `knowledge/sensitivity_index.json` grouped by sensitivity.
4. Build `knowledge/graph_neighbors.json` for top-level lookup.
5. Validate that every indexed path exists.

## Cursor Agent Role
Cursor should generate and test local validation scripts only.
No external calls are required.

## Manus Role
Manus should use the index outputs for synthesis and research briefs.

## Next
After this plan:
- build search index
- generate cluster candidates
- promote first final playbook