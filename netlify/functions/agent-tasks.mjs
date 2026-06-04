const STALLED_AFTER_MS = 2 * 60 * 1000;
const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

class HttpError extends Error {
  constructor(statusCode, message) {
    super(message);
    this.statusCode = statusCode;
  }
}

function response(payload, statusCode = 200) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      "Access-Control-Allow-Headers": "Authorization, Content-Type",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    },
    body: JSON.stringify(payload),
  };
}

function runtimeConfig() {
  const supabaseUrl = process.env.SUPABASE_URL?.replace(/\/+$/, "");
  const publishableKey =
    process.env.SUPABASE_PUBLISHABLE_KEY ?? process.env.VITE_SUPABASE_PUBLISHABLE_KEY;
  const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!supabaseUrl || !publishableKey || !serviceRoleKey) {
    throw new HttpError(503, "Agent task service is not configured");
  }
  return { supabaseUrl, publishableKey, serviceRoleKey };
}

function bearerToken(event) {
  const header = event.headers?.authorization ?? event.headers?.Authorization;
  if (!header?.startsWith("Bearer ")) throw new HttpError(401, "Unauthorized");
  const token = header.slice("Bearer ".length).trim();
  if (!token) throw new HttpError(401, "Unauthorized");
  return token;
}

async function requireUser(event, config) {
  const token = bearerToken(event);
  const authResponse = await fetch(`${config.supabaseUrl}/auth/v1/user`, {
    headers: {
      apikey: config.publishableKey,
      Authorization: `Bearer ${token}`,
    },
  });
  if (!authResponse.ok) throw new HttpError(401, "Unauthorized");
  const user = await authResponse.json();
  if (!user?.id) throw new HttpError(401, "Unauthorized");
  return user;
}

async function supabaseRest(config, method, path, body, prefer) {
  const headers = {
    apikey: config.serviceRoleKey,
    Authorization: `Bearer ${config.serviceRoleKey}`,
    "Content-Type": "application/json",
  };
  if (prefer) headers.Prefer = prefer;

  const result = await fetch(`${config.supabaseUrl}/rest/v1/${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await result.text();
  const payload = text ? JSON.parse(text) : [];
  if (!result.ok) {
    throw new HttpError(502, payload?.message ?? payload?.error ?? "Supabase request failed");
  }
  return payload;
}

function classifyRisk(prompt) {
  if (/(delete|remove|drop|wipe|format|حذف|مسح|تهيئة)/i.test(prompt)) {
    return { riskClass: "destructive", requiresApproval: true };
  }
  if (/(trade|buy|sell|order|portfolio|wallet|تحويل|شراء|بيع|صفقة|محفظة)/i.test(prompt)) {
    return { riskClass: "financial", requiresApproval: true };
  }
  if (/(scan|exploit|pentest|nmap|nuclei|فحص حي|اختبار اختراق|استغلال)/i.test(prompt)) {
    return { riskClass: "live_security", requiresApproval: true };
  }
  if (/(send|publish|deploy|email|webhook|نشر|إرسال|بريد)/i.test(prompt)) {
    return { riskClass: "external", requiresApproval: true };
  }
  return { riskClass: "internal_owned", requiresApproval: false };
}

function parseBody(event) {
  try {
    const source = event.isBase64Encoded
      ? Buffer.from(event.body ?? "", "base64").toString("utf8")
      : event.body;
    return JSON.parse(source || "{}");
  } catch {
    throw new HttpError(400, "Invalid JSON body");
  }
}

function routeSegments(event) {
  const path = event.queryStringParameters?.path ?? "";
  const segments = path
    .split("/")
    .map((part) => decodeURIComponent(part))
    .filter(Boolean);
  if (segments[0] && !UUID_PATTERN.test(segments[0])) {
    throw new HttpError(400, "Invalid task id");
  }
  return segments;
}

function effectiveTask(task) {
  if (task.status !== "running" || !task.last_heartbeat_at) return task;
  const age = Date.now() - new Date(task.last_heartbeat_at).getTime();
  if (age <= STALLED_AFTER_MS) return task;
  return {
    ...task,
    status: "stalled",
    current_step: "لم يصل heartbeat من المشغّل خلال دقيقتين",
  };
}

async function insertEvent(config, event) {
  await supabaseRest(config, "POST", "agent_task_events", event, "return=minimal");
}

async function persistStalled(config, task) {
  const effective = effectiveTask(task);
  if (effective.status !== "stalled" || task.status !== "running") return effective;

  const updated = await supabaseRest(
    config,
    "PATCH",
    `agent_tasks?id=eq.${task.id}&status=eq.running`,
    {
      status: "stalled",
      current_step: effective.current_step,
    },
    "return=representation",
  );
  if (!updated[0]) return effective;

  await insertEvent(config, {
    task_id: task.id,
    user_id: task.user_id,
    event_type: "stalled",
    status: "stalled",
    step: "heartbeat_timeout",
    message: "توقفت تحديثات المشغّل لأكثر من دقيقتين.",
  });
  return updated[0];
}

async function createTask(config, user, event) {
  const body = parseBody(event);
  const prompt = typeof body.prompt === "string" ? body.prompt.trim() : "";
  const requestedTitle = typeof body.title === "string" ? body.title.trim() : "";
  if (prompt.length < 3) throw new HttpError(400, "Prompt must contain at least 3 characters");
  if (prompt.length > 20_000) throw new HttpError(400, "Prompt exceeds 20,000 characters");

  const { riskClass, requiresApproval } = classifyRisk(prompt);
  const status = requiresApproval ? "awaiting_approval" : "queued";
  const currentStep = requiresApproval
    ? "بانتظار موافقة المشغل"
    : "بانتظار المشغّل المحلي";
  const rows = await supabaseRest(
    config,
    "POST",
    "agent_tasks",
    {
      user_id: user.id,
      title: (requestedTitle || prompt.replace(/\s+/g, " ")).slice(0, 120),
      prompt,
      status,
      progress: 0,
      current_step: currentStep,
      risk_class: riskClass,
      requires_approval: requiresApproval,
      approval_state: requiresApproval ? "pending" : "not_required",
    },
    "return=representation",
  );
  const task = rows[0];
  if (!task) throw new HttpError(502, "Supabase did not return the created task");

  await insertEvent(config, {
    task_id: task.id,
    user_id: user.id,
    event_type: requiresApproval ? "approval_required" : "queued",
    status,
    step: currentStep,
    message: requiresApproval
      ? `صُنفت المهمة ${riskClass} وتحتاج موافقة قبل التنفيذ.`
      : "تم إنشاء المهمة وإرسالها إلى المشغّل المحلي.",
    progress: 0,
    payload: { risk_class: riskClass },
  });
  return response({ task }, 201);
}

async function listTasks(config, user) {
  const tasks = await supabaseRest(
    config,
    "GET",
    `agent_tasks?user_id=eq.${user.id}&select=*&order=created_at.desc&limit=50`,
  );
  return response({ tasks: await Promise.all(tasks.map((task) => persistStalled(config, task))) });
}

async function taskDetail(config, user, taskId) {
  const tasks = await supabaseRest(
    config,
    "GET",
    `agent_tasks?id=eq.${taskId}&user_id=eq.${user.id}&select=*&limit=1`,
  );
  if (!tasks[0]) throw new HttpError(404, "Task not found");
  const task = await persistStalled(config, tasks[0]);
  const [events, receipts] = await Promise.all([
    supabaseRest(
      config,
      "GET",
      `agent_task_events?task_id=eq.${taskId}&user_id=eq.${user.id}&select=*&order=created_at.asc`,
    ),
    supabaseRest(
      config,
      "GET",
      `agent_receipts?task_id=eq.${taskId}&user_id=eq.${user.id}&select=*&order=created_at.desc`,
    ),
  ]);
  return response({ task, events, receipts });
}

async function approveTask(config, user, taskId) {
  const rows = await supabaseRest(
    config,
    "PATCH",
    `agent_tasks?id=eq.${taskId}&user_id=eq.${user.id}&status=eq.awaiting_approval`,
    {
      status: "queued",
      approval_state: "approved",
      current_step: "تمت الموافقة، بانتظار المشغّل المحلي",
      error_message: null,
    },
    "return=representation",
  );
  const task = rows[0];
  if (!task) throw new HttpError(409, "Task is not awaiting approval");
  await insertEvent(config, {
    task_id: taskId,
    user_id: user.id,
    event_type: "approved",
    status: "queued",
    step: task.current_step,
    message: "وافق المشغل على تنفيذ المهمة.",
    progress: task.progress,
  });
  return response({ task });
}

async function cancelTask(config, user, taskId) {
  const rows = await supabaseRest(
    config,
    "PATCH",
    `agent_tasks?id=eq.${taskId}&user_id=eq.${user.id}&status=in.(queued,running,awaiting_approval,stalled)`,
    {
      status: "canceled",
      current_step: "ألغيت بواسطة المشغل",
      completed_at: new Date().toISOString(),
    },
    "return=representation",
  );
  const task = rows[0];
  if (!task) throw new HttpError(409, "Task cannot be canceled");
  await insertEvent(config, {
    task_id: taskId,
    user_id: user.id,
    event_type: "canceled",
    status: "canceled",
    step: task.current_step,
    message: "ألغى المشغل المهمة.",
    progress: task.progress,
  });
  return response({ task });
}

export async function handler(event) {
  if (event.httpMethod === "OPTIONS") return response({}, 204);

  try {
    const config = runtimeConfig();
    const user = await requireUser(event, config);
    const segments = routeSegments(event);

    if (segments.length === 0 && event.httpMethod === "GET") {
      return await listTasks(config, user);
    }
    if (segments.length === 0 && event.httpMethod === "POST") {
      return await createTask(config, user, event);
    }
    if (segments.length === 1 && event.httpMethod === "GET") {
      return await taskDetail(config, user, segments[0]);
    }
    if (segments.length === 2 && segments[1] === "approve" && event.httpMethod === "POST") {
      return await approveTask(config, user, segments[0]);
    }
    if (segments.length === 2 && segments[1] === "cancel" && event.httpMethod === "POST") {
      return await cancelTask(config, user, segments[0]);
    }
    throw new HttpError(404, "Agent task route not found");
  } catch (error) {
    if (error instanceof HttpError) return response({ error: error.message }, error.statusCode);
    console.error("agent-tasks function failed", error);
    return response({ error: "Internal agent task service error" }, 500);
  }
}
