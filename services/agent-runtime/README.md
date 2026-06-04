# FATHIYA Agent Runtime v1

This service is the local execution plane for FATHIYA. The website queues work
in Supabase, and the local worker claims allowed tasks, records progress,
executes allowlisted tools, evaluates the result, and writes a receipt.

## Quick local proof

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\fathiya-runtime init
.\.venv\Scripts\fathiya-runtime enqueue "اختبار تنفيذ داخلي"
.\.venv\Scripts\fathiya-runtime worker --once
.\.venv\Scripts\fathiya-runtime list
```

The default SQLite store is for local verification. Set `FATHIYA_STORE=supabase`,
`SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` to connect the worker to the
production task queue.

Hugging Face retrieval is CPU-only by default and optional:

```powershell
.\.venv\Scripts\python -m pip install -e ".[huggingface]"
$env:FATHIYA_ENABLE_HF_RETRIEVAL="true"
```

The worker never reads a browser-exposed OpenRouter key. `OPENROUTER_API_KEY`
is read only by the local process.

Tasks involving money, real trading, live security testing, deletion, or
external publication remain in `awaiting_approval`. The worker only claims
`queued` tasks.

The connected-tool registry is refreshed from the live Zapier MCP inventory and
records agent providers such as Manus, Cursor, Zapier Agents, GitHub, and
Netlify. Read-only inventory is automatic; connected-app writes remain approval
gated.
