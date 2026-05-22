// FATHIYA CORE — Knowledge Card Schema v0
import type { MCPToolDefinition } from "../types.ts";

export const KNOWLEDGE_CARD_SCHEMA: MCPToolDefinition["inputSchema"] = {
  type: "object",
  properties: {
    id: { type: "string" },
    type: { type: "string", enum: ["article", "tool", "skill", "signal", "risk", "playbook", "target", "report", "decision", "workflow", "narrative"] },
    title: { type: "string" },
    source: { type: "string" },
    url: { type: "string" },
    created_at: { type: "string" },
    captured_at: { type: "string" },
    category: { type: "string" },
    tags: { type: "array", items: { type: "string" } },
    summary: { type: "string" },
    core_idea: { type: "string" },
    why_it_matters: { type: "string" },
    actionability: { type: "string", enum: ["none", "low", "medium", "high"] },
    risk_level: { type: "string", enum: ["none", "low", "medium", "high", "critical"] },
    confidence: { type: "number", minimum: 0, maximum: 1 },
    related_tools: { type: "array", items: { type: "string" } },
    related_domains: { type: "array", items: { type: "string" } },
    patterns: { type: "array", items: { type: "string" } },
    safe_takeaways: { type: "array", items: { type: "string" } },
    dangerous_parts_removed: { type: "boolean" },
    open_questions: { type: "array", items: { type: "string" } },
    next_actions: { type: "array", items: { type: "string" } },
    linked_cards: { type: "array", items: { type: "string" } },
    status: { type: "string", enum: ["draft", "review", "approved", "archived", "rejected"] },
  },
  required: ["id", "type", "title", "source", "category", "summary", "core_idea", "why_it_matters", "confidence", "status"],
};

export const KNOWLEDGE_CARD_REQUIRED_FIELDS = [
  "id", "type", "title", "source", "category", "summary", "core_idea", "why_it_matters", "confidence", "status",
];
