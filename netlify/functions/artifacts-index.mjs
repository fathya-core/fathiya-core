import { jsonResponse, loadLocalArtifactIndex } from "./_artifact-utils.mjs";

export async function handler() {
  try {
    return jsonResponse(loadLocalArtifactIndex());
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        error: "local_artifact_index_unavailable",
        detail: String(err),
      },
      500,
    );
  }
}
