// FATHIYA CORE — MCP Tools v0
// كل tool يقرأ من knowledge/ مباشرة — بدون Supabase
// الكتابة تتم عبر GitHub API (Zapier يستدعيها)

// ─── Types ───────────────────────────────────────────────────────────────────

export interface MCPToolResult {
  success: boolean;
  tool: string;
  timestamp: string;
  data?: unknown;
  error?: string;
  quality_gate_passed?: boolean;
  quality_warnings?: string[];
  requires_approval?: boolean;
  receipt_id?: string;
}

export interface MCPRequest {
  tool: string;
  params?: Record<string, unknown>;
  zapier_source?: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function makeReceiptId(tool: string): string {
  const ts = Date.now().toString(36).toUpperCase();
  const rand = Math.random().toString(36).slice(2, 5).toUpperCase();
  const slug = tool
    .replace(/[^a-z0-9]/gi, "")
    .slice(0, 6)
    .toUpperCase();
  return `MCP-${slug}-${ts}-${rand}`;
}

function ok(
  tool: string,
  data: unknown,
  opts?: {
    quality_warnings?: string[];
    requires_approval?: boolean;
    quality_gate_passed?: boolean;
  },
): MCPToolResult {
  return {
    success: true,
    tool,
    timestamp: new Date().toISOString(),
    data,
    quality_gate_passed: opts?.quality_gate_passed ?? true,
    quality_warnings: opts?.quality_warnings ?? [],
    requires_approval: opts?.requires_approval ?? false,
    receipt_id: makeReceiptId(tool),
  };
}

function fail(tool: string, error: string): MCPToolResult {
  return {
    success: false,
    tool,
    timestamp: new Date().toISOString(),
    error,
    quality_gate_passed: false,
    receipt_id: makeReceiptId(tool),
  };
}

function blocked(tool: string, reason: string): MCPToolResult {
  return {
    success: false,
    tool,
    timestamp: new Date().toISOString(),
    error: `Quality Gate Blocked: ${reason}`,
    quality_gate_passed: false,
    requires_approval: true,
    receipt_id: makeReceiptId(tool),
  };
}

// ─── Quality Gate ─────────────────────────────────────────────────────────────
const FORBIDDEN = [
  /\bbuy\b/i,
  /\bsell\b/i,
  /\benter\b/i,
  /\bexit\b/i,
  /\blong\b/i,
  /\bshort\b/i,
  /\u0627\u0634\u062a\u0631\u064a/,
  /\u0628\u0639/,
  /\u0627\u062f\u062e\u0644/,
  /\u0627\u062e\u0631\u062c/,
  /\u0636\u0627\u0631\u0628 \u0627\u0644\u0622\u0646/,
  /\u0627\u0641\u062a\u062d \u0635\u0641\u0642\u0629/,
  /\u0647\u062f\u0641 \u0633\u0639\u0631\u064a \u0642\u0637\u0639\u064a/,
];

export function qualityGate(text: string): { passed: boolean; reason?: string } {
  for (const pattern of FORBIDDEN) {
    if (pattern.test(text)) {
      return {
        passed: false,
        reason: `Output became a direct trading command. Returned to scenario analysis. (matched: ${pattern})`,
      };
    }
  }
  return { passed: true };
}

// ─── Tool: ping ───────────────────────────────────────────────────────────────
export function tool_ping(): MCPToolResult {
  return ok("ping", {
    status: "alive",
    server: "fathiya-core-mcp",
    version: "0.1.0",
    message: "FATHIYA MCP Server is running.",
  });
}

// ─── Tool: knowledge_get_awareness_state ─────────────────────────────────────
export function tool_knowledge_get_awareness_state(awarenessState: unknown): MCPToolResult {
  if (!awarenessState) {
    return fail("knowledge_get_awareness_state", "Awareness state not loaded.");
  }
  return ok("knowledge_get_awareness_state", awarenessState);
}

// ─── Tool: knowledge_search ───────────────────────────────────────────────────
export function tool_knowledge_search(
  index: {
    cards?: Array<{
      id: string;
      title: string;
      category: string;
      tags: string[];
      summary: string;
      type: string;
    }>;
  },
  params: { query?: string; category?: string; type?: string; limit?: number },
): MCPToolResult {
  const query = (params.query ?? "").toLowerCase().trim();
  const limit = Math.min(params.limit ?? 5, 10);

  if (!query) return fail("knowledge_search", "query param is required.");

  const cards = index.cards ?? [];
  const results = cards
    .filter((c) => {
      const matchQ =
        c.title?.toLowerCase().includes(query) ||
        c.summary?.toLowerCase().includes(query) ||
        c.tags?.some((t: string) => t.toLowerCase().includes(query));
      const matchCat = !params.category || c.category === params.category;
      const matchType = !params.type || c.type === params.type;
      return matchQ && matchCat && matchType;
    })
    .slice(0, limit);

  return ok("knowledge_search", { query, total: results.length, results });
}

// ─── Tool: knowledge_list_cards ───────────────────────────────────────────────
export function tool_knowledge_list_cards(
  index: { cards?: Array<Record<string, unknown>> },
  params: { category?: string; type?: string; status?: string; limit?: number },
): MCPToolResult {
  const limit = Math.min(params.limit ?? 10, 10);
  const cards = index.cards ?? [];
  const results = cards
    .filter((c) => {
      const matchCat = !params.category || c["category"] === params.category;
      const matchType = !params.type || c["type"] === params.type;
      const matchStatus = !params.status || c["status"] === params.status;
      return matchCat && matchType && matchStatus;
    })
    .slice(0, limit);
  return ok("knowledge_list_cards", { total: results.length, results });
}

// ─── Tool: intake_submit_raw ──────────────────────────────────────────────────
// يستقبل محتوى خام من Zapier — الكتابة الفعلية عبر Zapier GitHub action
export function tool_intake_submit_raw(params: {
  content?: string;
  source?: string;
  category?: string;
}): MCPToolResult {
  const content = (params.content ?? "").trim();
  const source = params.source ?? "zapier";

  if (!content) return fail("intake_submit_raw", "content param is required.");
  if (content.length > 50_000)
    return fail("intake_submit_raw", "content exceeds 50,000 chars limit.");

  const gate = qualityGate(content);
  if (!gate.passed) return blocked("intake_submit_raw", gate.reason!);

  const id = `raw-${Date.now().toString(36)}`;
  const date = new Date().toISOString().slice(0, 10);

  return ok(
    "intake_submit_raw",
    {
      id,
      source,
      category: params.category ?? "uncategorized",
      date,
      char_count: content.length,
      suggested_path: `knowledge/raw/${date}/${source}/${id}.md`,
      status: "pending_write",
      note: "Content accepted. Use Zapier GitHub action to write to knowledge/raw/.",
    },
    { requires_approval: true },
  );
}

// ─── Tool: crypto_create_signal_card ─────────────────────────────────────────
export function tool_crypto_create_signal_card(params: {
  source?: string;
  asset?: string;
  sector?: string;
  what_changed?: string;
  signal_direction?: string;
  impact_score?: number;
  confidence_score?: number;
  hidden_risk?: string;
  invalidation_conditions?: string[];
  bullish_scenario?: string;
  bearish_scenario?: string;
}): MCPToolResult {
  const required = ["source", "asset", "sector", "what_changed", "signal_direction", "hidden_risk"];
  const missing = required.filter((f) => !params[f as keyof typeof params]);
  if (missing.length > 0) {
    return fail("crypto_create_signal_card", `Missing required fields: ${missing.join(", ")}`);
  }

  const validDirections = ["supportive", "negative", "mixed", "unclear", "noise"];
  if (!validDirections.includes(params.signal_direction!)) {
    return blocked(
      "crypto_create_signal_card",
      `signal_direction must be one of: ${validDirections.join(", ")}. Got: "${params.signal_direction}"`,
    );
  }

  const textToCheck = [params.what_changed, params.bullish_scenario, params.bearish_scenario]
    .filter(Boolean)
    .join(" ");
  const gate = qualityGate(textToCheck);
  if (!gate.passed) return blocked("crypto_create_signal_card", gate.reason!);

  const id = `signal-${Date.now().toString(36)}`;
  const card = {
    id,
    timestamp: new Date().toISOString(),
    source: params.source,
    asset: params.asset,
    sector: params.sector,
    signal_direction: params.signal_direction,
    impact_score: params.impact_score ?? 5,
    confidence_score: params.confidence_score ?? 0.5,
    what_changed: params.what_changed,
    what_did_not_change: "",
    bullish_scenario: params.bullish_scenario ?? "",
    bearish_scenario: params.bearish_scenario ?? "",
    invalidation_conditions: params.invalidation_conditions ?? [],
    hidden_risk: params.hidden_risk,
    bias_traps: [],
    next_data_needed: [],
    decision_boundary: "",
    status: "draft",
  };

  return ok(
    "crypto_create_signal_card",
    {
      card,
      suggested_path: `knowledge/crypto/signal-cards/${id}.json`,
      note: "Signal Card draft created. Use Zapier GitHub action to write to knowledge/crypto/signal-cards/.",
    },
    { requires_approval: true },
  );
}

// ─── Tool: queue_get_pending ──────────────────────────────────────────────────
export function tool_queue_get_pending(runtimeQueue: {
  items?: Array<Record<string, unknown>>;
}): MCPToolResult {
  const items = (runtimeQueue.items ?? []).filter((i) => i["status"] === "pending");
  return ok("queue_get_pending", { total: items.length, items });
}

// ─── Tool: quality_gate_check ─────────────────────────────────────────────────
export function tool_quality_gate_check(params: { text?: string }): MCPToolResult {
  const text = (params.text ?? "").trim();
  if (!text) return fail("quality_gate_check", "text param is required.");
  const gate = qualityGate(text);
  return ok("quality_gate_check", {
    passed: gate.passed,
    reason: gate.reason ?? null,
    text_length: text.length,
  });
}

// ─── Tool Registry ────────────────────────────────────────────────────────────
export const TOOL_REGISTRY: Record<
  string,
  {
    description: string;
    read_only: boolean;
    requires_approval: boolean;
  }
> = {
  ping: {
    description: "Check if MCP server is alive.",
    read_only: true,
    requires_approval: false,
  },
  knowledge_get_awareness_state: {
    description: "Get current FATHIYA awareness state from knowledge/FATHIYA_AWARENESS_STATE.json.",
    read_only: true,
    requires_approval: false,
  },
  knowledge_search: {
    description: "Search knowledge vault by query, category, or type.",
    read_only: true,
    requires_approval: false,
  },
  knowledge_list_cards: {
    description: "List knowledge cards filtered by category, type, or status.",
    read_only: true,
    requires_approval: false,
  },
  intake_submit_raw: {
    description:
      "Submit raw content for intake. Returns receipt + suggested path. Write via Zapier GitHub action.",
    read_only: false,
    requires_approval: true,
  },
  crypto_create_signal_card: {
    description:
      "Create a crypto Signal Card draft. Passes Quality Gate. No trading commands allowed.",
    read_only: false,
    requires_approval: true,
  },
  queue_get_pending: {
    description: "Get pending items from runtime queue.",
    read_only: true,
    requires_approval: false,
  },
  quality_gate_check: {
    description: "Run Quality Gate on any text. Returns pass/fail.",
    read_only: true,
    requires_approval: false,
  },
};
