import { useEffect, useState, useCallback } from "react";

export interface ArtifactIndexEntry {
  task_id: string;
  path: string;
  kind: string;
  saved_at: string;
  bytes: number;
  model?: string;
}

export interface ArtifactIndex {
  version: number;
  tasks: ArtifactIndexEntry[];
}

let cache: ArtifactIndex | null = null;
const listeners = new Set<() => void>();

async function load(): Promise<ArtifactIndex> {
  const r = await fetch("/api/artifacts/", { cache: "no-store" });
  if (!r.ok) return { version: 1, tasks: [] };
  const data = (await r.json()) as ArtifactIndex;
  cache = data;
  listeners.forEach((fn) => fn());
  return data;
}

export function useArtifactIndex() {
  const [idx, setIdx] = useState<ArtifactIndex | null>(cache);
  const [loading, setLoading] = useState(!cache);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await load();
      setIdx(data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const sub = () => setIdx(cache);
    listeners.add(sub);
    if (!cache) refresh();
    return () => {
      listeners.delete(sub);
    };
  }, [refresh]);

  const entriesForTask = useCallback(
    (taskId: string): ArtifactIndexEntry[] =>
      (idx?.tasks ?? []).filter((t) => t.task_id === taskId),
    [idx],
  );

  const isDone = useCallback(
    (taskId: string, expectedPaths: string[]): boolean => {
      if (expectedPaths.length === 0) return false;
      const have = new Set((idx?.tasks ?? []).filter((t) => t.task_id === taskId).map((t) => t.path));
      return expectedPaths.every((p) => have.has(`artifacts/${p}`) || have.has(p));
    },
    [idx],
  );

  return { idx, loading, refresh, entriesForTask, isDone };
}

// Force reload from anywhere (e.g. after generate succeeds)
export async function refreshArtifactIndex() {
  await load();
}
