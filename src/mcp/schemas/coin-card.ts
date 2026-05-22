// FATHIYA CORE — Coin Card Schema v0
export const COIN_CARD_SCHEMA = {
  type: "object",
  properties: {
    symbol: { type: "string" },
    name: { type: "string" },
    sector: { type: "string" },
    chain: { type: "string" },
    market_role: { type: "string" },
    main_narrative: { type: "string" },
    secondary_narratives: { type: "array", items: { type: "string" } },
    known_risks: { type: "array", items: { type: "string" } },
    liquidity_profile: { type: "string" },
    volatility_profile: { type: "string" },
    dependency_map: { type: "array", items: { type: "string" } },
    macro_sensitivity: { type: "string", enum: ["low", "medium", "high"] },
    security_risks: { type: "array", items: { type: "string" } },
    regulatory_risks: { type: "array", items: { type: "string" } },
    watch_signals: { type: "array", items: { type: "string" } },
    invalidations: { type: "array", items: { type: "string" } },
    status: { type: "string", enum: ["draft", "review", "approved", "archived", "rejected"] },
  },
  required: ["symbol", "name", "sector", "chain", "market_role", "main_narrative"],
};
