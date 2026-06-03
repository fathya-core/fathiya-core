import { jsonResponse, normalizeArtifactPath, readArtifactContent } from "./_artifact-utils.mjs";

export async function handler(event) {
  let requestedPath = event.queryStringParameters?.path;

  if (event.httpMethod === "POST" && event.body) {
    try {
      const body = JSON.parse(event.body);
      requestedPath = body.path ?? requestedPath;
    } catch {
      return jsonResponse({ ok: false, error: "Invalid JSON body" }, 400);
    }
  }

  if (!requestedPath) {
    return jsonResponse({ ok: false, error: "path is required" }, 400);
  }

  const artifactPath = normalizeArtifactPath(requestedPath);
  const content = readArtifactContent(artifactPath);
  if (!content) {
    return jsonResponse({ ok: false, error: "Artifact not found", path: artifactPath }, 404);
  }

  let pretty = content;
  if (artifactPath.endsWith(".json")) {
    try {
      pretty = JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      // leave as-is
    }
  }

  return jsonResponse({
    ok: true,
    path: artifactPath,
    source: "netlify_local_artifacts",
    bytes: Buffer.byteLength(pretty, "utf8"),
    content: pretty,
  });
}
