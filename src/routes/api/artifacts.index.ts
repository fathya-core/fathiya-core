import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";
import { loadLocalArtifactIndex, type LocalArtifactEntry } from "@/lib/artifacts/local-artifacts";

export const Route = createFileRoute("/api/artifacts/")({
  server: {
    handlers: {
      GET: async () => {
        const localIndex = loadLocalArtifactIndex();
        const warnings: string[] = [];

        try {
          const { data, error } = await supabaseAdmin
            .from("ai_runs")
            .select("task_id, saved_path, save_kind, created_at, model, output")
            .eq("status", "ok")
            .not("saved_path", "is", null)
            .order("created_at", { ascending: false })
            .limit(500);

          if (error) throw new Error(error.message);

          // de-duplicate by (task_id, saved_path) keeping the latest
          const seen = new Set<string>();
          const tasks = [] as LocalArtifactEntry[];

          for (const r of data ?? []) {
            if (!r.task_id || !r.saved_path) continue;
            const path = r.saved_path.startsWith("artifacts/")
              ? r.saved_path
              : `artifacts/${r.saved_path}`;
            const key = `${r.task_id}::${path}`;
            if (seen.has(key)) continue;
            seen.add(key);
            tasks.push({
              task_id: r.task_id,
              path,
              kind: r.save_kind ?? "json",
              saved_at: r.created_at,
              bytes: r.output ? new TextEncoder().encode(r.output).length : 0,
              model: r.model ?? undefined,
            });
          }

          for (const local of localIndex.tasks) {
            const key = `${local.task_id}::${local.path}`;
            if (seen.has(key)) continue;
            seen.add(key);
            tasks.push(local);
          }

          // stable sort
          tasks.sort((a, b) => (a.task_id + a.path).localeCompare(b.task_id + b.path));

          return new Response(
            JSON.stringify({
              version: 1,
              generated_by: "ai_runs (supabase) + local artifacts fallback",
              rule: "كل مهمة لا تُغلق إلا بـ artifact دائم",
              tasks,
            }),
            {
              status: 200,
              headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
            },
          );
        } catch (err) {
          warnings.push(`supabase_unavailable: ${String(err)}`);
        }

        return new Response(
          JSON.stringify({
            ...localIndex,
            warnings,
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
          },
        );
      },
    },
  },
});
