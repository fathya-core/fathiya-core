// FATHIYA CORE — MCP Execution Logger v0
// كل استدعاء MCP يُسجَّل في knowledge/audit

import type { MCPToolResult } from "../types.ts";

export interface MCPAuditEntry {
  receipt_id: string;
  timestamp: string;
  tool: string;
  success: boolean;
  quality_gate_passed?: boolean;
  requires_approval?: boolean;
  error?: string;
  summary: string;
}

// ─── Generate Receipt ID ─────────────────────────────────────────────────────────
export function generateReceiptId(tool: string): string {
  const ts = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).slice(2, 6).toUpperCase();
  const toolSlug = tool
    .replace(/[^a-z0-9]/gi, "")
    .slice(0, 8)
    .toUpperCase();
  return `MCP-${toolSlug}-${ts}-${rand}`;
}

// ─── Build Audit Entry ────────────────────────────────────────────────────────────
export function buildAuditEntry<T>(result: MCPToolResult<T>): MCPAuditEntry {
  return {
    receipt_id: result.receipt_id ?? generateReceiptId(result.tool),
    timestamp: result.timestamp,
    tool: result.tool,
    success: result.success,
    quality_gate_passed: result.quality_gate_passed,
    requires_approval: result.requires_approval,
    error: result.error,
    summary: result.success
      ? `Tool "${result.tool}" executed successfully.`
      : `Tool "${result.tool}" failed: ${result.error ?? "unknown error"}`,
  };
}

// ─── Format Audit Entry as Markdown ───────────────────────────────────────────────
export function formatAuditMarkdown(entry: MCPAuditEntry): string {
  return [
    `# MCP Audit Receipt`,
    ``,
    `- **Receipt ID:** ${entry.receipt_id}`,
    `- **Timestamp:** ${entry.timestamp}`,
    `- **Tool:** ${entry.tool}`,
    `- **Success:** ${entry.success ? "✅" : "❌"}`,
    `- **Quality Gate:** ${entry.quality_gate_passed === undefined ? "N/A" : entry.quality_gate_passed ? "✅ Passed" : "❌ Failed"}`,
    `- **Requires Approval:** ${entry.requires_approval ? "⚠️ Yes" : "No"}`,
    entry.error ? `- **Error:** ${entry.error}` : "",
    ``,
    `## Summary`,
    entry.summary,
  ]
    .filter((line) => line !== undefined)
    .join("\n");
}

// ─── Console Logger (for development) ───────────────────────────────────────────
export function logMCPCall(tool: string, success: boolean, note?: string): void {
  const icon = success ? "✅" : "❌";
  const msg = `[FATHIYA MCP] ${icon} ${tool}${note ? ` — ${note}` : ""}`;
  if (success) {
    console.log(msg);
  } else {
    console.error(msg);
  }
}
