import { createFileRoute } from "@tanstack/react-router";
import { cancelAgentTask, requireAgentUser } from "@/lib/agent/server";

export const Route = createFileRoute("/api/agent/tasks/$taskId/cancel")({
  server: {
    handlers: {
      POST: async ({ request, params }) => {
        try {
          const user = await requireAgentUser(request);
          return Response.json({ task: await cancelAgentTask(user.id, params.taskId) });
        } catch (error) {
          if (error instanceof Response) return error;
          return Response.json({ error: String(error) }, { status: 500 });
        }
      },
    },
  },
});
