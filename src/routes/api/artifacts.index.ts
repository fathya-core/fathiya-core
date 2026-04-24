import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

export const Route = createFileRoute("/api/artifacts/index")({
  server: {
    handlers: {
      GET: async () => {
        const { data, error } = await supabaseAdmin
          .from("ai_runs")
          .select("task_id, saved_path, save_kind, created_at, model, output")
          .eq("status", "ok")
          .not("saved_path", "is", null)
          .order("created_at", { ascending: false })
          .limit(500);

        if (error) {
          return new Response(JSON.stringify({ error: error.message }), {
            status: 500,
            headers: { "Content-Type": "application/json" },
          });
        }

        // de-duplicate by (task_id, saved_path) keeping the latest
        const seen = new Set<string>();
        const tasks = [] as Array<{
          task_id: string;
          path: string;
          kind: string;
          saved_at: string;
          bytes: number;
          model?: string;
        }>;

        for (const r of data ?? []) {
          if (!r.task_id || !r.saved_path) continue;
          const key = `${r.task_id}::${r.saved_path}`;
          if (seen.has(key)) continue;
          seen.add(key);
          tasks.push({
            task_id: r.task_id,
            path: r.saved_path,
            kind: r.save_kind ?? "json",
            saved_at: r.created_at,
            bytes: r.output ? new TextEncoder().encode(r.output).length : 0,
            model: r.model ?? undefined,
          });
        }

        // stable sort
        tasks.sort((a, b) => (a.task_id + a.path).localeCompare(b.task_id + b.path));

        return new Response(
          JSON.stringify({
            version: 1,
            generated_by: "ai_runs (supabase)",
            rule: "كل مهمة لا تُغلق إلا بـ artifact دائم",
            tasks,
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
