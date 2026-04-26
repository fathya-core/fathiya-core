export const AI_MODELS = [
  { id: "gpt-4o-mini", label: "GPT-4o Mini (سريع · افتراضي)", tier: "fast" },
  { id: "gpt-4o", label: "GPT-4o", tier: "premium" },
  { id: "gpt-4.1", label: "GPT-4.1", tier: "premium" },
  { id: "gpt-4.1-mini", label: "GPT-4.1 Mini", tier: "fast" },
  { id: "gpt-4.1-nano", label: "GPT-4.1 Nano (أرخص)", tier: "fast" },
  { id: "o4-mini", label: "o4-mini (تفكير عميق)", tier: "premium" },
] as const;

export const DEFAULT_MODEL = "gpt-4o-mini";

export type AIModelId = (typeof AI_MODELS)[number]["id"];
