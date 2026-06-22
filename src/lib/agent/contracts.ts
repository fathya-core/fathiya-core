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
  latest_receipt_id?: string | null;
  latest_receipt_status?: string | null;
  latest_receipt_at?: string | null;
  latest_receipt_summary?: string | null;
  receipt_count?: number;
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

export type AgentKnowledgeIntakeStatus = {
  enabled: boolean;
  running: boolean;
  watch_root: string;
  scan_interval_seconds: number;
  max_report_characters: number;
  supported_extensions: string[];
  tracked_files: number;
  enqueued_count: number;
  ignored_count: number;
  last_scan_at: string | null;
  last_error: string | null;
  last_enqueued: {
    path: string;
    source_name: string;
    sha256: string;
    task_id: string;
    task_status: AgentTaskStatus;
    task_progress?: number;
    task_current_step?: string | null;
    captured_at: string;
  } | null;
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

export type AgentZapierInventoryApp = {
  app: string;
  action_count: number;
  modes: string[];
};

export type AgentProviderActionSet = {
  read?: string[];
  approval_gated_write?: string[];
};

export type AgentZapierCatalogAction = {
  key?: string | null;
  name: string;
  tool_name?: string | null;
  mode: "read" | "write" | string;
  inventory_only?: boolean;
};

export type AgentZapierActionCatalog = {
  available: boolean;
  connected?: boolean;
  provider: string;
  source?: string;
  inventory_available?: boolean;
  live_available?: boolean;
  needs_reconnect?: boolean;
  refresh_recommended?: boolean;
  auth_state?: string | null;
  last_refresh_error?: string | null;
  last_refresh_status_code?: number | null;
  error?: string | null;
  app?: string | null;
  app_count?: number;
  action_count: number;
  apps?: AgentZapierInventoryApp[];
  actions?: AgentZapierCatalogAction[];
};

export type AgentZapierDiagnostics = {
  mode: "zapier_mcp_activation_diagnostics_v1";
  activation_state: "live" | "inventory_only" | "reconnect_required" | "not_connected" | string;
  headline: string;
  connected: boolean;
  direct_execution: boolean;
  expired: boolean;
  refresh_recommended: boolean;
  needs_reconnect: boolean;
  token_source?: string | null;
  refresh_credential_saved: boolean;
  last_refresh_error?: string | null;
  last_refresh_status_code?: number | null;
  last_refresh_at?: number | null;
  endpoint?: string | null;
  inventory_available: boolean;
  hosted_inventory_available?: boolean;
  hosted_execution_state?: "schema_blocked" | "available" | "not_available" | string;
  hosted_execution_issue?: string | null;
  app_count: number;
  action_count: number;
  agent_provider_count: number;
  agent_provider_write_action_count: number;
  agent_providers: AgentMeshProviderSummary[];
  start_path: string;
  start_url: string;
  fresh_start_path?: string | null;
  fresh_start_url?: string | null;
  callback_url: string;
  return_to: string;
  next_actions: {
    id: string;
    title: string;
    action_type: "oauth" | "task" | "settings" | string;
    action_label: string;
    action_path?: string | null;
    prompt?: string | null;
    summary?: string | null;
  }[];
  secret_safe: true;
};

export type AgentConnectedToolInventory = {
  available: boolean;
  captured_at?: string | null;
  zapier_app_count: number;
  zapier_action_count: number;
  zapier_apps: AgentZapierInventoryApp[];
  agent_provider_actions: Record<string, AgentProviderActionSet>;
  direct_zapier_mcp?: {
    connected: boolean;
    direct_execution?: boolean;
    endpoint?: string;
    error?: string | null;
  } | null;
  zapier_mcp_status?: Record<string, Json>;
};

export type AgentIntegrationStatus = "ready" | "partial" | "needs_setup" | "needs_operator";

export type AgentIntegrationReadiness = {
  id: string;
  name: string;
  category: "model" | "control_plane" | "automation" | "financial" | "security" | "engineering";
  status: AgentIntegrationStatus;
  connection_mode: string;
  account_required: boolean;
  credential_policy: "none" | "local_server_only" | "oauth_managed";
  summary: string;
  next_step: string;
  missing_env: string[];
  connected_apps: string[];
  action_path?: string | null;
  action_label?: string | null;
  settings_path?: string | null;
  settings_label?: string | null;
  probe_path?: string | null;
  probe_label?: string | null;
  task_prompt?: string | null;
  task_label?: string | null;
  details: Record<string, Json>;
};

export type AgentIntegrationProbeResult = {
  integration_id: string;
  ok: boolean;
  status: AgentIntegrationStatus | "failed";
  summary: string;
  checked_at: string;
  secret_safe: true;
  action: string;
  details: Record<string, Json>;
};

export type AgentIntegrationSummary = {
  total: number;
  ready: number;
  partial: number;
  needs_setup: number;
  needs_operator: number;
};

export type AgentMeshLane = {
  id: "execution" | "trading" | "bug_bounty" | "knowledge" | "tool_bridge" | string;
  label: string;
  status: AgentIntegrationStatus | "failed" | string;
  signal: string;
  action_label: string;
  prompt: string;
};

export type AgentMeshAttentionItem = {
  id: string;
  name: string;
  status: AgentIntegrationStatus | string;
  summary: string;
  next_step: string;
  action_path?: string | null;
  action_label?: string | null;
};

export type AgentMeshQuickAction = {
  id: string;
  label: string;
  title: string;
  prompt: string;
  mode: string;
};

export type AgentMeshProviderSummary = {
  app: string;
  status: "ready" | "inventory_only" | string;
  execution_mode: "live_zapier_mcp" | "inventory_only_until_oauth" | string;
  inventory_only: boolean;
  read_count: number;
  write_count: number;
  total_actions: number;
  read_actions: string[];
  write_actions: string[];
  action_path?: string | null;
  action_label: string;
  next_step: string;
  task_prompt: string;
};

export type AgentMeshActivationAction = {
  id: string;
  name: string;
  status: AgentIntegrationStatus | string;
  action_type: "oauth" | "settings" | "probe" | string;
  action_tier?: "blocking" | "upgrade" | string;
  blocks_local_execution?: boolean;
  action_label: string;
  action_path?: string | null;
  summary?: string | null;
  next_step?: string | null;
};

export type AgentMeshActivationOverview = {
  mode: "agent_activation_overview_v1";
  executable_now?: boolean;
  ready_headline: string;
  primary_message: string;
  ready_lane_count: number;
  lane_count: number;
  ready_lane_labels: string[];
  safe_tool_count: number;
  capability_ready: number | null;
  capability_total: number | null;
  zapier_app_count: number | null;
  zapier_action_count: number | null;
  agent_provider_count: number;
  agent_provider_ready_count: number;
  agent_provider_write_action_count: number;
  agent_providers: AgentMeshProviderSummary[];
  operator_action_count: number;
  blocking_action_count?: number;
  upgrade_action_count?: number;
  operator_actions: AgentMeshActivationAction[];
  blocking_actions?: AgentMeshActivationAction[];
  upgrade_actions?: AgentMeshActivationAction[];
  default_action: {
    id: string;
    label: string;
    mode: string;
  };
};

export type AgentMeshSummary = {
  mode: "agent_mesh_status_v1";
  captured_at: string;
  ready_to_execute: boolean;
  worker_online: boolean;
  headline: string;
  summary: {
    integration_total: number;
    integration_ready: number;
    integration_attention: number;
    tool_count: number;
    capability_total: number | null;
    capability_ready: number | null;
    zapier_app_count: number | null;
    zapier_action_count: number | null;
    agent_provider_count: number;
    agent_provider_ready_count: number;
    connected_app_count?: number;
    connected_app_ready_count?: number;
    trading_running: boolean;
    knowledge_intake_running: boolean;
  };
  lanes: AgentMeshLane[];
  agent_providers: AgentMeshProviderSummary[];
  zapier_apps?: AgentZapierInventoryApp[];
  attention: AgentMeshAttentionItem[];
  quick_actions: AgentMeshQuickAction[];
  activation_overview?: AgentMeshActivationOverview;
  policy: {
    automatic_internal_execution: boolean;
    local_direct_execution_default?: boolean;
    approval_gated_external_writes: boolean;
    oauth_and_settings_are_followups?: boolean;
    external_impact_gate_does_not_block_internal_progress?: boolean;
    real_money_disabled_until_testnet_configured: boolean;
    live_security_testing_requires_scope_confirmation: boolean;
  };
};

export type AgentCommandCenterCommand = {
  id: string;
  label?: string | null;
  title?: string | null;
  group?: string | null;
  lane?: string | null;
  mode?: string | null;
  status: AgentIntegrationStatus | "ready" | "failed" | string;
  prompt: string;
  source: "quick_action" | "lane" | string;
  ui_action: "task" | string;
};

export type AgentCommandCenterCommandGroup = {
  id: string;
  label: string;
  ready_count: number;
  command_count: number;
  commands: AgentCommandCenterCommand[];
};

export type AgentCommandCenter = {
  mode: "fathiya_command_center_v1";
  captured_at: string;
  secret_safe: true;
  ready_to_execute: boolean;
  headline?: string | null;
  summary: {
    command_count: number;
    ready_command_count: number;
    command_group_count?: number | null;
    operator_queue_count: number;
    integration_ready: number | null;
    integration_total: number | null;
    tool_count: number | null;
    zapier_action_count: number | null;
    agent_provider_count: number | null;
    connected_app_count?: number | null;
    connected_app_ready_count?: number | null;
    trading_running: boolean | null;
    knowledge_intake_running: boolean | null;
  };
  commands: AgentCommandCenterCommand[];
  command_groups?: AgentCommandCenterCommandGroup[];
  operator_queue: AgentMeshActivationAction[];
  lanes: AgentMeshLane[];
  agent_providers: AgentMeshProviderSummary[];
  zapier_apps?: AgentZapierInventoryApp[];
  policy: AgentMeshSummary["policy"];
  powershell: {
    inspect: string;
    run_execute_mesh: string;
    run_agent_os?: string;
    run_trading: string;
    run_bug_bounty_draft: string;
    run_production_site_audit?: string;
  };
};

export type AgentLocalSettingField = {
  name: string;
  label: string;
  kind: "secret" | "url" | "text";
  required: boolean;
  placeholder?: string;
  configured: boolean;
  source: "local_store" | "environment" | "missing";
  clearable: boolean;
};

export type AgentLocalSettingsGroup = {
  id: string;
  name: string;
  description: string;
  restart_required: boolean;
  fields: AgentLocalSettingField[];
  configured_count: number;
};

export type AgentLocalSettingsResponse = {
  groups: AgentLocalSettingsGroup[];
  write_allowed: boolean;
  security: {
    values_returned: boolean;
    allowlisted_fields_only: boolean;
    storage_path: string;
  };
};

export type AgentRuntimeHealth = {
  status: "ok" | string;
  mode: string;
  worker_id: string;
  worker_online: boolean;
  api: string;
  agent_loop: {
    max_rounds: number;
    max_tool_steps_per_round: number;
    local_planning_enabled: boolean;
    local_generation_enabled: boolean;
    local_model: string;
    local_max_new_tokens: number;
    local_max_generation_seconds: number;
    openrouter_configured: boolean;
    openrouter_model: string;
    openrouter_research_model: string;
    openrouter_safety_model: string;
    planning_route: string;
  };
  knowledge_intake: AgentKnowledgeIntakeStatus;
  trading: {
    running: boolean;
    autostart: boolean;
    mode: string;
    symbol: string;
    cycle_target_seconds: number;
    latest_receipt_id: string | null;
  };
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
  strategy_advisory: {
    action: "buy" | "sell" | "hold";
    confidence: number;
    rationale: string;
    provider: string;
    generated_at: string;
    expires_at: string;
    active: boolean;
  } | null;
  strategy_advisory_policy: {
    mode: "veto_only";
    min_confidence: number;
    can_originate_orders: false;
  };
  cycle_count: number;
  last_error: string | null;
  latest_receipt_id: string | null;
  latest_cycle: AgentTradingCycle | null;
  execution_cadence: {
    target_seconds: number;
    target_tolerance_seconds: number;
    sample_count: number;
    latest_interval_seconds: number | null;
    average_interval_seconds: number | null;
    max_interval_seconds: number | null;
    within_target: boolean | null;
  };
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
