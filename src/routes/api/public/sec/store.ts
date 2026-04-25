import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

export const Route = createFileRoute("/api/public/sec/store")({
  server: {
    handlers: {
      // GET ?scanId=xxx → returns full scan record
      GET: async ({ request }) => {
        const url = new URL(request.url);
        const scanId = url.searchParams.get("scanId");
        if (!scanId) return Response.json({ error: "scanId required" }, { status: 400 });

        const { data, error } = await supabaseAdmin
          .from("security_scans")
          .select("*")
          .eq("scan_id", scanId)
          .maybeSingle();
        if (error) return Response.json({ error: error.message }, { status: 500 });
        if (!data) return Response.json({ error: "not found" }, { status: 404 });
        return Response.json(data);
      },
      // POST { scanId, findings } → upsert findings
      POST: async ({ request }) => {
        try {
          const body = await request.json();
          const scanId = String(body?.scanId ?? "");
          if (!scanId) return Response.json({ error: "scanId required" }, { status: 400 });

          const { error } = await supabaseAdmin
            .from("security_scans")
            .update({
              findings: body.findings ?? [],
              status: body.status ?? "completed",
              updated_at: new Date().toISOString(),
            })
            .eq("scan_id", scanId);
          if (error) throw error;
          return Response.json({ ok: true, scanId });
        } catch (e) {
          return Response.json({ error: String(e) }, { status: 500 });
        }
      },
    },
  },
});
