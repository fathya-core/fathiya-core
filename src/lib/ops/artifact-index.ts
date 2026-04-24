// Server-only helpers for reading/updating artifacts/_index.json
import { promises as fs } from "fs";
import path from "path";

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
  generated_by: string;
  rule: string;
  tasks: ArtifactIndexEntry[];
}

const INDEX_PATH = path.join(process.cwd(), "artifacts", "_index.json");

export async function readIndex(): Promise<ArtifactIndex> {
  try {
    const raw = await fs.readFile(INDEX_PATH, "utf8");
    const parsed = JSON.parse(raw) as ArtifactIndex;
    if (!Array.isArray(parsed.tasks)) parsed.tasks = [];
    return parsed;
  } catch {
    return {
      version: 1,
      generated_by: "src/lib/ops/artifact-index.ts",
      rule: "كل مهمة لا تُغلق إلا بـ artifact دائم تحت artifacts/",
      tasks: [],
    };
  }
}

export async function recordArtifact(entry: ArtifactIndexEntry): Promise<ArtifactIndex> {
  const idx = await readIndex();
  // remove any prior entry for same task_id + path
  idx.tasks = idx.tasks.filter((t) => !(t.task_id === entry.task_id && t.path === entry.path));
  idx.tasks.push(entry);
  // sort by task_id then path for stable diffs
  idx.tasks.sort((a, b) => (a.task_id + a.path).localeCompare(b.task_id + b.path));
  await fs.writeFile(INDEX_PATH, JSON.stringify(idx, null, 2) + "\n", "utf8");
  return idx;
}

export async function readArtifact(relPath: string): Promise<{ content: string; bytes: number } | null> {
  const safe = relPath.replace(/^\/+/, "").replace(/\.\.\//g, "");
  const abs = path.join(process.cwd(), "artifacts", safe);
  try {
    const content = await fs.readFile(abs, "utf8");
    const stat = await fs.stat(abs);
    return { content, bytes: stat.size };
  } catch {
    return null;
  }
}
