import { createFileRoute } from "@tanstack/react-router";
import { promises as fs } from "fs";
import path from "path";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

async function logRun(row: {
  task_id: string | null;
  model: string;
  system_prompt: string | null;
  user_prompt: string | null;
  output: string | null;
  saved_path: string | null;
  save_kind: string | null;
  status: "ok" | "error";
  error_message: string | null;
  http_status: number | null;
  duration_ms: number;
}) {
  try {
    await supabaseAdmin.from("ai_runs").insert(row);
  } catch (e) {
    console.error("[ai.generate] failed to log run:", e);
  }
}

interface GenerateBody {
  taskId?: string;
  model?: string;
  systemOverride?: string;
  userOverride?: string;
  saveAs?: string; // optional artifact path override (relative to artifacts/)
  saveKind?: "json" | "md";
}

export const Route = createFileRoute("/api/ai/generate")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const LOVABLE_API_KEY = process.env.LOVABLE_API_KEY;
        if (!LOVABLE_API_KEY) {
          return new Response(JSON.stringify({ error: "LOVABLE_API_KEY missing" }), {
            status: 500,
            headers: { "Content-Type": "application/json" },
          });
        }

        let body: GenerateBody;
        try {
          body = (await request.json()) as GenerateBody;
        } catch {
          return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        // Lazy import to avoid bundling task list issues
        const { TASK_PROMPTS } = await import("@/lib/ai/prompts");
        const { DEFAULT_GPT_MODEL } = await import("@/lib/ai/models");

        const spec = body.taskId ? TASK_PROMPTS[body.taskId] : null;
        const system = body.systemOverride ?? spec?.system ?? "أنت مساعد توليد محتوى نهائي.";
        const user = body.userOverride ?? spec?.userTemplate;
        if (!user) {
          return new Response(
            JSON.stringify({ error: "No prompt: provide taskId with known spec or userOverride" }),
            { status: 400, headers: { "Content-Type": "application/json" } },
          );
        }

        const model = body.model ?? DEFAULT_GPT_MODEL;
        const expectsJson = spec?.expectsJson ?? false;

        const upstream = await fetch("https://ai.gateway.lovable.dev/v1/chat/completions", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${LOVABLE_API_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model,
            messages: [
              { role: "system", content: system },
              { role: "user", content: user },
            ],
            ...(expectsJson ? { response_format: { type: "json_object" } } : {}),
          }),
        });

        if (!upstream.ok) {
          const text = await upstream.text();
          if (upstream.status === 429) {
            return new Response(
              JSON.stringify({ error: "Rate limited — try again shortly", upstream: text }),
              { status: 429, headers: { "Content-Type": "application/json" } },
            );
          }
          if (upstream.status === 402) {
            return new Response(
              JSON.stringify({
                error: "Lovable AI credits exhausted — top up in Settings → Workspace → Usage",
                upstream: text,
              }),
              { status: 402, headers: { "Content-Type": "application/json" } },
            );
          }
          return new Response(
            JSON.stringify({ error: `AI gateway ${upstream.status}`, upstream: text }),
            { status: 502, headers: { "Content-Type": "application/json" } },
          );
        }

        const data = (await upstream.json()) as {
          choices?: Array<{ message?: { content?: string } }>;
        };
        const content = data.choices?.[0]?.message?.content ?? "";
        if (!content.trim()) {
          return new Response(JSON.stringify({ error: "Empty response from model" }), {
            status: 502,
            headers: { "Content-Type": "application/json" },
          });
        }

        // Decide where to save
        const savePath = body.saveAs ?? spec?.artifactPath;
        const saveKind = body.saveKind ?? spec?.artifactKind ?? (expectsJson ? "json" : "md");

        let saved = false;
        let savedPath: string | null = null;
        let parsedPreview: unknown = null;

        if (savePath) {
          // sanitize: prevent escaping artifacts/
          const safe = savePath.replace(/^\/+/, "").replace(/\.\.\//g, "");
          const abs = path.join(process.cwd(), "artifacts", safe);
          await fs.mkdir(path.dirname(abs), { recursive: true });

          let toWrite = content.trim();
          if (saveKind === "json") {
            // strip code fences if any
            toWrite = toWrite.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "");
            try {
              const parsed = JSON.parse(toWrite);
              parsedPreview = parsed;
              toWrite = JSON.stringify(parsed, null, 2);
            } catch (e) {
              return new Response(
                JSON.stringify({
                  error: "Model returned invalid JSON",
                  raw: content,
                  parseError: String(e),
                }),
                { status: 502, headers: { "Content-Type": "application/json" } },
              );
            }
          }

          await fs.writeFile(abs, toWrite + (toWrite.endsWith("\n") ? "" : "\n"), "utf8");
          saved = true;
          savedPath = `artifacts/${safe}`;
        }

        return new Response(
          JSON.stringify({
            ok: true,
            model,
            taskId: body.taskId ?? null,
            content,
            saved,
            savedPath,
            preview: parsedPreview,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      },
    },
  },
});
