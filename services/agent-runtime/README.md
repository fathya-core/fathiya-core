# FATHIYA Agent Runtime v1

This service is the local execution plane for FATHIYA. The website queues work
in Supabase, and the local worker retrieves knowledge, builds a multi-tool plan,
executes the plan with prior-step context, evaluates the combined result, and
writes a receipt.

## Quick local proof

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\fathiya-runtime init
.\.venv\Scripts\fathiya-runtime enqueue "اختبار تنفيذ داخلي"
.\.venv\Scripts\fathiya-runtime worker --once
.\.venv\Scripts\fathiya-runtime list
.\.venv\Scripts\fathiya-runtime tools
```

The default SQLite store is for local verification. Set `FATHIYA_STORE=supabase`,
`SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` to connect the worker to the
production task queue.

Hugging Face retrieval is CPU-only by default and optional:

```powershell
.\.venv\Scripts\python -m pip install -e ".[huggingface]"
$env:FATHIYA_ENABLE_HF_RETRIEVAL="true"
```

Local Hugging Face generation can act as the bounded synthesis fallback when
OpenRouter is missing or unavailable:

```powershell
$env:FATHIYA_ENABLE_LOCAL_GENERATION="true"
$env:FATHIYA_LOCAL_MODEL="Qwen/Qwen2.5-0.5B-Instruct"
$env:FATHIYA_LOCAL_MAX_GENERATION_SECONDS="20"
```

The model is loaded lazily on CPU and each local generation is time bounded.
OpenRouter remains the first route for planning, synthesis, and evaluation.
When it is unavailable, the deterministic multi-tool planner selects the
actions, local Hugging Face produces a short evidence summary, and the
deterministic evaluator verifies that tool results exist. Local model planning
can be enabled explicitly with `FATHIYA_ENABLE_LOCAL_PLANNING=true`, but is off
by default on low-memory machines to keep task progress responsive.

The worker never reads a browser-exposed OpenRouter key. `OPENROUTER_API_KEY`
is read only by the local process.

Tasks involving money, real trading, live security testing, deletion, or
external publication remain in `awaiting_approval`. The worker only claims
`queued` tasks.

The planner uses OpenRouter when configured and validates every proposed step
against the runtime tool catalog. If OpenRouter is unavailable, a local
multi-tool planner routes the task by capability. A plan that selects a
sensitive tool is moved back to `awaiting_approval` before that tool runs, even
when the original request was not classified as sensitive.

The built-in catalog can fetch and ingest reports into local knowledge, search
and inspect the canonical repository, read authenticated GitHub metadata, read
n8n health/workflows, call an approved n8n webhook, inspect connected tools,
inspect Kali WSL, run the defensive security core, and execute versioned local
command profiles from `config/command_profiles.json`.

For local SQLite tasks:

```powershell
.\.venv\Scripts\fathiya-runtime approve <task-id>
.\.venv\Scripts\fathiya-runtime cancel <task-id>
```

The connected-tool registry is refreshed from the live Zapier MCP inventory and
records agent providers such as Manus, Cursor, Zapier Agents, GitHub, and
Netlify. Read-only inventory is automatic; connected-app writes remain approval
gated.
