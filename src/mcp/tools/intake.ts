// FATHIYA CORE — Daily Intake MCP Tools v0
import type { MCPToolDefinition, MCPToolResult, IntakeItem, KnowledgeCardType } from "../types.ts";
import { runQualityGate } from "../utils/validator.ts";
import { MCP_CONFIG } from "../config.ts";

export const INTAKE_TOOLS: MCPToolDefinition[] = [
  {
    name: "intake_submit_raw",
    description: "إدخال محتوى خام إلى النظام. أي خبر أو مقال أو ملاحظة يدخل من هنا.",
    inputSchema: {
      type: "object",
      properties: {
        content: { type: "string", description: "المحتوى الخام" },
        source: { type: "string", description: "مصدر المحتوى: news, medium, perplexity, manual, gemini, manus" },
        title: { type: "string", description: "عنوان اختياري" },
        url: { type: "string", description: "رابط اختياري" },
      },
      required: ["content", "source"],
    },
  },
  {
    name: "intake_classify",
    description: "تصنيف محتوى خام إلى نوع بطاقة وتصنيف",
    inputSchema: {
      type: "object",
      properties: {
        content: { type: "string", description: "المحتوى المراد تصنيفه" },
        hint: { type: "string", description: "تلميح اختياري للتصنيف" },
      },
      required: ["content"],
    },
  },
  {
    name: "intake_get_queue",
    description: "جلب قائمة انتظار المدخلات الخامة التي تحتاج تنظيف أو تصنيف",
    inputSchema: {
      type: "object",
      properties: {
        status: { type: "string", description: "clean | partial | corrupted | duplicate | needs_review" },
        limit: { type: "number", default: 10 },
      },
      required: [],
    },
  },
];

export async function handleIntakeTool(
  toolName: string,
  params: Record<string, unknown>,
): Promise<MCPToolResult<unknown>> {
  const timestamp = new Date().toISOString();

  switch (toolName) {
    case "intake_submit_raw": {
      const content = String(params["content"] ?? "");
      const source = String(params["source"] ?? "manual");
      const title = params["title"] as string | undefined;
      const url = params["url"] as string | undefined;

      if (!content.trim()) {
        return { success: false, tool: toolName, timestamp, error: "Content cannot be empty" };
      }

      if (content.length > MCP_CONFIG.max_content_length) {
        return {
          success: false, tool: toolName, timestamp,
          error: `Content exceeds max length of ${MCP_CONFIG.max_content_length} characters`,
        };
      }

      // Run quality gate
      const gateResult = runQualityGate(content);

      const item: IntakeItem = {
        id: `intake_${Date.now()}`,
        raw_content: content,
        source,
        submitted_at: timestamp,
        clean_status: gateResult.passed ? "clean" : "needs_review",
      };

      if (title) Object.assign(item, { title });
      if (url) Object.assign(item, { url });

      return {
        success: true, tool: toolName, timestamp,
        data: {
          item,
          quality_gate: gateResult,
          next_step: gateResult.passed ? "classify" : "review",
          storage_path: `${MCP_CONFIG.raw_path}/${timestamp.slice(0, 10)}/${source}/`,
        },
        quality_gate_passed: gateResult.passed,
        requires_approval: gateResult.needs_human_review,
        receipt_id: `receipt_${Date.now()}`,
      };
    }

    case "intake_classify": {
      const content = String(params["content"] ?? "");
      const hint = params["hint"] as string | undefined;

      // v0: keyword-based classification
      const lower = content.toLowerCase();
      let classified_as: KnowledgeCardType = "article";
      let category = "general";
      const tags: string[] = [];

      if (lower.includes("bitcoin") || lower.includes("btc") || lower.includes("ethereum") ||
          lower.includes("crypto") || lower.includes("defi") || lower.includes("blockchain")) {
        classified_as = "signal";
        category = "crypto";
        tags.push("crypto");
      } else if (lower.includes("vulnerability") || lower.includes("exploit") || lower.includes("bug bounty") ||
                 lower.includes("xss") || lower.includes("sqli") || lower.includes("rce")) {
        classified_as = "risk";
        category = "bug-bounty";
        tags.push("security");
      } else if (lower.includes("tool") || lower.includes("framework") || lower.includes("library")) {
        classified_as = "tool";
        category = "tools";
        tags.push("tooling");
      } else if (lower.includes("risk") || lower.includes("threat") || lower.includes("danger")) {
        classified_as = "risk";
        category = "risks";
        tags.push("risk");
      }

      if (hint) tags.push(hint);

      return {
        success: true, tool: toolName, timestamp,
        data: { classified_as, category, tags, confidence: 0.6, note: "v0: keyword-based. Upgrade to ML classifier in v1." },
        quality_gate_passed: true, requires_approval: false,
      };
    }

    case "intake_get_queue": {
      const status = params["status"] as string | undefined;
      const limit = Math.min(Number(params["limit"] ?? 10), MCP_CONFIG.max_items_per_call);
      return {
        success: true, tool: toolName, timestamp,
        data: {
          status_filter: status ?? "all",
          limit,
          source: MCP_CONFIG.raw_path,
          items: [],
          note: "v0: wire to raw archive reader for live queue",
        },
        quality_gate_passed: true, requires_approval: false,
      };
    }

    default:
      return { success: false, tool: toolName, timestamp, error: `Unknown intake tool: ${toolName}` };
  }
}
