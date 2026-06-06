# FATHIYA Agent Runtime v1 Runbook

## Purpose

This runbook connects the hosted FATHIYA operator site directly to the
loopback-only agent runtime running on the operator's machine. The browser never
receives OpenRouter, Supabase service-role, Zapier OAuth tokens, or local tool
credentials.

The canonical TanStack server routes and the Netlify `agent-tasks` function keep
the same `/api/agent/tasks` contract for an optional remote queue, but the
operator site now defaults to the local execution plane.

## Deployment Order

1. Configure `services/agent-runtime/.env` from `.env.example`.
   - Set `FATHIYA_OPERATOR_ORIGINS` to the exact hosted operator-site origins.
   - Enable `FATHIYA_ENABLE_HF_RETRIEVAL=true` for multilingual semantic search.
   - Enable `FATHIYA_ENABLE_LOCAL_GENERATION=true` to use the downloaded
     `Qwen/Qwen2.5-0.5B-Instruct` CPU model for bounded synthesis after
     OpenRouter fails or is absent. Deterministic local planning and evaluation
     keep the worker responsive; local model planning is opt-in.
   - Keep `FATHIYA_ENABLE_LOCAL_PLANNING=false` on CPU-only operators unless a
     latency check proves the local model can review the compact tool catalog
     promptly. OpenRouter or the deterministic reviewer keeps the loop moving
     when local planning is disabled. Set `FATHIYA_MAX_AGENT_ROUNDS` to bound the loop;
     invalid model plans fall back to the deterministic local reviewer.
   - Configure only the connector bridges that should be executable:
     `FATHIYA_N8N_WEBHOOK_URL`, `FATHIYA_ZAPIER_WEBHOOK_URL`,
     `FATHIYA_CURSOR_AGENT_URL`, and `FATHIYA_MANUS_AGENT_URL`.
     Their values stay in the local process; the website sees readiness only.
2. Start the local control plane and worker:

```powershell
cd services/agent-runtime
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\fathiya-runtime serve
```

3. Deploy the site. An optional remote queue can still use the Supabase
   migration and `FATHIYA_STORE=supabase`, but it is not required for the
   hosted site to control the local engine.

Run `.\.venv\Scripts\fathiya-runtime serve`, then open `/agent-tasks` from either
the development site or `https://fathya-core.com`. Both default to the
loopback-only API at `http://127.0.0.1:8765`. Confirm
`FATHIYA_OPERATOR_ORIGINS` contains the exact production origins; unrelated
browser origins must receive HTTP 403 from the local control plane.

The same command starts the continuous knowledge-intake watcher. Place a report
in `services/agent-runtime/runtime/knowledge-inbox`, or a structured operator
mission in a `*.mission.json` file, and verify that it appears in the task queue
within the configured watch interval and completes with a receipt.

## Operator Flow

1. Open `/agent-login` and authenticate.
2. Open `/agent-tasks`.
3. Submit an internal task such as:
   `اعرض حالة المستودع وسجل إيصال التنفيذ`
4. Use `تقرير إلى تنفيذ` to submit a named report plus an operator objective.
   Confirm `استيعاب التقرير` appears before retrieval and planning, and confirm
   the final receipt includes the persisted source path and SHA-256.
5. Confirm the worker claims the task within 30 seconds.
6. Confirm progress events show every selected tool, heartbeat, model trace,
   final result, and receipt.
7. Confirm the local connector panel shows `n8n_health` ready and external
   connector profiles as requiring setup or approval as appropriate.
8. In the integrations panel, select `ربط Zapier MCP محليًا`, complete OAuth,
   then confirm `fathiya-runtime zapier-actions --refresh` returns the live app
   and action counts without printing credentials.
9. From the loopback `/agent-tasks` page, open the local setup action for
   OpenRouter, Supabase, n8n, execution-mesh bridge URLs, or Binance Spot
   Testnet. Confirm saved values are never returned by `GET /api/agent/settings`,
   and confirm a production-origin page cannot write local settings.
10. Use the integration probe button for OpenRouter, Supabase, n8n, Zapier MCP,
    and Binance Spot Testnet. Confirm each result is secret-safe, and confirm
    OpenRouter probes do not spend model tokens while Testnet probes do not
    contact the broker until local Testnet credentials exist.
11. Use `تشغيل وكيل` from an integration card, then confirm a normal task is
    queued, `integration_probe` runs through the worker, and the result appears
    in the progress log and receipts panel.
12. Use `تشغيل شبكة الوكلاء` from `/agent-tasks`. Confirm the queued task runs
    `agent_mesh_audit`, reports tool, capability, connector, Zapier, n8n, Kali,
    model, and paper-trading readiness in one receipt-safe result, and lists the
    next executable prompts.
13. From the completed mesh-audit result, use one `next_actions` item. Confirm
    setup actions open the matching local settings sheet, OAuth actions open the
    local authorization route, and task actions queue a normal task that is
    selected, executed through the worker, and recorded with its own receipt.
14. Submit a read-only exact action such as:
   `Zapier action: GitHub / Find Repository`
   with repository parameters. Confirm it completes automatically and the
   receipt contains the friendly app/action names but no `selected_api`.
15. Submit a Zapier write action and confirm it remains in
    `awaiting_approval` until the operator approves it.
16. Submit `اعرض الموصلات ونفّذ الفحوصات الجاهزة`, then confirm the task shows
    at least two agent rounds: the first discovers connector readiness and the
    second runs the newly discovered configured read-only check.
17. Confirm a sensitive follow-up stores an execution checkpoint and resumes
    after approval without replaying completed rounds.
18. Submit a broad local-tool task and confirm `local_capability_inventory`
    reports live readiness for the local execution mesh.
19. Submit an `agent_delegate` request and confirm it stops at
    `awaiting_approval` before invoking Claude Code, Cursor, or Manus.
20. In Kali WSL, run `cursor-agent status`. The runtime treats an installed but
    unauthenticated Cursor Agent as partial, never ready. Complete
    `cursor-agent login` only as the operator, then submit an `auto` delegation
    and confirm the runtime prefers an authenticated local agent.
21. Submit `افحص جاهزية حساب التداول التجريبي`. Confirm Binance Spot Testnet
    public reachability is reported without credentials. After adding Testnet
    keys locally, validate an order through `/api/v3/order/test` before enabling
    `FATHIYA_TRADING_TESTNET_EXECUTION_ENABLED`.
22. Restart the local control plane and confirm the primary paper-trading agent
    resumes automatically when `FATHIYA_TRADING_AUTOSTART=true`. Confirm the
    website trading card shows the latest cycle receipts with action, price,
    latency, risk reason, and receipt id.
23. Place a new report in the continuous knowledge inbox. Confirm the watcher
    queues it once, the worker persists it before planning, and an unchanged
    report is not duplicated after restart.

Sensitive tasks remain in `awaiting_approval`. This includes money, real
trading, live security testing, deletion, and external publication.

## Production Verification

- Stop the local worker and submit a safe task.
- Confirm a previously running task becomes `stalled` after two minutes.
- Restart the worker and submit a new safe task.
- Confirm OpenRouter failures route to deterministic local planning, bounded
  `huggingface_local` synthesis, and deterministic local evaluation.
- Confirm local capability probes never return auth output, access tokens,
  command paths, or secret environment values.
- Confirm the trading Testnet gateway rejects non-Testnet hosts and that order
  submission remains approval-gated and disabled by default.
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

- OpenRouter is not configured in the local worker; Hugging Face and
  deterministic fallbacks remain active.
- Cursor Agent CLI `2026.06.04-5fd875e` is installed in Kali WSL but awaits
  operator browser authentication.
- Binance Spot Testnet support is implemented, but local Testnet API keys are
  not configured and Testnet order submission remains disabled.
- Zapier's Codex-exposed generic executor currently omits the required
  `selected_api` argument. The local direct OAuth gateway resolves and forwards
  it itself once the operator completes the local Zapier OAuth connection.
- n8n `2.23.2` is active locally and responds on port `5678`.
- n8n API workflow listing requires `N8N_API_KEY`. The local n8n CLI currently
  fails migrations with `temporary_webhook_entity already exists`; back up and
  repair the n8n SQLite database before importing or publishing the FATHIYA
  webhook bridge.
- Production verification requires applying the Supabase migration and
  deploying this branch to `fathya-core.com`.
