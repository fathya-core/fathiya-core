import { createFileRoute } from "@tanstack/react-router";
import { FathiyaFocusRedirect } from "@/components/FathiyaFocusRedirect";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "FATHIYA - التداول وصيد الثغرات" },
      {
        name: "description",
        content: "واجهة فتحية المركزة لوكيل التداول وصيد الثغرات.",
      },
    ],
  }),
  component: Home,
});

function Home() {
  return <FathiyaFocusRedirect source="الرئيسية" />;
}
