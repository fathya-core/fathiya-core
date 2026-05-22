// FATHIYA CORE — Signal Card Schema v0
export const SIGNAL_CARD_SCHEMA = {
  type: "object",
  properties: {
    id: { type: "string" },
    timestamp: { type: "string" },
    source: { type: "string" },
    asset: { type: "string" },
    sector: { type: "string" },
    event_type: { type: "string" },
    signal_direction: { type: "string", enum: ["supportive", "negative", "mixed", "unclear", "noise"] },
    time_horizon: { type: "string", enum: ["immediate", "short", "medium", "long"] },
    impact_score: { type: "number", minimum: 0, maximum: 10 },
    confidence_score: { type: "number", minimum: 0, maximum: 1 },
    what_changed: { type: "string" },
    what_did_not_change: { type: "string" },
    bullish_scenario: { type: "string" },
    bearish_scenario: { type: "string" },
    invalidation_conditions: { type: "array", items: { type: "string" } },
    hidden_risk: { type: "string" },
    bias_traps: { type: "array", items: { type: "string" } },
    next_data_needed: { type: "array", items: { type: "string" } },
    decision_boundary: { type: "string" },
    status: { type: "string", enum: ["draft", "review", "approved", "archived", "rejected"] },
  },
  required: ["id", "timestamp", "source", "asset", "sector", "signal_direction", "impact_score", "confidence_score", "what_changed", "invalidation_conditions", "hidden_risk"],
};

export const SIGNAL_CARD_REQUIRED_FIELDS = [
  "id", "timestamp", "source", "asset", "sector", "signal_direction",
  "impact_score", "confidence_score", "what_changed", "invalidation_conditions", "hidden_risk",
];
