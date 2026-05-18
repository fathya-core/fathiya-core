// FATHIYA CORE — MCP SDK Types v0

export interface MCPToolResult<T = unknown> {
  success: boolean;
  tool: string;
  timestamp: string;
  data?: T;
  error?: string;
  quality_gate_passed?: boolean;
  quality_warnings?: string[];
  requires_approval?: boolean;
  receipt_id?: string;
}

export type KnowledgeCardType =
  | "article"
  | "tool"
  | "skill"
  | "signal"
  | "risk"
  | "playbook"
  | "target"
  | "report"
  | "decision"
  | "workflow"
  | "narrative";

export type CardStatus = "draft" | "review" | "approved" | "archived" | "rejected";

export type SignalDirection = "supportive" | "negative" | "mixed" | "unclear" | "noise";

export type CryptoSector =
  | "Macro"
  | "Bitcoin"
  | "Ethereum"
  | "Solana"
  | "AI tokens"
  | "DeFi"
  | "RWA"
  | "Memecoins"
  | "Stablecoins"
  | "Regulation"
  | "Exchange Risk"
  | "Security / Exploit"
  | "On-chain Flow"
  | "Sentiment"
  | "Noise";

export interface KnowledgeCard {
  id: string;
  type: KnowledgeCardType;
  title: string;
  source: string;
  url?: string;
  created_at: string;
  captured_at: string;
  category: string;
  tags: string[];
  summary: string;
  core_idea: string;
  why_it_matters: string;
  actionability: "none" | "low" | "medium" | "high";
  risk_level: "none" | "low" | "medium" | "high" | "critical";
  confidence: number;
  related_tools?: string[];
  related_domains?: string[];
  patterns?: string[];
  safe_takeaways?: string[];
  dangerous_parts_removed?: boolean;
  open_questions?: string[];
  next_actions?: string[];
  linked_cards?: string[];
  status: CardStatus;
}

export interface SignalCard {
  id: string;
  timestamp: string;
  source: string;
  asset: string;
  sector: CryptoSector;
  event_type: string;
  signal_direction: SignalDirection;
  time_horizon: "immediate" | "short" | "medium" | "long";
  impact_score: number;
  confidence_score: number;
  what_changed: string;
  what_did_not_change: string;
  bullish_scenario: string;
  bearish_scenario: string;
  invalidation_conditions: string[];
  hidden_risk: string;
  bias_traps: string[];
  next_data_needed: string[];
  decision_boundary: string;
  status: CardStatus;
}

export interface CoinCard {
  symbol: string;
  name: string;
  sector: CryptoSector;
  chain: string;
  market_role: string;
  main_narrative: string;
  secondary_narratives: string[];
  known_risks: string[];
  liquidity_profile: string;
  volatility_profile: string;
  dependency_map: string[];
  macro_sensitivity: "low" | "medium" | "high";
  security_risks: string[];
  regulatory_risks: string[];
  watch_signals: string[];
  invalidations: string[];
  status: CardStatus;
}

export interface DecisionCard {
  id: string;
  date: string;
  decision: string;
  reason: string;
  alternatives_rejected: string[];
  risk: string;
  owner: string;
  status: "active" | "superseded" | "archived";
  review_date?: string;
}

export interface ToolCard {
  tool: string;
  role: string;
  best_for: string[];
  not_for: string[];
  inputs: string[];
  outputs: string[];
  risk_level: "low" | "medium" | "high";
  requires_approval: boolean;
  adapter_type: string;
  fallback: string;
  status: CardStatus;
}

export interface AwarenessState {
  current_focus: string[];
  active_domains: string[];
  known_tools: string[];
  available_resources: string[];
  active_risks: string[];
  knowledge_gaps: string[];
  top_opportunities: string[];
  blocked_actions: string[];
  next_best_artifacts: string[];
  last_updated: string;
}

export interface QualityGateResult {
  passed: boolean;
  warnings: string[];
  missing_fields: string[];
  unsafe_content: string[];
  needs_human_review: boolean;
  confidence: number;
  blocked_reason?: string;
}

export interface ApprovalQueueItem {
  id: string;
  created_at: string;
  tool_called: string;
  payload: unknown;
  quality_gate_result: QualityGateResult;
  status: "pending" | "approved" | "rejected";
  reviewed_at?: string;
  reviewer_note?: string;
}

export interface IntakeItem {
  id: string;
  raw_content: string;
  source: string;
  submitted_at: string;
  clean_status: "clean" | "partial" | "corrupted" | "duplicate" | "needs_review";
  classified_as?: KnowledgeCardType;
  category?: string;
  tags?: string[];
}

export interface MCPToolDefinition {
  name: string;
  description: string;
  inputSchema: {
    type: "object";
    properties: Record<string, unknown>;
    required?: string[];
  };
}
