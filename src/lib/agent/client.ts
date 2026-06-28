const configuredLocalUrl = import.meta.env.VITE_FATHIYA_LOCAL_API_URL?.replace(/\/+$/, "");
const loopbackUrl = /^https?:\/\/(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?$/;

export const localAgentRuntimeUrl =
  configuredLocalUrl && loopbackUrl.test(configuredLocalUrl)
    ? configuredLocalUrl
    : "http://127.0.0.1:8765";

export const isLocalAgentRuntime = Boolean(localAgentRuntimeUrl);

type AgentApiSession = {
  access_token: string;
};

export async function agentApi<T>(
  session: AgentApiSession | null,
  path: string,
  init?: RequestInit,
): Promise<T> {
  if (!isLocalAgentRuntime && !session) {
    throw new Error("Agent operator session is required");
  }
  const response = await fetch(`${localAgentRuntimeUrl}${path}`, {
    ...init,
    headers: {
      ...(session ? { Authorization: `Bearer ${session.access_token}` } : {}),
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `Agent API failed with HTTP ${response.status}`);
  }

  return (await response.json()) as T;
}
