import assert from "node:assert/strict";
import { handler } from "../functions/agent-tasks.mjs";

const originalFetch = globalThis.fetch;
const originalEnv = {
  SUPABASE_URL: process.env.SUPABASE_URL,
  SUPABASE_PUBLISHABLE_KEY: process.env.SUPABASE_PUBLISHABLE_KEY,
  SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY,
};

process.env.SUPABASE_URL = "https://example.supabase.co";
process.env.SUPABASE_PUBLISHABLE_KEY = "publishable-test";
process.env["SUPABASE_SERVICE_ROLE_KEY"] = "service-role-test";

const taskId = "11111111-1111-4111-8111-111111111111";
const userId = "22222222-2222-4222-8222-222222222222";
const calls = [];

globalThis.fetch = async (url, init = {}) => {
  calls.push({ url: String(url), init });
  if (String(url).endsWith("/auth/v1/user")) {
    return Response.json({ id: userId, email: "operator@example.com" });
  }
  if (String(url).endsWith("/rest/v1/agent_tasks") && init.method === "POST") {
    const body = JSON.parse(init.body);
    return Response.json([
      {
        id: taskId,
        ...body,
        worker_id: null,
        plan: [],
        result: null,
        error_message: null,
        last_heartbeat_at: null,
        started_at: null,
        completed_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    ]);
  }
  if (String(url).endsWith("/rest/v1/agent_task_events") && init.method === "POST") {
    return new Response(null, { status: 201 });
  }
  throw new Error(`Unexpected fetch: ${url}`);
};

try {
  const unauthorized = await handler({ httpMethod: "GET", headers: {} });
  assert.equal(unauthorized.statusCode, 401);

  const created = await handler({
    httpMethod: "POST",
    headers: { authorization: "Bearer test-token" },
    body: JSON.stringify({ prompt: "نفذ صفقة شراء حقيقية" }),
    queryStringParameters: {},
  });
  const createdBody = JSON.parse(created.body);
  assert.equal(created.statusCode, 201);
  assert.equal(createdBody.task.status, "awaiting_approval");
  assert.equal(createdBody.task.risk_class, "financial");
  assert.equal(createdBody.task.requires_approval, true);

  const invalidId = await handler({
    httpMethod: "GET",
    headers: { authorization: "Bearer test-token" },
    queryStringParameters: { path: "not-a-uuid" },
  });
  assert.equal(invalidId.statusCode, 400);
  assert.ok(calls.some((call) => call.url.endsWith("/auth/v1/user")));
  console.log("agent-tasks netlify bridge tests: PASS");
} finally {
  globalThis.fetch = originalFetch;
  for (const [key, value] of Object.entries(originalEnv)) {
    if (value === undefined) delete process.env[key];
    else process.env[key] = value;
  }
}
