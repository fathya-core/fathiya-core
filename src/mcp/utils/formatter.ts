// FATHIYA CORE — MCP Output Formatter v0
// تنسيق مخرجات MCP بشكل موحد

import type { MCPToolResult, KnowledgeCard, SignalCard } from '../types.ts';
import { generateReceiptId } from './logger.ts';

// ─── Build Success Result ────────────────────────────────────────────────────────
export function buildSuccess<T>(
  tool: string,
  data: T,
  options?: {
    quality_gate_passed?: boolean;
    quality_warnings?: string[];
    requires_approval?: boolean;
  }
): MCPToolResult<T> {
  return {
    success: true,
    tool,
    timestamp: new Date().toISOString(),
    data,
    quality_gate_passed: options?.quality_gate_passed ?? true,
    quality_warnings: options?.quality_warnings ?? [],
    requires_approval: options?.requires_approval ?? false,
    receipt_id: generateReceiptId(tool),
  };
}

// ─── Build Error Result ───────────────────────────────────────────────────────────
export function buildError(tool: string, error: string): MCPToolResult<null> {
  return {
    success: false,
    tool,
    timestamp: new Date().toISOString(),
    data: null,
    error,
    quality_gate_passed: false,
    receipt_id: generateReceiptId(tool),
  };
}

// ─── Build Blocked Result (Quality Gate failed) ─────────────────────────────────
export function buildBlocked(tool: string, reason: string): MCPToolResult<null> {
  return {
    success: false,
    tool,
    timestamp: new Date().toISOString(),
    data: null,
    error: `⚠️ Quality Gate Blocked: ${reason}`,
    quality_gate_passed: false,
    requires_approval: true,
    receipt_id: generateReceiptId(tool),
  };
}

// ─── Format Knowledge Card as Markdown ───────────────────────────────────────────
export function formatKnowledgeCardMarkdown(card: KnowledgeCard): string {
  return [
    `# ${card.title}`,
    ``,
    `**ID:** ${card.id}`,
    `**Type:** ${card.type}`,
    `**Category:** ${card.category}`,
    `**Source:** ${card.source}${card.url ? ` — [link](${card.url})` : ''}`,
    `**Status:** ${card.status}`,
    `**Confidence:** ${(card.confidence * 100).toFixed(0)}%`,
    `**Risk Level:** ${card.risk_level}`,
    `**Tags:** ${card.tags.join(', ')}`,
    ``,
    `## Summary`,
    card.summary,
    ``,
    `## Core Idea`,
    card.core_idea,
    ``,
    `## Why It Matters`,
    card.why_it_matters,
    card.open_questions?.length
      ? `\n## Open Questions\n${card.open_questions.map(q => `- ${q}`).join('\n')}`
      : '',
    card.next_actions?.length
      ? `\n## Next Actions\n${card.next_actions.map(a => `- ${a}`).join('\n')}`
      : '',
  ].filter(Boolean).join('\n');
}

// ─── Format Signal Card as Markdown ───────────────────────────────────────────────
export function formatSignalCardMarkdown(card: SignalCard): string {
  return [
    `# Signal Card — ${card.asset} [${card.signal_direction.toUpperCase()}]`,
    ``,
    `**ID:** ${card.id}`,
    `**Timestamp:** ${card.timestamp}`,
    `**Source:** ${card.source}`,
    `**Sector:** ${card.sector}`,
    `**Direction:** ${card.signal_direction}`,
    `**Impact Score:** ${card.impact_score}/10`,
    `**Confidence:** ${(card.confidence_score * 100).toFixed(0)}%`,
    `**Time Horizon:** ${card.time_horizon}`,
    `**Status:** ${card.status}`,
    ``,
    `## What Changed`,
    card.what_changed,
    ``,
    `## What Did NOT Change`,
    card.what_did_not_change,
    ``,
    `## Bullish Scenario`,
    card.bullish_scenario,
    ``,
    `## Bearish Scenario`,
    card.bearish_scenario,
    ``,
    `## Invalidation Conditions`,
    card.invalidation_conditions.map(c => `- ${c}`).join('\n'),
    ``,
    `## Hidden Risk`,
    card.hidden_risk,
    ``,
    `## Bias Traps`,
    card.bias_traps.map(b => `- ${b}`).join('\n'),
    ``,
    `## Next Data Needed`,
    card.next_data_needed.map(d => `- ${d}`).join('\n'),
  ].filter(Boolean).join('\n');
}
