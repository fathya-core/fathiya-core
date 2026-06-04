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
