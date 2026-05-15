# FATHIYA Retrieval Indexes v0

## Status
Built locally from `FATHIYA_AWARENESS_VAULT_v0_HUB_READY.zip`.

## Validation
Local build: PASS (see counts below).

Cursor Agent import (vault/hub-ready-v0): IMPORT_BLOCKED — `FATHIYA_RETRIEVAL_INDEXES_v0.zip` was not present in the agent workspace. See `knowledge/retrieval_validation_report.json`.

## Counts
- Search records: 243
- Domains: 23
- Sensitivities: 7
- Types: 11
- Graph neighbor nodes: 449
- Graph edges: 963

## Generated index files
- `knowledge/search_index.json`
- `knowledge/domain_index.json`
- `knowledge/sensitivity_index.json`
- `knowledge/type_index.json`
- `knowledge/graph_neighbors.json`
- `knowledge/retrieval_index_summary.json`
- `knowledge/retrieval_validation_report.json`

## Next
Cursor Agent should import `FATHIYA_RETRIEVAL_INDEXES_v0.zip`, place the JSON files under `knowledge/`, then validate paths and graph references.

No merge yet.