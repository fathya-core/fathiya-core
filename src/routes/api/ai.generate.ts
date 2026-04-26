import { createFileRoute } from "@tanstack/react-router";

interface GenerateBody {
  taskId?: string;
  model?: string;
  systemOverride?: string;
  userOverride?: string;
  saveAs?: string;
  saveKind?: "json" | "md";
}

export const Route = createFileRoute("/api/ai/generate")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        const SUPABASE_URL = process.env.SUPABASE_URL;
        const SUPABASE_ANON_KEY =
          process.env.SUPABASE_PUBLISHABLE_KEY ??
          process.env.VITE_SUPABASE_ANON_KEY;

        if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
          return new Response(
            JSON.stringify({ error: "Supabase env vars missing" }),
            { status: 500, headers: { "Content-Type": "application/json" } },
          );
        }

        let body: GenerateBody;
        try {
          body = (await request.json()) as GenerateBody;
        } catch {
          return new Response(
            JSON.stringify({ error: "Invalid JSON body" }),
            { status: 400, headers: { "Content-Type": "application/json" } },
          );
        }

        const { TASK_PROMPTS } = await import("@/lib/ai/prompts");
        const { DEFAULT_MODEL, getModelProvider } = await import(
          "@/lib/ai/models"
        );

        const spec = body.taskId ? TASK_PROMPTS[body.taskId] : null;
        const system =
          body.systemOverride ?? spec?.system ?? "أنت مساعد توليد محتوى نهائي.";
        const user = body.userOverride ?? spec?.userTemplate;
        const model = body.model ?? DEFAULT_MODEL;
        const provider = getModelProvider(model);

        if (!user) {
          return new Response(
            JSON.stringify({
              error:
                "No prompt: provide taskId with known spec or userOverride",
            }),
            { status: 400, headers: { "Content-Type": "application/json" } },
          );
        }

        const expectsJson = spec?.expectsJson ?? false;
        const savePath = body.saveAs ?? spec?.artifactPath;
        const saveKind =
          body.saveKind ?? spec?.artifactKind ?? (expectsJson ? "json" : "md");

        const edgeFnUrl = `${SUPABASE_URL}/functions/v1/ai-generate`;

        const upstream = await fetch(edgeFnUrl, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            model,
            provider,
            system,
            user,
            taskId: body.taskId ?? null,
            saveAs: savePath ?? null,
            saveKind,
            expectsJson,
          }),
        });

        const data = await upstream.json();

        return new Response(JSON.stringify(data), {
          status: upstream.status,
          headers: { "Content-Type": "application/json" },
        });
      },
    },
  },
});
