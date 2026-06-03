import artifactIndexRaw from "../../../artifacts/_index.json?raw";

export interface LocalArtifactEntry {
  task_id: string;
  path: string;
  kind: string;
  saved_at: string;
  bytes: number;
  model?: string;
}

export interface LocalArtifactIndex {
  version: number;
  generated_by: string;
  rule?: string;
  source: "local_artifacts";
  tasks: LocalArtifactEntry[];
}

const artifactModules = import.meta.glob("../../../artifacts/**/*", {
  eager: true,
  import: "default",
  query: "?raw",
}) as Record<string, string>;

function normalizeArtifactPath(path: string): string {
  const clean = path.replace(/\\/g, "/").replace(/^\.\//, "").replace(/^\/+/, "");
  return clean.startsWith("artifacts/") ? clean : `artifacts/${clean}`;
}

function modulePathToArtifactPath(path: string): string {
  const normalized = path.replace(/\\/g, "/");
  const marker = "artifacts/";
  const idx = normalized.indexOf(marker);
  return idx >= 0 ? normalized.slice(idx) : normalizeArtifactPath(normalized);
}

function inferKind(path: string): string {
  if (path.endsWith(".md")) return "md";
  if (path.endsWith(".yaml") || path.endsWith(".yml")) return "yaml";
  if (path.endsWith(".json")) return "json";
  return "text";
}

const localContentByPath = Object.fromEntries(
  Object.entries(artifactModules).map(([modulePath, content]) => [
    modulePathToArtifactPath(modulePath),
    content,
  ]),
) as Record<string, string>;

function sizeOf(path: string): number {
  return new TextEncoder().encode(localContentByPath[path] ?? "").length;
}

export function getLocalArtifactContent(path: string): string | undefined {
  const normalized = normalizeArtifactPath(path);
  return localContentByPath[normalized];
}

export function loadLocalArtifactIndex(): LocalArtifactIndex {
  const parsed = JSON.parse(artifactIndexRaw) as {
    version?: number;
    rule?: string;
    tasks?: Array<{
      task_id?: string;
      path?: string;
      kind?: string;
      saved_at?: string;
      bytes?: number;
      model?: string;
      artifacts?: string[];
      closed_at?: string;
    }>;
  };

  const tasks: LocalArtifactEntry[] = [];
  const seen = new Set<string>();

  for (const raw of parsed.tasks ?? []) {
    if (!raw.task_id) continue;

    const explicitPaths = raw.path ? [raw.path] : (raw.artifacts ?? []);
    for (const artifactPath of explicitPaths) {
      const path = normalizeArtifactPath(artifactPath);
      const key = `${raw.task_id}::${path}`;
      if (seen.has(key)) continue;
      seen.add(key);
      tasks.push({
        task_id: raw.task_id,
        path,
        kind: raw.kind ?? inferKind(path),
        saved_at: raw.saved_at ?? raw.closed_at ?? "2026-06-03T10:20:31Z",
        bytes: raw.bytes && raw.bytes > 0 ? raw.bytes : sizeOf(path),
        model: raw.model,
      });
    }
  }

  tasks.sort((a, b) => (a.task_id + a.path).localeCompare(b.task_id + b.path));

  return {
    version: parsed.version ?? 1,
    generated_by: "artifacts/_index.json + bundled local artifact files",
    rule: parsed.rule,
    source: "local_artifacts",
    tasks,
  };
}
