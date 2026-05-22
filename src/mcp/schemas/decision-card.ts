// FATHIYA CORE — Decision Card Schema v0
export const DECISION_CARD_SCHEMA = {
  type: "object",
  properties: {
    id: { type: "string" },
    date: { type: "string" },
    decision: { type: "string" },
    reason: { type: "string" },
    alternatives_rejected: { type: "array", items: { type: "string" } },
    risk: { type: "string" },
    owner: { type: "string" },
    status: { type: "string", enum: ["active", "superseded", "archived"] },
    review_date: { type: "string" },
  },
  required: ["id", "date", "decision", "reason", "owner", "status"],
};

export const DECISION_CARD_REQUIRED_FIELDS = ["id", "date", "decision", "reason", "owner", "status"];
