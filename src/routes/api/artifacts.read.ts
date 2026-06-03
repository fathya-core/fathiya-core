// Reads an artifact's content from the latest matching ai_runs row in Supabase.
// The Worker FS does not persist generated files across requests, so the source
// of truth for content is the ai_runs.output column.
import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";
import { getLocalArtifactContent } from "@/lib/artifacts/local-artifacts";

export const Route = createFileRoute("/api/artifacts/read")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let body: { path?: string };
        try {
          body = (await request.json()) as { path?: string };
        } catch {
          return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (!body.path) {
          return new Response(JSON.stringify({ error: "path is required" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }

        // Normalize: the index stores "artifacts/<path>" but callers may pass either.
        const normalized = body.path.startsWith("artifacts/")
          ? body.path
          : `artifacts/${body.path}`;

        try {
          const { data, error } = await supabaseAdmin
            .from("ai_runs")
            .select("output, save_kind, saved_path, created_at, model, task_id")
            .eq("status", "ok")
            .eq("saved_path", normalized)
            .order("created_at", { ascending: false })
            .limit(1)
            .maybeSingle();

          if (error) throw new Error(error.message);
          if (data?.output) {
            // Pretty-print JSON if applicable
            let content = data.output;
            if (data.save_kind === "json" || normalized.endsWith(".json")) {
              try {
                content = JSON.stringify(JSON.parse(content), null, 2);
              } catch {
                // leave as-is
              }
            }

            return new Response(
              JSON.stringify({
                ok: true,
                path: normalized,
                bytes: new TextEncoder().encode(content).length,
                content,
                model: data.model,
                task_id: data.task_id,
                saved_at: data.created_at,
                source: "supabase",
              }),
              { status: 200, headers: { "Content-Type": "application/json" } },
            );
          }
        } catch {
          // Fall through to bundled local artifacts. This keeps fathya-core.com useful
          // when Supabase env vars are absent or an artifact was committed directly.
        }

        const localContent = getLocalArtifactContent(normalized);
        if (!localContent) {
          return new Response(JSON.stringify({ error: "Artifact not found", path: normalized }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          });
        }

        let content = localContent;
        if (normalized.endsWith(".json")) {
          try {
            content = JSON.stringify(JSON.parse(content), null, 2);
          } catch {
            // leave as-is
          }
        }

        return new Response(
          JSON.stringify({
            ok: true,
            path: normalized,
            bytes: new TextEncoder().encode(content).length,
            content,
            source: "local_artifacts",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      },
    },
  },
});
