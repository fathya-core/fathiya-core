import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

interface Finding {
  severity: string;
  title: string;
  ref?: string;
}

function buildMarkdown(scanId: string, target: string, findings: Finding[]) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 } as Record<string, number>;
  findings.forEach((f) => {
    if (counts[f.severity] !== undefined) counts[f.severity]++;
  });
  const lines = [
    `# Security Report — ${scanId}`,
    "",
    `- Target: \`${target}\``,
    `- Critical: ${counts.critical}`,
    `- High: ${counts.high}`,
    `- Medium: ${counts.medium}`,
    `- Low: ${counts.low}`,
    "",
    "## Findings",
    ...findings.map((f) => `- **[${f.severity.toUpperCase()}]** ${f.title}${f.ref ? ` (\`${f.ref}\`)` : ""}`),
  ];
  return lines.join("\n");
}

export const Route = createFileRoute("/api/public/sec/report")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          const body = await request.json();
          const scanId = String(body?.scanId ?? "");
          if (!scanId) return Response.json({ error: "scanId required" }, { status: 400 });

          const { data: scan, error: fetchErr } = await supabaseAdmin
            .from("security_scans")
            .select("scan_id, target, findings")
            .eq("scan_id", scanId)
            .maybeSingle();
          if (fetchErr) throw fetchErr;
          if (!scan) return Response.json({ error: "scan not found" }, { status: 404 });

          const md = buildMarkdown(scan.scan_id, scan.target, (scan.findings as unknown as Finding[]) ?? []);
          const reportUrl = `/api/public/sec/report?scanId=${encodeURIComponent(scanId)}`;

          const { error: upErr } = await supabaseAdmin
            .from("security_scans")
            .update({ report_markdown: md, report_url: reportUrl, updated_at: new Date().toISOString() })
            .eq("scan_id", scanId);
          if (upErr) throw upErr;

          return Response.json({ scanId, reportUrl, length: md.length });
        } catch (e) {
          return Response.json({ error: String(e) }, { status: 500 });
        }
      },
      // GET ?scanId=xxx → returns markdown plain text
      GET: async ({ request }) => {
        const url = new URL(request.url);
        const scanId = url.searchParams.get("scanId");
        if (!scanId) return new Response("scanId required", { status: 400 });

        const { data, error } = await supabaseAdmin
          .from("security_scans")
          .select("report_markdown")
          .eq("scan_id", scanId)
          .maybeSingle();
        if (error || !data?.report_markdown) {
          return new Response("not found", { status: 404 });
        }
        return new Response(data.report_markdown, {
          status: 200,
          headers: { "Content-Type": "text/markdown; charset=utf-8" },
        });
      },
    },
  },
});
