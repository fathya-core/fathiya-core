// FATHIYA CORE — MCP Quality Gate Validator v0
// يمنع أي مخرج يتحول إلى أمر تداول مباشر

import type { QualityGateResult, SignalCard, KnowledgeCard } from "../types.ts";
import { MCP_CONFIG } from "../config.ts";

// ─── Forbidden Trading Phrases ──────────────────────────────────────────────
const FORBIDDEN_TRADING_PHRASES = [
  "buy",
  "sell",
  "enter",
  "exit",
  "long",
  "short",
  "leverage",
  "target price",
  "stop loss",
  "اشتري",
  "بع",
  "ادخل",
  "اخرج",
  "ضارب الآن",
  "افتح صفقة",
  "هدف سعري قطعي",
  "go long",
  "go short",
  "take profit",
  "stop loss target",
];

// ─── Required Fields per Card Type ──────────────────────────────────────────
const SIGNAL_CARD_REQUIRED = [
  "id",
  "timestamp",
  "source",
  "asset",
  "sector",
  "signal_direction",
  "impact_score",
  "confidence_score",
  "what_changed",
  "invalidation_conditions",
  "hidden_risk",
];

const KNOWLEDGE_CARD_REQUIRED = [
  "id",
  "type",
  "title",
  "source",
  "category",
  "summary",
  "core_idea",
  "why_it_matters",
  "confidence",
  "status",
];

// ─── Main Quality Gate ───────────────────────────────────────────────────────
export function runQualityGate(content: string): QualityGateResult {
  const warnings: string[] = [];
  const unsafe_content: string[] = [];
  const missing_fields: string[] = [];

  // 1. Check for forbidden trading phrases
  for (const phrase of FORBIDDEN_TRADING_PHRASES) {
    if (content.toLowerCase().includes(phrase.toLowerCase())) {
      unsafe_content.push(`Forbidden phrase detected: "${phrase}"`);
    }
  }

  // 2. Check for regex patterns from config
  for (const pattern of MCP_CONFIG.forbidden_output_patterns) {
    if (pattern.test(content)) {
      unsafe_content.push(`Forbidden pattern matched: ${pattern.toString()}`);
    }
  }

  // 3. Check content length
  if (content.length > MCP_CONFIG.max_content_length) {
    warnings.push(`Content exceeds max length (${MCP_CONFIG.max_content_length} chars)`);
  }

  // 4. Check for empty content
  if (!content || content.trim().length === 0) {
    missing_fields.push("content is empty");
  }

  const passed = unsafe_content.length === 0 && missing_fields.length === 0;
  const needs_human_review = warnings.length > 0 || unsafe_content.length > 0;

  const result: QualityGateResult = {
    passed,
    warnings,
    missing_fields,
    unsafe_content,
    needs_human_review,
    confidence: passed ? 0.9 : 0.1,
  };

  if (!passed && unsafe_content.length > 0) {
    result.blocked_reason = "المخرج تحوّل إلى قرار تداول مباشر. تمت إعادته إلى تحليل سيناريوهات.";
  }

  return result;
}

// ─── Signal Card Validator ───────────────────────────────────────────────────
export function validateSignalCard(card: Partial<SignalCard>): QualityGateResult {
  const missing_fields: string[] = [];
  const warnings: string[] = [];
  const unsafe_content: string[] = [];

  // Check required fields
  for (const field of SIGNAL_CARD_REQUIRED) {
    if (!(field in card) || card[field as keyof SignalCard] === undefined) {
      missing_fields.push(field);
    }
  }

  // Validate signal_direction is not a trading command
  const validDirections = ["supportive", "negative", "mixed", "unclear", "noise"];
  if (card.signal_direction && !validDirections.includes(card.signal_direction)) {
    unsafe_content.push(
      `Invalid signal_direction: "${card.signal_direction}". Must be one of: ${validDirections.join(", ")}`,
    );
  }

  // Validate scores
  if (card.impact_score !== undefined && (card.impact_score < 0 || card.impact_score > 10)) {
    warnings.push("impact_score must be between 0 and 10");
  }
  if (
    card.confidence_score !== undefined &&
    (card.confidence_score < 0 || card.confidence_score > 1)
  ) {
    warnings.push("confidence_score must be between 0 and 1");
  }

  // Run content quality gate on text fields
  const textContent = [
    card.what_changed,
    card.bullish_scenario,
    card.bearish_scenario,
    card.decision_boundary,
  ]
    .filter(Boolean)
    .join(" ");

  if (textContent) {
    const contentGate = runQualityGate(textContent);
    unsafe_content.push(...contentGate.unsafe_content);
    warnings.push(...contentGate.warnings);
  }

  const passed = unsafe_content.length === 0 && missing_fields.length === 0;

  return {
    passed,
    warnings,
    missing_fields,
    unsafe_content,
    needs_human_review: !passed || warnings.length > 0,
    confidence: passed ? 0.85 : 0.2,
    blocked_reason: !passed ? "Signal Card failed quality gate validation." : undefined,
  };
}

// ─── Knowledge Card Validator ────────────────────────────────────────────────
export function validateKnowledgeCard(card: Partial<KnowledgeCard>): QualityGateResult {
  const missing_fields: string[] = [];
  const warnings: string[] = [];
  const unsafe_content: string[] = [];

  for (const field of KNOWLEDGE_CARD_REQUIRED) {
    if (!(field in card) || card[field as keyof KnowledgeCard] === undefined) {
      missing_fields.push(field);
    }
  }

  if (card.confidence !== undefined && (card.confidence < 0 || card.confidence > 1)) {
    warnings.push("confidence must be between 0 and 1");
  }

  const passed = unsafe_content.length === 0 && missing_fields.length === 0;

  return {
    passed,
    warnings,
    missing_fields,
    unsafe_content,
    needs_human_review: !passed,
    confidence: passed ? 0.9 : 0.3,
  };
}
