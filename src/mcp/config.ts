// FATHIYA CORE — MCP Server Config v0

export const MCP_CONFIG = {
  // Server identity
  server_name: "fathiya-core-mcp",
  server_version: "0.1.0",
  protocol_version: "2024-11-05",

  // Limits
  max_items_per_call: 10,
  max_content_length: 50_000,

  // Quality Gate
  quality_gate_enabled: true,
  quality_gate_strict: true,

  // Approval Queue
  approval_queue_enabled: true,
  auto_approve_read_only: true, // read-only tools skip queue

  // Audit
  audit_enabled: true,
  audit_path: "knowledge/audit",

  // Forbidden output patterns (Crypto Quality Gate)
  forbidden_output_patterns: [
    /\bbuy\b/i,
    /\bsell\b/i,
    /\benter\b/i,
    /\bexit\b/i,
    /\blong\b/i,
    /\bshort\b/i,
    /\u0627شتري\b/,
    /\u0628ع\b/,
    /\u0627دخل\b/,
    /\u0627خرج\b/,
    /ضارب الآن/,
    /افتح صفقة/,
    /هدف سعري قطعي/,
  ],

  // Allowed output patterns (Crypto Quality Gate)
  allowed_signal_directions: ["supportive", "negative", "mixed", "unclear", "noise"],

  // Knowledge paths
  knowledge_base_path: "knowledge",
  cards_path: "knowledge/cards",
  crypto_path: "knowledge/crypto",
  raw_path: "knowledge/raw",
  decisions_path: "knowledge/decisions",
  retrieval_path: "knowledge/retrieval",
  awareness_state_file: "knowledge/FATHIYA_AWARENESS_STATE.json",
} as const;

export type MCPConfig = typeof MCP_CONFIG;
