# FATHIYA Deployment Topology v0

**Date:** 2026-05-18  
**Status:** Architecture Only -- No live deploy  
**ADR:** ADR-004  
**Branch:** `cursor/deployment-architecture-mcp-sdk-v0`

---

## Overview

FATHIYA Core runs as a single TanStack Start application deployed from `fathya-core/fathiya-core` (ADR-001). All subdomains are served from the same deployment unit. No Supabase. All state in `knowledge/` files.

---

## Domain Topology

```
+---------------------------+------------------------------------------+------------------+
| Domain                    | Role                                     | Status           |
+---------------------------+------------------------------------------+------------------+
| fathya-core.com           | Landing page / public status             | Planned          |
| app.fathya-core.com       | Command Center UI (TanStack Start)       | Planned          |
| api.fathya-core.com       | SDK/API Gateway -- /api/mcp              | Planned          |
| mcp.fathya-core.com       | MCP server / future JSON-RPC 2.0 layer   | Planned (v1)     |
| hooks.fathya-core.com     | Inbound webhook receiver (Zapier)        | Planned          |
| docs.fathya-core.com      | SDK docs / schemas / tool contracts      | Planned          |
+---------------------------+------------------------------------------+------------------+
```

---

## Request Flow

### Zapier -> MCP Tool

```
[Zapier Zap]
  POST https://hooks.fathya-core.com/inbound
  body: { tool: "intake_submit_raw", params: { content: "...", source: "zapier" } }
    |
    v
[Webhook Ingress Handler]
  -- validates source
  -- forwards to API Gateway
    |
    v
[api.fathya-core.com/api/mcp]
  POST { tool, params }
    |
    v
[MCP Tool Dispatcher]
  -- Quality Gate check
  -- routes to tool function
  -- reads from knowledge/
  -- optionally calls OpenRouter
    |
    v
[Response]
  { success, tool, data, receipt_id, quality_gate_passed }
```

### Direct API Call

```
[External Client / Zapier Webhooks by Zapier]
  POST https://api.fathya-core.com/api/mcp
  body: { tool: "ping" }
    |
    v
[MCP Tool Dispatcher]
  -> { success: true, data: { status: "alive" }, receipt_id: "MCP-PING-..." }
```

### GET Manifest

```
[Zapier / Developer]
  GET https://api.fathya-core.com/api/mcp
    |
    v
[Tool Manifest]
  {
    server: "fathiya-core-mcp",
    version: "0.1.0",
    supported_modes: { webhook_dispatcher_v0: true, mcp_protocol_full: false, ... },
    tools: [...],
    quality_gate: { enforced: true, ... },
    model_routing: { enabled: true, slots: [...] }
  }
```

---

## Subdomain Details

### fathya-core.com
- Public landing page
- System status (deployment readiness, MCP status)
- Links to docs, app, API
- No auth required

### app.fathya-core.com
- Command Center UI
- Shows: domain topology, deployment readiness, MCP status, SDK/API status, webhook ingress status, OpenRouter model slots, missing env vars, receipts
- Auth: operator only
- Reads from `knowledge/` at build time

### api.fathya-core.com
- Primary API Gateway
- Routes:
  - `GET  /api/mcp` -- tool manifest
  - `POST /api/mcp` -- tool dispatcher
  - `GET  /api/health` -- health check
- No auth in v0 (public webhook endpoint)
- Auth boundary planned for v1

### mcp.fathya-core.com
- **v0:** Placeholder -- redirects to `api.fathya-core.com/api/mcp`
- **v1:** Full MCP protocol layer
  - `GET  /` -- MCP manifest
  - `POST /` -- JSON-RPC 2.0 dispatcher
  - `POST /stream` -- Streamable HTTP (SSE)
  - Auth: Bearer token
  - MCP Client by Zapier native compatibility

### hooks.fathya-core.com
- Inbound webhook receiver
- Routes:
  - `POST /inbound` -- receives Zapier payloads
  - `GET  /health` -- health check
- Validates source, forwards to `/api/mcp`
- Returns receipt_id to Zapier
- No secrets in payload

### docs.fathya-core.com
- Static SDK documentation
- Tool contracts: `knowledge/mcp/mcp_server_contract_v0.json`
- SDK gateway contract: `knowledge/sdk/sdk_gateway_contract_v0.json`
- Webhook ingress contract: `knowledge/hooks/webhook_ingress_contract_v0.json`
- OpenRouter model routing registry
- Zapier integration guide

---

## Deployment Platform

- **Platform:** TBD (Cloudflare Workers / Vercel / Railway)
- **Build:** `npm run build` (Vite + TanStack Start)
- **Env vars:** Set in deployment platform secrets
- **No Supabase:** All state in `knowledge/` files
- **No live deploy in this PR:** Architecture artifacts only

---

## Command Center Deployment Panel (Planned)

The Command Center (`app.fathya-core.com`) will display:

```
Deployment Status
-----------------
fathya-core.com          [ planned ]
app.fathya-core.com      [ planned ]
api.fathya-core.com      [ planned ]
mcp.fathya-core.com      [ planned (v1) ]
hooks.fathya-core.com    [ planned ]
docs.fathya-core.com     [ planned ]

MCP Status
----------
webhook_dispatcher_v0    [ active ]
mcp_protocol_full        [ not yet ]
openrouter_model_routing [ active ]

OpenRouter Model Slots
----------------------
default    VITE_OPENROUTER_DEFAULT_MODEL    [ not set ]
fast       VITE_OPENROUTER_FAST_MODEL       [ not set ]
reasoning  VITE_OPENROUTER_REASONING_MODEL  [ not set ]
critic     VITE_OPENROUTER_CRITIC_MODEL     [ not set ]
structured VITE_OPENROUTER_STRUCTURED_MODEL [ not set ]

Missing Env Vars
----------------
VITE_OPENROUTER_API_KEY          [ required ]
FATHIYA_PUBLIC_APP_URL           [ required ]
...

Recent Receipts
---------------
[ last 5 receipts from receipt_ledger_v0.json ]
```

---

## Blockers Before Live Deploy

1. DNS configuration for 6 subdomains
2. Deployment platform selection
3. Env vars set in deployment secrets
4. Auth boundary for `api.fathya-core.com` (v1)
5. MCP protocol layer for `mcp.fathya-core.com` (v1)
