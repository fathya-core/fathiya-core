// FATHIYA CORE — Awareness State MCP Tools v0
import type { MCPToolDefinition, MCPToolResult } from "../types.ts";
import { MCP_CONFIG } from "../config.ts";

export const AWARENESS_TOOLS: MCPToolDefinition[] = [
  {
    name: "awareness_get_state",
    description: "جلب حالة الوعي الحالية لـ FATHIYA من FATHIYA_AWARENESS_STATE.json",
    inputSchema: { type: "object", properties: {}, required: [] },
  },
  {
    name: "awareness_get_daily_brief",
    description: "جلب أو توليد التقرير اليومي لـ FATHIYA",
    inputSchema: {
      type: "object",
      properties: {
        date: { type: "string", description: "التاريخ بصيغة YYYY-MM-DD (افتراضي: اليوم)" },
      },
      required: [],
    },
  },
  {
    name: "awareness_update_focus",
    description: "تحديث قائمة التركيز الحالية في Awareness State",
    inputSchema: {
      type: "object",
      properties: {
        current_focus: { type: "array", items: { type: "string" }, description: "قائمة التركيز الجديدة" },
        active_risks: { type: "array", items: { type: "string" }, description: "مخاطر نشطة" },
        knowledge_gaps: { type: "array", items: { type: "string" }, description: "فجوات معرفية" },
      },
      required: ["current_focus"],
    },
  },
];

export async function handleAwarenessTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "awareness_get_state": {
      return {
        success: true, tool: toolName, timestamp,
        data: {
          source: MCP_CONFIG.awareness_state_file,
          note: "v0: wire to FATHIYA_AWARENESS_STATE.json for live state",
          state: {
            current_focus: ["MCP SDK v0", "knowledge vault", "crypto radar"],
            active_domains: ["crypto", "bug-bounty", "tools"],
            active_risks: ["n8n instability", "knowledge fragmentation"],
            knowledge_gaps: ["vector search", "live retrieval"],
            last_updated: timestamp,
          },
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "awareness_get_daily_brief": {
      const date = (params["date"] as string) ?? timestamp.slice(0, 10);
      return {
        success: true, tool: toolName, timestamp,
        data: {
          date,
          source: `knowledge/FATHIYA_DAILY_AWARENESS_BRIEF_${date}.md`,
          note: "v0: wire to daily brief generator for live output",
          brief: {
            top_signals: [],
            top_risks: [],
            next_artifact: "knowledge/index.json",
            awareness_state_updated: false,
          },
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "awareness_update_focus": {
      const current_focus = params["current_focus"] as string[];
      const active_risks = (params["active_risks"] as string[]) ?? [];
      const knowledge_gaps = (params["knowledge_gaps"] as string[]) ?? [];
      return {
        success: true, tool: toolName, timestamp,
        data: {
          updated: { current_focus, active_risks, knowledge_gaps, last_updated: timestamp },
          target_file: MCP_CONFIG.awareness_state_file,
          note: "v0: wire to file writer to persist state",
        },
        quality_gate_passed: true,
        requires_approval: true,
        receipt_id: `receipt_${Date.now()}`,
      };
    }
    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown awareness tool: ${toolName}` };
  }
}
