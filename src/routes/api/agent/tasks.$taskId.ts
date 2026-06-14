import { createFileRoute } from "@tanstack/react-router";
import { getAgentTaskDetail, requireAgentUser } from "@/lib/agent/server";

export const Route = createFileRoute("/api/agent/tasks/$taskId")({
  server: {
    handlers: {
      GET: async ({ request, params }) => {
        try {
          const user = await requireAgentUser(request);
          return Response.json(await getAgentTaskDetail(user.id, params.taskId));
        } catch (error) {
          if (error instanceof Response) return error;
          return Response.json({ error: String(error) }, { status: 500 });
        }
      },
    },
  },
});
