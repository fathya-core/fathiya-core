import { existsSync, readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const functionDir = path.dirname(fileURLToPath(import.meta.url));

function candidateRoots() {
  return [
    process.cwd(),
    path.resolve(functionDir, "../.."),
    path.resolve(functionDir, "../../.."),
    path.resolve(functionDir, "../../../.."),
    path.resolve("/var/task"),
  ];
}

export function findRepoRoot() {
  for (const root of candidateRoots()) {
    if (existsSync(path.join(root, "artifacts", "_index.json"))) return root;
  }
  return process.cwd();
}

export function jsonResponse(payload, statusCode = 200) {
  return {
    statusCode,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
    },
    body: JSON.stringify(payload, null, 2),
  };
}

export function normalizeArtifactPath(input) {
  const clean = String(input ?? "")
    .replace(/\\/g, "/")
    .replace(/^\.\//, "")
    .replace(/^\/+/, "");
  return clean.startsWith("artifacts/") ? clean : `artifacts/${clean}`;
}

function inferKind(filePath) {
  if (filePath.endsWith(".md")) return "md";
  if (filePath.endsWith(".yaml") || filePath.endsWith(".yml")) return "yaml";
  if (filePath.endsWith(".json")) return "json";
  return "text";
}

function walkFiles(root) {
  if (!existsSync(root)) return [];
  const out = [];
  const stack = [root];
  while (stack.length) {
    const current = stack.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else out.push(full);
    }
  }
  return out;
}

export function artifactAbsolutePath(artifactPath) {
  const repoRoot = findRepoRoot();
  const normalized = normalizeArtifactPath(artifactPath);
  return path.join(repoRoot, ...normalized.split("/"));
}

export function readArtifactContent(artifactPath) {
  const abs = artifactAbsolutePath(artifactPath);
  if (!existsSync(abs)) return undefined;
  return readFileSync(abs, "utf8");
}

export function loadLocalArtifactIndex() {
  const repoRoot = findRepoRoot();
  const indexPath = path.join(repoRoot, "artifacts", "_index.json");
  const parsed = JSON.parse(readFileSync(indexPath, "utf8"));
  const seen = new Set();
  const tasks = [];

  for (const raw of parsed.tasks ?? []) {
    if (!raw.task_id) continue;
    const paths = raw.path ? [raw.path] : (raw.artifacts ?? []);
    for (const rawPath of paths) {
      const artifactPath = normalizeArtifactPath(rawPath);
      const key = `${raw.task_id}::${artifactPath}`;
      if (seen.has(key)) continue;
      seen.add(key);
      const content = readArtifactContent(artifactPath) ?? "";
      tasks.push({
        task_id: raw.task_id,
        path: artifactPath,
        kind: raw.kind ?? inferKind(artifactPath),
        saved_at: raw.saved_at ?? raw.closed_at ?? "2026-06-03T10:45:52Z",
        bytes: raw.bytes && raw.bytes > 0 ? raw.bytes : Buffer.byteLength(content, "utf8"),
        model: raw.model,
      });
    }
  }

  tasks.sort((a, b) => (a.task_id + a.path).localeCompare(b.task_id + b.path));

  return {
    version: parsed.version ?? 1,
    generated_by: "netlify/functions + artifacts/_index.json",
    rule: parsed.rule ?? "كل مهمة لا تغلق إلا بـ artifact دائم",
    source: "local_artifacts",
    repo_root_found: existsSync(indexPath),
    tasks,
  };
}

export function loadJsonArtifact(artifactPath) {
  const content = readArtifactContent(artifactPath);
  if (!content) return undefined;
  return JSON.parse(content);
}

export function listArtifactFiles(prefix) {
  const repoRoot = findRepoRoot();
  const base = path.join(repoRoot, ...normalizeArtifactPath(prefix).split("/"));
  return walkFiles(base).map(
    (file) =>
      `artifacts/${path.relative(path.join(repoRoot, "artifacts"), file).replace(/\\/g, "/")}`,
  );
}
