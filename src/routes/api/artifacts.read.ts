import { createFileRoute } from "@tanstack/react-router";
import { readArtifact } from "@/lib/ops/artifact-index";

export const Route = createFileRoute("/api/artifacts/read")({
  server: {
    handlers: {
      POST: async ({ request }) => {
        let body: { path?: string };
        try {
          body = (await request.json()) as { path?: string };
        } catch {
          return new Response(JSON.stringify({ error: "Invalid JSON body" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
        if (!body.path) {
          return new Response(JSON.stringify({ error: "path is required" }), {
            status: 400,
            headers: { "Content-Type": "application/json" },
          });
        }
        const result = await readArtifact(body.path);
        if (!result) {
          return new Response(JSON.stringify({ error: "Artifact not found", path: body.path }), {
            status: 404,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(
          JSON.stringify({ ok: true, path: body.path, bytes: result.bytes, content: result.content }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      },
    },
  },
});
