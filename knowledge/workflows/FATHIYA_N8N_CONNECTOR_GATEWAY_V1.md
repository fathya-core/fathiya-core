# FATHIYA n8n Connector Gateway v1

## Artifact

`artifacts/workflows/n8n/fathiya-connector-gateway-v1.json` is an importable,
inactive n8n workflow for brokering approved connector requests.

## Behavior

1. Accepts `POST /webhook/fathiya-agent-bridge-v1` from loopback only.
2. Requires `task_id` and an allowlisted connector profile.
3. Treats every request as staged unless `approval_state` is exactly
   `approved`.
4. Sends approved requests only to `FATHIYA_CONNECTOR_DISPATCH_URL`, with the
   token read from `FATHIYA_CONNECTOR_DISPATCH_TOKEN`.
5. Returns a staged receipt for rejected or awaiting-approval requests.

The workflow is committed with `active: false`. Importing does not activate it.
Do not activate it until the dispatch URL, token, rollback procedure, and
operator approval have been reviewed.

## Validation

Run the structural checks without touching the current n8n database:

```powershell
cd services/agent-runtime
.\.venv\Scripts\python -m unittest tests.test_n8n_connector_workflow -v
```

To validate that n8n accepts the export format, import it into a disposable n8n
user folder. This creates a separate temporary SQLite database and does not
touch `%USERPROFILE%\.n8n`:

```powershell
$env:N8N_USER_FOLDER="$env:TEMP\fathiya-n8n-import-check"
n8n.cmd import:workflow --input="artifacts/workflows/n8n/fathiya-connector-gateway-v1.json"
Remove-Item Env:N8N_USER_FOLDER
```
