import awarenessRaw from "../../knowledge/FATHIYA_AWARENESS_STATE.json?raw";
import approvalPolicyRaw from "../../knowledge/registries/approval_policy_registry_v0.json?raw";
import agentRegistryRaw from "../../knowledge/registries/agent_registry_v0.json?raw";
import machineTaskRegistryRaw from "../../knowledge/registries/machine_task_registry_v0.json?raw";
import modelRouterRegistryRaw from "../../knowledge/registries/model_router_registry_v0.json?raw";
import skillRegistryRaw from "../../knowledge/registries/skill_registry_v0.json?raw";
import toolContractRegistryRaw from "../../knowledge/registries/tool_contract_registry_v0.json?raw";
import workflowRegistryRaw from "../../knowledge/registries/workflow_registry_v0.json?raw";
import receiptLedgerRaw from "../../knowledge/runtime/receipt_ledger_v0.json?raw";
import runtimeQueueRaw from "../../knowledge/runtime/runtime_queue_v0.json?raw";
import retrievalSummaryRaw from "../../knowledge/retrieval_index_summary.json?raw";
import retrievalValidationRaw from "../../knowledge/retrieval_validation_report.json?raw";
import backboneValidationRaw from "../../knowledge/audit/FATHIYA_BACKBONE_VALIDATION_REPORT_v0.json?raw";
import cryptoRadarBatchRaw from "../../knowledge/crypto/radar/FATHIYA_CRYPTO_RADAR_BATCH_v0.json?raw";
import playbook001Raw from "../../knowledge/playbooks/PLAYBOOK_001_CORPUS_INTAKE_KNOWLEDGE_CONVERSION.md?raw";
import playbook002Raw from "../../knowledge/playbooks/PLAYBOOK_002_AGENT_MACHINE_WORKFLOW_INTELLIGENCE_INTAKE.md?raw";
import playbook003Raw from "../../knowledge/playbooks/PLAYBOOK_003_RUNTIME_QUEUE_RECEIPT_LEDGER.md?raw";
import playbook004Raw from "../../knowledge/playbooks/PLAYBOOK_004_TOOL_CONTRACT_RESOLVER.md?raw";
import playbook005Raw from "../../knowledge/playbooks/PLAYBOOK_005_SCOPE_AUTHORIZATION_PREPARATION.md?raw";
import playbook006Raw from "../../knowledge/playbooks/PLAYBOOK_006_CRYPTO_RADAR_SIGNAL_INTAKE.md?raw";
import playbook007Raw from "../../knowledge/playbooks/PLAYBOOK_007_DAILY_INTAKE_AUTOMATION.md?raw";
import playbook008Raw from "../../knowledge/playbooks/PLAYBOOK_008_COMMAND_CENTER_UI_REQUIREMENTS.md?raw";
import playbook009Raw from "../../knowledge/playbooks/PLAYBOOK_009_MODEL_ROUTER_COST_AWARE_INFERENCE.md?raw";

const CRYPTO_RADAR_CARD_FILES = import.meta.glob("../../knowledge/crypto/radar/cards/*.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const TARGET_CARD_FILES = import.meta.glob("../../knowledge/security/targets/*.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const SCOPE_MAP_FILES = import.meta.glob("../../knowledge/security/scope_maps/*.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

type StatusTone = "neutral" | "good" | "warn" | "danger" | "info";

export type DataStatus = "live" | "empty" | "derived_from_backbone" | "planned";

export type DataProvenance = {
  source_file: string;
  data_status: DataStatus;
  notes: string;
};

type AwarenessState = {
  current_focus: string | null;
  last_updated: string | null;
  active_queue_count: number;
  blocked_items: Array<string | { id?: string; reason?: string; status?: string }>;
  latest_receipts: Array<string | { receipt_id?: string; path?: string; status?: string }>;
  open_prs: string[];
  active_agents: string[];
  completed_artifacts: string[];
  blockers: Array<string | { id?: string; reason?: string }>;
  next_recommended_action: string | null;
};

type RuntimeQueue = {
  queues: Record<
    string,
    {
      purpose: string;
      default_approval: boolean | string;
      allowed_outputs?: string[];
      allowed_adapters?: string[];
    }
  >;
  queue_entries: QueueEntry[];
  required_entry_fields: string[];
};

type QueueEntry = {
  id: string;
  timestamp: string;
  source: string;
  requested_by?: string;
  queue: string;
  adapter: string;
  mode: string;
  input_artifact?: string;
  expected_output: string;
  approval_required: boolean | string;
  status: string;
  receipt_path?: string | null;
  next_step: string;
};

type ReceiptLedger = {
  receipts: ReceiptEntry[];
  required_receipt_fields: string[];
  status_values: string[];
  receipt_policy: Record<string, string>;
};

type ReceiptEntry = {
  receipt_id: string;
  timestamp: string;
  source_request?: string;
  queue: string;
  adapter: string;
  input_artifact: string;
  output_artifact: string;
  status: string;
  error?: string | null;
  approval_reference?: string | null;
  next_step: string;
};

type CryptoRadarBatch = {
  batch_id: string;
  created_at: string;
  status: string;
  mode: string;
  playbook: string;
  source_file: string;
  source_brief_title: string;
  queue_entry_id: string;
  receipt_id: string;
  card_ids: string[];
  card_paths: string[];
  card_count: number;
  boundary: string;
  notes: string[];
};

type CryptoRadarCard = {
  id: string;
  title: string;
  asset_or_sector: string;
  classification: string[];
  source_file: string;
  source_urls: string[];
  timeframe: string;
  what_changed: string;
  why_it_matters: string;
  catalyst: string;
  risks: string[];
  invalidation_conditions: string[];
  confidence: string;
  status: string;
  boundary: string;
};

type TargetCard = {
  target_id: string;
  name: string;
  program: string;
  policy_url: string;
  authorization: string;
  authorized_scope: Array<{
    asset: string;
    asset_type?: string;
    asset_status: string;
    testing_status?: string;
    notes?: string;
  }>;
  forbidden_scope: string[];
  asset_types: string[];
  engagement_rules: string[];
  rate_limits: string[];
  data_handling: string[];
  reporting_channel: string;
  allowed_artifacts: string[];
  forbidden_actions: string[];
  approval_required: string;
  status: string;
  mode: string;
  assets: Array<{
    url: string;
    asset_status: string;
    testing_status?: string;
  }>;
  asset_status: string;
  boundary_note: string;
  playbook: string;
  created_at: string;
};

type ScopeMap = {
  scope_map_id: string;
  target_id: string;
  name: string;
  program: string;
  mode: string;
  authorization_status: string;
  policy_status: string;
  status: string;
  in_scope: Array<{
    asset: string;
    asset_status: string;
    allowed_activity: string;
    notes?: string;
  }>;
  out_of_scope: string[];
  unknown_scope: string[];
  requires_clarification: string[];
  next_artifacts: string[];
  boundary_note: string;
  playbook: string;
  created_at: string;
};

type AgentRegistry = {
  agents: Array<{
    agent_id: string;
    name: string;
    role: string;
    queue: string;
    capabilities: string[];
    tools: string[];
    permissions: string[];
    failure_modes: string[];
    status: string;
  }>;
};

type WorkflowRegistry = {
  workflows: Array<{
    workflow_id: string;
    name: string;
    playbook: string;
    trigger: string;
    mode: string;
    queue: string;
    steps: string[];
    adapters: string[];
    approval_required: boolean;
    receipt_required: boolean;
    status: string;
  }>;
};

type ToolContractRegistry = {
  contracts: Array<{
    tool_id: string;
    name: string;
    adapter: string;
    queue: string;
    allowed_actions: string[];
    side_effects: string[];
    approval_required: boolean;
    receipt_required: boolean;
    failure_modes: string[];
    status: string;
  }>;
};

type SkillRegistry = {
  skills: Array<{
    skill_id: string;
    name: string;
    queues: string[];
    status: string;
  }>;
};

type MachineTaskRegistry = {
  machine_tasks: Array<{
    task_id: string;
    name: string;
    queue: string;
    adapter: string;
    approval_required: boolean;
    receipt_required: boolean;
    status: string;
  }>;
};

type ModelRouterRegistry = {
  lanes: Array<{
    lane_id: string;
    name: string;
    use_when: string[];
    outputs: string[];
    approval_required: boolean;
    receipt_required: boolean;
  }>;
  fallback_rules: string[];
  cost_controls: string[];
};

type ApprovalPolicyRegistry = {
  default_rule: string;
  approval_classes: Array<{
    class_id: string;
    name: string;
    requires_approval: boolean;
    examples: string[];
    receipt_required: boolean;
    requires?: string[];
    status?: string;
  }>;
  approval_entry_fields: string[];
  status_values: string[];
};

type RetrievalSummary = {
  created_at: string;
  source_archive: string;
  counts: {
    search_records: number;
    domains: number;
    sensitivities: number;
    types: number;
    graph_neighbor_nodes: number;
    graph_edges: number;
  };
  top_domains: Array<[string, number]>;
  top_types: Array<[string, number]>;
  files: string[];
};

type RetrievalValidation = {
  validated_at: string;
  records_created: number;
  duplicate_ids: string[];
  status: string;
};

type BackboneValidation = {
  validation_date: string;
  overall_status: string;
  summary: {
    files_checked: number;
    playbooks: number;
    registries: number;
    issues_found: number;
    warnings: number;
    blocking_issues: number;
  };
  warnings: Array<{ warn_id: string; description: string }>;
  checks: {
    command_center_ui_data_sources: {
      sources: Array<{ path: string; exists: boolean }>;
    };
  };
};

export type CommandCenterSnapshot = {
  generatedAt: string;
  loaderMode: "bundled-knowledge-files" | "mock-fallback";
  loaderNote: string;
  lineage: {
    backbonePR: string;
    commandCenterPR: string;
    baseBranch: string;
    note: string;
  };
  overview: {
    currentFocus: string;
    activeQueueCount: number;
    blockedItemsCount: number;
    latestReceiptsCount: number;
    openPrCount: number;
    activeAgentsCount: number;
    nextRecommendedAction: string;
    validationStatus: string;
    warningsCount: number;
  };
  sectionProvenance: Record<string, DataProvenance>;
  sources: Array<{
    label: string;
    path: string;
    kind: "canonical" | "derived";
    note: string;
  }>;
  queueEntries: QueueEntry[];
  queueCatalog: Array<{
    name: string;
    purpose: string;
    defaultApproval: string;
    outputs: string[];
    adapters: string[];
  }>;
  runtimeRequiredFields: string[];
  receipts: ReceiptEntry[];
  receiptRequiredFields: string[];
  receiptPolicy: Array<{ queue: string; policy: string }>;
  agents: Array<{
    agentId: string;
    name: string;
    role: string;
    queue: string;
    capabilities: string[];
    tools: string[];
    permissions: string[];
    status: string;
    failureModes: string[];
  }>;
  workflows: Array<{
    workflowId: string;
    name: string;
    playbook: string;
    trigger: string;
    queue: string;
    mode: string;
    adapters: string[];
    status: string;
  }>;
  playbooks: Array<{
    playbookId: string;
    title: string;
    status: string;
    purpose: string;
    requiredFiles: string[];
    nextPlaybook: string;
    lastValidation: string;
  }>;
  toolContracts: Array<{
    toolId: string;
    name: string;
    adapter: string;
    queue: string;
    allowedActions: string[];
    sideEffects: string[];
    approvalRequired: boolean;
    receiptRequired: boolean;
    failureModes: string[];
    status: string;
  }>;
  dailyIntake: Array<{
    source: string;
    capturedCount: number;
    duplicates: number;
    classifiedDomains: string[];
    cardsDrafted: number;
    blockers: string[];
    receipts: string[];
    nextActions: string[];
    sourceType: "canonical" | "derived_from_backbone";
  }>;
  cryptoRadarBatch: {
    batchId: string;
    createdAt: string;
    status: string;
    mode: string;
    playbook: string;
    sourceFile: string;
    queueEntryId: string;
    receiptId: string;
    cardCount: number;
    boundary: string;
    notes: string[];
  } | null;
  cryptoRadar: Array<{
    id: string;
    title: string;
    assetOrSector: string;
    classification: string[];
    sourceFile: string;
    sourceUrls: string[];
    timeframe: string;
    whatChanged: string;
    whyItMatters: string;
    catalyst: string;
    risks: string[];
    invalidationConditions: string[];
    confidence: string;
    status: string;
    boundary: string;
  }>;
  targetCards: Array<{
    targetId: string;
    name: string;
    program: string;
    policyUrl: string;
    authorization: string;
    status: string;
    mode: string;
    assetStatus: string;
    reportingChannel: string;
    approvalRequired: string;
    allowedArtifacts: string[];
    forbiddenActions: string[];
    engagementRules: string[];
    rateLimits: string[];
    dataHandling: string[];
    boundaryNote: string;
    playbook: string;
    createdAt: string;
    assets: Array<{
      url: string;
      assetStatus: string;
      testingStatus: string;
    }>;
  }>;
  scopeMaps: Array<{
    scopeMapId: string;
    targetId: string;
    name: string;
    program: string;
    mode: string;
    authorizationStatus: string;
    policyStatus: string;
    status: string;
    boundaryNote: string;
    nextArtifacts: string[];
    outOfScope: string[];
    unknownScope: string[];
    requiresClarification: string[];
    playbook: string;
    createdAt: string;
    inScope: Array<{
      asset: string;
      assetStatus: string;
      allowedActivity: string;
      notes: string;
    }>;
  }>;
  scopeAuthorization: Array<{
    targetId: string;
    name: string;
    policyUrl: string;
    scopeStatus: string;
    authorizationStatus: string;
    blockedReason: string;
    nextArtifact: string;
    receipt: string;
    sourceType: "canonical" | "derived_from_backbone";
  }>;
  approvalQueue: Array<{
    approvalId: string;
    requestedAction: string;
    toolContract: string;
    payloadPreview: string;
    sideEffects: string[];
    rollbackOrRecovery: string;
    requester: string;
    status: string;
    sourceType: "canonical" | "derived_from_backbone";
  }>;
  registriesSummary: {
    workflowCount: number;
    skillCount: number;
    machineTaskCount: number;
    modelLaneCount: number;
    approvalClassCount: number;
  };
  modelRouter: {
    lanes: Array<{
      laneId: string;
      name: string;
      useWhen: string[];
      outputs: string[];
      approvalRequired: boolean;
    }>;
    fallbackRules: string[];
    costControls: string[];
  };
  awareness: AwarenessState;
};

const PLAYBOOK_FILES = [
  {
    path: "knowledge/playbooks/PLAYBOOK_001_CORPUS_INTAKE_KNOWLEDGE_CONVERSION.md",
    raw: playbook001Raw,
  },
  {
    path: "knowledge/playbooks/PLAYBOOK_002_AGENT_MACHINE_WORKFLOW_INTELLIGENCE_INTAKE.md",
    raw: playbook002Raw,
  },
  { path: "knowledge/playbooks/PLAYBOOK_003_RUNTIME_QUEUE_RECEIPT_LEDGER.md", raw: playbook003Raw },
  { path: "knowledge/playbooks/PLAYBOOK_004_TOOL_CONTRACT_RESOLVER.md", raw: playbook004Raw },
  {
    path: "knowledge/playbooks/PLAYBOOK_005_SCOPE_AUTHORIZATION_PREPARATION.md",
    raw: playbook005Raw,
  },
  { path: "knowledge/playbooks/PLAYBOOK_006_CRYPTO_RADAR_SIGNAL_INTAKE.md", raw: playbook006Raw },
  { path: "knowledge/playbooks/PLAYBOOK_007_DAILY_INTAKE_AUTOMATION.md", raw: playbook007Raw },
  {
    path: "knowledge/playbooks/PLAYBOOK_008_COMMAND_CENTER_UI_REQUIREMENTS.md",
    raw: playbook008Raw,
  },
  {
    path: "knowledge/playbooks/PLAYBOOK_009_MODEL_ROUTER_COST_AWARE_INFERENCE.md",
    raw: playbook009Raw,
  },
] as const;

export function loadCommandCenterSnapshot(): CommandCenterSnapshot {
  try {
    return buildSnapshot();
  } catch (error) {
    return buildFallbackSnapshot(String(error));
  }
}

export function getStatusTone(status: string): StatusTone {
  const value = status.toLowerCase();
  if (
    value.includes("pass") ||
    value.includes("complete") ||
    value.includes("available") ||
    value.includes("active") ||
    value.includes("approved") ||
    value.includes("core") ||
    value.includes("ready")
  ) {
    return "good";
  }
  if (
    value.includes("warn") ||
    value.includes("review") ||
    value.includes("planned") ||
    value.includes("waiting") ||
    value.includes("draft") ||
    value.includes("needs_") ||
    value.includes("needs ")
  ) {
    return "warn";
  }
  if (value.includes("block") || value.includes("fail") || value.includes("reject")) {
    return "danger";
  }
  if (value.includes("run") || value.includes("queue") || value.includes("monitor")) {
    return "info";
  }
  return "neutral";
}

function buildSnapshot(): CommandCenterSnapshot {
  const awareness = parseJson<AwarenessState>(awarenessRaw, "awareness");
  const runtimeQueue = parseJson<RuntimeQueue>(runtimeQueueRaw, "runtime queue");
  const receiptLedger = parseJson<ReceiptLedger>(receiptLedgerRaw, "receipt ledger");
  const agentRegistry = parseJson<AgentRegistry>(agentRegistryRaw, "agent registry");
  const workflowRegistry = parseJson<WorkflowRegistry>(workflowRegistryRaw, "workflow registry");
  const toolContractRegistry = parseJson<ToolContractRegistry>(
    toolContractRegistryRaw,
    "tool contract registry",
  );
  const skillRegistry = parseJson<SkillRegistry>(skillRegistryRaw, "skill registry");
  const machineTaskRegistry = parseJson<MachineTaskRegistry>(
    machineTaskRegistryRaw,
    "machine task registry",
  );
  const modelRouterRegistry = parseJson<ModelRouterRegistry>(
    modelRouterRegistryRaw,
    "model router registry",
  );
  const approvalPolicyRegistry = parseJson<ApprovalPolicyRegistry>(
    approvalPolicyRaw,
    "approval policy registry",
  );
  const retrievalSummary = parseJson<RetrievalSummary>(retrievalSummaryRaw, "retrieval summary");
  const retrievalValidation = parseJson<RetrievalValidation>(
    retrievalValidationRaw,
    "retrieval validation",
  );
  const backboneValidation = parseJson<BackboneValidation>(
    backboneValidationRaw,
    "backbone validation",
  );
  const cryptoRadarBatch = parseJson<CryptoRadarBatch>(cryptoRadarBatchRaw, "crypto radar batch");
  const cryptoRadar = buildCryptoRadarCards(cryptoRadarBatch);
  const targetCards = buildTargetCards();
  const scopeMaps = buildScopeMaps();

  const playbooks = PLAYBOOK_FILES.map((playbook) =>
    buildPlaybookView(playbook.path, playbook.raw, backboneValidation.validation_date),
  );
  const queueEntries = runtimeQueue.queue_entries ?? [];
  const receipts = receiptLedger.receipts ?? [];
  const hasQueueEntries = queueEntries.length > 0;
  const hasReceipts = receipts.length > 0;
  const liveActiveQueueCount = queueEntries.filter((entry) =>
    ["queued", "running", "waiting_approval"].includes(entry.status),
  ).length;
  const blockedItemsCount =
    normalizeTextList(awareness.blocked_items).length +
    queueEntries.filter((entry) => entry.status === "blocked").length;
  const latestReceiptsCount = hasReceipts
    ? receipts.length
    : (awareness.latest_receipts?.length ?? 0);
  const activeQueueCount = hasQueueEntries ? liveActiveQueueCount : awareness.active_queue_count;
  const hasLiveRuntimeData = hasQueueEntries || hasReceipts;
  const hasLiveCryptoRadarData = cryptoRadar.length > 0;
  const hasLiveScopeAuthorizationData = targetCards.length > 0 || scopeMaps.length > 0;

  return {
    generatedAt: new Date().toISOString(),
    loaderMode: "bundled-knowledge-files",
    loaderNote: hasLiveScopeAuthorizationData
      ? "Command Center v0 is hydrated from bundled local knowledge files. Runtime Queue, Receipt Ledger, Crypto Radar, and Scope & Authorization now render live canonical data. The first PB005 target remains explicitly in draft / needs_policy state, and no active testing is authorized."
      : hasLiveCryptoRadarData
        ? "Command Center v0 is hydrated from bundled local knowledge files. Runtime Queue, Receipt Ledger, and Crypto Radar now render live canonical data, while sections with no target-specific artifacts still show explicit empty states."
        : hasLiveRuntimeData
          ? "Command Center v0 is hydrated from bundled local knowledge files. Runtime Queue and Receipt Ledger render live canonical data, while sections with no live data still show explicit empty states."
          : "Command Center v0 is hydrated from bundled local knowledge files. Sections with no live data show explicit empty states. Approval Queue rows are derived from the backbone policy registry and labeled accordingly.",
    lineage: {
      backbonePR: "PR #5 — Validate Operating Backbone v0",
      commandCenterPR: hasLiveScopeAuthorizationData
        ? "PB005 — FATHIYA Core owned-surface scope/auth live target prep + PR chain stabilization"
        : "PB006 — FATHIYA Crypto Radar live batch v0",
      baseBranch: hasLiveScopeAuthorizationData
        ? "cursor/crypto-radar-live-v0"
        : "cursor/command-center-live-queue-v0",
      note: hasLiveScopeAuthorizationData
        ? "This layer builds on the ordered PR chain through the live PB006 Crypto Radar batch, then adds the first canonical PB005 Target Card and Scope Map so Scope & Authorization renders live in preparation-only mode with a needs_policy boundary."
        : hasLiveCryptoRadarData
          ? "This layer builds on the validated PR #5 Backbone checkpoint and the existing live runtime queue and receipt ledger, then adds the first PB006 Crypto Radar batch so the Command Center renders four canonical monitoring cards."
          : hasLiveRuntimeData
            ? "This layer builds on the validated PR #5 Backbone checkpoint and the existing live runtime queue and receipt ledger."
            : "The Backbone provides the canonical knowledge files that this UI reads.",
    },
    overview: {
      currentFocus:
        awareness.current_focus ??
        (hasLiveScopeAuthorizationData
          ? "Scope & authorization preparation for owned FATHIYA assets"
          : hasLiveRuntimeData
            ? "Command Center live runtime visibility"
            : "Command Center v0 bootstrap"),
      activeQueueCount,
      blockedItemsCount,
      latestReceiptsCount,
      openPrCount: awareness.open_prs?.length ?? 0,
      activeAgentsCount: awareness.active_agents?.length ?? 0,
      nextRecommendedAction:
        awareness.next_recommended_action ??
        (hasLiveScopeAuthorizationData
          ? "Publish the formal written FATHIYA Core policy before any live testing or external target activity; until then, keep the Target Card in preparation-only needs_policy state."
          : hasLiveRuntimeData
            ? "Review the first live runtime queue and receipt ledger rows, then continue promoting real runtime activity into additional sections."
            : "Create the first runtime queue entry, then record a receipt so the UI begins reflecting live state."),
      validationStatus: backboneValidation.overall_status,
      warningsCount: backboneValidation.warnings.length,
    },
    sectionProvenance: {
      overview: {
        source_file:
          "knowledge/FATHIYA_AWARENESS_STATE.json, knowledge/audit/FATHIYA_BACKBONE_VALIDATION_REPORT_v0.json",
        data_status: "live",
        notes: "Metrics computed from awareness state and backbone validation report.",
      },
      runtimeQueue: {
        source_file: "knowledge/runtime/runtime_queue_v0.json",
        data_status: hasQueueEntries ? "live" : "empty",
        notes: hasQueueEntries
          ? "Live queue rows are read directly from queue_entries, including the command-center-hardening task, the PB006 crypto radar intake batch, and the PB005 scope/auth target-preparation batch."
          : "Queue catalog is populated but queue_entries array is empty. Schema is ready for first routed task.",
      },
      receiptLedger: {
        source_file: "knowledge/runtime/receipt_ledger_v0.json",
        data_status: hasReceipts ? "live" : "empty",
        notes: hasReceipts
          ? "Live receipt rows are read directly from receipts, including the command-center-hardening receipt, the PB006 crypto radar batch receipt, and the PB005 scope/auth preparation receipt."
          : "Receipt policy and required fields are populated. Receipts array is empty until first task completes.",
      },
      agents: {
        source_file:
          "knowledge/registries/agent_registry_v0.json, knowledge/registries/workflow_registry_v0.json",
        data_status: "live",
        notes: "Agent and workflow registries are populated from validated backbone files.",
      },
      playbooks: {
        source_file: "knowledge/playbooks/PLAYBOOK_*.md",
        data_status: "live",
        notes:
          "Parsed from 9 markdown playbooks. Status, purpose, and chain links extracted at load time.",
      },
      toolContracts: {
        source_file:
          "knowledge/registries/tool_contract_registry_v0.json, knowledge/registries/model_router_registry_v0.json",
        data_status: "live",
        notes: "Tool contracts and model router lanes from validated registries.",
      },
      dailyIntake: {
        source_file:
          "knowledge/retrieval_index_summary.json, knowledge/retrieval_validation_report.json",
        data_status: "derived_from_backbone",
        notes:
          "Row 1 uses canonical retrieval data. Row 2 is a derived summary from backbone validation. No live daily batch dataset exists yet.",
      },
      cryptoRadar: {
        source_file:
          "knowledge/crypto/radar/FATHIYA_CRYPTO_RADAR_BATCH_v0.json, knowledge/crypto/radar/cards/*.json",
        data_status: hasLiveCryptoRadarData ? "live" : "planned",
        notes: hasLiveCryptoRadarData
          ? "Canonical PB006 radar data now renders from the preserved Manus source brief, the batch manifest, and four card files. Boundaries remain research and monitoring only with no trading execution."
          : "No live signal-card dataset exists. PB006 defines the intake process. Signals will appear once the first PB006 batch runs.",
      },
      scopeAuthorization: {
        source_file: hasLiveScopeAuthorizationData
          ? "knowledge/security/targets/TARGET_FATHIYA_CORE_OWNED_SURFACE_v0.json, knowledge/security/scope_maps/SCOPE_MAP_FATHIYA_CORE_OWNED_SURFACE_v0.json"
          : "—",
        data_status: hasLiveScopeAuthorizationData ? "live" : "planned",
        notes: hasLiveScopeAuthorizationData
          ? "Canonical PB005 target-preparation data now renders from the first owned-surface Target Card and Scope Map. The section is explicitly preparation-only with status draft / needs_policy, and no active testing is authorized."
          : "No Target Cards or scope maps exist yet. PB005 defines the preparation process.",
      },
      approvalQueue: {
        source_file:
          "knowledge/registries/approval_policy_registry_v0.json, knowledge/registries/tool_contract_registry_v0.json",
        data_status: "derived_from_backbone",
        notes:
          "Rows are derived from approval policy classes, not live approval requests. Shows which gates exist in policy.",
      },
    },
    sources: [
      {
        label: "Awareness State",
        path: "knowledge/FATHIYA_AWARENESS_STATE.json",
        kind: "canonical",
        note: "Overview focus, blockers, latest receipts, and next recommended action.",
      },
      {
        label: "Runtime Queue",
        path: "knowledge/runtime/runtime_queue_v0.json",
        kind: "canonical",
        note: "Queue catalog plus live queue entries.",
      },
      {
        label: "Receipt Ledger",
        path: "knowledge/runtime/receipt_ledger_v0.json",
        kind: "canonical",
        note: "Receipt proof layer and queue-to-receipt policy.",
      },
      {
        label: "Registries",
        path: "knowledge/registries/*.json",
        kind: "canonical",
        note: "Agents, workflows, tool contracts, skills, machine tasks, model router, and approval classes.",
      },
      {
        label: "Playbooks",
        path: "knowledge/playbooks/PLAYBOOK_*.md",
        kind: "canonical",
        note: "Parsed for status, purpose, required files, and next-playbook chain.",
      },
      {
        label: "Retrieval Summary",
        path: "knowledge/retrieval_index_summary.json",
        kind: "canonical",
        note: "Feeds Daily Intake counts and corpus coverage cards.",
      },
      {
        label: "Crypto Radar Batch",
        path: "knowledge/crypto/radar/FATHIYA_CRYPTO_RADAR_BATCH_v0.json",
        kind: "canonical",
        note: "PB006 batch manifest with card ids, receipt linkage, and monitoring boundary.",
      },
      {
        label: "Crypto Radar Source Brief",
        path: "knowledge/raw/crypto/FATHIYA_CRYPTO_RADAR_SOURCE_BRIEF_v0.md",
        kind: "canonical",
        note: "Preserved Manus brief used as the sole factual source for the first live radar batch.",
      },
      {
        label: "Security Targets",
        path: "knowledge/security/targets/*.json, knowledge/security/scope_maps/*.json",
        kind: "canonical",
        note: hasLiveScopeAuthorizationData
          ? "PB005 canonical target-preparation artifacts for owned FATHIYA surfaces. The current target is live in the UI but remains draft / needs_policy with no active testing."
          : "Reserved for future Target Cards and Scope Maps once PB005 preparation runs.",
      },
    ],
    queueEntries,
    queueCatalog: Object.entries(runtimeQueue.queues).map(([name, queue]) => ({
      name,
      purpose: queue.purpose,
      defaultApproval: formatApprovalValue(queue.default_approval),
      outputs: queue.allowed_outputs ?? [],
      adapters: queue.allowed_adapters ?? [],
    })),
    runtimeRequiredFields: runtimeQueue.required_entry_fields,
    receipts,
    receiptRequiredFields: receiptLedger.required_receipt_fields,
    receiptPolicy: Object.entries(receiptLedger.receipt_policy).map(([queue, policy]) => ({
      queue,
      policy,
    })),
    agents: agentRegistry.agents.map((agent) => ({
      agentId: agent.agent_id,
      name: agent.name,
      role: agent.role,
      queue: agent.queue,
      capabilities: agent.capabilities,
      tools: agent.tools,
      permissions: agent.permissions,
      status: agent.status,
      failureModes: agent.failure_modes,
    })),
    workflows: workflowRegistry.workflows.map((workflow) => ({
      workflowId: workflow.workflow_id,
      name: workflow.name,
      playbook: workflow.playbook,
      trigger: workflow.trigger,
      queue: workflow.queue,
      mode: workflow.mode,
      adapters: workflow.adapters,
      status: workflow.status,
    })),
    playbooks,
    toolContracts: toolContractRegistry.contracts.map((contract) => ({
      toolId: contract.tool_id,
      name: contract.name,
      adapter: contract.adapter,
      queue: contract.queue,
      allowedActions: contract.allowed_actions,
      sideEffects: contract.side_effects,
      approvalRequired: contract.approval_required,
      receiptRequired: contract.receipt_required,
      failureModes: contract.failure_modes,
      status: contract.status,
    })),
    dailyIntake: buildDailyIntakeRows(
      retrievalSummary,
      retrievalValidation,
      awareness,
      receiptLedger,
      backboneValidation,
    ),
    cryptoRadarBatch: {
      batchId: cryptoRadarBatch.batch_id,
      createdAt: cryptoRadarBatch.created_at,
      status: cryptoRadarBatch.status,
      mode: cryptoRadarBatch.mode,
      playbook: cryptoRadarBatch.playbook,
      sourceFile: cryptoRadarBatch.source_file,
      queueEntryId: cryptoRadarBatch.queue_entry_id,
      receiptId: cryptoRadarBatch.receipt_id,
      cardCount: cryptoRadarBatch.card_count,
      boundary: cryptoRadarBatch.boundary,
      notes: cryptoRadarBatch.notes,
    },
    cryptoRadar,
    targetCards: targetCards.map((card) => ({
      targetId: card.target_id,
      name: card.name,
      program: card.program,
      policyUrl: card.policy_url,
      authorization: card.authorization,
      status: card.status,
      mode: card.mode,
      assetStatus: card.asset_status,
      reportingChannel: card.reporting_channel,
      approvalRequired: card.approval_required,
      allowedArtifacts: card.allowed_artifacts,
      forbiddenActions: card.forbidden_actions,
      engagementRules: card.engagement_rules,
      rateLimits: card.rate_limits,
      dataHandling: card.data_handling,
      boundaryNote: card.boundary_note,
      playbook: card.playbook,
      createdAt: card.created_at,
      assets: card.assets.map((asset) => ({
        url: asset.url,
        assetStatus: asset.asset_status,
        testingStatus: asset.testing_status ?? "not_specified",
      })),
    })),
    scopeMaps: scopeMaps.map((scopeMap) => ({
      scopeMapId: scopeMap.scope_map_id,
      targetId: scopeMap.target_id,
      name: scopeMap.name,
      program: scopeMap.program,
      mode: scopeMap.mode,
      authorizationStatus: scopeMap.authorization_status,
      policyStatus: scopeMap.policy_status,
      status: scopeMap.status,
      boundaryNote: scopeMap.boundary_note,
      nextArtifacts: scopeMap.next_artifacts,
      outOfScope: scopeMap.out_of_scope,
      unknownScope: scopeMap.unknown_scope,
      requiresClarification: scopeMap.requires_clarification,
      playbook: scopeMap.playbook,
      createdAt: scopeMap.created_at,
      inScope: scopeMap.in_scope.map((item) => ({
        asset: item.asset,
        assetStatus: item.asset_status,
        allowedActivity: item.allowed_activity,
        notes: item.notes ?? "—",
      })),
    })),
    scopeAuthorization: buildScopeAuthorizationRows(targetCards, scopeMaps),
    approvalQueue: buildApprovalQueueRows(approvalPolicyRegistry, toolContractRegistry),
    registriesSummary: {
      workflowCount: workflowRegistry.workflows.length,
      skillCount: skillRegistry.skills.length,
      machineTaskCount: machineTaskRegistry.machine_tasks.length,
      modelLaneCount: modelRouterRegistry.lanes.length,
      approvalClassCount: approvalPolicyRegistry.approval_classes.length,
    },
    modelRouter: {
      lanes: modelRouterRegistry.lanes.map((lane) => ({
        laneId: lane.lane_id,
        name: lane.name,
        useWhen: lane.use_when,
        outputs: lane.outputs,
        approvalRequired: lane.approval_required,
      })),
      fallbackRules: modelRouterRegistry.fallback_rules,
      costControls: modelRouterRegistry.cost_controls,
    },
    awareness,
  };
}

function buildFallbackSnapshot(error: string): CommandCenterSnapshot {
  return {
    generatedAt: new Date().toISOString(),
    loaderMode: "mock-fallback",
    loaderNote:
      "The canonical knowledge bundle could not be parsed, so the adapter returned a documented fallback snapshot. Fix the parse error below to restore canonical file-backed rendering.",
    lineage: {
      backbonePR: "PR #5 — Validate Operating Backbone v0",
      commandCenterPR: "PR #6 — Add initial FATHIYA Command Center v0",
      baseBranch: "cursor/validate-backbone-v0",
      note: "Loader error — lineage cannot be verified until knowledge files parse successfully.",
    },
    overview: {
      currentFocus: "Knowledge loader recovery",
      activeQueueCount: 0,
      blockedItemsCount: 1,
      latestReceiptsCount: 0,
      openPrCount: 0,
      activeAgentsCount: 0,
      nextRecommendedAction: "Repair the Command Center knowledge adapter parse failure.",
      validationStatus: "loader_error",
      warningsCount: 1,
    },
    sectionProvenance: {
      overview: {
        source_file: "—",
        data_status: "empty",
        notes: "Loader error: " + error,
      },
    },
    sources: [
      {
        label: "Fallback snapshot",
        path: "src/lib/command-center.ts",
        kind: "derived",
        note: error,
      },
    ],
    queueEntries: [],
    queueCatalog: [],
    runtimeRequiredFields: [],
    receipts: [],
    receiptRequiredFields: [],
    receiptPolicy: [],
    agents: [],
    workflows: [],
    playbooks: [],
    toolContracts: [],
    dailyIntake: [
      {
        source: "adapter fallback",
        capturedCount: 0,
        duplicates: 0,
        classifiedDomains: ["loader_error"],
        cardsDrafted: 0,
        blockers: [error],
        receipts: [],
        nextActions: ["Fix local knowledge imports or malformed JSON."],
        sourceType: "derived_from_backbone",
      },
    ],
    cryptoRadarBatch: null,
    cryptoRadar: [],
    targetCards: [],
    scopeMaps: [],
    scopeAuthorization: [],
    approvalQueue: [],
    registriesSummary: {
      workflowCount: 0,
      skillCount: 0,
      machineTaskCount: 0,
      modelLaneCount: 0,
      approvalClassCount: 0,
    },
    modelRouter: {
      lanes: [],
      fallbackRules: [],
      costControls: [],
    },
    awareness: {
      current_focus: "Knowledge loader recovery",
      last_updated: null,
      active_queue_count: 0,
      blocked_items: [error],
      latest_receipts: [],
      open_prs: [],
      active_agents: [],
      completed_artifacts: [],
      blockers: [error],
      next_recommended_action: "Repair the Command Center knowledge adapter parse failure.",
    },
  };
}

function buildPlaybookView(path: string, raw: string, validationDate: string) {
  const title = getMarkdownHeading(raw) ?? path.split("/").pop() ?? path;
  return {
    playbookId: path.match(/PLAYBOOK_(\d+)/)?.[1]?.padStart(3, "0")
      ? `PB${path.match(/PLAYBOOK_(\d+)/)?.[1]}`
      : title,
    title,
    status: readSectionValue(raw, "Status") ?? "Unknown",
    purpose: readSectionValue(raw, "Purpose") ?? "Purpose not captured.",
    requiredFiles: extractRequiredFiles(raw),
    nextPlaybook: readSectionValue(raw, "Next playbook") ?? "—",
    lastValidation: validationDate,
  };
}

function buildDailyIntakeRows(
  retrievalSummary: RetrievalSummary,
  retrievalValidation: RetrievalValidation,
  awareness: AwarenessState,
  receiptLedger: ReceiptLedger,
  backboneValidation: BackboneValidation,
) {
  const topDomains = retrievalSummary.top_domains
    .slice(0, 3)
    .map(([domain, count]) => `${domain} (${count})`);
  const knowledgeCardCount =
    retrievalSummary.top_types.find(([type]) => type === "knowledge_card")?.[1] ?? 0;
  return [
    {
      source: retrievalSummary.source_archive,
      capturedCount: retrievalValidation.records_created,
      duplicates: retrievalValidation.duplicate_ids.length,
      classifiedDomains: topDomains,
      cardsDrafted: knowledgeCardCount,
      blockers:
        awareness.blockers.length > 0
          ? normalizeTextList(awareness.blockers)
          : ["No recorded blockers in retrieval validation."],
      receipts:
        receiptLedger.receipts.length > 0
          ? receiptLedger.receipts.slice(0, 3).map((receipt) => receipt.receipt_id)
          : ["No intake receipts recorded yet."],
      nextActions: [
        awareness.next_recommended_action ??
          "Run the first PLAYBOOK 007 intake batch against new sources.",
      ],
      sourceType: "canonical" as const,
    },
    {
      source: "Backbone validation audit",
      capturedCount: backboneValidation.summary.files_checked,
      duplicates: 0,
      classifiedDomains: [
        `${backboneValidation.summary.playbooks} playbooks`,
        `${backboneValidation.summary.registries} registries`,
      ],
      cardsDrafted: 0,
      blockers:
        backboneValidation.warnings.length > 0
          ? backboneValidation.warnings.map((warning) => warning.warn_id)
          : ["No warnings"],
      receipts: ["knowledge/audit/FATHIYA_BACKBONE_VALIDATION_REPORT_v0.md"],
      nextActions: [
        "Promote live queue entries so the Command Center shifts from audit mode to runtime mode.",
      ],
      sourceType: "derived_from_backbone" as const,
    },
  ];
}

function buildCryptoRadarCards(batch: CryptoRadarBatch): CommandCenterSnapshot["cryptoRadar"] {
  const cardsById = Object.values(CRYPTO_RADAR_CARD_FILES)
    .map((raw, index) => parseJson<CryptoRadarCard>(raw, `crypto radar card ${index + 1}`))
    .reduce<Record<string, CryptoRadarCard>>((accumulator, card) => {
      accumulator[card.id] = card;
      return accumulator;
    }, {});

  return batch.card_ids
    .map((cardId) => cardsById[cardId])
    .filter((card): card is CryptoRadarCard => Boolean(card))
    .map((card) => ({
      id: card.id,
      title: card.title,
      assetOrSector: card.asset_or_sector,
      classification: card.classification,
      sourceFile: card.source_file,
      sourceUrls: card.source_urls,
      timeframe: card.timeframe,
      whatChanged: card.what_changed,
      whyItMatters: card.why_it_matters,
      catalyst: card.catalyst,
      risks: card.risks,
      invalidationConditions: card.invalidation_conditions,
      confidence: card.confidence,
      status: card.status,
      boundary: card.boundary,
    }));
}

function buildTargetCards() {
  return Object.values(TARGET_CARD_FILES)
    .map((raw, index) => parseJson<TargetCard>(raw, `target card ${index + 1}`))
    .sort((left, right) => left.target_id.localeCompare(right.target_id));
}

function buildScopeMaps() {
  return Object.values(SCOPE_MAP_FILES)
    .map((raw, index) => parseJson<ScopeMap>(raw, `scope map ${index + 1}`))
    .sort((left, right) => left.scope_map_id.localeCompare(right.scope_map_id));
}

function buildScopeAuthorizationRows(
  targetCards: TargetCard[],
  scopeMaps: ScopeMap[],
): CommandCenterSnapshot["scopeAuthorization"] {
  const scopeMapsByTarget = scopeMaps.reduce<Record<string, ScopeMap>>((accumulator, scopeMap) => {
    accumulator[scopeMap.target_id] = scopeMap;
    return accumulator;
  }, {});

  return targetCards.map((card) => {
    const scopeMap = scopeMapsByTarget[card.target_id];
    return {
      targetId: card.target_id,
      name: card.name,
      policyUrl: card.policy_url,
      scopeStatus: scopeMap?.status ?? card.status,
      authorizationStatus: card.authorization,
      blockedReason:
        scopeMap?.boundary_note ??
        "Preparation-only mode remains in effect until a formal written policy exists.",
      nextArtifact: scopeMap?.next_artifacts?.join(", ") ?? "Scope Map",
      receipt: "receipt-2026-05-16-fathiya-pb005-target-preparation-batch-v0",
      sourceType: "canonical" as const,
    };
  });
}

function buildApprovalQueueRows(
  approvalPolicyRegistry: ApprovalPolicyRegistry,
  toolContractRegistry: ToolContractRegistry,
) {
  return approvalPolicyRegistry.approval_classes
    .filter((approvalClass) => approvalClass.requires_approval)
    .map((approvalClass) => ({
      approvalId: `policy_${approvalClass.class_id}`,
      requestedAction: approvalClass.examples[0] ?? approvalClass.name,
      toolContract: inferToolContract(approvalClass.class_id, toolContractRegistry),
      payloadPreview: `${approvalClass.name} — ${approvalClass.examples.join(", ")}`,
      sideEffects: approvalClass.examples,
      rollbackOrRecovery: inferRollback(approvalClass.class_id),
      requester: "policy_layer",
      status: approvalClass.status ?? "policy_ready",
      sourceType: "derived_from_backbone" as const,
    }));
}

function inferToolContract(classId: string, toolContractRegistry: ToolContractRegistry) {
  const lookup: Record<string, string> = {
    approval_repo_write: "cursor_launch_agent / github_create_or_update_file",
    approval_external_message: "future_email_contract",
    approval_webhook_or_workflow: "n8n_workflow / zapier_mcp_action",
    approval_market_execution: "separate_market_execution_policy_required",
    approval_target_specific_external: "PLAYBOOK_005 target gate",
  };

  const hint = lookup[classId] ?? "policy_defined_contract";
  if (hint.includes("/")) {
    return hint;
  }

  const direct = toolContractRegistry.contracts.find((contract) => contract.tool_id === hint);
  return direct?.tool_id ?? hint;
}

function inferRollback(classId: string) {
  switch (classId) {
    case "approval_repo_write":
      return "Revert the branch commit or close the draft PR.";
    case "approval_external_message":
      return "Do not send until approved; if sent, issue a correction using the same channel.";
    case "approval_webhook_or_workflow":
      return "Disable the workflow, inspect logs, and write a failed receipt.";
    case "approval_market_execution":
      return "Blocked in v0; no execution should occur.";
    case "approval_target_specific_external":
      return "Return to Scope Map review and record the blocked reason.";
    default:
      return "Record the failure mode and define the next reversible step.";
  }
}

function parseJson<T>(raw: string, label: string): T {
  try {
    return JSON.parse(raw) as T;
  } catch (error) {
    throw new Error(`Failed to parse ${label}: ${String(error)}`);
  }
}

function getMarkdownHeading(raw: string) {
  const match = raw.match(/^#\s+(.+)$/m);
  return match?.[1]?.trim() ?? null;
}

function readSectionValue(raw: string, heading: string) {
  const section = getSection(raw, heading);
  if (!section) return null;
  const lines = section
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  return lines[0] ?? null;
}

function extractRequiredFiles(raw: string) {
  const section = getSection(raw, "Required files");
  if (!section) return [];

  const bulletLines = section
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.startsWith("- "))
    .map((line) => line.slice(2).trim());

  if (bulletLines.length > 0) {
    return bulletLines;
  }

  const codeBlockMatch = section.match(/```[\w]*\n([\s\S]*?)```/);
  if (!codeBlockMatch) return [];

  return codeBlockMatch[1]
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function getSection(raw: string, heading: string) {
  const escaped = heading.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`##\\s+${escaped}\\n([\\s\\S]*?)(?=\\n##\\s+|$)`);
  return raw.match(regex)?.[1]?.trim() ?? null;
}

function normalizeTextList(values: Array<string | Record<string, unknown>>) {
  return values.map((value) => {
    if (typeof value === "string") return value;
    return Object.values(value)
      .filter((item) => typeof item === "string" && item.length > 0)
      .join(" — ");
  });
}

function formatApprovalValue(value: boolean | string) {
  if (typeof value === "boolean") {
    return value ? "required" : "not_required";
  }
  return value;
}
