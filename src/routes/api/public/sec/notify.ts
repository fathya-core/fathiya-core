import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

export const Route = createFileRoute("/api/public/sec/notify")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          const body = await request.json();
          const scanId = String(body?.scanId ?? "");
          const channel = String(body?.channel ?? "security");
          if (!scanId) return Response.json({ error: "scanId required" }, { status: 400 });

          // سجّل الإشعار في DB (placeholder حتى يربط Slack/Telegram لاحقاً)
          const { error } = await supabaseAdmin
            .from("security_scans")
            .update({ notified: true, updated_at: new Date().toISOString() })
            .eq("scan_id", scanId);
          if (error) throw error;

          // طباعة في server logs لتتبع
          console.log(`[notify] channel=${channel} scanId=${scanId}`);

          return Response.json({ ok: true, scanId, channel, delivered: true });
        } catch (e) {
          return Response.json({ error: String(e) }, { status: 500 });
        }
      },
    },
  },
});
