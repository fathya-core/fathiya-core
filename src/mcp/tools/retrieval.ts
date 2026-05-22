// FATHIYA CORE — Retrieval Engine MCP Tools v0
import type { MCPToolDefinition, MCPToolResult } from "../types.ts";
import { MCP_CONFIG } from "../config.ts";

export const RETRIEVAL_TOOLS: MCPToolDefinition[] = [
  {
    name: "retrieval_search",
    description: "بحث متقدم في Knowledge Vault باستخدام كلمات مفتاحية وتصنيف ووسوم",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "كلمة البحث" },
        category: { type: "string", description: "تصنيف اختياري" },
        tags: { type: "array", items: { type: "string" }, description: "وسوم اختيارية" },
        limit: { type: "number", default: 5 },
      },
      required: ["query"],
    },
  },
  {
    name: "retrieval_get_index",
    description: "جلب فهرس Knowledge Vault الكامل (index.json)",
    inputSchema: { type: "object", properties: {}, required: [] },
  },
  {
    name: "retrieval_get_related",
    description: "جلب البطاقات ذات الصلة ببطاقة محددة",
    inputSchema: {
      type: "object",
      properties: {
        card_id: { type: "string", description: "معرف البطاقة" },
        limit: { type: "number", default: 5 },
      },
      required: ["card_id"],
    },
  },
];

export async function handleRetrievalTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "retrieval_search": {
      const query = String(params["query"] ?? "");
      const category = params["category"] as string | undefined;
      const tags = params["tags"] as string[] | undefined;
      const limit = Math.min(Number(params["limit"] ?? 5), MCP_CONFIG.max_items_per_call);
      return {
        success: true, tool: toolName, timestamp,
        data: {
          query, filters: { category, tags }, limit,
          results: [],
          index_source: `${MCP_CONFIG.knowledge_base_path}/index.json`,
          note: "v0: keyword index search. Upgrade to vector search in v1.",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "retrieval_get_index": {
      return {
        success: true, tool: toolName, timestamp,
        data: {
          source: `${MCP_CONFIG.knowledge_base_path}/index.json`,
          note: "v0: wire to index.json file reader for live data",
          index: {},
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "retrieval_get_related": {
      const card_id = String(params["card_id"] ?? "");
      const limit = Math.min(Number(params["limit"] ?? 5), MCP_CONFIG.max_items_per_call);
      if (!card_id) return { success: false, tool: toolName, timestamp, error: "Missing required field: card_id" };
      return {
        success: true, tool: toolName, timestamp,
        data: {
          card_id, limit,
          related: [],
          graph_source: `${MCP_CONFIG.knowledge_base_path}/graph.json`,
          note: "v0: wire to graph.json for relation-based retrieval",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown retrieval tool: ${toolName}` };
  }
}
