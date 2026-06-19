import { createFileRoute } from "@tanstack/react-router";
import { FathiyaFocusRedirect } from "@/components/FathiyaFocusRedirect";

export const Route = createFileRoute("/ai-console")({
  head: () => ({
    meta: [
      { title: "FATHIYA - تم نقل AI Console" },
      {
        name: "description",
        content: "تم نقل AI Console إلى واجهة فتحية المركزة للتداول وصيد الثغرات.",
      },
    ],
  }),
  component: AiConsoleRedirect,
});

function AiConsoleRedirect() {
  return <FathiyaFocusRedirect source="AI Console القديم" />;
}
