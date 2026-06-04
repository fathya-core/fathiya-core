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

For the usable local website flow, start the loopback-only API and persistent
worker together:

```powershell
.\.venv\Scripts\fathiya-runtime serve
```

`/agent-tasks` automatically connects to `http://127.0.0.1:8765` in development
and production so the hosted operator site can use the engine running on the
operator's own machine. The local API accepts browser requests only from
loopback origins or exact origins listed in `FATHIYA_OPERATOR_ORIGINS`; unrelated
remote web origins are rejected.

The default SQLite store is for local verification. Set `FATHIYA_STORE=supabase`,
`SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY` to connect the worker to the
production task queue.

### Multi-round agent loop

Each task runs as an agent loop instead of a one-shot plan. After every
execution round, OpenRouter or the enabled local Hugging Face planning model
reviews the observed tool results and either closes the task with a reason or
selects a new, non-duplicate set of registered tools. If model review is
unavailable or invalid, a deterministic local reviewer continues useful
configured read-only checks.

`FATHIYA_MAX_AGENT_ROUNDS` bounds one task's review/execution loop while
`FATHIYA_MAX_TOOL_STEPS` bounds each round. A later round that selects an
approval-gated tool stores an execution checkpoint. After approval, the worker
resumes that round without repeating completed actions. Receipts record the
round count and termination reason.

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

`GET /api/agent/integrations` returns a secret-safe readiness view for local
models, OpenRouter, Supabase, n8n, Zapier MCP, and the future broker Testnet
account. It reports only status, missing environment variable names, connected
OAuth app names, and the next safe operator action. It never returns passwords,
API-key values, webhook URLs, or broker credentials.

Tasks involving money, real trading, live security testing, deletion, or
external publication remain in `awaiting_approval`. The worker only claims
`queued` tasks.

The planner uses OpenRouter when configured and validates every proposed step
against the runtime tool catalog. If OpenRouter is unavailable, a local
multi-tool planner routes the task by capability. A plan that selects a
sensitive tool is moved back to `awaiting_approval` before that tool runs, even
when the original request was not classified as sensitive.

The task composer also supports a `FATHIYA_KNOWLEDGE_MISSION_V1` envelope for
report-to-execution work. The worker persists the report into local knowledge
before retrieval and planning, pins that exact source into the evidence set,
then lets the report guide safe read-only inspections. Report content is always
treated as untrusted evidence: it cannot originate trading, deletion, external
writes, command profiles, or other non-read-only actions. Those actions must be
explicitly requested by the operator and still pass the normal approval gate.
The final receipt records the source path and SHA-256 without copying the raw
report into the receipt.

The built-in catalog can fetch and ingest reports into local knowledge, search
and inspect the canonical repository, read authenticated GitHub metadata, read
n8n health/workflows, call an approved n8n webhook, inspect connected tools,
inspect Kali WSL, run the defensive security core, and execute versioned local
command profiles from `config/command_profiles.json`.

Version-controlled connector profiles in `config/connector_profiles.json`
provide a single execution contract for n8n, Zapier, Cursor, Manus, and future
agent providers. Read-only configured profiles run automatically. External
write profiles are selected by the planner but pause in `awaiting_approval`
before the HTTP request is sent. URLs and authentication headers are resolved
from local environment variables and are never returned by the connector
catalog or written into receipts.

The inactive, importable n8n gateway is stored at
`artifacts/workflows/n8n/fathiya-connector-gateway-v1.json`. It accepts local
requests, validates the connector allowlist, and reaches its dispatch node only
when `approval_state` is exactly `approved`.

Initialize the authenticated local dispatch endpoint without printing its
token:

```powershell
.\.venv\Scripts\fathiya-runtime bridge-init
```

The token is stored in ignored local runtime data. The dispatch endpoint
re-validates the task and approval state, rejects the n8n ingress profile to
prevent loops, executes only explicitly bridge-enabled connector profiles, and
writes a bounded receipt.

For local SQLite tasks:

```powershell
.\.venv\Scripts\fathiya-runtime approve <task-id>
.\.venv\Scripts\fathiya-runtime cancel <task-id>
```

The connected-tool registry is refreshed from the live Zapier MCP inventory and
records agent providers such as Manus, Cursor, Zapier Agents, GitHub, and
Netlify. Read-only inventory is automatic; connected-app writes remain approval
gated.

### Direct Zapier MCP gateway

The local control plane connects directly to Zapier MCP through OAuth without
asking the operator to paste a password or token into chat. Open
`/agent-tasks`, then use `ربط Zapier MCP محليًا` in the integrations panel.
OAuth credentials are stored only under the ignored local runtime directory.

After connection, the runtime resolves the exact enabled app and action,
forwards Zapier's internal `selected_api` identifier itself, and executes through
the registered `zapier_action` tool. Read actions run automatically. Zapier
write actions remain approval-gated and generate normal task receipts.

Deterministic requests can use this explicit form:

```text
Zapier action: GitHub / Find Repository
params: {"repo":"fathiya-core","owner":"fathiya-core"}
```

Inspect the local connection without exposing credentials:

```powershell
.\.venv\Scripts\fathiya-runtime zapier-status
.\.venv\Scripts\fathiya-runtime zapier-actions --refresh
.\.venv\Scripts\fathiya-runtime zapier-actions --app GitHub
```

## Primary trading agent

The first executable specialist agent is a local paper-trading loop. Its market
observation, prediction, risk check, optional paper fill, portfolio snapshot,
latency, and receipt are recorded every cycle. The default target is one cycle
per second:

```powershell
.\.venv\Scripts\fathiya-runtime trading-status
.\.venv\Scripts\fathiya-runtime trading-tick
.\.venv\Scripts\fathiya-runtime trading-proof --cycles 5
```

The local control plane also exposes:

- `GET /api/agent/trading/status`
- `GET /api/agent/trading/receipts`
- `POST /api/agent/trading/start`
- `POST /api/agent/trading/stop`
- `POST /api/agent/trading/tick`

The primary trading agent is also registered in the general execution catalog,
so the same task queue, planner, progress log, evaluator, and receipt flow can
control it. Example local website requests:

- `اعرض حالة وكيل التداول وجودة التنبؤ`
- `شغّل وكيل التداول الورقي`
- `أوقف وكيل التداول الورقي`
- `نفّذ نبضة واحدة لوكيل التداول`
- `حدّث مستشار استراتيجية وكيل التداول`

The local control plane shares one trading-agent instance between the direct
trading API and the task worker. A task-started loop therefore appears
immediately in the website trading card and can be stopped through either
surface. Explicit status, start, stop, and single-tick requests use a
deterministic fast-control path: they bypass knowledge retrieval and model
generation, while broader trading research requests continue through the full
knowledge and model pipeline.

`trading_strategy_refresh` runs outside the one-second loop and asks OpenRouter
first, then local Hugging Face, for a short-lived structured advisory. The
advisory uses a deterministic `veto_only` policy: it may confirm an existing
paper signal or downgrade a conflicting paper signal to `hold`, but it cannot
originate an order, bypass risk checks, or enable live execution. Invalid or
unavailable model output becomes a zero-confidence deterministic fallback with
no trading effect.

This version is deliberately paper-only and long-only. By default it observes
the public Coinbase spot price for `BTC-USD` once per second, records the
outcome of each eligible one-second prediction, and exposes measured
directional accuracy and theoretical strategy return. If the public provider
fails, a clearly labeled fallback tick keeps the loop observable while the risk
engine blocks paper fills and prediction scoring for that tick. Set
`FATHIYA_TRADING_MARKET_PROVIDER=synthetic_second_market` for deterministic
offline tests.

Live orders are not implemented, and setting `FATHIYA_TRADING_MODE` to anything
other than `paper` blocks the loop. A future live connector must use a
trade-only account without withdrawal permission and an explicit financial
approval policy. Broker and engine state are isolated per symbol. The paper
ledger keeps the newest
`FATHIYA_TRADING_MAX_RECEIPTS` cycles and prunes older cycles in bounded
batches.
