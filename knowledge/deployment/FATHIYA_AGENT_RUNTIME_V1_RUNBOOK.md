# FATHIYA Agent Runtime v1 Runbook

## Purpose

This runbook connects the authenticated FATHIYA site to the local agent worker
through Supabase. The browser never receives OpenRouter, Supabase service-role,
or local tool credentials.

The canonical TanStack server routes and the Netlify `agent-tasks` function
expose the same `/api/agent/tasks` contract. The Netlify bridge is required by
the current production deployment because it publishes `dist/client` as a
static site.

## Deployment Order

1. Apply `supabase/migrations/20260604120000_agent_runtime_v1.sql` to project
   `qywkyxcljhoitdcaskyu`.
2. Configure the site server with:
   - `SUPABASE_URL`
   - `SUPABASE_PUBLISHABLE_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`
3. Configure the browser build with:
   - `VITE_SUPABASE_URL`
   - `VITE_SUPABASE_PUBLISHABLE_KEY`
4. Configure `services/agent-runtime/.env` from `.env.example`.
   - Enable `FATHIYA_ENABLE_HF_RETRIEVAL=true` for multilingual semantic search.
   - Enable `FATHIYA_ENABLE_LOCAL_GENERATION=true` to use the downloaded
     `Qwen/Qwen2.5-0.5B-Instruct` CPU model for bounded synthesis after
     OpenRouter fails or is absent. Deterministic local planning and evaluation
     keep the worker responsive; local model planning is opt-in.
5. Set `FATHIYA_STORE=supabase` on the local worker.
6. Start the worker:

```powershell
cd services/agent-runtime
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\fathiya-runtime worker
```

For a fully local website-to-worker proof without changing production, run
`.\.venv\Scripts\fathiya-runtime serve`, start the site development server, and
open `/agent-tasks`. Development mode automatically uses the loopback-only API
at `http://127.0.0.1:8765`.

## Operator Flow

1. Open `/agent-login` and authenticate.
2. Open `/agent-tasks`.
3. Submit an internal task such as:
   `اعرض حالة المستودع وسجل إيصال التنفيذ`
4. Confirm the worker claims the task within 30 seconds.
5. Confirm progress events show every selected tool, heartbeat, model trace,
   final result, and receipt.

Sensitive tasks remain in `awaiting_approval`. This includes money, real
trading, live security testing, deletion, and external publication.

## Production Verification

- Stop the local worker and submit a safe task.
- Confirm a previously running task becomes `stalled` after two minutes.
- Restart the worker and submit a new safe task.
- Confirm OpenRouter failures route to deterministic local planning, bounded
  `huggingface_local` synthesis, and deterministic local evaluation.
- Confirm no `sk-or-v1-`, service-role value, or `VITE_OPENROUTER_*` string is
  present in `dist/client`.
- Run:

```powershell
npm run build
node netlify/tests/agent-tasks.test.mjs
cd services/agent-runtime
.\.venv\Scripts\python -m unittest discover -s tests -v
```

## Current External Blockers

- OpenRouter currently returns HTTP 402 for the configured local key.
- n8n `2.23.2` is active locally and responds on port `5678`.
- n8n API workflow listing requires `N8N_API_KEY`. The local n8n CLI currently
  fails migrations with `temporary_webhook_entity already exists`; back up and
  repair the n8n SQLite database before importing or publishing the FATHIYA
  webhook bridge.
- Production verification requires applying the Supabase migration and
  deploying this branch to `fathya-core.com`.
