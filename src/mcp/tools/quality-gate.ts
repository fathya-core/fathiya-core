// FATHIYA CORE — Quality Gate MCP Tools v0
import type { MCPToolDefinition, MCPToolResult, KnowledgeCard, SignalCard } from "../types.ts";
import { runQualityGate, validateSignalCard, validateKnowledgeCard } from "../utils/validator.ts";

export const QUALITY_GATE_TOOLS: MCPToolDefinition[] = [
  {
    name: "quality_gate_check_content",
    description: "فحص محتوى نصي عبر Quality Gate. يمنع أوامر التداول والمحتوى غير الآمن.",
    inputSchema: {
      type: "object",
      properties: { content: { type: "string", description: "المحتوى المراد فحصه" } },
      required: ["content"],
    },
  },
  {
    name: "quality_gate_validate_signal_card",
    description: "التحقق من صحة Signal Card قبل الحفظ",
    inputSchema: {
      type: "object",
      properties: {
        card: { type: "object", description: "بيانات Signal Card" },
      },
      required: ["card"],
    },
  },
  {
    name: "quality_gate_validate_knowledge_card",
    description: "التحقق من صحة Knowledge Card قبل الحفظ",
    inputSchema: {
      type: "object",
      properties: {
        card: { type: "object", description: "بيانات Knowledge Card" },
      },
      required: ["card"],
    },
  },
];

export async function handleQualityGateTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "quality_gate_check_content": {
      const content = String(params["content"] ?? "");
      const result = runQualityGate(content);
      return {
        success: true, tool: toolName, timestamp,
        data: result,
        quality_gate_passed: result.passed,
        requires_approval: result.needs_human_review,
      };
    }
    case "quality_gate_validate_signal_card": {
      const card = (params["card"] ?? {}) as Partial<SignalCard>;
      const result = validateSignalCard(card);
      return {
        success: true, tool: toolName, timestamp,
        data: result,
        quality_gate_passed: result.passed,
        requires_approval: result.needs_human_review,
      };
    }
    case "quality_gate_validate_knowledge_card": {
      const card = (params["card"] ?? {}) as Partial<KnowledgeCard>;
      const result = validateKnowledgeCard(card);
      return {
        success: true, tool: toolName, timestamp,
        data: result,
        quality_gate_passed: result.passed,
        requires_approval: result.needs_human_review,
      };
    }
    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown quality gate tool: ${toolName}` };
  }
}
