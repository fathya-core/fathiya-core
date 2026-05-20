// FATHIYA CORE — OpenRouter Provider Contract v0
// يقرأ env vars بالاسم فقط — لا secret values هنا
// يدعم multi-model — كل model له دور محدد

// ─── Env Contract ───────────────────────────────────────────────────────────────
// Required env vars (set in .env / deployment secrets):
//   VITE_OPENROUTER_API_KEY           — your OpenRouter API key
//   VITE_OPENROUTER_BASE_URL          — default: https://openrouter.ai/api/v1
//   VITE_OPENROUTER_DEFAULT_MODEL     — fallback model
//   VITE_OPENROUTER_FAST_MODEL        — fast / formatting / small transforms
//   VITE_OPENROUTER_REASONING_MODEL   — reasoning / planning / complex analysis
//   VITE_OPENROUTER_CRITIC_MODEL      — critique / failure modes / risk review
//   VITE_OPENROUTER_STRUCTURED_MODEL  — JSON / schema / extraction

export const OPENROUTER_ENV = {
  API_KEY: "VITE_OPENROUTER_API_KEY",
  BASE_URL: "VITE_OPENROUTER_BASE_URL",
  DEFAULT_MODEL: "VITE_OPENROUTER_DEFAULT_MODEL",
  FAST_MODEL: "VITE_OPENROUTER_FAST_MODEL",
  REASONING_MODEL: "VITE_OPENROUTER_REASONING_MODEL",
  CRITIC_MODEL: "VITE_OPENROUTER_CRITIC_MODEL",
  STRUCTURED_MODEL: "VITE_OPENROUTER_STRUCTURED_MODEL",
} as const;

// ─── Types ───────────────────────────────────────────────────────────────────
export type ModelSlot = "default" | "fast" | "reasoning" | "critic" | "structured";

export interface OpenRouterMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface OpenRouterRequest {
  model: string;
  messages: OpenRouterMessage[];
  temperature?: number;
  max_tokens?: number;
  response_format?: { type: "json_object" | "text" };
}

export interface OpenRouterResponse {
  success: boolean;
  model_used: string;
  model_slot: ModelSlot;
  content: string;
  usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
  error?: string;
  receipt_id?: string;
}

// ─── Resolve model from env ──────────────────────────────────────────────────────
export function resolveModel(slot: ModelSlot): string {
  const env = import.meta.env;
  const slotMap: Record<ModelSlot, string> = {
    default: (env[OPENROUTER_ENV.DEFAULT_MODEL] as string) ?? "openai/gpt-4o-mini",
    fast: (env[OPENROUTER_ENV.FAST_MODEL] as string) ?? "openai/gpt-4o-mini",
    reasoning: (env[OPENROUTER_ENV.REASONING_MODEL] as string) ?? "openai/o3-mini",
    critic: (env[OPENROUTER_ENV.CRITIC_MODEL] as string) ?? "anthropic/claude-3-5-sonnet",
    structured: (env[OPENROUTER_ENV.STRUCTURED_MODEL] as string) ?? "openai/gpt-4o-mini",
  };
  return slotMap[slot];
}

// ─── Core call ─────────────────────────────────────────────────────────────────
export async function callOpenRouter(
  slot: ModelSlot,
  messages: OpenRouterMessage[],
  opts?: {
    temperature?: number;
    max_tokens?: number;
    json_mode?: boolean;
  },
): Promise<OpenRouterResponse> {
  const env = import.meta.env;
  const apiKey = env[OPENROUTER_ENV.API_KEY] as string | undefined;
  const baseUrl =
    (env[OPENROUTER_ENV.BASE_URL] as string | undefined) ?? "https://openrouter.ai/api/v1";
  const model = resolveModel(slot);

  const receiptId = `OR-${slot.toUpperCase()}-${Date.now().toString(36).toUpperCase()}`;

  if (!apiKey) {
    return {
      success: false,
      model_used: model,
      model_slot: slot,
      content: "",
      error: `Missing env var: ${OPENROUTER_ENV.API_KEY}`,
      receipt_id: receiptId,
    };
  }

  const body: OpenRouterRequest = {
    model,
    messages,
    temperature: opts?.temperature ?? 0.3,
    max_tokens: opts?.max_tokens ?? 2048,
    ...(opts?.json_mode ? { response_format: { type: "json_object" as const } } : {}),
  };

  try {
    const res = await fetch(`${baseUrl}/chat/completions`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://fathya-core.com",
        "X-Title": "FATHIYA CORE MCP",
      },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      const errText = await res.text();
      return {
        success: false,
        model_used: model,
        model_slot: slot,
        content: "",
        error: `OpenRouter HTTP ${res.status}: ${errText.slice(0, 200)}`,
        receipt_id: receiptId,
      };
    }

    const json = (await res.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
      usage?: { prompt_tokens: number; completion_tokens: number; total_tokens: number };
    };

    const content = json.choices?.[0]?.message?.content ?? "";

    return {
      success: true,
      model_used: model,
      model_slot: slot,
      content,
      usage: json.usage,
      receipt_id: receiptId,
    };
  } catch (err) {
    return {
      success: false,
      model_used: model,
      model_slot: slot,
      content: "",
      error: `OpenRouter fetch error: ${String(err)}`,
      receipt_id: receiptId,
    };
  }
}
