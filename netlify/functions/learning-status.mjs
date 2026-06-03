import {
  jsonResponse,
  listArtifactFiles,
  loadJsonArtifact,
  loadLocalArtifactIndex,
} from "./_artifact-utils.mjs";

const profilePaths = [
  "artifacts/profiles/FATHIYA_SECURITY_BASE.json",
  "artifacts/profiles/FATHIYA_CRYPTO_BASE.json",
  "artifacts/profiles/FATHIYA_RESEARCH_BASE.json",
  "artifacts/profiles/FATHIYA_CODE_BASE.json",
];

export async function handler() {
  try {
    const index = loadLocalArtifactIndex();
    const profiles = profilePaths
      .map((artifactPath) => loadJsonArtifact(artifactPath))
      .filter(Boolean);
    const evalFiles = listArtifactFiles("artifacts/evals").filter((file) => file.endsWith(".json"));
    const routingFiles = listArtifactFiles("artifacts/routing").filter((file) =>
      file.endsWith(".json"),
    );

    const completedTasks = [...new Set(index.tasks.map((item) => item.task_id))].sort();
    const activeProfiles = profiles.filter((profile) => profile.status === "active");
    const guardrailCount = activeProfiles.reduce(
      (sum, profile) => sum + (profile.guardrails?.length ?? 0),
      0,
    );

    const understandingChecks = [
      {
        id: "profiles_active",
        passed: activeProfiles.length === profilePaths.length,
        evidence: `${activeProfiles.length}/${profilePaths.length} profiles active`,
      },
      {
        id: "account_registry_visible",
        passed: index.tasks.some((item) => item.task_id === "T05"),
        evidence: "T05 appears in artifact index",
      },
      {
        id: "evals_available",
        passed: evalFiles.length >= 2,
        evidence: `${evalFiles.length} eval files available`,
      },
      {
        id: "routing_available",
        passed: routingFiles.length >= 2,
        evidence: `${routingFiles.length} routing files available`,
      },
      {
        id: "guardrails_loaded",
        passed: guardrailCount >= 12,
        evidence: `${guardrailCount} profile guardrails loaded`,
      },
    ];

    const status = understandingChecks.every((check) => check.passed)
      ? "learning_foundation_active"
      : "learning_foundation_partial";

    return jsonResponse({
      ok: true,
      status,
      mode: "safe_internal_learning",
      generated_at: new Date().toISOString(),
      completed_tasks: completedTasks,
      active_profiles: activeProfiles.map((profile) => ({
        profile_id: profile.profile_id,
        role: profile.identity?.role,
        guardrails: profile.guardrails?.length ?? 0,
        evals_ref: profile.evals_ref ?? [],
      })),
      understanding_checks: understandingChecks,
      learning_loop: {
        retrieve: "Use artifact index, knowledge cards, profiles, routing, and eval files.",
        reason: "Route work through profile purpose, OpenRouter slot hints, and task class.",
        critique: "Apply profile guardrails, quality gate, failure modes, and eval references.",
        remember:
          "Persist outputs as artifacts, queue entries, receipts, and future knowledge cards.",
      },
      hard_blocks: [
        "no live trading",
        "no portfolio mutation",
        "no live security scanning or probing",
        "no webhook/workflow activation without approval",
        "no secrets in artifacts",
      ],
      next_internal_tasks: ["T02", "T03", "T12", "T13", "T14", "T15", "T16"],
    });
  } catch (err) {
    return jsonResponse(
      {
        ok: false,
        error: "learning_status_unavailable",
        detail: String(err),
      },
      500,
    );
  }
}
