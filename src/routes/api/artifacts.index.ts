import { createFileRoute } from "@tanstack/react-router";
import { readIndex } from "@/lib/ops/artifact-index";

export const Route = createFileRoute("/api/artifacts/")({
  server: {
    handlers: {
      GET: async () => {
        const idx = await readIndex();
        return new Response(JSON.stringify(idx), {
          status: 200,
          headers: { "Content-Type": "application/json", "Cache-Control": "no-store" },
        });
      },
    },
  },
});
