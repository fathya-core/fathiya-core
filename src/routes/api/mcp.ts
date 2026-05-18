// FATHIYA CORE — MCP API Route v0
// /api/mcp في v0 هو: Webhook-compatible tool endpoint
// وليس MCP protocol كامل — انظر supported_modes في GET response

import { createFileRoute } from "@tanstack/react-router";
import {
  tool_ping,
  tool_knowledge_get_awareness_state,
  tool_knowledge_search,
  tool_knowledge_list_cards,
  tool_intake_submit_raw,
  tool_crypto_create_signal_card,
  tool_queue_get_pending,
  tool_quality_gate_check,
  TOOL_REGISTRY,
  type MCPRequest,
} from "@/lib/mcp/tools";

import awarenessStateRaw from "../../../knowledge/FATHIYA_AWARENESS_STATE.json";
import retrievalIndexRaw from "../../../knowledge/retrieval_index_summary.json";

// ─── Tool Schemas (for manifest) ──────────────────────────────────────────────────────
const TOOL_SCHEMAS: Record<string, Record<string, unknown>> = {
  ping: {},
  knowledge_get_awareness_state: {},
  knowledge_search: {
    query: { type: "string", required: true },
    category: { type: "string", required: false },
    type: { type: "string", required: false },
    limit: { type: "number", required: false, default: 5, max: 10 },
  },
  knowledge_list_cards: {
    category: { type: "string", required: false },
    type: { type: "string", required: false },
    status: { type: "string", required: false },
    limit: { type: "number", required: false, default: 10, max: 10 },
  },
  intake_submit_raw: {
    content: { type: "string", required: true, max_length: 50000 },
    source: { type: "string", required: false, default: "zapier" },
    category: { type: "string", required: false },
  },
  crypto_create_signal_card: {
    source: { type: "string", required: true },
    asset: { type: "string", required: true },
    sector: { type: "string", required: true },
    what_changed: { type: "string", required: true },
    signal_direction: {
      type: "string",
      required: true,
      enum: ["supportive", "negative", "mixed", "unclear", "noise"],
    },
    impact_score: { type: "number", required: false, min: 0, max: 10 },
    confidence_score: { type: "number", required: false, min: 0, max: 1 },
    hidden_risk: { type: "string", required: true },
    invalidation_conditions: { type: "array", required: false },
    bullish_scenario: { type: "string", required: false },
    bearish_scenario: { type: "string", required: false },
  },
  queue_get_pending: {},
  quality_gate_check: {
    text: { type: "string", required: true },
  },
};

// ─── Route ───────────────────────────────────────────────────────────────────
export const Route = createFileRoute("/api/mcp")({
  server: {
    handlers: {
      // GET /api/mcp — Tool manifest + server info
      GET: async () => {
        const manifest = {
          server: "fathiya-core-mcp",
          version: "0.1.0",
          description: [
            "FATHIYA CORE MCP Server v0.",
            "This endpoint is a Webhook-compatible tool dispatcher.",
            "It is NOT a full MCP protocol implementation.",
            "See supported_modes for current capabilities.",
          ].join(" "),

          supported_modes: {
            webhook_dispatcher_v0: true,
            mcp_protocol_full: false,
            openrouter_model_routing: true,
            json_rpc_2_0: false,
            streamable_http: false,
            mcp_client_zapier_native: false,
            auth_boundary: false,
            tool_discovery_protocol: false,
          },

          future_mcp_protocol_layer: {
            planned: true,
            features: [
              "JSON-RPC 2.0 envelope: { jsonrpc, id, method, params }",
              "tools/list method",
              "tools/call method",
              "Auth: Bearer token / API key header",
              "Streamable HTTP (SSE) for long-running tools",
              "MCP Client by Zapier native compatibility",
            ],
          },

          tools: Object.entries(TOOL_REGISTRY).map(([name, meta]) => ({
            name,
            ...meta,
            schema: TOOL_SCHEMAS[name] ?? {},
          })),

          zapier_usage: {
            action: "Webhooks by Zapier",
            method: "POST",
            url: "https://your-domain.com/api/mcp",
            body_format: { tool: "<tool_name>", params: { "...": "..." } },
            example: { tool: "ping" },
          },

          quality_gate: {
            enforced: true,
            forbidden: [
              "buy",
              "sell",
              "enter",
              "exit",
              "long",
              "short",
              "leverage",
              "target price as instruction",
              "stop loss as instruction",
            ],
            allowed_signal_directions: ["supportive", "negative", "mixed", "unclear", "noise"],
          },

          model_routing: {
            enabled: true,
            registry: "knowledge/registries/model_routing_registry_v0.json",
            slots: ["default", "fast", "reasoning", "critic", "structured"],
          },
        };

        return new Response(JSON.stringify(manifest, null, 2), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      },

      // POST /api/mcp — Tool dispatcher
      POST: async ({ request }) => {
        let body: MCPRequest;
        try {
          body = (await request.json()) as MCPRequest;
        } catch {
          return new Response(JSON.stringify({ success: false, error: "Invalid JSON body" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        const { tool, params = {} } = body;

        if (!tool) {
          return new Response(
            JSON.stringify({ success: false, error: "Missing 'tool' field" }),
            { status: 400, headers: { "Content-Type": "application/json" } },
          );
        }

        let result;

        switch (tool) {
          case "ping":
            result = tool_ping();
            break;
          case "knowledge_get_awareness_state":
            result = tool_knowledge_get_awareness_state(awarenessStateRaw);
            break;
          case "knowledge_search":
            result = tool_knowledge_search(
              retrievalIndexRaw as never,
              params as { query?: string; category?: string; type?: string; limit?: number },
            );
            break;
          case "knowledge_list_cards":
            result = tool_knowledge_list_cards(
              retrievalIndexRaw as never,
              params as { category?: string; type?: string; status?: string; limit?: number },
            );
            break;
          case "intake_submit_raw":
            result = tool_intake_submit_raw(
              params as { content?: string; source?: string; category?: string },
            );
            break;
          case "crypto_create_signal_card":
            result = tool_crypto_create_signal_card(params as never);
            break;
          case "queue_get_pending":
            result = tool_queue_get_pending({ items: [] });
            break;
          case "quality_gate_check":
            result = tool_quality_gate_check(params as { text?: string });
            break;
          default:
            return new Response(
              JSON.stringify({
                success: false,
                error: `Unknown tool: "${tool}". Available: ${Object.keys(TOOL_REGISTRY).join(", ")}.`,
              }),
              { status: 404, headers: { "Content-Type": "application/json" } },
            );
        }

        return new Response(JSON.stringify(result), {
          status: result.success ? 200 : 422,
          headers: { "Content-Type": "application/json" },
        });
      },
    },
  },
});
