import type { Session } from "@supabase/supabase-js";

export async function agentApi<T>(session: Session, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${session.access_token}`,
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
