# FATHIYA Deployment Architecture MCP SDK Bootstrap Report v0

**Report ID:** rt-2026-05-20-deployment-architecture-mcp-sdk-v0  
**Receipt ID:** receipt-2026-05-20-deployment-architecture-mcp-sdk-v0  
**Timestamp:** 2026-05-20T09:00:00Z  
**Branch:** `cursor/deployment-architecture-mcp-sdk-v0`  
**Base commit:** `833b4b9b79b868927d162dc99f9614b70966d267` (main after MCP SDK v0)

---

## Scope

Architecture artifacts only. No live deploy. No DNS. No secrets. No Supabase. No live webhooks.

---

## Artifacts Created

| File | Type | Status |
|------|------|--------|
| `knowledge/decisions/ADR_004_FATHIYA_DEPLOYMENT_ARCHITECTURE_MCP_SDK.md` | ADR | created |
| `knowledge/deployment/FATHIYA_DEPLOYMENT_TOPOLOGY_v0.md` | Topology doc | created |
| `knowledge/deployment/domain_routing_plan_v0.json` | JSON | created |
| `knowledge/deployment/env_contract_v0.json` | JSON | created |
| `knowledge/mcp/mcp_server_contract_v0.json` | JSON | created |
| `knowledge/sdk/sdk_gateway_contract_v0.json` | JSON | created |
| `knowledge/hooks/webhook_ingress_contract_v0.json` | JSON | created |
| `knowledge/audit/FATHIYA_DEPLOYMENT_MCP_SDK_BOOTSTRAP_REPORT_v0.md` | Audit | this file |
| `knowledge/runtime/runtime_queue_v0.json` | Runtime queue | appended |
| `knowledge/runtime/receipt_ledger_v0.json` | Receipt ledger | appended |
| `knowledge/runtime/receipts/receipt-2026-05-20-deployment-architecture-mcp-sdk-v0.json` | Receipt | created |

---

## Domain Topology Summary

| Domain | Role | Status |
|--------|------|--------|
| `fathya-core.com` | Landing / public status | planned |
| `app.fathya-core.com` | Command Center UI | planned |
| `api.fathya-core.com` | SDK/API Gateway | planned |
| `mcp.fathya-core.com` | MCP server / future JSON-RPC 2.0 | planned (v1) |
| `hooks.fathya-core.com` | Webhook ingress (Zapier) | planned |
| `docs.fathya-core.com` | SDK docs / contracts | planned |

---

## Env Contract Summary

| Var | Scope | Required | Secret |
|-----|-------|----------|--------|
| `VITE_OPENROUTER_API_KEY` | client | yes | yes |
| `VITE_OPENROUTER_BASE_URL` | client | no | no |
| `VITE_OPENROUTER_DEFAULT_MODEL` | client | no | no |
| `VITE_OPENROUTER_FAST_MODEL` | client | no | no |
| `VITE_OPENROUTER_REASONING_MODEL` | client | no | no |
| `VITE_OPENROUTER_CRITIC_MODEL` | client | no | no |
| `VITE_OPENROUTER_STRUCTURED_MODEL` | client | no | no |
| `FATHIYA_PUBLIC_APP_URL` | server | yes | no |
| `FATHIYA_PUBLIC_API_URL` | server | yes | no |
| `FATHIYA_PUBLIC_MCP_URL` | server | yes | no |
| `FATHIYA_PUBLIC_HOOKS_URL` | server | yes | no |
| `FATHIYA_PUBLIC_DOCS_URL` | server | yes | no |

**Rule enforced:** Names only. No values in any artifact.

---

## JSON Validation

| File | Valid JSON |
|------|----------|
| `domain_routing_plan_v0.json` | pass |
| `env_contract_v0.json` | pass |
| `mcp_server_contract_v0.json` | pass |
| `sdk_gateway_contract_v0.json` | pass |
| `webhook_ingress_contract_v0.json` | pass |

---

## Build & Lint

No source code changes in this PR. All artifacts are `knowledge/` files only.

- `npm run build` -- not required (no src changes)
- `eslint` -- not required (no src changes)
- JSON parse -- pass (all 5 JSON files validated)

---

## Boundaries Enforced

| Rule | Status |
|------|--------|
| No live DNS | enforced |
| No live webhooks | enforced |
| No secrets in artifacts | enforced |
| No Supabase | enforced |
| No live deploy | enforced |
| Env var names only | enforced |

---

## Command Center Next Steps

After this PR merges, Cursor should add a **Deployment Panel** to the Command Center (`src/lib/command-center.ts`) that reads from:

- `knowledge/deployment/domain_routing_plan_v0.json` -- domain topology
- `knowledge/deployment/env_contract_v0.json` -- env var status
- `knowledge/mcp/mcp_server_contract_v0.json` -- MCP status
- `knowledge/sdk/sdk_gateway_contract_v0.json` -- SDK/API status
- `knowledge/hooks/webhook_ingress_contract_v0.json` -- webhook ingress status

And displays:
- Domain topology table
- Deployment readiness per domain
- MCP supported_modes
- OpenRouter model slots + env var status
- Missing required env vars
- Recent receipts

---

## Blockers Before Live Deploy

1. DNS configuration for 6 subdomains
2. Deployment platform selection (Cloudflare Workers / Vercel / Railway)
3. Env vars set in deployment platform secrets
4. Auth boundary for `api.fathya-core.com` (v1)
5. MCP protocol layer for `mcp.fathya-core.com` (v1)
6. Command Center Deployment Panel implementation

---

## Next Recommended Task

Merge this PR into `main`, then implement the Command Center Deployment Panel in a follow-up Cursor task.
