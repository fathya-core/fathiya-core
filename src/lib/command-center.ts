import awarenessRaw from "../../knowledge/FATHIYA_AWARENESS_STATE.json?raw";
import approvalPolicyRaw from "../../knowledge/registries/approval_policy_registry_v0.json?raw";
import agentRegistryRaw from "../../knowledge/registries/agent_registry_v0.json?raw";
import machineTaskRegistryRaw from "../../knowledge/registries/machine_task_registry_v0.json?raw";
import modelRouterRegistryRaw from "../../knowledge/registries/model_router_registry_v0.json?raw";
import operationsToolContractsRaw from "../../knowledge/registries/operations_tool_contracts_v0.json?raw";
import skillRegistryRaw from "../../knowledge/registries/skill_registry_v0.json?raw";
import toolContractRegistryRaw from "../../knowledge/registries/tool_contract_registry_v0.json?raw";
import workflowRegistryRaw from "../../knowledge/registries/workflow_registry_v0.json?raw";
import domainRoutingPlanRaw from "../../knowledge/deployment/domain_routing_plan_v0.json?raw";
import envContractRaw from "../../knowledge/deployment/env_contract_v0.json?raw";
import webhookIngressContractRaw from "../../knowledge/hooks/webhook_ingress_contract_v0.json?raw";
import mcpServerContractRaw from "../../knowledge/mcp/mcp_server_contract_v0.json?raw";
import operationsAutopilotQueueRaw from "../../knowledge/operations/operations_autopilot_queue_v0.json?raw";
import appsGptsRoutingMapRaw from "../../knowledge/routing/apps_gpts_routing_map_v1.json?raw";
import appsGptsRoutingRulesRaw from "../../knowledge/routing/apps_gpts_routing_rules_v1.json?raw";
import receiptLedgerRaw from "../../knowledge/runtime/receipt_ledger_v0.json?raw";
import runtimeQueueRaw from "../../knowledge/runtime/runtime_queue_v0.json?raw";
import sdkGatewayContractRaw from "../../knowledge/sdk/sdk_gateway_contract_v0.json?raw";
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

const DAILY_INTAKE_BATCH_FILES = import.meta.glob(
  "../../knowledge/intake/daily/*/daily_intake_batch_*.json",
  {
    query: "?raw",
    import: "default",
    eager: true,
  },
) as Record<string, string>;

const DAILY_SOURCE_MANIFEST_FILES = import.meta.glob(
  "../../knowledge/intake/daily/*/source_manifest_batch_*.json",
  {
    query: "?raw",
    import: "default",
    eager: true,
  },
) as Record<string, string>;

const DAILY_KNOWLEDGE_CARD_FILES = import.meta.glob("../../knowledge/cards/daily/*/*.json", {
  query: "?raw",
  import: "default",
  eager: true,
}) as Record<string, string>;

const RECEIPT_FILES = import.meta.glob("../../knowledge/runtime/receipts/*.json", {
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

type DailyIntakeBatch = {
  batch_id: string;
  cycle: string;
  created_at: string;
  source_count: number;
  ingested_count: number;
  pending_count: number;
  themes: string[];
  derived_cards: string[];
  queue_id: string;
  receipt_id: string;
  next_steps: string[];
};

type DailyKnowledgeCard = {
  card_id: string;
  title: string;
  domain: string;
  classification: string[];
  created_at: string;
  source_files: string[];
  source_batch: string;
  status: string;
  receipt_id: string;
};

type SourceManifest = {
  batch_id: string;
  created_at: string;
  cycle: string;
  source_count: number;
  sources: Array<{
    filename: string;
    source_type: string;
    primary_topic: string;
    ingestion_status: string;
    intended_artifact_class: string;
    notes?: string;
  }>;
};

type AppsGptsRoutingMap = {
  status: string;
  created_at: string;
  source_file: {
    filename: string;
    source_manifest: string;
    daily_intake_batch: string;
  };
  apps_summary: {
    total_app_rows: number;
  };
  gpts_summary: {
    total_gpt_rows: number;
  };
  workflow_templates: Array<{
    workflow_id: string;
    name: string;
  }>;
  receipts: {
    source_daily_intake_receipt: string;
    integration_receipt: string;
  };
};

type AppsGptsRoutingRules = {
  status: string;
  global_hard_rules: Array<{
    rule_id: string;
    severity: string;
    rule: string;
  }>;
  activation_requirements: string[];
};

type OperationsAutopilotQueue = {
  status: string;
  purpose: string;
  queues: Record<
    string,
    {
      purpose: string;
      default_status: string;
      allowed_statuses: string[];
    }
  >;
  entry_fields: string[];
  entries: Array<{
    entry_id: string;
    timestamp: string;
    tool_contract_id: string;
    approval_class: string;
    operation_type: string;
    description: string;
    payload_preview: string;
    target_reference: string;
    credential_reference?: string | null;
    scope_map_reference?: string | null;
    status: string;
    approval_id?: string | null;
    receipt_path?: string | null;
    rollback_note_path?: string | null;
    requested_by: string;
    notes?: string[];
  }>;
};

type OperationsToolContractRegistry = {
  status: string;
  contracts: Array<{
    tool_id: string;
    name: string;
    adapter: string;
    queue: string;
    approval_class: string;
    status: string;
  }>;
};

type IndividualReceipt = {
  receipt_id: string;
  timestamp: string;
  source_request?: string;
  queue: string;
  adapter: string;
  mode?: string;
  output_artifact?: string;
  status: string;
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

type DomainRoutingPlan = {
  schema_version: string;
  description: string;
  last_updated: string;
  status: string;
  adr: string;
  domains: Array<{
    domain: string;
    role: string;
    description: string;
    status: string;
    routes?: Array<{
      path: string;
      handler: string;
      auth?: boolean;
    }>;
    v1_routes?: Array<{
      path: string;
      handler: string;
    }>;
    command_center_panels?: string[];
    auth_required: boolean;
    env_vars?: string[];
  }>;
  no_live_dns_rule: {
    enforced: boolean;
    description: string;
  };
  no_live_webhooks_rule: {
    enforced: boolean;
    description: string;
  };
  no_secrets_rule: {
    enforced: boolean;
    description: string;
  };
};

type EnvContract = {
  schema_version: string;
  description: string;
  last_updated: string;
  adr: string;
  rules: {
    no_secret_values: boolean;
    names_only: boolean;
    vite_prefix_for_client: string;
    no_prefix_for_server: string;
  };
  env_vars: Array<{
    name: string;
    scope: "client" | "server";
    required: boolean;
    description: string;
    used_by: string[];
    default: string | null;
    secret: boolean;
  }>;
  deployment_checklist: string[];
  command_center_display: {
    description: string;
    required_vars: string[];
  };
};

type McpServerContract = {
  schema_version: string;
  description: string;
  last_updated: string;
  adr: string;
  server: {
    name: string;
    version: string;
    base_url_env: string;
    endpoint: string;
  };
  protocol: {
    type: string;
    description: string;
    supported_modes: Record<string, boolean>;
    future_v1: {
      planned: boolean;
      features: string[];
    };
  };
  tools: Array<{
    name: string;
    description: string;
    read_only: boolean;
    requires_approval: boolean;
  }>;
  quality_gate: {
    enforced: boolean;
    forbidden_patterns: string[];
    arabic_forbidden: boolean;
    allowed_signal_directions: string[];
  };
  model_routing: {
    enabled: boolean;
    registry: string;
    slots: string[];
  };
};

type SdkGatewayContract = {
  schema_version: string;
  description: string;
  last_updated: string;
  adr: string;
  gateway: {
    name: string;
    version: string;
    base_url_env: string;
    planned_domain: string;
  };
  endpoints: Array<{
    method: string;
    path: string;
    description: string;
    auth_required: boolean;
  }>;
  rate_limits: {
    v0: string;
    v1_planned: string;
  };
  auth: {
    v0: string;
    v1_planned: string;
  };
  no_supabase: boolean;
  state_source: string;
};

type WebhookIngressContract = {
  schema_version: string;
  description: string;
  last_updated: string;
  adr: string;
  ingress: {
    name: string;
    version: string;
    base_url_env: string;
    planned_domain: string;
  };
  endpoints: Array<{
    method: string;
    path: string;
    description: string;
    auth_required: boolean;
  }>;
  validation_rules: {
    required_fields: string[];
    quality_gate: string;
    no_trading_commands: boolean;
    max_content_length: number;
  };
  forwarding: {
    target_env: string;
    target_path: string;
    method: string;
    passes_receipt_id: boolean;
  };
  no_live_webhooks_rule: {
    enforced: boolean;
    description: string;
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
  latestDailyIntake: {
    batchId: string;
    cycle: string;
    createdAt: string;
    sourceCount: number;
    derivedCardCount: number;
    pendingItems: string[];
    receiptId: string;
    queueId: string;
    latestBatchDate: string;
  } | null;
  knowledgeCards: Array<{
    cardId: string;
    domain: string;
    title: string;
    status: string;
    createdAt: string;
    sourceCoverage: string;
    sourceFiles: string[];
    receiptId: string;
  }>;
  routingSummary: {
    status: string;
    sourceSpreadsheet: string;
    sourceSpreadsheetStatus: string;
    appRows: number;
    gptRows: number;
    sampleWorkflows: number;
    highLevelRules: string[];
    receiptIds: string[];
  } | null;
  operationsQueue: {
    status: string;
    purpose: string;
    stagedEntriesCount: number;
    totalEntries: number;
    entryFields: string[];
    statusBreakdown: Array<{
      status: string;
      count: number;
    }>;
    queueDefinitions: Array<{
      name: string;
      purpose: string;
      defaultStatus: string;
      allowedStatuses: string[];
    }>;
  } | null;
  operationsToolContracts: Array<{
    toolId: string;
    name: string;
    status: string;
    category: string;
    queue: string;
    approvalClass: string;
  }>;
  recentIntakeRoutingReceipts: Array<{
    receiptId: string;
    timestamp: string;
    queue: string;
    status: string;
    summary: string;
    nextStep: string;
  }>;
  deploymentPanel: {
    domainTopology: Array<{
      domain: string;
      role: string;
      description: string;
      status: string;
      authRequired: boolean;
      routes: string[];
      envVars: string[];
    }>;
    deploymentReadiness: Array<{
      check: string;
      status: string;
      detail: string;
      source: string;
    }>;
    mcpStatus: {
      name: string;
      version: string;
      endpoint: string;
      baseUrlEnv: string;
      protocolType: string;
      protocolDescription: string;
      supportedModes: Array<{
        mode: string;
        status: string;
      }>;
      toolCount: number;
      readOnlyToolCount: number;
      writeToolCount: number;
      qualityGateStatus: string;
      futureFeatures: string[];
    };
    sdkApiStatus: {
      name: string;
      version: string;
      plannedDomain: string;
      baseUrlEnv: string;
      endpoints: Array<{
        method: string;
        path: string;
        authRequired: boolean;
        description: string;
      }>;
      authStatus: string;
      rateLimitStatus: string;
      stateSource: string;
      noSupabase: boolean;
    };
    webhookIngressStatus: {
      name: string;
      version: string;
      plannedDomain: string;
      baseUrlEnv: string;
      endpoints: Array<{
        method: string;
        path: string;
        authRequired: boolean;
        description: string;
      }>;
      validationRules: string[];
      forwardingTarget: string;
      noLiveWebhooksStatus: string;
    };
    openRouterModelSlots: Array<{
      slot: string;
      envVar: string;
      required: boolean;
      status: string;
      valueSource: string;
      defaultModel: string;
      secret: boolean;
      description: string;
    }>;
    missingEnvVars: Array<{
      name: string;
      scope: string;
      required: boolean;
      secret: boolean;
      defaultValue: string;
      description: string;
      status: string;
    }>;
    recentDeploymentReceipts: Array<{
      receiptId: string;
      timestamp: string;
      queue: string;
      adapter: string;
      status: string;
      summary: string;
      nextStep: string;
    }>;
    blockers: string[];
  };
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
    value.includes("ready") ||
    value.includes("enforced") ||
    value.includes("enabled") ||
    value.includes("present") ||
    value.includes("contract")
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
  if (
    value.includes("block") ||
    value.includes("fail") ||
    value.includes("reject") ||
    value.includes("missing_required")
  ) {
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
  const domainRoutingPlan = parseJson<DomainRoutingPlan>(
    domainRoutingPlanRaw,
    "domain routing plan",
  );
  const envContract = parseJson<EnvContract>(envContractRaw, "environment contract");
  const mcpServerContract = parseJson<McpServerContract>(
    mcpServerContractRaw,
    "mcp server contract",
  );
  const sdkGatewayContract = parseJson<SdkGatewayContract>(
    sdkGatewayContractRaw,
    "sdk gateway contract",
  );
  const webhookIngressContract = parseJson<WebhookIngressContract>(
    webhookIngressContractRaw,
    "webhook ingress contract",
  );
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
  const operationsToolContracts = parseJson<OperationsToolContractRegistry>(
    operationsToolContractsRaw,
    "operations tool contracts",
  );
  const operationsAutopilotQueue = parseJson<OperationsAutopilotQueue>(
    operationsAutopilotQueueRaw,
    "operations autopilot queue",
  );
  const appsGptsRoutingMap = parseJson<AppsGptsRoutingMap>(
    appsGptsRoutingMapRaw,
    "apps/gpts routing map",
  );
  const appsGptsRoutingRules = parseJson<AppsGptsRoutingRules>(
    appsGptsRoutingRulesRaw,
    "apps/gpts routing rules",
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
  const latestDailyIntake = buildLatestDailyIntake();
  const knowledgeCards = buildLatestDailyKnowledgeCards();
  const routingSummary = buildRoutingSummary(appsGptsRoutingMap, appsGptsRoutingRules);
  const operationsQueue = buildOperationsQueueSummary(operationsAutopilotQueue);
  const operationsToolContractRows = buildOperationsToolContractRows(operationsToolContracts);
  const recentIntakeRoutingReceipts = buildRecentIntakeRoutingReceipts([
    latestDailyIntake?.receiptId,
    ...(routingSummary?.receiptIds ?? []),
  ]);
  const deploymentPanel = buildDeploymentPanel(
    domainRoutingPlan,
    envContract,
    mcpServerContract,
    sdkGatewayContract,
    webhookIngressContract,
    receiptLedger,
  );

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
    loaderNote:
      "Command Center Expansion v0 hydrates one overview surface from bundled local knowledge files across intake, daily knowledge cards, Apps/GPTs routing, staged operations, runtime queue, receipt ledger, and the validated backbone registries.",
    lineage: {
      backbonePR: "main @ fd49d932258935aa35eb552e2c433277d6de9d24",
      commandCenterPR: "FATHIYA Command Center Expansion v0",
      baseBranch: "main",
      note: "This layer builds from main after Daily Intake Cycle 001 and the Apps/GPTs Routing parse landed, then expands the Command Center so intake, knowledge cards, routing, operations staging, and recent receipts are readable from one UI while preserving existing detailed tabs.",
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
          "knowledge/intake/daily/*/daily_intake_batch_*.json, knowledge/intake/daily/*/source_manifest_batch_*.json, knowledge/cards/daily/*/*.json",
        data_status:
          Object.keys(DAILY_INTAKE_BATCH_FILES).length > 0 ? "live" : "derived_from_backbone",
        notes:
          Object.keys(DAILY_INTAKE_BATCH_FILES).length > 0
            ? `Live daily intake data from ${Object.keys(DAILY_INTAKE_BATCH_FILES).length} batch(es), ${Object.keys(DAILY_SOURCE_MANIFEST_FILES).length} source manifest(s), and ${Object.keys(DAILY_KNOWLEDGE_CARD_FILES).length} knowledge card(s).`
            : "Row 1 uses canonical retrieval data. Row 2 is a derived summary from backbone validation. No live daily batch dataset exists yet.",
      },
      routing: {
        source_file:
          "knowledge/routing/apps_gpts_routing_map_v1.json, knowledge/routing/apps_gpts_routing_rules_v1.json",
        data_status: routingSummary ? "live" : "planned",
        notes: routingSummary
          ? "Structured routing map data is live, including the spreadsheet parse status, row counts, workflow templates, and hard routing rules."
          : "Routing map parse has not been promoted yet.",
      },
      operationsQueue: {
        source_file: "knowledge/operations/operations_autopilot_queue_v0.json",
        data_status: operationsQueue && operationsQueue.totalEntries > 0 ? "live" : "empty",
        notes:
          operationsQueue && operationsQueue.totalEntries > 0
            ? "Staged operations entries now render from the operations autopilot queue."
            : "Operations queue schema and queue definitions are present, but no staged entries have been recorded yet.",
      },
      operationsToolContracts: {
        source_file: "knowledge/registries/operations_tool_contracts_v0.json",
        data_status: operationsToolContractRows.length > 0 ? "live" : "planned",
        notes:
          operationsToolContractRows.length > 0
            ? "Operations-specific tool contracts now surface staged webhook, workflow, messaging, and repo-management adapters."
            : "Operations-specific tool contracts have not been populated yet.",
      },
      runtimeAndReceipts: {
        source_file:
          "knowledge/runtime/runtime_queue_v0.json, knowledge/runtime/receipt_ledger_v0.json, knowledge/runtime/receipts/*.json",
        data_status: hasLiveRuntimeData ? "live" : "empty",
        notes: hasLiveRuntimeData
          ? "Recent receipt linkage now highlights the daily intake and routing integration receipts alongside the live runtime queue and ledger."
          : "Runtime queue and receipt ledger are wired, but no recent runtime or receipt rows are available yet.",
      },
      deploymentPanel: {
        source_file:
          "knowledge/deployment/domain_routing_plan_v0.json, knowledge/deployment/env_contract_v0.json, knowledge/mcp/mcp_server_contract_v0.json, knowledge/sdk/sdk_gateway_contract_v0.json, knowledge/hooks/webhook_ingress_contract_v0.json",
        data_status: "planned",
        notes:
          "Deployment Panel v0 is contract-backed only. It surfaces planned domains, readiness gates, MCP/API/webhook boundaries, OpenRouter model slots, missing runtime env names, and deployment receipts without deploying or changing DNS.",
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
        label: "Daily Intake Batches",
        path: "knowledge/intake/daily/*/daily_intake_batch_*.json",
        kind: "canonical",
        note:
          Object.keys(DAILY_INTAKE_BATCH_FILES).length > 0
            ? `${Object.keys(DAILY_INTAKE_BATCH_FILES).length} live daily intake batch(es) with ${Object.keys(DAILY_KNOWLEDGE_CARD_FILES).length} derived knowledge cards.`
            : "No daily intake batches exist yet. PB007 defines the intake process.",
      },
      {
        label: "Daily Intake Source Manifests",
        path: "knowledge/intake/daily/*/source_manifest_batch_*.json",
        kind: "canonical",
        note: "Operator-provided source manifests used to compute pending items and parse status.",
      },
      {
        label: "Daily Knowledge Cards",
        path: "knowledge/cards/daily/*/*.json",
        kind: "canonical",
        note: "Latest daily knowledge cards used for the compact card table in Command Center.",
      },
      {
        label: "Apps/GPTs Routing",
        path: "knowledge/routing/apps_gpts_routing_map_v1.json, knowledge/routing/apps_gpts_routing_rules_v1.json",
        kind: "canonical",
        note: "Structured spreadsheet parse facts, workflow counts, and high-level routing rules.",
      },
      {
        label: "Operations Queue",
        path: "knowledge/operations/operations_autopilot_queue_v0.json",
        kind: "canonical",
        note: "Staged operations queue definitions and any staged entries awaiting approval or execution policy.",
      },
      {
        label: "Operations Tool Contracts",
        path: "knowledge/registries/operations_tool_contracts_v0.json",
        kind: "canonical",
        note: "Operations-layer contract drafts for webhook, workflow, messaging, and repository adapters.",
      },
      {
        label: "Deployment Contracts",
        path: "knowledge/deployment/domain_routing_plan_v0.json, knowledge/deployment/env_contract_v0.json, knowledge/mcp/mcp_server_contract_v0.json, knowledge/sdk/sdk_gateway_contract_v0.json, knowledge/hooks/webhook_ingress_contract_v0.json",
        kind: "canonical",
        note: "Read-only deployment panel inputs for topology, readiness, MCP/API/webhook status, OpenRouter slots, and missing env names. No DNS, deployment, secrets, or live webhooks are changed.",
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
    latestDailyIntake,
    knowledgeCards,
    routingSummary,
    operationsQueue,
    operationsToolContracts: operationsToolContractRows,
    recentIntakeRoutingReceipts,
    deploymentPanel,
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
    latestDailyIntake: null,
    knowledgeCards: [],
    routingSummary: null,
    operationsQueue: null,
    operationsToolContracts: [],
    recentIntakeRoutingReceipts: [],
    deploymentPanel: {
      domainTopology: [],
      deploymentReadiness: [
        {
          check: "Deployment contract loader",
          status: "blocked",
          detail: error,
          source: "src/lib/command-center.ts",
        },
      ],
      mcpStatus: {
        name: "unavailable",
        version: "unavailable",
        endpoint: "unavailable",
        baseUrlEnv: "unavailable",
        protocolType: "loader_error",
        protocolDescription: error,
        supportedModes: [],
        toolCount: 0,
        readOnlyToolCount: 0,
        writeToolCount: 0,
        qualityGateStatus: "loader_error",
        futureFeatures: [],
      },
      sdkApiStatus: {
        name: "unavailable",
        version: "unavailable",
        plannedDomain: "unavailable",
        baseUrlEnv: "unavailable",
        endpoints: [],
        authStatus: "loader_error",
        rateLimitStatus: "loader_error",
        stateSource: "unavailable",
        noSupabase: false,
      },
      webhookIngressStatus: {
        name: "unavailable",
        version: "unavailable",
        plannedDomain: "unavailable",
        baseUrlEnv: "unavailable",
        endpoints: [],
        validationRules: [],
        forwardingTarget: "unavailable",
        noLiveWebhooksStatus: "loader_error",
      },
      openRouterModelSlots: [],
      missingEnvVars: [],
      recentDeploymentReceipts: [],
      blockers: [error],
    },
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

function buildDeploymentPanel(
  domainRoutingPlan: DomainRoutingPlan,
  envContract: EnvContract,
  mcpServerContract: McpServerContract,
  sdkGatewayContract: SdkGatewayContract,
  webhookIngressContract: WebhookIngressContract,
  receiptLedger: ReceiptLedger,
): CommandCenterSnapshot["deploymentPanel"] {
  const missingEnvVars = buildMissingEnvVars(envContract);
  const missingRequiredNoDefault = missingEnvVars.filter(
    (envVar) => envVar.required && envVar.defaultValue === "—",
  );
  const openRouterModelSlots = buildOpenRouterModelSlots(
    mcpServerContract.model_routing.slots,
    envContract,
  );
  const recentDeploymentReceipts = buildRecentDeploymentReceipts(receiptLedger);

  return {
    domainTopology: domainRoutingPlan.domains.map((domain) => ({
      domain: domain.domain,
      role: domain.role,
      description: domain.description,
      status: domain.status,
      authRequired: domain.auth_required,
      routes: [...(domain.routes ?? []), ...(domain.v1_routes ?? [])].map(
        (route) => `${route.path} -> ${route.handler}`,
      ),
      envVars: domain.env_vars ?? [],
    })),
    deploymentReadiness: [
      {
        check: "Domain routing plan",
        status: domainRoutingPlan.status,
        detail: `${domainRoutingPlan.domains.length} domains documented under ${domainRoutingPlan.adr}; architecture only.`,
        source: "knowledge/deployment/domain_routing_plan_v0.json",
      },
      {
        check: "No live DNS changes",
        status: domainRoutingPlan.no_live_dns_rule.enforced ? "enforced" : "blocked",
        detail: domainRoutingPlan.no_live_dns_rule.description,
        source: "knowledge/deployment/domain_routing_plan_v0.json",
      },
      {
        check: "No live webhook activation",
        status:
          domainRoutingPlan.no_live_webhooks_rule.enforced &&
          webhookIngressContract.no_live_webhooks_rule.enforced
            ? "enforced"
            : "blocked",
        detail: webhookIngressContract.no_live_webhooks_rule.description,
        source: "knowledge/hooks/webhook_ingress_contract_v0.json",
      },
      {
        check: "No secret values",
        status:
          domainRoutingPlan.no_secrets_rule.enforced &&
          envContract.rules.no_secret_values &&
          envContract.rules.names_only
            ? "enforced"
            : "needs_review",
        detail: `${envContract.rules.vite_prefix_for_client}; ${envContract.rules.no_prefix_for_server}.`,
        source: "knowledge/deployment/env_contract_v0.json",
      },
      {
        check: "Required runtime env",
        status: missingRequiredNoDefault.length === 0 ? "ready" : "blocked",
        detail:
          missingRequiredNoDefault.length === 0
            ? "Required Command Center env names are either present or have documented contract defaults."
            : `Missing required env with no default: ${missingRequiredNoDefault
                .map((envVar) => envVar.name)
                .join(", ")}.`,
        source: "knowledge/deployment/env_contract_v0.json",
      },
      {
        check: "MCP v0 boundary",
        status: mcpServerContract.protocol.supported_modes.mcp_protocol_full
          ? "needs_review"
          : "contract_ready",
        detail: `${mcpServerContract.protocol.type}; full MCP protocol remains planned for v1.`,
        source: "knowledge/mcp/mcp_server_contract_v0.json",
      },
      {
        check: "SDK state source",
        status: sdkGatewayContract.no_supabase ? "ready" : "blocked",
        detail: `${sdkGatewayContract.state_source}; no_supabase=${String(
          sdkGatewayContract.no_supabase,
        )}.`,
        source: "knowledge/sdk/sdk_gateway_contract_v0.json",
      },
    ],
    mcpStatus: {
      name: mcpServerContract.server.name,
      version: mcpServerContract.server.version,
      endpoint: mcpServerContract.server.endpoint,
      baseUrlEnv: mcpServerContract.server.base_url_env,
      protocolType: mcpServerContract.protocol.type,
      protocolDescription: mcpServerContract.protocol.description,
      supportedModes: Object.entries(mcpServerContract.protocol.supported_modes).map(
        ([mode, enabled]) => ({
          mode,
          status: enabled ? "enabled" : "disabled_v0",
        }),
      ),
      toolCount: mcpServerContract.tools.length,
      readOnlyToolCount: mcpServerContract.tools.filter((tool) => tool.read_only).length,
      writeToolCount: mcpServerContract.tools.filter((tool) => !tool.read_only).length,
      qualityGateStatus: mcpServerContract.quality_gate.enforced ? "enforced" : "not_enforced",
      futureFeatures: mcpServerContract.protocol.future_v1.features,
    },
    sdkApiStatus: {
      name: sdkGatewayContract.gateway.name,
      version: sdkGatewayContract.gateway.version,
      plannedDomain: sdkGatewayContract.gateway.planned_domain,
      baseUrlEnv: sdkGatewayContract.gateway.base_url_env,
      endpoints: sdkGatewayContract.endpoints.map((endpoint) => ({
        method: endpoint.method,
        path: endpoint.path,
        authRequired: endpoint.auth_required,
        description: endpoint.description,
      })),
      authStatus: sdkGatewayContract.auth.v0,
      rateLimitStatus: sdkGatewayContract.rate_limits.v0,
      stateSource: sdkGatewayContract.state_source,
      noSupabase: sdkGatewayContract.no_supabase,
    },
    webhookIngressStatus: {
      name: webhookIngressContract.ingress.name,
      version: webhookIngressContract.ingress.version,
      plannedDomain: webhookIngressContract.ingress.planned_domain,
      baseUrlEnv: webhookIngressContract.ingress.base_url_env,
      endpoints: webhookIngressContract.endpoints.map((endpoint) => ({
        method: endpoint.method,
        path: endpoint.path,
        authRequired: endpoint.auth_required,
        description: endpoint.description,
      })),
      validationRules: [
        `Required fields: ${webhookIngressContract.validation_rules.required_fields.join(", ")}`,
        `Quality gate: ${webhookIngressContract.validation_rules.quality_gate}`,
        `No trading commands: ${webhookIngressContract.validation_rules.no_trading_commands ? "yes" : "no"}`,
        `Max content length: ${webhookIngressContract.validation_rules.max_content_length}`,
      ],
      forwardingTarget: `${webhookIngressContract.forwarding.method} ${webhookIngressContract.forwarding.target_env}${webhookIngressContract.forwarding.target_path}`,
      noLiveWebhooksStatus: webhookIngressContract.no_live_webhooks_rule.enforced
        ? "enforced"
        : "blocked",
    },
    openRouterModelSlots,
    missingEnvVars,
    recentDeploymentReceipts,
    blockers:
      missingRequiredNoDefault.length > 0
        ? missingRequiredNoDefault.map(
            (envVar) => `${envVar.name} is required and has no contract default.`,
          )
        : [
            "No blockers for the read-only deployment panel. Production deployment still requires operator-managed platform configuration.",
          ],
  };
}

function buildOpenRouterModelSlots(slots: string[], envContract: EnvContract) {
  return slots.map((slot) => {
    const envVarName = getOpenRouterModelEnvName(slot);
    const envVar = envContract.env_vars.find((candidate) => candidate.name === envVarName);
    const runtimeValue = getRuntimeEnvValue(envVarName);
    const hasDefault = Boolean(envVar?.default);

    return {
      slot,
      envVar: envVarName,
      required: envVar?.required ?? false,
      status: runtimeValue ? "env_present" : hasDefault ? "using_contract_default" : "unset",
      valueSource: runtimeValue ? "runtime_env" : hasDefault ? "contract_default" : "unset",
      defaultModel: envVar?.default ?? "—",
      secret: envVar?.secret ?? false,
      description: envVar?.description ?? "OpenRouter model slot",
    };
  });
}

function buildMissingEnvVars(envContract: EnvContract) {
  const requiredDisplayVars = new Set(envContract.command_center_display.required_vars);

  return envContract.env_vars
    .filter((envVar) => requiredDisplayVars.has(envVar.name) && !getRuntimeEnvValue(envVar.name))
    .map((envVar) => ({
      name: envVar.name,
      scope: envVar.scope,
      required: envVar.required,
      secret: envVar.secret,
      defaultValue: envVar.default ?? "—",
      description: envVar.description,
      status: envVar.default ? "missing_runtime_uses_default" : "missing_required",
    }));
}

function buildRecentDeploymentReceipts(
  receiptLedger: ReceiptLedger,
): CommandCenterSnapshot["deploymentPanel"]["recentDeploymentReceipts"] {
  return receiptLedger.receipts
    .filter((receipt) =>
      [
        receipt.receipt_id,
        receipt.source_request ?? "",
        receipt.input_artifact,
        receipt.output_artifact,
      ]
        .join(" ")
        .toLowerCase()
        .includes("deployment"),
    )
    .sort((left, right) => right.timestamp.localeCompare(left.timestamp))
    .slice(0, 5)
    .map((receipt) => ({
      receiptId: receipt.receipt_id,
      timestamp: receipt.timestamp,
      queue: receipt.queue,
      adapter: receipt.adapter,
      status: receipt.status,
      summary: receipt.output_artifact,
      nextStep: receipt.next_step,
    }));
}

function getOpenRouterModelEnvName(slot: string) {
  const normalizedSlot = slot === "default" ? "DEFAULT" : slot.toUpperCase();
  return `OPENROUTER_${normalizedSlot}_MODEL`;
}

function getRuntimeEnvValue(name: string) {
  const value = process.env[name] ?? import.meta.env[name];
  return typeof value === "string" && value.trim().length > 0 ? value : null;
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

function buildDailyIntakeBatchRows(): CommandCenterSnapshot["dailyIntake"] {
  const batches = readJsonCollection<DailyIntakeBatch>(
    DAILY_INTAKE_BATCH_FILES,
    "daily intake batch",
  ).map((entry) => entry.value);

  const cardCount = Object.values(DAILY_KNOWLEDGE_CARD_FILES).length;
  const cardDomains = Object.values(DAILY_KNOWLEDGE_CARD_FILES)
    .map((raw, index) => {
      try {
        return parseJson<DailyKnowledgeCard>(raw, `knowledge card ${index + 1}`);
      } catch {
        return null;
      }
    })
    .filter((card): card is DailyKnowledgeCard => card !== null)
    .map((card) => card.domain);

  const uniqueDomains = [...new Set(cardDomains)];

  return batches.map((batch) => ({
    source: `Daily Intake ${batch.cycle} (${batch.created_at.slice(0, 10)})`,
    capturedCount: batch.source_count,
    duplicates: 0,
    classifiedDomains:
      uniqueDomains.length > 0 ? uniqueDomains.slice(0, 6) : batch.themes.slice(0, 6),
    cardsDrafted: cardCount,
    blockers:
      batch.pending_count > 0
        ? [`${batch.pending_count} source(s) pending structured parse`]
        : ["No blockers"],
    receipts: [batch.receipt_id],
    nextActions: batch.next_steps.slice(0, 2),
    sourceType: "canonical" as const,
  }));
}

function buildLatestDailyIntake(): CommandCenterSnapshot["latestDailyIntake"] {
  const batches = readJsonCollection<DailyIntakeBatch>(
    DAILY_INTAKE_BATCH_FILES,
    "daily intake batch",
  );
  const manifests = readJsonCollection<SourceManifest>(
    DAILY_SOURCE_MANIFEST_FILES,
    "daily intake source manifest",
  );
  const manifestsByDate = manifests.reduce<Record<string, SourceManifest>>((accumulator, entry) => {
    const dateKey = getDatedPathKey(entry.path);
    if (dateKey) {
      accumulator[dateKey] = entry.value;
    }
    return accumulator;
  }, {});

  const latestBatch = batches
    .sort((left, right) => right.value.created_at.localeCompare(left.value.created_at))
    .at(0);

  if (!latestBatch) return null;

  const latestDate = getDatedPathKey(latestBatch.path);
  const manifest = latestDate ? manifestsByDate[latestDate] : undefined;
  const pendingItems =
    manifest?.sources
      ?.filter(
        (source) => !["ingested", "structured_parse_completed"].includes(source.ingestion_status),
      )
      .map((source) => `${source.filename} — ${source.ingestion_status}`) ?? [];

  return {
    batchId: latestBatch.value.batch_id,
    cycle: latestBatch.value.cycle,
    createdAt: latestBatch.value.created_at,
    sourceCount: latestBatch.value.source_count,
    derivedCardCount: latestBatch.value.derived_cards.length,
    pendingItems,
    receiptId: latestBatch.value.receipt_id,
    queueId: latestBatch.value.queue_id,
    latestBatchDate: latestBatch.value.created_at.slice(0, 10),
  };
}

function buildLatestDailyKnowledgeCards(): CommandCenterSnapshot["knowledgeCards"] {
  const latestDate = getLatestDatedPathKey(Object.keys(DAILY_KNOWLEDGE_CARD_FILES));
  if (!latestDate) return [];

  return readJsonCollection<DailyKnowledgeCard>(DAILY_KNOWLEDGE_CARD_FILES, "daily knowledge card")
    .filter((entry) => getDatedPathKey(entry.path) === latestDate)
    .sort(
      (left, right) =>
        right.value.created_at.localeCompare(left.value.created_at) ||
        left.value.card_id.localeCompare(right.value.card_id),
    )
    .map(({ value }) => ({
      cardId: value.card_id,
      domain: value.domain,
      title: value.title,
      status: value.status,
      createdAt: value.created_at,
      sourceCoverage:
        value.source_files.length === 1
          ? "1 source file"
          : `${value.source_files.length} source files`,
      sourceFiles: value.source_files,
      receiptId: value.receipt_id,
    }));
}

function buildRoutingSummary(
  routingMap: AppsGptsRoutingMap,
  routingRules: AppsGptsRoutingRules,
): CommandCenterSnapshot["routingSummary"] {
  return {
    status: routingRules.status,
    sourceSpreadsheet: routingMap.source_file.filename,
    sourceSpreadsheetStatus: routingMap.status,
    appRows: routingMap.apps_summary.total_app_rows,
    gptRows: routingMap.gpts_summary.total_gpt_rows,
    sampleWorkflows: routingMap.workflow_templates.length,
    highLevelRules: routingRules.global_hard_rules.map((rule) => rule.rule),
    receiptIds: [
      routingMap.receipts.source_daily_intake_receipt,
      routingMap.receipts.integration_receipt,
    ],
  };
}

function buildOperationsQueueSummary(
  operationsQueue: OperationsAutopilotQueue,
): CommandCenterSnapshot["operationsQueue"] {
  const statusCounts = operationsQueue.entries.reduce<Record<string, number>>(
    (accumulator, entry) => {
      accumulator[entry.status] = (accumulator[entry.status] ?? 0) + 1;
      return accumulator;
    },
    {},
  );

  if (!("staged" in statusCounts)) {
    statusCounts.staged = 0;
  }

  return {
    status: operationsQueue.status,
    purpose: operationsQueue.purpose,
    stagedEntriesCount: statusCounts.staged ?? 0,
    totalEntries: operationsQueue.entries.length,
    entryFields: operationsQueue.entry_fields,
    statusBreakdown: Object.entries(statusCounts)
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([status, count]) => ({ status, count })),
    queueDefinitions: Object.entries(operationsQueue.queues).map(([name, queue]) => ({
      name,
      purpose: queue.purpose,
      defaultStatus: queue.default_status,
      allowedStatuses: queue.allowed_statuses,
    })),
  };
}

function buildOperationsToolContractRows(
  operationsContracts: OperationsToolContractRegistry,
): CommandCenterSnapshot["operationsToolContracts"] {
  return operationsContracts.contracts.map((contract) => ({
    toolId: contract.tool_id,
    name: contract.name,
    status: contract.status,
    category: inferOperationsToolCategory(contract.tool_id, contract.name),
    queue: contract.queue,
    approvalClass: contract.approval_class,
  }));
}

function buildRecentIntakeRoutingReceipts(
  receiptIds: Array<string | null | undefined>,
): CommandCenterSnapshot["recentIntakeRoutingReceipts"] {
  const wantedIds = new Set(
    receiptIds.filter((receiptId): receiptId is string => Boolean(receiptId)),
  );
  if (wantedIds.size === 0) return [];

  const individualReceipts = readJsonCollection<IndividualReceipt>(
    RECEIPT_FILES,
    "individual receipt",
  );

  return individualReceipts
    .filter((entry) => wantedIds.has(entry.value.receipt_id))
    .sort((left, right) => right.value.timestamp.localeCompare(left.value.timestamp))
    .map(({ value }) => ({
      receiptId: value.receipt_id,
      timestamp: value.timestamp,
      queue: value.queue,
      status: value.status,
      summary: value.mode ?? value.output_artifact ?? value.adapter,
      nextStep: value.next_step,
    }));
}

function buildDailyIntakeRows(
  retrievalSummary: RetrievalSummary,
  retrievalValidation: RetrievalValidation,
  awareness: AwarenessState,
  receiptLedger: ReceiptLedger,
  backboneValidation: BackboneValidation,
) {
  const liveBatchRows = buildDailyIntakeBatchRows();

  const topDomains = retrievalSummary.top_domains
    .slice(0, 3)
    .map(([domain, count]) => `${domain} (${count})`);
  const knowledgeCardCount =
    retrievalSummary.top_types.find(([type]) => type === "knowledge_card")?.[1] ?? 0;

  const legacyRows = [
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

  return [...liveBatchRows, ...legacyRows];
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

function safeParseJson<T>(raw: string, label: string): T | null {
  try {
    return parseJson<T>(raw, label);
  } catch {
    return null;
  }
}

function readJsonCollection<T>(files: Record<string, string>, label: string) {
  return Object.entries(files)
    .map(([path, raw], index) => {
      const value = safeParseJson<T>(raw, `${label} ${index + 1}`);
      return value ? { path, value } : null;
    })
    .filter((entry): entry is { path: string; value: T } => entry !== null);
}

function getDatedPathKey(path: string) {
  return path.match(/\/(\d{4}-\d{2}-\d{2})\//)?.[1] ?? null;
}

function getLatestDatedPathKey(paths: string[]) {
  return (
    [
      ...new Set(
        paths
          .map((path) => getDatedPathKey(path))
          .filter((value): value is string => Boolean(value)),
      ),
    ]
      .sort((left, right) => right.localeCompare(left))
      .at(0) ?? null
  );
}

function inferOperationsToolCategory(toolId: string, name: string) {
  if (toolId.includes("webhook")) return "webhook";
  if (toolId.includes("workflow") || name.toLowerCase().includes("workflow")) return "workflow";
  if (toolId.includes("gmail") || toolId.includes("outlook")) return "messaging";
  if (toolId.includes("github") || name.toLowerCase().includes("repository")) return "repository";
  return "operations_adapter";
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
