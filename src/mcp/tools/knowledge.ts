// FATHIYA CORE — Knowledge Vault MCP Tools v0
import type { MCPToolDefinition, MCPToolResult, KnowledgeCard, AwarenessState } from "../types.ts";
import { validateKnowledgeCard } from "../utils/validator.ts";
import { MCP_CONFIG } from "../config.ts";

export const KNOWLEDGE_TOOLS: MCPToolDefinition[] = [
  {
    name: "knowledge_search",
    description: "بحث في Knowledge Vault باستخدام كلمة مفتاحية أو تصنيف",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "كلمة البحث" },
        category: { type: "string", description: "تصنيف اختياري: crypto, bug-bounty, tools, articles" },
        type: { type: "string", description: "نوع البطاقة: article, tool, skill, signal, risk, playbook" },
        limit: { type: "number", description: "عدد النتائج (max 10)", default: 5 },
      },
      required: ["query"],
    },
  },
  {
    name: "knowledge_get_card",
    description: "جلب بطاقة معرفة كاملة باستخدام الـ ID",
    inputSchema: {
      type: "object",
      properties: { id: { type: "string", description: "معرف البطاقة" } },
      required: ["id"],
    },
  },
  {
    name: "knowledge_create_card",
    description: "إنشاء بطاقة معرفة جديدة. تمر عبر Quality Gate وتدخل Approval Queue إذا احتاجت مراجعة.",
    inputSchema: {
      type: "object",
      properties: {
        type: { type: "string" },
        title: { type: "string" },
        source: { type: "string" },
        category: { type: "string" },
        summary: { type: "string" },
        core_idea: { type: "string" },
        why_it_matters: { type: "string" },
        confidence: { type: "number" },
        tags: { type: "array", items: { type: "string" } },
        url: { type: "string" },
      },
      required: ["type", "title", "source", "category", "summary", "core_idea", "why_it_matters", "confidence"],
    },
  },
  {
    name: "knowledge_list_cards",
    description: "قائمة بطاقات المعرفة مع فلترة بالتصنيف أو النوع أو الحالة",
    inputSchema: {
      type: "object",
      properties: {
        category: { type: "string" },
        type: { type: "string" },
        status: { type: "string", description: "draft, review, approved, archived, rejected" },
        limit: { type: "number", default: 10 },
      },
      required: [],
    },
  },
  {
    name: "knowledge_get_awareness_state",
    description: "جلب حالة الوعي الحالية لـ FATHIYA: التركيز الحالي، المخاطر، الفجوات، الفرص",
    inputSchema: { type: "object", properties: {}, required: [] },
  },
];

export async function handleKnowledgeTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "knowledge_search": {
      const query = String(params["query"] ?? "");
      const category = params["category"] as string | undefined;
      const type = params["type"] as string | undefined;
      const limit = Math.min(Number(params["limit"] ?? 5), MCP_CONFIG.max_items_per_call);
      return {
        success: true, tool: toolName, timestamp,
        data: { query, filters: { category, type }, limit, source: `${MCP_CONFIG.knowledge_base_path}/index.json`, results: [], note: "v0: wire to retrieval engine for live results" },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "knowledge_get_card": {
      const id = String(params["id"] ?? "");
      if (!id) return { success: false, tool: toolName, timestamp, error: "Missing required field: id" };
      return {
        success: true, tool: toolName, timestamp,
        data: { id, source: `${MCP_CONFIG.cards_path}/${id}.json`, note: "v0: wire to file reader for live data" },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "knowledge_create_card": {
      const cardData = params as Partial<KnowledgeCard>;
      const gateResult = validateKnowledgeCard(cardData);
      if (!gateResult.passed) {
        return {
          success: false, tool: toolName, timestamp,
          error: "Knowledge Card failed Quality Gate",
          quality_gate_passed: false,
          quality_warnings: [...gateResult.missing_fields, ...gateResult.warnings],
          requires_approval: true,
        };
      }
      const newCard: Partial<KnowledgeCard> = {
        ...cardData,
        id: `card_${Date.now()}`,
        created_at: timestamp,
        captured_at: timestamp,
        status: "draft",
        tags: (cardData.tags as string[]) ?? [],
      };
      return {
        success: true, tool: toolName, timestamp,
        data: newCard,
        quality_gate_passed: true,
        requires_approval: gateResult.needs_human_review,
        receipt_id: `receipt_${Date.now()}`,
      };
    }
    case "knowledge_list_cards": {
      const category = params["category"] as string | undefined;
      const type = params["type"] as string | undefined;
      const status = params["status"] as string | undefined;
      const limit = Math.min(Number(params["limit"] ?? 10), MCP_CONFIG.max_items_per_call);
      return {
        success: true, tool: toolName, timestamp,
        data: { filters: { category, type, status }, limit, source: MCP_CONFIG.cards_path, cards: [], note: "v0: wire to file reader for live data" },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "knowledge_get_awareness_state": {
      const state: AwarenessState = {
        current_focus: ["build knowledge vault", "MCP SDK v0", "crypto radar", "bug bounty readiness"],
        active_domains: ["crypto", "bug-bounty", "tools", "awareness"],
        known_tools: ["Zapier", "n8n", "Cursor", "Gemini", "Perplexity", "Manus", "DataCamp"],
        available_resources: ["Perplexity Pro", "Gemini Pro", "Manus Pro", "DataCamp"],
        active_risks: ["n8n batching instability", "MCP tool mismatch", "knowledge fragmentation"],
        knowledge_gaps: ["live retrieval engine", "vector search", "Supabase integration"],
        top_opportunities: ["MCP SDK v0 completion", "first 20 knowledge cards", "crypto signal pipeline"],
        blocked_actions: ["exchange API keys", "automated trading", "leverage automation"],
        next_best_artifacts: ["FATHIYA_ONTOLOGY_v0.json", "knowledge/index.json", "first 20 Knowledge Cards"],
        last_updated: timestamp,
      };
      return { success: true, tool: toolName, timestamp, data: state, quality_gate_passed: true, requires_approval: false };
    }
    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown knowledge tool: ${toolName}` };
  }
}
