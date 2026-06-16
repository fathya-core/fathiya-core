import { createFileRoute } from "@tanstack/react-router";
import { FathiyaFocusRedirect } from "@/components/FathiyaFocusRedirect";

export const Route = createFileRoute("/ai-runs")({
  head: () => ({
    meta: [
      { title: "FATHIYA - تم نقل AI Runs" },
      {
        name: "description",
        content: "تم نقل سجل AI Runs إلى واجهة فتحية المركزة للتداول وصيد الثغرات.",
      },
    ],
  }),
  component: AiRunsRedirect,
});

function AiRunsRedirect() {
  return <FathiyaFocusRedirect source="AI Runs القديم" />;
}
