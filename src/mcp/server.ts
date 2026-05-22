// FATHIYA CORE — MCP Server Entry Point v0
// هذا هو نقطة دخول MCP Server الخاصة بـ FATHIYA CORE
// MCP هو adapter فقط — ليس العقل
// العقل: Knowledge Vault + FATHIYA Kernel + Quality Gates

import { MCP_CONFIG } from "./config.ts";
import type { MCPToolDefinition, MCPToolResult } from "./types.ts";
import { runQualityGate } from "./utils/validator.ts";
import { formatMCPResponse } from "./utils/formatter.ts";
import { logMCPCall } from "./utils/logger.ts";

// ─── Tool Registry ────────────────────────────────────────────────────────────
import { KNOWLEDGE_TOOLS, handleKnowledgeTool } from "./tools/knowledge.ts";
import { INTAKE_TOOLS, handleIntakeTool } from "./tools/intake.ts";
import { CRYPTO_TOOLS, handleCryptoTool } from "./tools/crypto.ts";
import { SIGNAL_TOOLS, handleSignalTool } from "./tools/signals.ts";
import { RETRIEVAL_TOOLS, handleRetrievalTool } from "./tools/retrieval.ts";
import { AWARENESS_TOOLS, handleAwarenessTool } from "./tools/awareness.ts";
import { QUALITY_GATE_TOOLS, handleQualityGateTool } from "./tools/quality-gate.ts";
import { APPROVAL_QUEUE_TOOLS, handleApprovalQueueTool } from "./tools/approval-queue.ts";

// ─── All Tools ────────────────────────────────────────────────────────────────
export const ALL_TOOLS: MCPToolDefinition[] = [
  ...KNOWLEDGE_TOOLS,
  ...INTAKE_TOOLS,
  ...CRYPTO_TOOLS,
  ...SIGNAL_TOOLS,
  ...RETRIEVAL_TOOLS,
  ...AWARENESS_TOOLS,
  ...QUALITY_GATE_TOOLS,
  ...APPROVAL_QUEUE_TOOLS,
];

// ─── Tool Router ──────────────────────────────────────────────────────────────
export async function routeTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const startTime = Date.now();

  try {
    let result: MCPToolResult<unknown>;

    // Route to correct handler
    if (KNOWLEDGE_TOOLS.find((t) => t.name === toolName)) {
      result = await handleKnowledgeTool(toolName, params);
    } else if (INTAKE_TOOLS.find((t) => t.name === toolName)) {
      result = await handleIntakeTool(toolName, params);
    } else if (CRYPTO_TOOLS.find((t) => t.name === toolName)) {
      result = await handleCryptoTool(toolName, params);
    } else if (SIGNAL_TOOLS.find((t) => t.name === toolName)) {
      result = await handleSignalTool(toolName, params);
    } else if (RETRIEVAL_TOOLS.find((t) => t.name === toolName)) {
      result = await handleRetrievalTool(toolName, params);
    } else if (AWARENESS_TOOLS.find((t) => t.name === toolName)) {
      result = await handleAwarenessTool(toolName, params);
    } else if (QUALITY_GATE_TOOLS.find((t) => t.name === toolName)) {
      result = await handleQualityGateTool(toolName, params);
    } else if (APPROVAL_QUEUE_TOOLS.find((t) => t.name === toolName)) {
      result = await handleApprovalQueueTool(toolName, params);
    } else {
      result = {
        success: false,
        tool: toolName,
        timestamp: new Date().toISOString(),
        error: `Unknown tool: ${toolName}`,
      };
    }

    // Log the call
    logMCPCall({
      tool: toolName,
      params,
      result,
      duration_ms: Date.now() - startTime,
    });

    return result;
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err);
    const failResult: MCPToolResult<unknown> = {
      success: false,
      tool: toolName,
      timestamp: new Date().toISOString(),
      error,
    };
    logMCPCall({
      tool: toolName,
      params,
      result: failResult,
      duration_ms: Date.now() - startTime,
    });
    return failResult;
  }
}

// ─── MCP Protocol Handler ─────────────────────────────────────────────────────
// يعالج طلبات MCP القادمة من Zapier أو أي MCP Client
export async function handleMCPRequest(request: {
  method: string;
  params?: Record<string, unknown>;
}): Promise<unknown> {
  const { method, params = {} } = request;

  switch (method) {
    // MCP initialize
    case "initialize":
      return {
        protocolVersion: MCP_CONFIG.protocol_version,
        capabilities: {
          tools: {},
        },
        serverInfo: {
          name: MCP_CONFIG.server_name,
          version: MCP_CONFIG.server_version,
        },
      };

    // List available tools
    case "tools/list":
      return {
        tools: ALL_TOOLS.map((t) => ({
          name: t.name,
          description: t.description,
          inputSchema: t.inputSchema,
        })),
      };

    // Call a tool
    case "tools/call": {
      const toolName = params["name"] as string;
      const toolArgs = (params["arguments"] ?? {}) as Record<string, unknown>;

      if (!toolName) {
        return formatMCPResponse({
          success: false,
          tool: "unknown",
          timestamp: new Date().toISOString(),
          error: "Missing tool name in tools/call request",
        });
      }

      // Quality Gate on input (if content field present)
      if (MCP_CONFIG.quality_gate_enabled && toolArgs["content"]) {
        const gateResult = runQualityGate(String(toolArgs["content"]));
        if (!gateResult.passed) {
          return formatMCPResponse({
            success: false,
            tool: toolName,
            timestamp: new Date().toISOString(),
            error: gateResult.blocked_reason ?? "Quality Gate blocked this request",
            quality_gate_passed: false,
            quality_warnings: gateResult.unsafe_content,
          });
        }
      }

      const result = await routeTool(toolName, toolArgs);
      return formatMCPResponse(result);
    }

    default:
      return {
        error: {
          code: -32601,
          message: `Method not found: ${method}`,
        },
      };
  }
}

// ─── Server Info ──────────────────────────────────────────────────────────────
export const SERVER_INFO = {
  name: MCP_CONFIG.server_name,
  version: MCP_CONFIG.server_version,
  protocol_version: MCP_CONFIG.protocol_version,
  tools_count: ALL_TOOLS.length,
  quality_gate_enabled: MCP_CONFIG.quality_gate_enabled,
  approval_queue_enabled: MCP_CONFIG.approval_queue_enabled,
};
