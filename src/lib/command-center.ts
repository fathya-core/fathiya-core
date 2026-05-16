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
import playbook001Raw from "../../knowledge/playbooks/PLAYBOOK_001_CORPUS_INTAKE_KNOWLEDGE_CONVERSION.md?raw";
import playbook002Raw from "../../knowledge/playbooks/PLAYBOOK_002_AGENT_MACHINE_WORKFLOW_INTELLIGENCE_INTAKE.md?raw";
import playbook003Raw from "../../knowledge/playbooks/PLAYBOOK_003_RUNTIME_QUEUE_RECEIPT_LEDGER.md?raw";
import playbook004Raw from "../../knowledge/playbooks/PLAYBOOK_004_TOOL_CONTRACT_RESOLVER.md?raw";
import playbook005Raw from "../../knowledge/playbooks/PLAYBOOK_005_SCOPE_AUTHORIZATION_PREPARATION.md?raw";
import playbook006Raw from "../../knowledge/playbooks/PLAYBOOK_006_CRYPTO_RADAR_SIGNAL_INTAKE.md?raw";
import playbook007Raw from "../../knowledge/playbooks/PLAYBOOK_007_DAILY_INTAKE_AUTOMATION.md?raw";
import playbook008Raw from "../../knowledge/playbooks/PLAYBOOK_008_COMMAND_CENTER_UI_REQUIREMENTS.md?raw";
import playbook009Raw from "../../knowledge/playbooks/PLAYBOOK_009_MODEL_ROUTER_COST_AWARE_INFERENCE.md?raw";

type StatusTone = "neutral" | "good" | "warn" | "danger" | "info";

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
    sourceType: "canonical" | "derived";
  }>;
  cryptoRadar: Array<{
    signalId: string;
    assetOrSector: string;
    narrative: string;
    catalyst: string;
    timeframe: string;
    riskFactors: string[];
    invalidation: string;
    confidence: string;
    status: string;
    sourceType: "canonical" | "derived";
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
    sourceType: "canonical" | "derived";
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
    sourceType: "canonical" | "derived";
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
    value.includes("draft")
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

  const playbooks = PLAYBOOK_FILES.map((playbook) =>
    buildPlaybookView(playbook.path, playbook.raw, backboneValidation.validation_date),
  );
  const queueEntries = runtimeQueue.queue_entries ?? [];
  const receipts = receiptLedger.receipts ?? [];
  const blockedItemsCount =
    normalizeTextList(awareness.blocked_items).length +
    queueEntries.filter((entry) => entry.status === "blocked").length;
  const latestReceiptsCount = (awareness.latest_receipts?.length ?? 0) || receipts.length;
  const activeQueueCount =
    awareness.active_queue_count ||
    queueEntries.filter((entry) => ["queued", "running", "waiting_approval"].includes(entry.status))
      .length;

  return {
    generatedAt: new Date().toISOString(),
    loaderMode: "bundled-knowledge-files",
    loaderNote:
      "Command Center v0 is hydrated from bundled local knowledge files. Where live operational arrays are still empty, the adapter derives policy-aware fallback rows from the backbone playbooks and registries.",
    overview: {
      currentFocus: awareness.current_focus ?? "Command Center v0 bootstrap",
      activeQueueCount,
      blockedItemsCount,
      latestReceiptsCount,
      openPrCount: awareness.open_prs?.length ?? 0,
      activeAgentsCount: awareness.active_agents?.length ?? 0,
      nextRecommendedAction:
        awareness.next_recommended_action ??
        "Create the first runtime queue entry, then record a receipt so the UI begins reflecting live state.",
      validationStatus: backboneValidation.overall_status,
      warningsCount: backboneValidation.warnings.length,
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
        label: "Derived fallback lanes",
        path: "knowledge/playbooks/PLAYBOOK_005_*.md + PLAYBOOK_006_*.md + approval_policy_registry_v0.json",
        kind: "derived",
        note: "Used for Scope/Auth, Crypto Radar, and Approval Queue until live entries exist.",
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
    cryptoRadar: buildCryptoRadarRows(retrievalSummary, approvalPolicyRegistry),
    scopeAuthorization: buildScopeAuthorizationRows(),
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
        sourceType: "derived",
      },
    ],
    cryptoRadar: [],
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
      sourceType: "derived" as const,
    },
  ];
}

function buildCryptoRadarRows(
  retrievalSummary: RetrievalSummary,
  approvalPolicyRegistry: ApprovalPolicyRegistry,
) {
  const cryptoCount =
    retrievalSummary.top_domains.find(([domain]) => domain === "crypto")?.[1] ?? 0;
  const marketExecutionClass = approvalPolicyRegistry.approval_classes.find(
    (approvalClass) => approvalClass.class_id === "approval_market_execution",
  );

  return [
    {
      signalId: "signal_bootstrap_crypto_domain",
      assetOrSector: "Crypto domain / watchlist bootstrap",
      narrative:
        cryptoCount > 0
          ? `The retrieval indexes already contain ${cryptoCount} crypto-tagged records, but no live signal cards have been routed into the runtime queue yet.`
          : "PLAYBOOK 006 is present, but the current knowledge bundle does not yet contain routed crypto signal cards.",
      catalyst: "First PLAYBOOK 006 intake batch with preserved source material",
      timeframe: "Daily monitoring",
      riskFactors: [
        "missing preserved source",
        "missing catalyst or timeframe",
        "direct market execution request",
      ],
      invalidation:
        "Do not promote beyond radar mode without source preservation, risk factors, and invalidation criteria.",
      confidence: cryptoCount > 0 ? "low_to_moderate" : "low",
      status: cryptoCount > 0 ? "monitoring" : "awaiting_sources",
      sourceType: "derived" as const,
    },
    {
      signalId: "signal_policy_market_execution_gate",
      assetOrSector: "External execution lane",
      narrative:
        "The policy layer allows radar, watchlists, and paper simulation artifacts, but blocks automated trading execution in v0.",
      catalyst: marketExecutionClass?.status ?? "separate_execution_policy_required",
      timeframe: "Until a separate execution policy exists",
      riskFactors: ["external side effects", "capital risk", "approval missing"],
      invalidation:
        "Only proceed after explicit approval queue entry plus separate market execution policy.",
      confidence: "high",
      status: "blocked",
      sourceType: "derived" as const,
    },
  ];
}

function buildScopeAuthorizationRows() {
  return [
    {
      targetId: "target_card_required_v0",
      name: "Target-specific work",
      policyUrl: "Required before Target-Specific Mode",
      scopeStatus: "blocked_missing_target_card",
      authorizationStatus: "required",
      blockedReason: "No Target Card or policy URL is present in the current knowledge bundle.",
      nextArtifact: "Target Card + Scope Map",
      receipt: "—",
      sourceType: "derived" as const,
    },
    {
      targetId: "lab_mode_local_owned_app",
      name: "Owned local app / sandbox",
      policyUrl: "Local or self-owned environment",
      scopeStatus: "ready_for_lab_mode",
      authorizationStatus: "self_authorized",
      blockedReason: "—",
      nextArtifact: "Experiment Plan / Local Checklist",
      receipt: "—",
      sourceType: "derived" as const,
    },
  ];
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
      sourceType: "derived" as const,
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
