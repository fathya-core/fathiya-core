// Available models on Lovable AI Gateway
export const AI_MODELS = [
  { id: "google/gemini-3-flash-preview", label: "Gemini 3 Flash (سريع · افتراضي)", tier: "fast" },
  { id: "google/gemini-2.5-flash", label: "Gemini 2.5 Flash", tier: "fast" },
  { id: "google/gemini-2.5-pro", label: "Gemini 2.5 Pro", tier: "premium" },
  { id: "google/gemini-3.1-pro-preview", label: "Gemini 3.1 Pro (preview)", tier: "premium" },
  { id: "openai/gpt-5", label: "GPT-5 (بديل GPT الكامل)", tier: "premium" },
  { id: "openai/gpt-5-mini", label: "GPT-5 Mini", tier: "fast" },
  { id: "openai/gpt-5.2", label: "GPT-5.2 (الأقوى)", tier: "premium" },
] as const;

export const DEFAULT_MODEL = "google/gemini-3-flash-preview";
export const DEFAULT_GPT_MODEL = "openai/gpt-5";

export type AIModelId = (typeof AI_MODELS)[number]["id"];
