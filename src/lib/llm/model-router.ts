// FATHIYA CORE — Model Router v0
// يختار النموذج حسب نوع المهمة — لا يستدعي نموذج مباشرة
// الأدوات تستدعي routeModel(taskClass, payload) فقط

import {
  callOpenRouter,
  type ModelSlot,
  type OpenRouterMessage,
  type OpenRouterResponse,
} from "./openrouter";

// ─── Task Classes ─────────────────────────────────────────────────────────────
export type TaskClass =
  | "formatting" // fast: small text transforms, markdown cleanup
  | "knowledge_search" // fast: keyword matching, tag extraction
  | "intake_classification" // fast: classify raw content into category/type
  | "crypto_analysis" // reasoning: scenario building, narrative analysis
  | "quality_gate" // critic: detect forbidden patterns, bias traps
  | "critic_review" // critic: failure modes, risk review, invalidation
  | "structured_extraction"; // structured: JSON extraction, schema filling

// ─── Task → Model Slot Mapping ────────────────────────────────────────────────────
export const TASK_TO_SLOT: Record<TaskClass, ModelSlot> = {
  formatting: "fast",
  knowledge_search: "fast",
  intake_classification: "fast",
  crypto_analysis: "reasoning",
  quality_gate: "critic",
  critic_review: "critic",
  structured_extraction: "structured",
};

// ─── Route Payload ──────────────────────────────────────────────────────────────
export interface RouteModelPayload {
  task: TaskClass;
  system: string;
  user: string;
  temperature?: number;
  max_tokens?: number;
  json_mode?: boolean;
}

export interface RouteModelResult extends OpenRouterResponse {
  task_class: TaskClass;
  slot_used: ModelSlot;
}

// ─── Main Router ────────────────────────────────────────────────────────────────
export async function routeModel(payload: RouteModelPayload): Promise<RouteModelResult> {
  const slot = TASK_TO_SLOT[payload.task] ?? "default";

  const messages: OpenRouterMessage[] = [
    { role: "system", content: payload.system },
    { role: "user", content: payload.user },
  ];

  const result = await callOpenRouter(slot, messages, {
    temperature: payload.temperature,
    max_tokens: payload.max_tokens,
    json_mode: payload.json_mode,
  });

  return {
    ...result,
    task_class: payload.task,
    slot_used: slot,
  };
}

// ─── System Prompts per Task Class ──────────────────────────────────────────────────
export const TASK_SYSTEM_PROMPTS: Record<TaskClass, string> = {
  formatting: [
    "You are a formatting assistant for FATHIYA CORE.",
    "Clean, structure, and format text. Output only the formatted result.",
    "Do not add analysis, opinions, or trading instructions.",
  ].join(" "),

  knowledge_search: [
    "You are a knowledge retrieval assistant for FATHIYA CORE.",
    "Extract relevant tags, categories, and key concepts from the input.",
    "Output structured JSON only. No trading instructions.",
  ].join(" "),

  intake_classification: [
    "You are an intake classifier for FATHIYA CORE.",
    "Classify the input into: category (crypto/bug-bounty/tools/awareness),",
    "type (article/signal/risk/tool/narrative), and extract tags.",
    "Output JSON only. No trading instructions.",
  ].join(" "),

  crypto_analysis: [
    "You are a crypto intelligence analyst for FATHIYA CORE.",
    "Build scenario analysis ONLY. Output: scenarios, invalidation conditions,",
    "hidden risks, bias traps, next data needed.",
    "FORBIDDEN: buy, sell, enter, exit, long, short, target price, stop loss as instruction.",
    "ALLOWED: supportive / negative / mixed / unclear / noise signal directions only.",
  ].join(" "),

  quality_gate: [
    "You are the Quality Gate for FATHIYA CORE.",
    "Detect if the input contains direct trading commands:",
    "buy, sell, enter, exit, long, short, leverage, target price as instruction, stop loss as instruction.",
    "Also detect: FOMO language, certainty claims, price predictions.",
    "Output JSON: { passed: boolean, violations: string[], warnings: string[] }",
  ].join(" "),

  critic_review: [
    "You are the Critic for FATHIYA CORE.",
    "Review the input for: failure modes, hidden risks, confirmation bias,",
    "survivorship bias, narrative exhaustion, regulatory risk, liquidity risk.",
    "Output: risk_score (0-10), main_risk, hidden_risk, worst_case, invalidations.",
    "No trading instructions.",
  ].join(" "),

  structured_extraction: [
    "You are a structured data extractor for FATHIYA CORE.",
    "Extract data from the input and fill the requested JSON schema.",
    "Output valid JSON only. No extra text. No trading instructions.",
  ].join(" "),
};

// ─── Convenience: route with default system prompt ───────────────────────────────────
export async function routeTask(
  task: TaskClass,
  userContent: string,
  opts?: { temperature?: number; max_tokens?: number; json_mode?: boolean },
): Promise<RouteModelResult> {
  return routeModel({
    task,
    system: TASK_SYSTEM_PROMPTS[task],
    user: userContent,
    ...opts,
  });
}
