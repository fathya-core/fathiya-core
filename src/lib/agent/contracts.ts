import type { Json } from "@/integrations/supabase/types";

export const AGENT_TASK_STATUSES = [
  "queued",
  "running",
  "awaiting_approval",
  "completed",
  "failed",
  "stalled",
  "canceled",
] as const;

export type AgentTaskStatus = (typeof AGENT_TASK_STATUSES)[number];

export const AGENT_RISK_CLASSES = [
  "internal_owned",
  "financial",
  "live_security",
  "destructive",
  "external",
] as const;

export type AgentRiskClass = (typeof AGENT_RISK_CLASSES)[number];
export type AgentApprovalState = "not_required" | "pending" | "approved" | "rejected";

export type AgentTask = {
  id: string;
  user_id: string;
  title: string;
  prompt: string;
  status: AgentTaskStatus;
  progress: number;
  current_step: string | null;
  risk_class: AgentRiskClass;
  requires_approval: boolean;
  approval_state: AgentApprovalState;
  worker_id: string | null;
  plan: Json;
  result: Json | null;
  error_message: string | null;
  last_heartbeat_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type AgentTaskEvent = {
  id: number;
  task_id: string;
  user_id: string;
  event_type: string;
  status: string | null;
  step: string | null;
  message: string;
  progress: number | null;
  payload: Json;
  created_at: string;
};

export type AgentReceipt = {
  id: string;
  receipt_id: string;
  task_id: string;
  user_id: string;
  status: string;
  summary: string;
  evidence: Json;
  created_at: string;
};

export type AgentTaskDetail = {
  task: AgentTask;
  events: AgentTaskEvent[];
  receipts: AgentReceipt[];
};

export type CreateAgentTaskBody = {
  prompt: string;
  title?: string;
};

export type AgentConnectorProfile = {
  name: string;
  provider: string;
  description: string | null;
  method: "GET" | "POST";
  risk_class: AgentRiskClass;
  requires_approval: boolean;
  read_only: boolean;
  bridge_dispatch_allowed: boolean;
  configured: boolean;
  missing_env: string[];
};

export type AgentConnectorBridge = {
  configured: boolean;
  endpoint: string;
  allowed_profile_count: number;
  ready_profile_count: number;
  allowed_profiles: string[];
};

export type AgentTradingCycle = {
  receipt_id: string;
  status: "observed" | "executed";
  mode: "paper";
  tick: {
    symbol: string;
    price: number;
    observed_at: string;
    source: string;
    sequence: number;
  };
  prediction: {
    action: "buy" | "sell" | "hold";
    score: number;
    confidence: number;
    horizon_seconds: number;
    model: string;
    reason: string;
  };
  risk: {
    allowed: boolean;
    action: "buy" | "sell" | "hold";
    order_notional: number;
    reason: string;
  };
  fill: Json | null;
  portfolio: {
    initial_cash: number;
    cash: number;
    quantity: number;
    average_price: number;
    mark_price: number;
    position_notional: number;
    unrealized_pnl: number;
    realized_pnl: number;
    fees_paid: number;
    equity: number;
    net_pnl: number;
    daily_pnl: number;
  };
  latency_ms: number;
  created_at: string;
};

export type AgentTradingStatus = {
  agent: string;
  running: boolean;
  mode: "paper";
  requested_mode: string;
  live_execution_enabled: boolean;
  live_execution_block_reason: string;
  symbol: string;
  cycle_target_seconds: number;
  market_provider: string;
  current_market_source: string | null;
  market_health: {
    provider: string;
    active_source?: string | null;
    fallback_active?: boolean;
    fallback_count?: number;
    last_error?: string | null;
    primary?: {
      provider: string;
      success_count: number;
      failure_count: number;
      last_error: string | null;
    } | null;
  } | null;
  signal_model: string;
  cycle_count: number;
  last_error: string | null;
  latest_receipt_id: string | null;
  latest_cycle: AgentTradingCycle | null;
  portfolio: AgentTradingCycle["portfolio"];
  prediction_quality: {
    evaluated_count: number;
    correct_count: number;
    directional_accuracy: number | null;
    cumulative_strategy_return_bps: number;
    average_strategy_return_bps: number;
    latest_evaluation: {
      receipt_id: string;
      symbol: string;
      model: string;
      action: "buy" | "sell" | "hold";
      entry_price: number;
      exit_price: number;
      realized_return: number;
      strategy_return_bps: number;
      correct: boolean;
      horizon_seconds: number;
      evaluated_at: string;
    } | null;
  };
  risk_limits: {
    max_order_notional: number;
    max_position_notional: number;
    daily_loss_limit: number;
    min_order_notional: number;
    max_tick_age_seconds: number;
    long_only: boolean;
  };
};
