import { createClient } from "@supabase/supabase-js";
import { supabaseAdmin } from "@/integrations/supabase/client.server";
import type { AgentRiskClass, AgentTask, AgentTaskDetail, CreateAgentTaskBody } from "./contracts";

const STALLED_AFTER_MS = 2 * 60 * 1000;

type AuthenticatedUser = {
  id: string;
  email: string | null;
};

function getBearerToken(request: Request): string {
  const authHeader = request.headers.get("authorization");
  if (!authHeader?.startsWith("Bearer ")) {
    throw new Response("Unauthorized", { status: 401 });
  }

  const token = authHeader.slice("Bearer ".length).trim();
  if (!token) throw new Response("Unauthorized", { status: 401 });
  return token;
}

export async function requireAgentUser(request: Request): Promise<AuthenticatedUser> {
  const supabaseUrl = process.env.SUPABASE_URL;
  const publishableKey = process.env.SUPABASE_PUBLISHABLE_KEY;
  if (!supabaseUrl || !publishableKey) {
    throw new Response("Agent authentication is not configured", { status: 503 });
  }

  const token = getBearerToken(request);
  const client = createClient(supabaseUrl, publishableKey, {
    global: { headers: { Authorization: `Bearer ${token}` } },
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await client.auth.getUser(token);
  if (error || !data.user) throw new Response("Unauthorized", { status: 401 });

  return { id: data.user.id, email: data.user.email ?? null };
}

export function classifyAgentRisk(prompt: string): {
  riskClass: AgentRiskClass;
  requiresApproval: boolean;
} {
  const value = prompt.toLowerCase();

  if (/(delete|remove|drop|wipe|format|حذف|مسح|تهيئة)/i.test(value)) {
    return { riskClass: "destructive", requiresApproval: true };
  }
  if (/(trade|buy|sell|order|portfolio|wallet|تحويل|شراء|بيع|صفقة|محفظة)/i.test(value)) {
    return { riskClass: "financial", requiresApproval: true };
  }
  if (/(scan|exploit|pentest|nmap|nuclei|فحص حي|اختبار اختراق|استغلال)/i.test(value)) {
    return { riskClass: "live_security", requiresApproval: true };
  }
  if (/(send|publish|deploy|email|webhook|نشر|إرسال|بريد)/i.test(value)) {
    return { riskClass: "external", requiresApproval: true };
  }
  return { riskClass: "internal_owned", requiresApproval: false };
}

export function taskTitle(body: CreateAgentTaskBody): string {
  if (body.title?.trim()) return body.title.trim().slice(0, 120);
  return body.prompt.trim().replace(/\s+/g, " ").slice(0, 80);
}

export async function createAgentTask(
  userId: string,
  body: CreateAgentTaskBody,
): Promise<AgentTask> {
  const prompt = body.prompt?.trim();
  if (!prompt || prompt.length < 3) {
    throw new Response("Prompt must contain at least 3 characters", { status: 400 });
  }
  if (prompt.length > 20_000) {
    throw new Response("Prompt exceeds 20,000 characters", { status: 400 });
  }

  const { riskClass, requiresApproval } = classifyAgentRisk(prompt);
  const status = requiresApproval ? "awaiting_approval" : "queued";
  const approvalState = requiresApproval ? "pending" : "not_required";

  const { data, error } = await supabaseAdmin
    .from("agent_tasks")
    .insert({
      user_id: userId,
      title: taskTitle(body),
      prompt,
      status,
      progress: 0,
      current_step: requiresApproval ? "بانتظار موافقة المشغل" : "بانتظار المشغّل المحلي",
      risk_class: riskClass,
      requires_approval: requiresApproval,
      approval_state: approvalState,
    })
    .select("*")
    .single();
  if (error) throw new Response(error.message, { status: 500 });

  await supabaseAdmin.from("agent_task_events").insert({
    task_id: data.id,
    user_id: userId,
    event_type: requiresApproval ? "approval_required" : "queued",
    status,
    step: data.current_step,
    message: requiresApproval
      ? `صُنفت المهمة ${riskClass} وتحتاج موافقة قبل التنفيذ.`
      : "تم إنشاء المهمة وإرسالها إلى المشغّل المحلي.",
    progress: 0,
    payload: { risk_class: riskClass },
  });

  return data as AgentTask;
}

export async function listAgentTasks(userId: string): Promise<AgentTask[]> {
  const { data, error } = await supabaseAdmin
    .from("agent_tasks")
    .select("*")
    .eq("user_id", userId)
    .order("created_at", { ascending: false })
    .limit(50);
  if (error) throw new Response(error.message, { status: 500 });
  return (data ?? []).map((task) => effectiveTask(task as AgentTask));
}

export async function getAgentTaskDetail(userId: string, taskId: string): Promise<AgentTaskDetail> {
  const { data: task, error } = await supabaseAdmin
    .from("agent_tasks")
    .select("*")
    .eq("id", taskId)
    .eq("user_id", userId)
    .maybeSingle();
  if (error) throw new Response(error.message, { status: 500 });
  if (!task) throw new Response("Task not found", { status: 404 });

  const normalized = effectiveTask(task as AgentTask);
  if (normalized.status === "stalled" && task.status === "running") {
    await markTaskStalled(userId, taskId);
  }

  const [{ data: events, error: eventsError }, { data: receipts, error: receiptsError }] =
    await Promise.all([
      supabaseAdmin
        .from("agent_task_events")
        .select("*")
        .eq("task_id", taskId)
        .eq("user_id", userId)
        .order("created_at", { ascending: true }),
      supabaseAdmin
        .from("agent_receipts")
        .select("*")
        .eq("task_id", taskId)
        .eq("user_id", userId)
        .order("created_at", { ascending: false }),
    ]);

  if (eventsError) throw new Response(eventsError.message, { status: 500 });
  if (receiptsError) throw new Response(receiptsError.message, { status: 500 });

  return {
    task: normalized,
    events: events ?? [],
    receipts: receipts ?? [],
  } as AgentTaskDetail;
}

export async function approveAgentTask(userId: string, taskId: string): Promise<AgentTask> {
  const { data, error } = await supabaseAdmin
    .from("agent_tasks")
    .update({
      status: "queued",
      approval_state: "approved",
      current_step: "تمت الموافقة، بانتظار المشغّل المحلي",
      error_message: null,
    })
    .eq("id", taskId)
    .eq("user_id", userId)
    .eq("status", "awaiting_approval")
    .select("*")
    .maybeSingle();
  if (error) throw new Response(error.message, { status: 500 });
  if (!data) throw new Response("Task is not awaiting approval", { status: 409 });

  await supabaseAdmin.from("agent_task_events").insert({
    task_id: taskId,
    user_id: userId,
    event_type: "approved",
    status: "queued",
    step: data.current_step,
    message: "وافق المشغل على تنفيذ المهمة.",
    progress: data.progress,
  });
  return data as AgentTask;
}

export async function cancelAgentTask(userId: string, taskId: string): Promise<AgentTask> {
  const { data, error } = await supabaseAdmin
    .from("agent_tasks")
    .update({
      status: "canceled",
      current_step: "ألغيت بواسطة المشغل",
      completed_at: new Date().toISOString(),
    })
    .eq("id", taskId)
    .eq("user_id", userId)
    .in("status", ["queued", "running", "awaiting_approval", "stalled"])
    .select("*")
    .maybeSingle();
  if (error) throw new Response(error.message, { status: 500 });
  if (!data) throw new Response("Task cannot be canceled", { status: 409 });

  await supabaseAdmin.from("agent_task_events").insert({
    task_id: taskId,
    user_id: userId,
    event_type: "canceled",
    status: "canceled",
    step: data.current_step,
    message: "ألغى المشغل المهمة.",
    progress: data.progress,
  });
  return data as AgentTask;
}

function effectiveTask(task: AgentTask): AgentTask {
  if (task.status !== "running" || !task.last_heartbeat_at) return task;
  const heartbeatAge = Date.now() - new Date(task.last_heartbeat_at).getTime();
  if (heartbeatAge <= STALLED_AFTER_MS) return task;
  return {
    ...task,
    status: "stalled",
    current_step: "لم يصل heartbeat من المشغّل خلال دقيقتين",
  };
}

async function markTaskStalled(userId: string, taskId: string) {
  const { data } = await supabaseAdmin
    .from("agent_tasks")
    .update({
      status: "stalled",
      current_step: "لم يصل heartbeat من المشغّل خلال دقيقتين",
    })
    .eq("id", taskId)
    .eq("user_id", userId)
    .eq("status", "running")
    .select("id")
    .maybeSingle();

  if (!data) return;

  await supabaseAdmin.from("agent_task_events").insert({
    task_id: taskId,
    user_id: userId,
    event_type: "stalled",
    status: "stalled",
    step: "heartbeat_timeout",
    message: "توقفت تحديثات المشغّل لأكثر من دقيقتين.",
  });
}
