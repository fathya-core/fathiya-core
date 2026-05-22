// FATHIYA CORE — Signal Card MCP Tools v0
import type { MCPToolDefinition, MCPToolResult } from "../types.ts";
import { MCP_CONFIG } from "../config.ts";

export const SIGNAL_TOOLS: MCPToolDefinition[] = [
  {
    name: "signal_list",
    description: "قائمة Signal Cards مع فلترة بالأصل أو القطاع أو الاتجاه",
    inputSchema: {
      type: "object",
      properties: {
        asset: { type: "string", description: "العملة أو الأصل" },
        sector: { type: "string", description: "القطاع" },
        signal_direction: { type: "string", description: "supportive | negative | mixed | unclear | noise" },
        limit: { type: "number", default: 10 },
      },
      required: [],
    },
  },
  {
    name: "signal_get",
    description: "جلب Signal Card كاملة بالـ ID",
    inputSchema: {
      type: "object",
      properties: { id: { type: "string", description: "معرف الإشارة" } },
      required: ["id"],
    },
  },
  {
    name: "signal_update_status",
    description: "تحديث حالة Signal Card: draft → review → approved → archived",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "معرف الإشارة" },
        status: { type: "string", description: "draft | review | approved | archived | rejected" },
        note: { type: "string", description: "ملاحظة اختيارية" },
      },
      required: ["id", "status"],
    },
  },
];

export async function handleSignalTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "signal_list": {
      const asset = params["asset"] as string | undefined;
      const sector = params["sector"] as string | undefined;
      const signal_direction = params["signal_direction"] as string | undefined;
      const limit = Math.min(Number(params["limit"] ?? 10), MCP_CONFIG.max_items_per_call);
      return {
        success: true, tool: toolName, timestamp,
        data: {
          filters: { asset, sector, signal_direction }, limit,
          source: `${MCP_CONFIG.crypto_path}/signal-cards/`,
          signals: [],
          note: "v0: wire to signal-cards directory for live data",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "signal_get": {
      const id = String(params["id"] ?? "");
      if (!id) return { success: false, tool: toolName, timestamp, error: "Missing required field: id" };
      return {
        success: true, tool: toolName, timestamp,
        data: { id, source: `${MCP_CONFIG.crypto_path}/signal-cards/${id}.json`, note: "v0: wire to file reader" },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "signal_update_status": {
      const id = String(params["id"] ?? "");
      const status = String(params["status"] ?? "");
      const note = params["note"] as string | undefined;
      if (!id || !status) return { success: false, tool: toolName, timestamp, error: "Missing required fields: id, status" };
      const validStatuses = ["draft", "review", "approved", "archived", "rejected"];
      if (!validStatuses.includes(status)) {
        return { success: false, tool: toolName, timestamp, error: `Invalid status: ${status}. Must be one of: ${validStatuses.join(", ")}` };
      }
      return {
        success: true, tool: toolName, timestamp,
        data: { id, status, note, updated_at: timestamp, requires_approval: status === "approved" },
        quality_gate_passed: true,
        requires_approval: status === "approved",
        receipt_id: `receipt_${Date.now()}`,
      };
    }
    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown signal tool: ${toolName}` };
  }
}
