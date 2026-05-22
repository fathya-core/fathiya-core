// FATHIYA CORE — Approval Queue MCP Tools v0
// كل action يمر بـ Approval Queue قبل التنفيذ
import type { MCPToolDefinition, MCPToolResult, ApprovalQueueItem } from "../types.ts";
import { MCP_CONFIG } from "../config.ts";

export const APPROVAL_QUEUE_TOOLS: MCPToolDefinition[] = [
  {
    name: "queue_get_pending",
    description: "جلب العناصر المعلقة في Approval Queue التي تحتاج موافقة بشرية",
    inputSchema: {
      type: "object",
      properties: {
        limit: { type: "number", default: 10 },
        tool_filter: { type: "string", description: "فلترة باسم الأداة" },
      },
      required: [],
    },
  },
  {
    name: "queue_approve",
    description: "الموافقة على عنصر في Approval Queue",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "معرف العنصر" },
        reviewer_note: { type: "string", description: "ملاحظة المراجع اختيارية" },
      },
      required: ["id"],
    },
  },
  {
    name: "queue_reject",
    description: "رفض عنصر في Approval Queue مع سبب",
    inputSchema: {
      type: "object",
      properties: {
        id: { type: "string", description: "معرف العنصر" },
        reason: { type: "string", description: "سبب الرفض" },
      },
      required: ["id", "reason"],
    },
  },
];

export async function handleApprovalQueueTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "queue_get_pending": {
      const limit = Math.min(Number(params["limit"] ?? 10), MCP_CONFIG.max_items_per_call);
      const tool_filter = params["tool_filter"] as string | undefined;
      return {
        success: true, tool: toolName, timestamp,
        data: {
          status: "pending",
          tool_filter: tool_filter ?? "all",
          limit,
          items: [] as ApprovalQueueItem[],
          source: `${MCP_CONFIG.audit_path}/approval_queue.json`,
          note: "v0: wire to approval queue file for live data",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }
    case "queue_approve": {
      const id = String(params["id"] ?? "");
      const reviewer_note = params["reviewer_note"] as string | undefined;
      if (!id) return { success: false, tool: toolName, timestamp, error: "Missing required field: id" };
      return {
        success: true, tool: toolName, timestamp,
        data: {
          id,
          status: "approved",
          reviewed_at: timestamp,
          reviewer_note: reviewer_note ?? "Approved via MCP",
          receipt_id: `receipt_${Date.now()}`,
          note: "v0: wire to approval queue writer to persist",
        },
        quality_gate_passed: true,
        requires_approval: false,
        receipt_id: `receipt_${Date.now()}`,
      };
    }
    case "queue_reject": {
      const id = String(params["id"] ?? "");
      const reason = String(params["reason"] ?? "");
      if (!id || !reason) return { success: false, tool: toolName, timestamp, error: "Missing required fields: id, reason" };
      return {
        success: true, tool: toolName, timestamp,
        data: {
          id,
          status: "rejected",
          reviewed_at: timestamp,
          reviewer_note: reason,
          receipt_id: `receipt_${Date.now()}`,
          note: "v0: wire to approval queue writer to persist",
        },
        quality_gate_passed: true,
        requires_approval: false,
        receipt_id: `receipt_${Date.now()}`,
      };
    }
    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown approval queue tool: ${toolName}` };
  }
}
