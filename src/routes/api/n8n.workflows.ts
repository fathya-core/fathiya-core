import { createFileRoute } from "@tanstack/react-router";

interface N8nWorkflow {
  id: string;
  name: string;
  active: boolean;
  updatedAt: string;
  createdAt: string;
}
interface N8nExecution {
  id: string;
  workflowId: string;
  status: string;
  startedAt: string;
  stoppedAt?: string;
  finished: boolean;
}

const N8N_BASE = process.env.N8N_BASE_URL; // e.g. https://my.app.n8n.cloud
const N8N_API_KEY = process.env.N8N_API_KEY;

async function n8nFetch(path: string) {
  if (!N8N_BASE || !N8N_API_KEY) {
    throw new Error("missing_credentials");
  }
  const r = await fetch(`${N8N_BASE.replace(/\/+$/, "")}/api/v1${path}`, {
    headers: { "X-N8N-API-KEY": N8N_API_KEY, Accept: "application/json" },
  });
  if (!r.ok) throw new Error(`n8n ${r.status}: ${await r.text()}`);
  return r.json();
}

export const Route = createFileRoute("/api/n8n/workflows")({
  server: {
    handlers: {
      GET: async () => {
        if (!N8N_BASE || !N8N_API_KEY) {
          return new Response(
            JSON.stringify({
              configured: false,
              workflows: [],
              message:
                "أضف N8N_BASE_URL و N8N_API_KEY في الأسرار لتفعيل الجسر المباشر. حالياً نعرض workflows ثابتة من MCP snapshot.",
              snapshot: [
                { id: "br6l9Sld1SBuIqm5", name: "FATHIYA V1 — Security Scan", active: true },
                { id: "UDgB9WgTP6w40tBG", name: "FATHIYA V1 — Smoke Tests", active: false },
                { id: "YCOsCjL2jKCsbweu", name: "FATHIYA V1 — Control Cases", active: false },
                { id: "rhz6FuAANUAeEkOl", name: "FATHIYA V1 — Status Report", active: false },
                { id: "70arOAh0pj9cXpcB", name: "AI Agent workflow", active: false },
              ],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        try {
          const data = (await n8nFetch("/workflows?limit=50")) as { data: N8nWorkflow[] };
          // For each workflow, fetch last execution (best-effort)
          const enriched = await Promise.all(
            (data.data ?? []).map(async (wf) => {
              try {
                const ex = (await n8nFetch(
                  `/executions?workflowId=${wf.id}&limit=1`,
                )) as { data: N8nExecution[] };
                const last = ex.data?.[0];
                return {
                  id: wf.id,
                  name: wf.name,
                  active: wf.active,
                  updatedAt: wf.updatedAt,
                  lastExecution: last
                    ? {
                        id: last.id,
                        status: last.status,
                        startedAt: last.startedAt,
                        stoppedAt: last.stoppedAt,
                        finished: last.finished,
                      }
                    : null,
                };
              } catch {
                return {
                  id: wf.id,
                  name: wf.name,
                  active: wf.active,
                  updatedAt: wf.updatedAt,
                  lastExecution: null,
                };
              }
            }),
          );
          return new Response(
            JSON.stringify({ configured: true, workflows: enriched }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        } catch (e) {
          return new Response(
            JSON.stringify({ configured: true, error: String(e), workflows: [] }),
            { status: 502, headers: { "Content-Type": "application/json" } },
          );
        }
      },
    },
  },
});
