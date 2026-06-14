import { createFileRoute } from "@tanstack/react-router";
import { createAgentTask, listAgentTasks, requireAgentUser } from "@/lib/agent/server";
import type { CreateAgentTaskBody } from "@/lib/agent/contracts";

export const Route = createFileRoute("/api/agent/tasks")({
  server: {
    handlers: {
      GET: async ({ request }) => {
        try {
          const user = await requireAgentUser(request);
          return Response.json({ tasks: await listAgentTasks(user.id) });
        } catch (error) {
          return agentErrorResponse(error);
        }
      },
      POST: async ({ request }) => {
        try {
          const user = await requireAgentUser(request);
          const body = (await request.json()) as CreateAgentTaskBody;
          return Response.json({ task: await createAgentTask(user.id, body) }, { status: 201 });
        } catch (error) {
          return agentErrorResponse(error);
        }
      },
    },
  },
});

function agentErrorResponse(error: unknown) {
  if (error instanceof Response) return error;
  return Response.json({ error: String(error) }, { status: 500 });
}
