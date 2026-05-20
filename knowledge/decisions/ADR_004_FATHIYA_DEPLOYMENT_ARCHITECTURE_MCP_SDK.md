# ADR-004 — FATHIYA Deployment Architecture for MCP SDK v0

**Status:** Accepted  
**Date:** 2026-05-18  
**Deciders:** FATHIYA CORE  
**Branch:** `cursor/deployment-architecture-mcp-sdk-v0`

---

## Context

MCP SDK v0 has been integrated into `main` (commit `833b4b9`). It provides:

- `GET /api/mcp` — Webhook-compatible tool manifest
- `POST /api/mcp` — Tool dispatcher (ping, knowledge, intake, crypto signal, quality gate)
- OpenRouter multi-model routing (5 slots: default, fast, reasoning, critic, structured)
- Quality Gate (no trading commands)
- Knowledge Vault tools (reads from `knowledge/`)

We now need a deployment topology that:
1. Separates concerns across subdomains
2. Supports future MCP protocol layer (JSON-RPC 2.0)
3. Keeps all secrets in deployment environment only
4. Enables Zapier webhook ingestion
5. Serves SDK docs and tool contracts publicly

---

## Decision

Adopt a **6-subdomain topology** for FATHIYA Core:

| Subdomain | Role | Current Status |
|-----------|------|----------------|
| `fathya-core.com` | Landing page / public status | Planned |
| `app.fathya-core.com` | Command Center UI (TanStack Start) | Planned |
| `api.fathya-core.com` | SDK/API Gateway (proxies `/api/mcp`) | Planned |
| `mcp.fathya-core.com` | MCP server endpoint / future protocol layer | Planned |
| `hooks.fathya-core.com` | Inbound webhook receiver (Zapier ingress) | Planned |
| `docs.fathya-core.com` | SDK docs / schemas / tool contracts | Planned |

**Single repo, single deployment** — all subdomains served from `fathya-core/fathiya-core` per ADR-001.

---

## Routing Architecture

```
Zapier Webhook
    |
hooks.fathya-core.com/inbound
    |
api.fathya-core.com/api/mcp  (POST)
    |
MCP Tool Dispatcher
    |-- knowledge/ (read)
    |-- OpenRouter (LLM calls)
    +-- Quality Gate

mcp.fathya-core.com  (future: JSON-RPC 2.0 / Streamable HTTP)
app.fathya-core.com  (Command Center UI)
docs.fathya-core.com (tool contracts, schemas, SDK guide)
```

---

## Consequences

### Positive
- Clear separation: UI / API / MCP / Webhooks / Docs
- Zapier connects to `hooks.fathya-core.com` -- stable URL
- `mcp.fathya-core.com` reserved for future full MCP protocol
- `docs.fathya-core.com` serves tool registry publicly
- All env vars in deployment secrets only

### Negative / Risks
- 6 subdomains require DNS configuration (deferred)
- `mcp.fathya-core.com` is placeholder until JSON-RPC 2.0 layer is built

### Neutral
- No Supabase -- all state in `knowledge/` files
- No live deploy in this PR -- artifacts only

---

## Env Contract

All secrets in deployment environment only. Names defined in `knowledge/deployment/env_contract_v0.json`.

Prefix convention:
- `VITE_` -- client-side (Vite `import.meta.env`)
- No prefix -- server-side only

---

## Future MCP Protocol Layer (v1)

When `mcp.fathya-core.com` is activated:

```
GET  /api/mcp          -> tool manifest + schemas
POST /api/mcp          -> JSON-RPC 2.0 dispatcher
POST /api/mcp/stream   -> Streamable HTTP (SSE)
```

Required additions:
- JSON-RPC 2.0 envelope: `{ jsonrpc, id, method, params }`
- `tools/list` and `tools/call` methods
- Auth: Bearer token / API key header
- MCP Client by Zapier native compatibility

---

## Related

- ADR-001: Monorepo consolidation
- ADR-002: Autopilot internal build
- ADR-003: Operations autopilot
- PR #26: MCP SDK v0 (applied to main `833b4b9`)
