export type Provider = "openrouter" | "huggingface";

export interface AIModel {
  id: string;
  label: string;
  tier: "fast" | "premium" | "free";
  provider: Provider;
}

export const AI_MODELS: readonly AIModel[] = [
  // OpenRouter
  { id: "google/gemini-2.5-flash", label: "Gemini 2.5 Flash (سريع)", tier: "fast", provider: "openrouter" },
  { id: "google/gemini-2.5-pro", label: "Gemini 2.5 Pro", tier: "premium", provider: "openrouter" },
  { id: "meta-llama/llama-4-maverick", label: "Llama 4 Maverick", tier: "fast", provider: "openrouter" },
  { id: "meta-llama/llama-4-scout", label: "Llama 4 Scout", tier: "fast", provider: "openrouter" },
  { id: "deepseek/deepseek-r1", label: "DeepSeek R1 (تفكير عميق)", tier: "premium", provider: "openrouter" },
  { id: "deepseek/deepseek-chat-v3-0324", label: "DeepSeek V3", tier: "fast", provider: "openrouter" },
  { id: "qwen/qwen3-235b-a22b", label: "Qwen3 235B", tier: "premium", provider: "openrouter" },
  { id: "mistralai/mistral-small-3.2-24b-instruct", label: "Mistral Small 3.2", tier: "fast", provider: "openrouter" },
  // Hugging Face
  { id: "Qwen/Qwen2.5-72B-Instruct", label: "Qwen 2.5 72B (HF)", tier: "free", provider: "huggingface" },
  { id: "meta-llama/Llama-3.3-70B-Instruct", label: "Llama 3.3 70B (HF)", tier: "free", provider: "huggingface" },
  { id: "mistralai/Mistral-Small-24B-Instruct-2501", label: "Mistral Small 24B (HF)", tier: "free", provider: "huggingface" },
  { id: "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B", label: "DeepSeek R1 32B (HF)", tier: "free", provider: "huggingface" },
] as const;

export const DEFAULT_MODEL = "google/gemini-2.5-flash";
export const DEFAULT_PROVIDER: Provider = "openrouter";

export function getModelProvider(modelId: string): Provider {
  const m = AI_MODELS.find((m) => m.id === modelId);
  return m?.provider ?? "openrouter";
}

export type AIModelId = (typeof AI_MODELS)[number]["id"];
