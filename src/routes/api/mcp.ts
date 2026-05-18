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

// ─── Knowledge files (imported at build time) ────────────────────────────────
import awarenessStateRaw from "../../../knowledge/FATHIYA_AWARENESS_STATE.json";
import retrievalIndexRaw from "../../../knowledge/retrieval_index_summary.json";

// ─── Route ───────────────────────────────────────────────────────────────────
export const Route = createFileRoute("/api/mcp")({ 
  server: {
    handlers: {
      // GET /api/mcp — returns tool registry (for Zapier discovery)
      GET: async () => {
        return new Response(
          JSON.stringify({
            server: "fathiya-core-mcp",
            version: "0.1.0",
            description: "FATHIYA CORE MCP Server — Knowledge Vault + Quality Gate",
            tools: Object.entries(TOOL_REGISTRY).map(([name, meta]) => ({
              name,
              ...meta,
            })),
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        );
      },

      // POST /api/mcp — main tool dispatcher
      POST: async ({ request }) => {
        // ── Parse body ──
        let body: MCPRequest;
        try {
          body = (await request.json()) as MCPRequest;
        } catch {
          return new Response(
            JSON.stringify({ success: false, error: "Invalid JSON body" }),
            { status: 400, headers: { "Content-Type": "application/json" } }
          );
        }

        const { tool, params = {} } = body;

        if (!tool) {
          return new Response(
            JSON.stringify({ success: false, error: "Missing 'tool' field" }),
            { status: 400, headers: { "Content-Type": "application/json" } }
          );
        }

        // ── Dispatch ──
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
              params as { query?: string; category?: string; type?: string; limit?: number }
            );
            break;

          case "knowledge_list_cards":
            result = tool_knowledge_list_cards(
              retrievalIndexRaw as never,
              params as { category?: string; type?: string; status?: string; limit?: number }
            );
            break;

          case "intake_submit_raw":
            result = tool_intake_submit_raw(
              params as { content?: string; source?: string; category?: string }
            );
            break;

          case "crypto_create_signal_card":
            result = tool_crypto_create_signal_card(params as never);
            break;

          case "queue_get_pending":
            result = tool_queue_get_pending({ items: [] });
            break;

          case "quality_gate_check":
            result = tool_quality_gate_check(
              params as { text?: string }
            );
            break;

          default:
            return new Response(
              JSON.stringify({
                success: false,
                error: `Unknown tool: "${tool}". Available: ${Object.keys(TOOL_REGISTRY).join(", ")}.`,
              }),
              { status: 404, headers: { "Content-Type": "application/json" } }
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
