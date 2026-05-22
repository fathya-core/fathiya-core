// FATHIYA CORE — Tool Card Schema v0
export const TOOL_CARD_SCHEMA = {
  type: "object",
  properties: {
    tool: { type: "string" },
    role: { type: "string" },
    best_for: { type: "array", items: { type: "string" } },
    not_for: { type: "array", items: { type: "string" } },
    inputs: { type: "array", items: { type: "string" } },
    outputs: { type: "array", items: { type: "string" } },
    risk_level: { type: "string", enum: ["low", "medium", "high"] },
    requires_approval: { type: "boolean" },
    adapter_type: { type: "string" },
    fallback: { type: "string" },
    status: { type: "string", enum: ["draft", "review", "approved", "archived", "rejected"] },
  },
  required: ["tool", "role", "risk_level", "requires_approval", "adapter_type", "status"],
};

export const TOOL_CARD_REQUIRED_FIELDS = ["tool", "role", "risk_level", "requires_approval", "adapter_type", "status"];
