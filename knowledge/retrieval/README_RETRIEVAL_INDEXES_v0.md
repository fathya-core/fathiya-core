# FATHIYA Retrieval Indexes v0

## Status
Built locally from `FATHIYA_AWARENESS_VAULT_v0_HUB_READY.zip`.

## Validation
PASS

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

## Import commands
### Direct ZIP import
1. Copy the archive into the canonical workspace location:
   - `cp /absolute/path/FATHIYA_RETRIEVAL_INDEXES_v0.zip knowledge/retrieval/FATHIYA_RETRIEVAL_INDEXES_v0.zip`
2. Run the importer:
   - `python3 knowledge/retrieval/fathiya_retrieval.py import`

You can also point at a different ZIP path directly:
- `python3 knowledge/retrieval/fathiya_retrieval.py import --source zip --zip /absolute/path/FATHIYA_RETRIEVAL_INDEXES_v0.zip`

### Chunked base64 import
1. Place the chunk manifest and all `chunk_*.b64` files under:
   - `knowledge/retrieval/artifacts/FATHIYA_RETRIEVAL_INDEXES_v0/`
2. Run the chunked importer:
   - `python3 knowledge/retrieval/fathiya_retrieval.py import --source chunks`

The chunked flow reconstructs `knowledge/retrieval/FATHIYA_RETRIEVAL_INDEXES_v0.zip`, verifies the manifest `sha256`, extracts the retrieval JSON files into `knowledge/`, and rewrites the summary/report after validation.

### Validation only
- `python3 knowledge/retrieval/fathiya_retrieval.py validate`

If neither the direct ZIP nor the chunked artifacts are present, the importer writes `knowledge/retrieval_validation_report.json` with `IMPORT_BLOCKED` plus the exact next steps to unblock the import.

No merge yet.