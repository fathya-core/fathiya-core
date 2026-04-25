import { createFileRoute } from "@tanstack/react-router";
import { supabaseAdmin } from "@/integrations/supabase/client.server";

// محاكاة سكانر حقيقي: يولّد findings حسب scanType
function simulateScan(scanType: string, target: string) {
  const samples: Record<string, Array<{ severity: string; title: string; ref: string }>> = {
    sca: [
      { severity: "high", title: "lodash <4.17.21 prototype pollution", ref: "CVE-2021-23337" },
      { severity: "medium", title: "axios <1.6.0 SSRF", ref: "CVE-2023-45857" },
    ],
    sast: [
      { severity: "critical", title: "Hardcoded secret in repo", ref: "RULE-SAST-001" },
    ],
    dast: [
      { severity: "low", title: "Missing security headers", ref: "OWASP-A05" },
    ],
  };
  return samples[scanType] ?? [];
}

export const Route = createFileRoute("/api/public/sec/scan")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        try {
          const body = await request.json();
          const scanType = String(body?.scanType ?? "sca");
          const target = String(body?.target ?? "unknown");

          if (!["sca", "sast", "dast"].includes(scanType)) {
            return Response.json({ error: "invalid scanType" }, { status: 400 });
          }

          const scanId = `scan_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 7)}`;
          const findings = simulateScan(scanType, target);

          const { error } = await supabaseAdmin.from("security_scans").insert({
            scan_id: scanId,
            scan_type: scanType,
            target,
            status: "completed",
            findings,
          });
          if (error) throw error;

          return Response.json({ scanId, status: "completed", findingsCount: findings.length });
        } catch (e) {
          return Response.json({ error: String(e) }, { status: 500 });
        }
      },
    },
  },
});
