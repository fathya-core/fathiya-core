import { createFileRoute } from "@tanstack/react-router";
import { FathiyaFocusRedirect } from "@/components/FathiyaFocusRedirect";

export const Route = createFileRoute("/command-center")({
  head: () => ({
    meta: [
      { title: "FATHIYA - تم نقل مركز القيادة" },
      {
        name: "description",
        content: "تم نقل مركز القيادة إلى واجهة فتحية المركزة للتداول وصيد الثغرات.",
      },
    ],
  }),
  component: CommandCenterRedirect,
});

function CommandCenterRedirect() {
  return <FathiyaFocusRedirect source="Command Center القديم" />;
}
