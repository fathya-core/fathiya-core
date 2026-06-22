import type { Session } from "@supabase/supabase-js";
import { createFileRoute, Link } from "@tanstack/react-router";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Cable,
  CheckCircle2,
  ChevronDown,
  CircleAlert,
  Clock3,
  FileCheck2,
  FolderSearch,
  Eye,
  EyeOff,
  KeyRound,
  ListChecks,
  Loader2,
  LogOut,
  Play,
  RefreshCw,
  Save,
  Settings2,
  ShieldAlert,
  Square,
  TrendingUp,
  Trash2,
  XCircle,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { getSupabaseConfigurationError, supabase } from "@/integrations/supabase/client";
import { agentApi, isLocalAgentRuntime, localAgentRuntimeUrl } from "@/lib/agent/client";
import {
  buildKnowledgeMissionPrompt,
  MAX_KNOWLEDGE_OBJECTIVE_CHARACTERS,
  MAX_KNOWLEDGE_REPORT_CHARACTERS,
  MAX_KNOWLEDGE_SOURCE_CHARACTERS,
  parseKnowledgeMissionPrompt,
} from "@/lib/agent/knowledge-mission";
import type {
  AgentConnectedToolInventory,
  AgentCommandCenter,
  AgentCommandCenterCommand,
  AgentConnectorBridge,
  AgentConnectorProfile,
  AgentIntegrationReadiness,
  AgentIntegrationProbeResult,
  AgentIntegrationStatus,
  AgentIntegrationSummary,
  AgentKnowledgeIntakeStatus,
  AgentLocalSettingsGroup,
  AgentLocalSettingsResponse,
  AgentMeshSummary,
  AgentRuntimeHealth,
  AgentTradingCycle,
  AgentZapierActionCatalog,
  AgentZapierCatalogAction,
  AgentZapierDiagnostics,
  AgentTask,
  AgentTaskDetail,
  AgentTaskStatus,
  AgentTradingStatus,
  CreateAgentTaskBody,
} from "@/lib/agent/contracts";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/agent-tasks")({
  head: () => ({
    meta: [
      { title: "مهام الوكلاء - FATHIYA" },
      { name: "description", content: "إنشاء ومراقبة واعتماد مهام مشغّل فتحية المحلي." },
    ],
  }),
  component: AgentTasksPage,
});

const ACTIVE_STATUSES = new Set<AgentTaskStatus>([
  "queued",
  "running",
  "awaiting_approval",
  "stalled",
]);

const STATUS_LABELS: Record<AgentTaskStatus, string> = {
  queued: "في الطابور",
  running: "قيد التنفيذ",
  awaiting_approval: "بانتظار الموافقة",
  completed: "مكتملة",
  failed: "فشلت",
  stalled: "متوقفة",
  canceled: "ملغاة",
};

const AGENT_MESH_EXECUTE_PROMPT = [
  "agent mesh execute:",
  "شغّل شبكة وكلاء فتحية الآمنة: الأدوات المحلية، Hugging Face المحلي، OpenRouter، Zapier MCP، n8n، Kali WSL، GitHub Codespaces، ووكيل التداول الأساسي.",
  "نفّذ فقط الأدوات الداخلية أو القراءة أو Paper/Testnet التي لا تحتاج موافقة، ثم سجل ما عمل وما تخطّيته بسبب بوابة المخاطر.",
].join("\n");

const GITHUB_CODESPACES_AGENT_PROMPT = [
  "شغّل وكيل GitHub Codespaces للهدف الهندسي:",
  "استخدم حساب GitHub المصادق واشتراك Codespaces كبيئة وكيل بعيدة.",
  "ابدأ بجرد Codespaces، اختر البيئة الأنسب لمستودع فتحية إن وجدت، ولا تنفذ أوامر بعيدة الآن.",
  "أخرج إيصالًا فيه الجاهزية، Codespace المختارة، وما يحتاجه التشغيل البعيد التالي.",
].join("\n");

const OPENROUTER_MODEL_STRATEGY_PROMPT = [
  "openrouter model strategy:",
  "استوعب إيميل OpenRouter منتصف يونيو 2026 عن Fusion وAdvisor وSubagent والنماذج الجديدة.",
  "اعرض كيف تستخدم فتحية النماذج المجانية والقوية للتخطيط العادي، ومتى تستخدم openrouter/fusion للبحث العميق فقط.",
  "أكد أن Fusion لا يدخل لوب التداول بالثانية، وأن نموذج السلامة المجاني يستخدم كطبقة فحص قبل/بعد المهام عالية الأثر.",
  "سجل إيصالًا عمليًا فيه المسارات: تخطيط رخيص، بحث عميق، مستشار تداول، وسلامة.",
].join("\n");

function localSettingsProbeTaskBody(groupId: string, groupName?: string): CreateAgentTaskBody {
  const label = groupName || groupId || "local settings";
  const probes: Record<string, CreateAgentTaskBody> = {
    local_execution_mesh: {
      title: "فحص جسر الوكلاء بعد الحفظ",
      prompt: [
        "agent mesh execute:",
        "FATHIYA_POST_SETTINGS_PROBE_V1",
        "افحص جسر الوكلاء المحلي بعد حفظ الإعدادات بدون كشف الأسرار.",
        "نفذ فقط جرد الأدوات والقراءة الداخلية الآمنة، وسجل إيصالًا يوضح الجاهز والناقص.",
      ].join("\n"),
    },
    openrouter: {
      title: "فحص OpenRouter/Fusion بعد الحفظ",
      prompt: [
        "integration probe: openrouter",
        "openrouter model strategy:",
        "افحص إعداد OpenRouter بعد الحفظ دون كشف المفتاح أو صرف رموز غير لازمة.",
        "اعرض استراتيجية Fusion/Advisor/Subagent من بطاقة OpenRouter، وأكد أن Fusion للبحث العميق وليس لوب التداول بالثانية.",
      ].join("\n"),
    },
    broker_testnet: {
      title: "فحص Broker Testnet بعد الحفظ",
      prompt: [
        "integration probe: broker_testnet",
        "افحص Testnet بعد حفظ الإعدادات بدون إرسال أوامر تداول حقيقية.",
        "أثبت حالة الاتصال، وضع التداول الورقي، وما يلزم قبل أي تنفيذ مالي.",
      ].join("\n"),
    },
  };
  return (
    probes[groupId] ?? {
      title: `فحص ${label} بعد الحفظ`,
      prompt: [
        `integration probe: ${groupId}`,
        "FATHIYA_POST_SETTINGS_PROBE_V1",
        `افحص بوابة ${label} بعد حفظ الإعدادات دون كشف الأسرار.`,
        "سجل إيصالًا واضحًا: جاهز، جزئي، أو يحتاج تفعيل.",
      ].join("\n"),
    }
  );
}

const KNOWLEDGE_EXECUTION_PROMPT = [
  "knowledge execution mission:",
  "FATHIYA_KNOWLEDGE_EXECUTION_V1",
  "استوعب المعرفة والتقارير الحالية، ثم اختر الأدوات والنماذج المناسبة، ثم نفذ شبكة الوكلاء الداخلية الجاهزة.",
  "استخدم Hugging Face المحلي للاسترجاع/الفهم، OpenRouter لتوجيه النماذج، Zapier MCP وn8n وKali وGitHub ووكيل التداول كقدرات تنفيذ.",
  "نفّذ داخليًا ما لا يحتاج موافقة، واترك الإرسال الخارجي أو المال أو الفحص الحي أو الحذف كبوابات أثر لا كتعطيل.",
  "أخرج إيصالًا يثبت: ما فهمته، الأدوات التي اختيرت، ما نُفذ فعليًا، وما بقي ينتظر ربطًا أو موافقة.",
].join("\n");

const FATHIYA_EXECUTION_OS_PROMPT = [
  "agent mesh execute:",
  "FATHIYA_EXECUTION_OS_MISSION_V1",
  "شغّل محرك فتحية التنفيذي كشبكة وكلاء لا كتحليل فقط.",
  "ابدأ وكيل التداول الورقي إذا كان متوقفًا، وفعّل مستشار الاستراتيجية، واجعل التنبؤ والتنفيذ الورقي بنبض الثانية هو الأولوية الأولى.",
  "افحص جاهزية Hugging Face المحلي وOpenRouter وSupabase وn8n المحلي وZapier MCP وKali WSL وGitHub Codespaces وBroker Testnet.",
  "استخدم جرد Zapier وموفري الوكلاء المفيدين مثل ChatGPT وAI by Zapier وApify كقدرات تنفيذ، مع ترك الأفعال عالية الأثر لبوابة المخاطر.",
  "سجل إيصالًا واضحًا: ما نُفّذ فعليًا، ما أصبح جاهزًا، ما يحتاج ربطًا، وما هي المتابعة التنفيذية التالية.",
].join("\n");

const FATHIYA_ACTIVATION_SWEEP_PROMPT = [
  "agent mesh execute:",
  "FATHIYA_ACTIVATION_SWEEP_V1",
  "فعّل الناقص في فتحية كمسار تشغيل واحد لا كتنقل بين الإعدادات.",
  "افحص بوابات Zapier MCP وGitHub Codespaces وSupabase وn8n المحلي وKali WSL وOpenRouter وHugging Face وBroker Testnet.",
  "نفّذ كل فحص أو قراءة أو تشغيل داخلي آمن متاح الآن، ولا توقف المهمة بسبب بوابات OAuth أو مفاتيح أو موافقة أثر.",
  "حوّل كل بوابة غير جاهزة إلى next_action واضح: ماذا أضغط، ماذا أربط، وأي إعداد محلي مطلوب بدون كشف أسرار.",
  "ابدأ أو تحقق من وكيل التداول الورقي، وأثبت أن مسار النماذج المحلي/OpenRouter جاهز.",
  "سجل إيصالًا فيه: الجاهز الآن، ما نُفّذ، ما بقي، وأول ثلاث خطوات تفعيل مرتبة.",
].join("\n");

type BugBountyPlatform = "auto" | "hackerone" | "bugcrowd";
type BugBountyRunMode = "hunt" | "dedupe" | "draft-gate";

const BUG_BOUNTY_PLATFORM_LABELS: Record<BugBountyPlatform, string> = {
  auto: "تلقائي",
  hackerone: "HackerOne",
  bugcrowd: "Bugcrowd",
};

const BUG_BOUNTY_KNOWLEDGE_PATH =
  "knowledge/security/bug-bounty/hackerone/20260615-hacktivity-high-critical-lessons.md";

function isVisibleAgentProviderApp(app: string): boolean {
  return Boolean(app.trim());
}

function normalizeOptionalUrl(value: string): string {
  const clean = value.trim();
  if (!clean) return "";
  if (/^https?:\/\//i.test(clean)) return clean;
  return `https://${clean}`;
}

function formatKnowledgeReferences(value: string): string {
  const references = value
    .split(/\r?\n|,/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 8);
  if (!references.length) return "";
  const lines = references.map((item) =>
    /^https?:\/\//i.test(item) ? item : `source_path: ${item}`,
  );
  return ["مصادر المعرفة المطلوب استيعابها:", ...lines].join("\n");
}

function isGithubRepoUrl(value: string): boolean {
  return /^https?:\/\/(?:www\.)?github\.com\/[^/\s]+\/[^/\s]+/i.test(value.trim());
}

function bugBountyProgramLabel(platform: BugBountyPlatform, programUrl: string): string {
  if (!programUrl.trim()) {
    return platform === "auto"
      ? "اختيار تلقائي من البرامج المصرحة"
      : `${BUG_BOUNTY_PLATFORM_LABELS[platform]} authorized program`;
  }
  try {
    const url = new URL(normalizeOptionalUrl(programUrl));
    const parts = url.pathname.split("/").filter(Boolean);
    return parts.slice(0, 2).join("/") || url.hostname;
  } catch {
    return programUrl.trim().slice(0, 80);
  }
}

function buildBugBountyHuntPrompt(options: {
  platform: BugBountyPlatform;
  programUrl: string;
  repoUrl: string;
  focus: string;
  allowedScope: string;
  exclusions: string;
  evidencePlan: string;
  dedupeNotes: string;
  mode: Exclude<BugBountyRunMode, "draft-gate">;
}): string {
  const programUrl = normalizeOptionalUrl(options.programUrl);
  const repoUrl = normalizeOptionalUrl(options.repoUrl || (isGithubRepoUrl(programUrl) ? programUrl : ""));
  const program = bugBountyProgramLabel(options.platform, programUrl);
  const phase = options.mode === "dedupe" ? "dedupe_only" : "hunt_static_review_then_internal_draft";
  const scopeNote = [
    `platform=${BUG_BOUNTY_PLATFORM_LABELS[options.platform]}`,
    programUrl ? `program_url=${programUrl}` : "selection=auto_authorized_program",
    repoUrl ? `repo_url=${repoUrl}` : "repo_url=not_provided",
    `phase=${phase}`,
  ].join("; ");
  const focus =
    options.focus.trim() ||
    "استخدم معرفة تقارير HackerOne High/Critical لصيد مرشح قوي، ثم صعّد فقط بالدليل واكتب مسودة تقرير داخل فتحية.";
  const allowedScope = options.allowedScope.trim() || "use_program_scope_only";
  const exclusions =
    options.exclusions.trim() ||
    "respect_program_policy; no live testing unless explicitly in-scope and approved";
  const evidencePlan =
    options.evidencePlan.trim() ||
    "steps_to_reproduce; impact_statement; screenshots_or_local_poc_if_available; severity_reasoning";
  const dedupeNotes =
    options.dedupeNotes.trim() ||
    "check disclosed reports, prior duplicate IDs, GitHub issues/PRs, changelog, CVEs, exact function names, and root-cause terms before drafting";

  return [
    options.mode === "dedupe" ? "" : "bug bounty hunt flow:",
    "bug bounty static review:",
    `phase: ${phase}`,
    `platform: ${BUG_BOUNTY_PLATFORM_LABELS[options.platform]}`,
    `program: ${program}`,
    programUrl ? `program_url: ${programUrl}` : "program_url: auto",
    repoUrl ? `repo_url: ${repoUrl}` : "repo_url:",
    "target_path: .",
    `allowed_scope: ${allowedScope}`,
    `exclusions: ${exclusions}`,
    `scope_note: ${scopeNote}`,
    `focus: ${focus}`,
    `evidence_required: ${evidencePlan}`,
    `dedupe_required: ${dedupeNotes}`,
    `knowledge_path: ${BUG_BOUNTY_KNOWLEDGE_PATH}`,
    options.mode === "dedupe" ? "" : "draft_gate: internal_only",
    "novelty_gate: لا تكتب Draft قابل للرفع إذا كان الجذر أو الاستغلال أو الأثر مكررًا؛ اكتب قرار not_ready مع سبب dedupe.",
    "impact_gate: لا تصعّد severity بلا أثر عملي قابل للعرض. يجب أن يجيب التقرير: as an attacker I could ... بدليل.",
    "constraints: مراجعة ساكنة ومصرحة فقط في المرحلة الأولى؛ لا فحص حي ولا استغلال ولا إرسال خارجي. إذا احتجت فعلًا عالي الأثر فحوّله إلى بوابة موافقة.",
  ].filter(Boolean).join("\n");
}

function buildBugBountyDraftGatePrompt(options: {
  platform: BugBountyPlatform;
  programUrl: string;
}): string {
  const programUrl = normalizeOptionalUrl(options.programUrl);
  const program = bugBountyProgramLabel(options.platform, programUrl);
  return [
    "bug bounty draft gate:",
    `platform: ${BUG_BOUNTY_PLATFORM_LABELS[options.platform]}`,
    `program: ${program}`,
    programUrl ? `program_url: ${programUrl}` : "program_url: auto",
    "تحقق من أحدث تقرير static review داخل فتحية.",
    "لا ترفعه خارجيًا. قيّم فقط: هل فيه أثر عملي؟ هل فيه دليل؟ هل تجاوز dedupe؟ هل يصلح Draft داخلي؟",
    "إذا ناقص، اكتب not_ready مع قائمة الأدلة المطلوبة بدل صياغة تقرير ضعيف.",
  ].join("\n");
}

type AgentMeshNextAction = {
  id: string;
  title: string;
  prompt: string;
  reason: string;
  ui_action?: "task" | "settings" | "oauth";
  settings_group?: string;
  integration_id?: string;
  action_path?: string;
  action_label?: string;
};

type ZapierReadAction = {
  id: string;
  app: string;
  action: string;
};

type WorkspaceView = "request" | "trading" | "bug-bounty" | "knowledge" | "reports" | "tools";
type MissionMode = "execution" | "trading" | "bug-bounty" | "knowledge" | "tools";
type MissionAutonomyMode = "direct" | "guided" | "activation";
type ExecutionDecisionAction = "run" | "activate" | "refresh";
type LiveExecutionProof = {
  task: AgentTask;
  receiptId: string | null;
  summary: string;
  tools: string[];
  roundCount: number;
  completedAt: string | null;
};

const DEFAULT_WORKSPACE_VIEW: WorkspaceView = "request";
const WORKSPACE_VIEW_IDS = new Set<WorkspaceView>([
  "request",
  "trading",
  "bug-bounty",
  "knowledge",
  "reports",
  "tools",
]);

function normalizeWorkspaceView(value: unknown): WorkspaceView {
  return typeof value === "string" && WORKSPACE_VIEW_IDS.has(value as WorkspaceView)
    ? (value as WorkspaceView)
    : DEFAULT_WORKSPACE_VIEW;
}

function readWorkspaceViewFromLocation(): WorkspaceView {
  if (typeof window === "undefined") return DEFAULT_WORKSPACE_VIEW;
  try {
    return normalizeWorkspaceView(new URL(window.location.href).searchParams.get("view"));
  } catch {
    return DEFAULT_WORKSPACE_VIEW;
  }
}

function writeWorkspaceViewToLocation(view: WorkspaceView): void {
  if (typeof window === "undefined") return;
  try {
    const url = new URL(window.location.href);
    if (view === DEFAULT_WORKSPACE_VIEW) {
      url.searchParams.delete("view");
    } else {
      url.searchParams.set("view", view);
    }
    const next = `${url.pathname}${url.search}${url.hash}`;
    const current = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    if (next !== current) {
      window.history.replaceState(window.history.state, "", next);
    }
  } catch {
    // URL syncing is progressive enhancement; the in-app state remains authoritative.
  }
}

type ExecutionDecision = {
  state: "offline" | "local_ready" | "activation_required" | "fully_ready";
  title: string;
  summary: string;
  badge: string;
  primaryAction: ExecutionDecisionAction;
  primaryLabel: string;
  secondaryAction?: ExecutionDecisionAction;
  secondaryLabel?: string;
  facts: string[];
  blockers: string[];
  attentionLabel?: string;
};

const MISSION_MODE_LABELS: Record<MissionMode, string> = {
  execution: "تشغيل عام",
  trading: "التداول",
  "bug-bounty": "صيد الثغرات",
  knowledge: "معرفة وتقارير",
  tools: "الأدوات",
};

const MISSION_AUTONOMY_LABELS: Record<MissionAutonomyMode, string> = {
  direct: "مباشر محلي",
  guided: "موجّه",
  activation: "تفعيل الأدوات",
};

function missionAutonomyDirective(mode: MissionAutonomyMode): string {
  if (mode === "activation") {
    return [
      "autonomy_mode: activation",
      "لا تعامل النواقص كفشل؛ افحص كل بوابة، نفذ الفحوصات والقراءة الداخلية الجاهزة، ثم أخرج أزرار OAuth/Settings/Follow-up لكل مزود يحتاج ربطًا.",
      "اجعل Zapier MCP وGitHub Codespaces وSupabase وBroker Testnet عناصر تفعيل مرتبة، مع منع كشف الأسرار.",
    ].join("\n");
  }
  if (mode === "guided") {
    return [
      "autonomy_mode: guided",
      "افهم الهدف، اختر الأدوات المناسبة، نفذ الداخلي والقراءة، ثم توقف عند أول فعل خارجي عالي الأثر مع صياغة متابعة قابلة للتشغيل.",
      "اعرض السبب والأداة المقترحة قبل أي إرسال خارجي أو حذف أو مال أو فحص حي.",
    ].join("\n");
  }
  return [
    "autonomy_mode: direct_local",
    "افهم الهدف ثم تحرك كوكيل: اختر النماذج والأدوات، نفذ كل ما هو داخلي أو قراءة أو Paper/Testnet جاهز دون سؤال إضافي، وسجل إيصالًا.",
    "لا تجعل OAuth أو إعدادات ناقصة توقف المهمة؛ حوّلها إلى next_action واضح واستمر بما هو متاح.",
    "الأفعال الخارجية عالية الأثر، المال الحقيقي، الحذف، والإرسال العام تبقى كبوابات أثر منفصلة، لكنها لا تمنع التنفيذ المحلي.",
  ].join("\n");
}

function buildMissionTaskBody(
  mode: MissionMode,
  objectiveValue = "",
  sourcesValue = "",
  autonomyMode: MissionAutonomyMode = "direct",
): CreateAgentTaskBody {
  const objective =
    objectiveValue.trim() ||
    "نفذ المسار المختار بالأدوات الداخلية الجاهزة وسجل إيصالًا واضحًا.";
  const references = formatKnowledgeReferences(sourcesValue);
  const autonomy = missionAutonomyDirective(autonomyMode);

  if (mode === "trading") {
    return {
      title: "تشغيل وكيل التداول",
      prompt: [
        "agent mesh execute:",
        "FATHIYA_TRADING_AGENT_MISSION_V1",
        autonomy,
        "ابدأ أو تحقق من وكيل التداول الورقي، وحدث مستشار الاستراتيجية، واجعل نبض الثانية هو المسار الأساسي.",
        objective,
        references,
        "استخدم Hugging Face المحلي للاسترجاع وOpenRouter لمستشار الاستراتيجية عند الحاجة، ولا تستخدم مالًا حقيقيًا.",
      ]
        .filter(Boolean)
        .join("\n"),
    };
  }

  if (mode === "bug-bounty") {
    const firstToken = objective.split(/\s+/)[0] ?? "";
    const looksLikeUrl =
      /^https?:\/\//i.test(firstToken) || /^[\w.-]+\.[a-z]{2,}/i.test(firstToken);
    const inlineProgram = looksLikeUrl ? normalizeOptionalUrl(firstToken) : "";
    return {
      title: inlineProgram
        ? `صيد ثغرات: ${bugBountyProgramLabel("auto", inlineProgram)}`
        : "صيد ثغرات: اختيار تلقائي",
      prompt: [
        "bug bounty hunt flow:",
        "bug bounty static review:",
        autonomy,
        "platform: تلقائي",
        inlineProgram ? `program_url: ${inlineProgram}` : "program_url: auto",
        "target_path: .",
        "allowed_scope: use_program_scope_only",
        `focus: ${objective}`,
        references,
        "evidence_required: steps_to_reproduce; impact_statement; screenshots_or_local_poc_if_available; severity_reasoning",
        "dedupe_required: disclosed reports, duplicate IDs, GitHub issues/PRs, changelog, CVEs, exact function names, and root-cause terms",
        `knowledge_path: ${BUG_BOUNTY_KNOWLEDGE_PATH}`,
        "draft_gate: internal_only",
        "novelty_gate: لا تكتب Draft قابل للرفع إذا كان الجذر أو الاستغلال أو الأثر مكررًا؛ اكتب قرار not_ready مع سبب dedupe.",
        "impact_gate: لا تصعّد severity بلا أثر عملي قابل للعرض.",
        "constraints: استخدم المعرفة والأدوات المحلية والمصادر المصرح بها، واعرض التقرير والإثبات داخل فتحية قبل أي إرسال خارجي.",
      ]
        .filter(Boolean)
        .join("\n"),
    };
  }

  if (mode === "knowledge") {
    return {
      title: "استيعاب معرفة وتشغيل",
      prompt: [
        "knowledge execution mission:",
        "FATHIYA_KNOWLEDGE_EXECUTION_V1",
        autonomy,
        objective,
        references,
        "استوعب المصادر عبر Hugging Face المحلي، استخدم OpenRouter/Fusion للبحث العميق عند الحاجة، ثم اختر الأدوات المناسبة ونفذ الداخلي الجاهز.",
      ]
        .filter(Boolean)
        .join("\n"),
    };
  }

  if (mode === "tools") {
    return {
      title: "تشغيل أدوات فتحية",
      prompt: [
        "agent mesh execute:",
        "FATHIYA_TOOL_ORCHESTRATION_MISSION_V1",
        autonomy,
        "استكشف أدوات Zapier MCP وn8n وKali وGitHub Codespaces وحالة الموصلات، ثم نفذ القراءة أو الداخلي الجاهز.",
        objective,
        references,
        "سجل ما استُخدم فعليًا وما ينتظر OAuth أو إعدادًا أو موافقة أثر.",
      ]
        .filter(Boolean)
        .join("\n"),
    };
  }

  return {
    title: "تشغيل محرك فتحية",
    prompt: [FATHIYA_EXECUTION_OS_PROMPT, autonomy, objective, references]
      .filter(Boolean)
      .join("\n"),
  };
}

function buildDirectAgentRequestTaskBody(
  objectiveValue: string,
  titleValue = "",
): CreateAgentTaskBody {
  const objective = objectiveValue.trim();
  const cleanTitle = titleValue.trim();
  const fallbackTitle = objective
    ? `طلب وكيل: ${objective.split(/\s+/).slice(0, 10).join(" ")}`
    : "طلب وكيل";
  return {
    title: cleanTitle || fallbackTitle.slice(0, 120),
    prompt: [
      "knowledge execution mission:",
      "FATHIYA_OPERATOR_AGENT_REQUEST_V1",
      missionAutonomyDirective("direct"),
      "operator_request:",
      objective,
      "حوّل طلب المشغل إلى خطة أدوات قابلة للتنفيذ: استرجع المعرفة المناسبة، اختر نموذج OpenRouter عند الحاجة، استخدم Hugging Face المحلي للفهم، وافحص Zapier MCP وn8n وKali وGitHub والتداول كقدرات تنفيذ.",
      "نفّذ الداخلي والقراءة وPaper/Testnet المتاح الآن، ثم أخرج إيصالًا واضحًا بما تم فعله وما بقي كمتابعة OAuth/Settings/Approval.",
    ]
      .filter(Boolean)
      .join("\n"),
  };
}

function AgentTasksPage() {
  const localMode = isLocalAgentRuntime;
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [connectors, setConnectors] = useState<AgentConnectorProfile[]>([]);
  const [connectorBridge, setConnectorBridge] = useState<AgentConnectorBridge | null>(null);
  const [connectedInventory, setConnectedInventory] =
    useState<AgentConnectedToolInventory | null>(null);
  const [integrations, setIntegrations] = useState<AgentIntegrationReadiness[]>([]);
  const [integrationSummary, setIntegrationSummary] = useState<AgentIntegrationSummary | null>(
    null,
  );
  const [meshSummary, setMeshSummary] = useState<AgentMeshSummary | null>(null);
  const [commandCenter, setCommandCenter] = useState<AgentCommandCenter | null>(null);
  const [runtimeHealth, setRuntimeHealth] = useState<AgentRuntimeHealth | null>(null);
  const [localSettings, setLocalSettings] = useState<AgentLocalSettingsResponse | null>(null);
  const [selectedSettingsGroup, setSelectedSettingsGroup] = useState<string | null>(null);
  const [integrationProbes, setIntegrationProbes] = useState<
    Record<string, AgentIntegrationProbeResult>
  >({});
  const [probingIntegration, setProbingIntegration] = useState<string | null>(null);
  const [startingIntegrationTask, setStartingIntegrationTask] = useState<string | null>(null);
  const [startingZapierReadAction, setStartingZapierReadAction] = useState<string | null>(null);
  const [selectedZapierApp, setSelectedZapierApp] = useState("");
  const [zapierActionParams, setZapierActionParams] = useState("{}");
  const [zapierActionInstructions, setZapierActionInstructions] = useState("");
  const [zapierCatalog, setZapierCatalog] = useState<AgentZapierActionCatalog | null>(null);
  const [zapierDiagnostics, setZapierDiagnostics] = useState<AgentZapierDiagnostics | null>(null);
  const [loadingZapierCatalog, setLoadingZapierCatalog] = useState(false);
  const [startingZapierCatalogAction, setStartingZapierCatalogAction] = useState<string | null>(
    null,
  );
  const [startingConnectorProfile, setStartingConnectorProfile] = useState<string | null>(null);
  const [trading, setTrading] = useState<AgentTradingStatus | null>(null);
  const [tradingReceipts, setTradingReceipts] = useState<AgentTradingCycle[]>([]);
  const [intake, setIntake] = useState<AgentKnowledgeIntakeStatus | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AgentTaskDetail | null>(null);
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [composerMode, setComposerMode] = useState<"direct" | "knowledge">("direct");
  const [reportSource, setReportSource] = useState("");
  const [reportObjective, setReportObjective] = useState("");
  const [reportContent, setReportContent] = useState("");
  const [reportReferences, setReportReferences] = useState("");
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>(readWorkspaceViewFromLocation);
  const [missionMode, setMissionMode] = useState<MissionMode>("execution");
  const [missionAutonomyMode, setMissionAutonomyMode] =
    useState<MissionAutonomyMode>("direct");
  const [missionObjective, setMissionObjective] = useState("");
  const [missionSources, setMissionSources] = useState("");
  const [creating, setCreating] = useState(false);
  const [startingMission, setStartingMission] = useState(false);
  const [startingMissionMode, setStartingMissionMode] = useState<MissionMode | null>(null);
  const [acting, setActing] = useState(false);
  const [startingMeshExecute, setStartingMeshExecute] = useState(false);
  const [startingCommandCenterId, setStartingCommandCenterId] = useState<string | null>(null);
  const [startingExecutionOs, setStartingExecutionOs] = useState(false);
  const [startingActivationSweep, setStartingActivationSweep] = useState(false);
  const [startingCodespacesAgent, setStartingCodespacesAgent] = useState(false);
  const [startingOpenRouterStrategy, setStartingOpenRouterStrategy] = useState(false);
  const [startingKnowledgeExecution, setStartingKnowledgeExecution] = useState(false);
  const [startingBugBountyHunt, setStartingBugBountyHunt] = useState(false);
  const [startingAgentProviderProbe, setStartingAgentProviderProbe] = useState<string | null>(null);
  const [startingAgentProviderPrepare, setStartingAgentProviderPrepare] = useState<string | null>(null);
  const [bugBountyPlatform, setBugBountyPlatform] = useState<BugBountyPlatform>("auto");
  const [bugBountyProgramUrl, setBugBountyProgramUrl] = useState("");
  const [bugBountyRepoUrl, setBugBountyRepoUrl] = useState("");
  const [bugBountyFocus, setBugBountyFocus] = useState("");
  const [bugBountyAllowedScope, setBugBountyAllowedScope] = useState("");
  const [bugBountyExclusions, setBugBountyExclusions] = useState("");
  const [bugBountyEvidencePlan, setBugBountyEvidencePlan] = useState("");
  const [bugBountyDedupeNotes, setBugBountyDedupeNotes] = useState("");
  const [startingBugBountyAction, setStartingBugBountyAction] =
    useState<BugBountyRunMode | null>(null);
  const [startingFollowUpPrompt, setStartingFollowUpPrompt] = useState<string | null>(null);
  const [tradingActing, setTradingActing] = useState(false);
  const [intakeActing, setIntakeActing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (localMode) {
      setSession(null);
      return undefined;
    }
    const configurationError = getSupabaseConfigurationError();
    if (configurationError) {
      setError(configurationError);
      setSession(null);
      return undefined;
    }
    try {
      void supabase.auth.getSession().then(({ data }) => setSession(data.session));
      const { data } = supabase.auth.onAuthStateChange((_event, nextSession) =>
        setSession(nextSession),
      );
      return () => data.subscription.unsubscribe();
    } catch (sessionError) {
      setError(String(sessionError));
      setSession(null);
      return undefined;
    }
  }, [localMode]);

  const hasAccess = localMode || Boolean(session);

  useEffect(() => {
    writeWorkspaceViewToLocation(workspaceView);
  }, [workspaceView]);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const syncWorkspaceView = () => setWorkspaceView(readWorkspaceViewFromLocation());
    window.addEventListener("popstate", syncWorkspaceView);
    return () => window.removeEventListener("popstate", syncWorkspaceView);
  }, []);

  const loadTasks = useCallback(async () => {
    if (!hasAccess) return;
    try {
      const data = await agentApi<{ tasks: AgentTask[] }>(session ?? null, "/api/agent/tasks");
      setTasks(data.tasks);
      setSelectedId((current) => current ?? data.tasks[0]?.id ?? null);
      setError("");
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [hasAccess, session]);

  const loadDetail = useCallback(async () => {
    if (!hasAccess || !selectedId) {
      setDetail(null);
      return;
    }
    try {
      const data = await agentApi<AgentTaskDetail>(
        session ?? null,
        `/api/agent/tasks/${selectedId}`,
      );
      setDetail(data);
      setTasks((current) => current.map((task) => (task.id === data.task.id ? data.task : task)));
      setError("");
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [hasAccess, selectedId, session]);

  const loadConnectors = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<{
        connectors: AgentConnectorProfile[];
        bridge: AgentConnectorBridge;
        inventory: AgentConnectedToolInventory;
      }>(null, "/api/agent/connectors");
      setConnectors(data.connectors);
      setConnectorBridge(data.bridge);
      setConnectedInventory(data.inventory);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadRuntimeHealth = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<AgentRuntimeHealth>(null, "/api/agent/health");
      setRuntimeHealth(data);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadTrading = useCallback(async () => {
    if (!localMode) return;
    try {
      const [statusData, receiptsData] = await Promise.all([
        agentApi<{ trading: AgentTradingStatus }>(null, "/api/agent/trading/status"),
        agentApi<{ receipts: AgentTradingCycle[] }>(null, "/api/agent/trading/receipts"),
      ]);
      setTrading(statusData.trading);
      setTradingReceipts(receiptsData.receipts.slice(0, 5));
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadIntake = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<{ intake: AgentKnowledgeIntakeStatus }>(
        null,
        "/api/agent/intake/status",
      );
      setIntake(data.intake);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadIntegrations = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<{
        integrations: AgentIntegrationReadiness[];
        summary: AgentIntegrationSummary;
      }>(null, "/api/agent/integrations");
      setIntegrations(data.integrations);
      setIntegrationSummary(data.summary);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadMeshSummary = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<AgentMeshSummary>(null, "/api/agent/mesh/summary");
      setMeshSummary(data);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadCommandCenter = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<AgentCommandCenter>(null, "/api/agent/command-center");
      setCommandCenter(data);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadZapierDiagnostics = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<{ zapier_mcp: AgentZapierDiagnostics }>(
        null,
        "/api/agent/oauth/zapier/diagnostics",
      );
      setZapierDiagnostics(data.zapier_mcp);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadLocalSettings = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<AgentLocalSettingsResponse>(null, "/api/agent/settings");
      setLocalSettings(data);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  useEffect(() => {
    if (!hasAccess) return;
    void loadTasks();
    const timer = window.setInterval(() => void loadTasks(), 5000);
    return () => window.clearInterval(timer);
  }, [hasAccess, loadTasks]);

  useEffect(() => {
    if (!localMode) return;
    void loadConnectors();
    const timer = window.setInterval(() => void loadConnectors(), 15_000);
    return () => window.clearInterval(timer);
  }, [loadConnectors, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadRuntimeHealth();
    const timer = window.setInterval(() => void loadRuntimeHealth(), 2000);
    return () => window.clearInterval(timer);
  }, [loadRuntimeHealth, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadTrading();
    const timer = window.setInterval(() => void loadTrading(), 1000);
    return () => window.clearInterval(timer);
  }, [loadTrading, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadIntake();
    const timer = window.setInterval(() => void loadIntake(), 5000);
    return () => window.clearInterval(timer);
  }, [loadIntake, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadIntegrations();
    const timer = window.setInterval(() => void loadIntegrations(), 15_000);
    return () => window.clearInterval(timer);
  }, [loadIntegrations, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadMeshSummary();
    const timer = window.setInterval(() => void loadMeshSummary(), 5000);
    return () => window.clearInterval(timer);
  }, [loadMeshSummary, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadCommandCenter();
    const timer = window.setInterval(() => void loadCommandCenter(), 5000);
    return () => window.clearInterval(timer);
  }, [loadCommandCenter, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadZapierDiagnostics();
    const timer = window.setInterval(() => void loadZapierDiagnostics(), 10_000);
    return () => window.clearInterval(timer);
  }, [loadZapierDiagnostics, localMode]);

  useEffect(() => {
    if (!localMode) return;
    void loadLocalSettings();
  }, [loadLocalSettings, localMode]);

  useEffect(() => {
    if (!hasAccess || !selectedId) return;
    void loadDetail();
    const timer = window.setInterval(() => void loadDetail(), 2000);
    return () => window.clearInterval(timer);
  }, [hasAccess, loadDetail, selectedId]);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    if (!hasAccess) return;
    setCreating(true);
    setError("");
    try {
      const taskPrompt =
        composerMode === "knowledge"
          ? buildKnowledgeMissionPrompt({
              source_name: reportSource,
              objective: [reportObjective.trim(), formatKnowledgeReferences(reportReferences)]
                .filter(Boolean)
                .join("\n\n"),
              content:
                reportContent.trim() ||
                reportReferences.trim() ||
                "Operator provided source references for FATHIYA knowledge execution.",
            })
          : buildDirectAgentRequestTaskBody(prompt, title).prompt;
      if (!taskPrompt) return;
      const body: CreateAgentTaskBody = {
        prompt: taskPrompt,
        title:
          title.trim() ||
          (composerMode === "knowledge"
            ? `تنفيذ من تقرير: ${reportSource.trim()}`
            : buildDirectAgentRequestTaskBody(prompt).title),
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPrompt("");
      setReportSource("");
      setReportObjective("");
      setReportContent("");
      setReportReferences("");
      setTitle("");
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (createError) {
      setError(String(createError));
    } finally {
      setCreating(false);
    }
  }

  function meshQuickActionBody(
    actionId: string,
    fallbackTitle: string,
    fallbackPrompt: string,
  ): CreateAgentTaskBody {
    const action = meshSummary?.quick_actions.find((item) => item.id === actionId);
    return {
      title: action?.title || fallbackTitle,
      prompt: action?.prompt || fallbackPrompt,
    };
  }

  async function startAgentMeshExecute() {
    if (!hasAccess) return;
    setStartingMeshExecute(true);
    setError("");
    try {
      const body = meshQuickActionBody(
        "execute_mesh",
        "تشغيل شبكة الوكلاء",
        AGENT_MESH_EXECUTE_PROMPT,
      );
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingMeshExecute(false);
    }
  }

  async function runCommandCenterCommand(command: AgentCommandCenterCommand) {
    if (!localMode) return;
    setStartingCommandCenterId(command.id);
    setError("");
    try {
      const data = await agentApi<{ task: AgentTask; command: AgentCommandCenterCommand }>(
        null,
        "/api/agent/command-center/run",
        {
          method: "POST",
          body: JSON.stringify({ command_id: command.id }),
        },
      );
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await Promise.all([loadTasks(), loadCommandCenter()]);
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingCommandCenterId(null);
    }
  }

  async function runCommandCenterCommandById(
    commandId: string,
    fallback: () => Promise<void> | void,
  ) {
    const command = commandCenter?.commands.find((item) => item.id === commandId);
    if (localMode && command) {
      await runCommandCenterCommand(command);
      return;
    }
    await fallback();
  }

  async function startExecutionOsMission() {
    if (!hasAccess) return;
    setStartingExecutionOs(true);
    setError("");
    try {
      const body = meshQuickActionBody(
        "execute_mesh",
        "تشغيل محرك فتحية التنفيذي",
        FATHIYA_EXECUTION_OS_PROMPT,
      );
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingExecutionOs(false);
    }
  }

  async function startActivationSweep() {
    if (!hasAccess) return;
    setStartingActivationSweep(true);
    setError("");
    try {
      const body = meshQuickActionBody(
        "activate_tools",
        "تفعيل نواقص فتحية",
        FATHIYA_ACTIVATION_SWEEP_PROMPT,
      );
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingActivationSweep(false);
    }
  }

  async function startCodespacesAgent() {
    if (!hasAccess) return;
    setStartingCodespacesAgent(true);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: "تشغيل وكيل GitHub Codespaces",
        prompt: GITHUB_CODESPACES_AGENT_PROMPT,
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingCodespacesAgent(false);
    }
  }

  async function startOpenRouterStrategy() {
    if (!hasAccess) return;
    setStartingOpenRouterStrategy(true);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: "استراتيجية OpenRouter/Fusion",
        prompt: OPENROUTER_MODEL_STRATEGY_PROMPT,
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingOpenRouterStrategy(false);
    }
  }

  async function startAgentProviderProbe(providerApp: string) {
    if (!hasAccess || !providerApp.trim()) return;
    setStartingAgentProviderProbe(providerApp);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: `فحص وكيل تطبيق: ${providerApp}`,
        prompt: [
          `agent provider probe: ${providerApp}`,
          "افحص هذا المزود من مخزون Zapier MCP داخل فتحية.",
          "اعرض أفعال القراءة والكتابة المتاحة، ولا تنفذ أي إجراء خارجي.",
        ].join("\n"),
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingAgentProviderProbe(null);
    }
  }

  async function startAgentProviderPrepare(providerApp: string) {
    if (!hasAccess || !providerApp.trim()) return;
    setStartingAgentProviderPrepare(providerApp);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: `تحضير تشغيل وكيل: ${providerApp}`,
        prompt: [
          `agent provider action: ${providerApp}`,
          "حضّر أفضل فعل Zapier مناسب لتشغيل هذا المزود كوكيل تطبيق.",
          "لا تنفذ أي إجراء خارجي الآن؛ أعد action name وtask prompt واحتياج OAuth/الموافقة.",
        ].join("\n"),
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingAgentProviderPrepare(null);
    }
  }

  async function startKnowledgeExecution() {
    if (!hasAccess) return;
    setStartingKnowledgeExecution(true);
    setError("");
    try {
      const body = meshQuickActionBody(
        "learn_and_execute",
        "استيعاب وتشغيل فتحية",
        KNOWLEDGE_EXECUTION_PROMPT,
      );
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingKnowledgeExecution(false);
    }
  }

  async function startMissionLauncher() {
    if (!hasAccess) return;
    setStartingMission(true);
    setError("");
    try {
      const body = buildMissionTaskBody(
        missionMode,
        missionObjective,
        missionSources,
        missionAutonomyMode,
      );
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setMissionObjective("");
      setMissionSources("");
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingMission(false);
    }
  }

  async function startMissionFollowUp(mode: MissionMode) {
    if (!hasAccess) return;
    setStartingMissionMode(mode);
    setError("");
    try {
      const body = buildMissionTaskBody(
        mode,
        `تابع مسار ${MISSION_MODE_LABELS[mode]} من آخر نتيجة، نفذ الخطوة الداخلية التالية المناسبة، ثم سجل إيصالًا واضحًا.`,
        "",
        missionAutonomyMode,
      );
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingMissionMode(null);
    }
  }

  async function startBugBountyHunt(mode: BugBountyRunMode = "hunt") {
    if (!hasAccess) return;
    setStartingBugBountyHunt(true);
    setStartingBugBountyAction(mode);
    setError("");
    try {
      const normalizedProgramUrl = normalizeOptionalUrl(bugBountyProgramUrl);
      const prompt =
        mode === "draft-gate"
          ? buildBugBountyDraftGatePrompt({
              platform: bugBountyPlatform,
              programUrl: normalizedProgramUrl,
            })
          : buildBugBountyHuntPrompt({
              platform: bugBountyPlatform,
              programUrl: normalizedProgramUrl,
              repoUrl: bugBountyRepoUrl,
              focus: bugBountyFocus,
              allowedScope: bugBountyAllowedScope,
              exclusions: bugBountyExclusions,
              evidencePlan: bugBountyEvidencePlan,
              dedupeNotes: bugBountyDedupeNotes,
              mode,
            });
      const titlePrefix =
        mode === "dedupe" ? "Dedupe صيد ثغرات" : mode === "draft-gate" ? "تحقق Draft" : "صيد ثغرات";
      const body: CreateAgentTaskBody = {
        title: `${titlePrefix}: ${bugBountyProgramLabel(bugBountyPlatform, normalizedProgramUrl)}`,
        prompt,
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingBugBountyHunt(false);
      setStartingBugBountyAction(null);
    }
  }

  async function startFollowUpTask(action: AgentMeshNextAction) {
    if (!hasAccess || !action.prompt.trim()) return;
    setStartingFollowUpPrompt(action.prompt);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: action.title || "متابعة تنفيذية",
        prompt: action.prompt,
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingFollowUpPrompt(null);
    }
  }

  async function handleFollowUpAction(action: AgentMeshNextAction) {
    const mode = followUpActionMode(action);
    if (mode === "settings") {
      setSelectedSettingsGroup(action.settings_group ?? null);
      return;
    }
    if (mode === "oauth") {
      window.location.assign(integrationActionHref(action.action_path ?? ""));
      return;
    }
    await startFollowUpTask(action);
  }

  async function startLocalSettingsProbe(group: AgentLocalSettingsGroup) {
    if (!hasAccess) return null;
    const body = localSettingsProbeTaskBody(group.id, group.name);
    const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
      method: "POST",
      body: JSON.stringify(body),
    });
    setSelectedId(data.task.id);
    setWorkspaceView("reports");
    await loadTasks();
    return data.task;
  }

  async function taskAction(action: "approve" | "cancel") {
    if (!hasAccess || !selectedId) return;
    setActing(true);
    setError("");
    try {
      await agentApi(session ?? null, `/api/agent/tasks/${selectedId}/${action}`, {
        method: "POST",
      });
      await Promise.all([loadTasks(), loadDetail()]);
    } catch (actionError) {
      setError(String(actionError));
    } finally {
      setActing(false);
    }
  }

  async function tradingAction(action: "start" | "stop" | "tick" | "strategy-refresh") {
    if (!localMode) return;
    setTradingActing(true);
    setError("");
    try {
      await agentApi(null, `/api/agent/trading/${action}`, { method: "POST" });
      await loadTrading();
    } catch (actionError) {
      setError(String(actionError));
    } finally {
      setTradingActing(false);
    }
  }

  async function intakeAction(action: "start" | "stop" | "scan") {
    if (!localMode) return;
    setIntakeActing(true);
    setError("");
    try {
      await agentApi(null, `/api/agent/intake/${action}`, { method: "POST" });
      await Promise.all([loadIntake(), loadRuntimeHealth(), loadTasks()]);
    } catch (actionError) {
      setError(String(actionError));
    } finally {
      setIntakeActing(false);
    }
  }

  async function probeIntegration(integration: AgentIntegrationReadiness) {
    if (!localMode || !integration.probe_path) return;
    setProbingIntegration(integration.id);
    setError("");
    try {
      const result = await agentApi<AgentIntegrationProbeResult>(null, integration.probe_path, {
        method: "POST",
      });
      setIntegrationProbes((current) => ({ ...current, [integration.id]: result }));
      await loadIntegrations();
    } catch (probeError) {
      setError(String(probeError));
    } finally {
      setProbingIntegration(null);
    }
  }

  async function startIntegrationTask(integration: AgentIntegrationReadiness) {
    if (!localMode || !integration.task_prompt) return;
    setStartingIntegrationTask(integration.id);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: `فحص اتصال: ${integration.name}`,
        prompt: integration.task_prompt,
      };
      const data = await agentApi<{ task: AgentTask }>(null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingIntegrationTask(null);
    }
  }

  async function handleZapierCommand() {
    if (!localMode) return;
    if (!zapierIntegration) {
      setWorkspaceView("tools");
      return;
    }
    if (zapierIntegration.action_path && zapierIntegration.status !== "ready") {
      window.location.assign(integrationActionHref(zapierIntegration.action_path));
      return;
    }
    if (zapierIntegration.task_prompt) {
      await startIntegrationTask(zapierIntegration);
      return;
    }
    if (zapierIntegration.probe_path) {
      await probeIntegration(zapierIntegration);
      return;
    }
    setWorkspaceView("tools");
  }

  async function startZapierReadTask(action: ZapierReadAction) {
    if (!localMode) return;
    if (!zapierLiveExecutionReady) {
      setError("قراءة Zapier تحتاج OAuth محلي مفعل. المخزون ظاهر الآن، لكن التنفيذ الحي غير متصل.");
      setWorkspaceView("tools", { scroll: false });
      return;
    }
    setStartingZapierReadAction(action.id);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: `قراءة Zapier: ${action.app}/${action.action}`,
        prompt: [
          `Zapier action: ${action.app} / ${action.action}`,
          "نفذ إجراء قراءة آمن من Zapier MCP عبر مشغل فتحية، ثم سجل التقدم والإيصال.",
          "params:{}",
        ].join("\n"),
      };
      const data = await agentApi<{ task: AgentTask }>(null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingZapierReadAction(null);
    }
  }

  async function loadZapierCatalog(app = selectedZapierApp, refresh = false) {
    const cleanApp = app.trim();
    if (!localMode || !cleanApp) return;
    setLoadingZapierCatalog(true);
    setError("");
    try {
      const params = new URLSearchParams({ app: cleanApp });
      if (refresh) params.set("refresh", "true");
      const data = await agentApi<AgentZapierActionCatalog>(
        null,
        `/api/agent/zapier/catalog?${params.toString()}`,
      );
      setZapierCatalog(data);
    } catch (catalogError) {
      setError(String(catalogError));
    } finally {
      setLoadingZapierCatalog(false);
    }
  }

  async function startZapierCatalogAction(action: AgentZapierCatalogAction) {
    if (!localMode || !selectedZapierApp.trim() || !action.name.trim()) return;
    if (zapierCatalog?.live_available === false || action.inventory_only) {
      setError("إجراء Zapier ظاهر من المخزون فقط الآن. اربط Zapier OAuth المحلي قبل التنفيذ الحي.");
      setWorkspaceView("tools", { scroll: false });
      return;
    }
    const actionId = `${selectedZapierApp}:${action.name}`;
    const isRead = action.mode === "read";
    setStartingZapierCatalogAction(actionId);
    setError("");
    try {
      let parsedParams: Record<string, unknown> = {};
      const cleanParams = zapierActionParams.trim();
      if (cleanParams) {
        const parsed = JSON.parse(cleanParams) as unknown;
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
          throw new Error("مدخلات Zapier يجب أن تكون JSON object");
        }
        parsedParams = parsed as Record<string, unknown>;
      }
      const paramsLine = `params:${JSON.stringify(parsedParams)}`;
      const instructions = zapierActionInstructions.trim();
      const body: CreateAgentTaskBody = {
        title: `${isRead ? "قراءة" : "تشغيل"} Zapier: ${selectedZapierApp}/${action.name}`,
        prompt: [
          `Zapier action: ${selectedZapierApp} / ${action.name}`,
          isRead
            ? "نفذ إجراء قراءة آمن من Zapier MCP عبر مشغل فتحية، ثم سجل التقدم والإيصال."
            : "حضّر إجراء Zapier خارجي عبر مشغل فتحية وبوابة المخاطر، ولا ترسل أو تعدل شيئًا خارج الحساب قبل موافقة صريحة داخل المهمة.",
          instructions ? `instructions: ${instructions}` : "",
          paramsLine,
        ]
          .filter(Boolean)
          .join("\n"),
      };
      const data = await agentApi<{ task: AgentTask }>(null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      setWorkspaceView("reports");
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingZapierCatalogAction(null);
    }
  }

  async function startConnectorTask(connector: AgentConnectorProfile) {
    if (!localMode || !connector.configured) return;
    setStartingConnectorProfile(connector.name);
    setError("");
    try {
      const body: CreateAgentTaskBody = {
        title: `تشغيل موصل: ${connector.provider}/${connector.name}`,
        prompt: [
          `Connector profile: ${connector.name}`,
          `نفذ موصل ${connector.provider} المسمى ${connector.name} عبر مشغل فتحية، ثم سجل التقدم والإيصال.`,
          "payload:{}",
        ].join("\n"),
      };
      const data = await agentApi<{ task: AgentTask }>(null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedId(data.task.id);
      await loadTasks();
    } catch (taskError) {
      setError(String(taskError));
    } finally {
      setStartingConnectorProfile(null);
    }
  }

  async function signOut() {
    if (localMode) {
      setTasks([]);
      setDetail(null);
      return;
    }
    await supabase.auth.signOut();
    setTasks([]);
    setDetail(null);
  }

  const activeCount = useMemo(
    () => tasks.filter((task) => ACTIVE_STATUSES.has(task.status)).length,
    [tasks],
  );
  const configuredConnectorCount = useMemo(
    () => connectors.filter((connector) => connector.configured).length,
    [connectors],
  );
  const automaticConnectorCount = useMemo(
    () =>
      connectors.filter((connector) => connector.configured && !connector.requires_approval)
        .length,
    [connectors],
  );
  const engineReadyCount = integrationSummary?.ready ?? 0;
  const enginePartialCount = integrationSummary?.partial ?? 0;
  const activationIntegrations = useMemo(
    () => buildActivationQueue(integrations),
    [integrations],
  );
  const codespacesIntegration = useMemo(
    () => integrations.find((integration) => integration.id === "github_codespaces") ?? null,
    [integrations],
  );
  const zapierIntegration = useMemo(
    () => integrations.find((integration) => integration.id === "zapier_mcp") ?? null,
    [integrations],
  );
  const zapierNeedsOAuth = Boolean(
    zapierIntegration?.action_path && zapierIntegration.status !== "ready",
  );
  const zapierCommandLabel = zapierNeedsOAuth
    ? zapierIntegration?.action_label || "ربط Zapier"
    : "فحص Zapier";
  const zapierCommandDisabled =
    !zapierIntegration ||
    startingIntegrationTask === "zapier_mcp" ||
    probingIntegration === "zapier_mcp" ||
    (!zapierIntegration.action_path &&
      !zapierIntegration.task_prompt &&
      !zapierIntegration.probe_path);
  const zapierActionCount = connectedInventory?.zapier_action_count ?? 0;
  const zapierAppCount = connectedInventory?.zapier_app_count ?? 0;
  const zapierLiveExecutionReady = Boolean(
    connectedInventory?.direct_zapier_mcp?.connected &&
      connectedInventory?.direct_zapier_mcp?.direct_execution,
  );
  const zapierCatalogInventoryOnly = Boolean(
    zapierCatalog?.inventory_available ||
      (zapierCatalog?.source === "connected_tool_inventory_fallback" &&
        zapierCatalog.action_count > 0),
  );
  const zapierCatalogLive = Boolean(
    zapierCatalog?.connected && zapierCatalog.live_available !== false,
  );
  const workerOnline = Boolean(runtimeHealth?.worker_online);
  const intakeRunning = Boolean(runtimeHealth?.knowledge_intake.running ?? intake?.running);
  const meshActivation = meshSummary?.activation_overview;
  const localExecutionReady = Boolean(
    workerOnline &&
      (commandCenter?.ready_to_execute ||
        meshSummary?.ready_to_execute ||
        meshActivation?.executable_now),
  );
  const readyLaneLabel = meshActivation
    ? `${meshActivation.ready_lane_count}/${meshActivation.lane_count} مسارات`
    : `${engineReadyCount}/${integrationSummary?.total ?? integrations.length} تكاملات`;
  const upgradeActionCount = meshActivation?.upgrade_action_count ?? 0;
  const blockingActionCount = meshActivation?.blocking_action_count ?? 0;
  const planningRoute = runtimeHealth?.agent_loop.local_planning_enabled
    ? "Hugging Face المحلي ثم OpenRouter"
    : "OpenRouter→حتمي";
  const loopBudget = runtimeHealth
    ? `${runtimeHealth.agent_loop.max_rounds} جولات · ${runtimeHealth.agent_loop.max_tool_steps_per_round} أدوات · ${planningRoute}`
    : "--";
  const missionModeItems = [
    {
      id: "execution" as const,
      icon: Activity,
      meta: "كل الوكلاء",
    },
    {
      id: "trading" as const,
      icon: TrendingUp,
      meta: "Paper · ثانية",
    },
    {
      id: "bug-bounty" as const,
      icon: ShieldAlert,
      meta: "H1 · BC · Draft",
    },
    {
      id: "knowledge" as const,
      icon: FolderSearch,
      meta: "HF · Fusion",
    },
    {
      id: "tools" as const,
      icon: Settings2,
      meta: "Zapier · n8n",
    },
  ];
  const missionAutonomyItems = [
    {
      id: "direct" as const,
      label: MISSION_AUTONOMY_LABELS.direct,
      description: "ينفذ الداخلي والقراءة فورًا",
    },
    {
      id: "guided" as const,
      label: MISSION_AUTONOMY_LABELS.guided,
      description: "يفتح بوابة أثر واضحة",
    },
    {
      id: "activation" as const,
      label: MISSION_AUTONOMY_LABELS.activation,
      description: "يرتب OAuth والإعدادات الناقصة",
    },
  ];
  const latestMeshRuntime = useMemo(() => {
    const completed = tasks
      .filter((task) => task.status === "completed" && task.result !== null)
      .sort((a, b) => {
        const aTime = new Date(a.completed_at || a.updated_at || a.created_at).getTime();
        const bTime = new Date(b.completed_at || b.updated_at || b.created_at).getTime();
        return bTime - aTime;
      });
    for (const task of completed) {
      const result = asRecord(task.result);
      const runtime = result ? extractAgentMeshRuntimeResult(result) : null;
      if (runtime) return { task, runtime };
    }
    return null;
  }, [tasks]);
  const zapierReadActions = useMemo(
    () => buildZapierReadActions(connectedInventory),
    [connectedInventory],
  );
  const agentProviderSummaries = useMemo(
    () =>
      Object.entries(connectedInventory?.agent_provider_actions ?? {})
        .filter(([app]) => isVisibleAgentProviderApp(app))
        .map(([app, actionSet]) => ({
          app,
          readCount: actionSet.read?.length ?? 0,
          writeCount: actionSet.approval_gated_write?.length ?? 0,
          readActions: actionSet.read ?? [],
          writeActions: actionSet.approval_gated_write ?? [],
        }))
        .sort((a, b) => b.readCount + b.writeCount - (a.readCount + a.writeCount))
        .slice(0, 8),
    [connectedInventory],
  );
  const meshAgentProviders =
    meshSummary?.agent_providers ?? meshActivation?.agent_providers ?? [];
  const meshAgentProviderCount =
    meshActivation?.agent_provider_count ??
    (meshAgentProviders.length || agentProviderSummaries.length);
  const visibleZapierApps = useMemo(
    () =>
      connectedInventory?.zapier_apps
        ?.filter((app) => isVisibleAgentProviderApp(app.app)) ?? [],
    [connectedInventory],
  );
  const topZapierApps = useMemo(() => visibleZapierApps.slice(0, 10), [visibleZapierApps]);
  useEffect(() => {
    if (!selectedZapierApp && topZapierApps[0]?.app) {
      setSelectedZapierApp(topZapierApps[0].app);
    }
  }, [selectedZapierApp, topZapierApps]);

  useEffect(() => {
    if (!localMode || !zapierIntegration?.task_prompt || typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (params.get("integration") !== "zapier_mcp" || params.get("status") !== "connected") {
      return;
    }
    const guardKey = "fathiya.zapier.oauth.connected.task.v1";
    const guardValue = `${window.location.pathname}?${params.toString()}`;
    if (window.sessionStorage.getItem(guardKey) === guardValue) {
      return;
    }
    window.sessionStorage.setItem(guardKey, guardValue);
    const cleanUrl = new URL(window.location.href);
    cleanUrl.searchParams.delete("integration");
    cleanUrl.searchParams.delete("status");
    window.history.replaceState(
      null,
      "",
      `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`,
    );
    void startIntegrationTask(zapierIntegration);
  }, [localMode, zapierIntegration]);

  useEffect(() => {
    if (!localMode || !codespacesIntegration?.task_prompt || typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    if (params.get("integration") !== "github_codespaces") return;
    const status = params.get("status");
    const guardKey = "fathiya.codespaces.oauth.connected.task.v1";
    const guardValue = `${window.location.pathname}?${params.toString()}`;
    const cleanUrl = new URL(window.location.href);
    cleanUrl.searchParams.delete("integration");
    cleanUrl.searchParams.delete("status");
    window.history.replaceState(
      null,
      "",
      `${cleanUrl.pathname}${cleanUrl.search}${cleanUrl.hash}`,
    );
    if (status !== "connected") {
      setError("تعذر إكمال تفويض GitHub Codespaces. افتح زر التفويض أو شغّل gh auth refresh -h github.com -s codespace ثم أعد الفحص.");
      return;
    }
    if (window.sessionStorage.getItem(guardKey) === guardValue) return;
    window.sessionStorage.setItem(guardKey, guardValue);
    void startIntegrationTask(codespacesIntegration);
  }, [localMode, codespacesIntegration]);

  const activeSettingsGroup = useMemo(
    () =>
      localSettings?.groups.find((group) => group.id === selectedSettingsGroup) ?? null,
    [localSettings, selectedSettingsGroup],
  );
  const canCreateTask =
    composerMode === "knowledge"
      ? Boolean(
          reportSource.trim() &&
            reportObjective.trim() &&
            (reportContent.trim() || reportReferences.trim()),
        )
      : Boolean(prompt.trim());
  const focusedTasks = useMemo(() => {
    const matches = tasks.filter((task) => {
      const haystack = `${task.title}\n${task.prompt}`.toLowerCase();
      return (
        haystack.includes("bug bounty") ||
        haystack.includes("صيد") ||
        haystack.includes("ثغر") ||
        haystack.includes("hackerone") ||
        haystack.includes("bugcrowd") ||
        haystack.includes("trading") ||
        haystack.includes("تداول") ||
        haystack.includes("paper") ||
        haystack.includes("zapier") ||
        haystack.includes("زابير") ||
        haystack.includes("mcp") ||
        haystack.includes("codespaces") ||
        haystack.includes("knowledge execution") ||
        haystack.includes("استيعاب وتشغيل")
      );
    });
    return (matches.length > 0 ? matches : tasks).slice(0, 12);
  }, [tasks]);
  const latestMissionTasks = useMemo(() => {
    const latest = Object.fromEntries(
      (Object.keys(MISSION_MODE_LABELS) as MissionMode[]).map((mode) => [mode, null]),
    ) as Record<MissionMode, AgentTask | null>;
    const ordered = [...tasks].sort((a, b) => {
      const aTime = new Date(a.completed_at || a.updated_at || a.created_at).getTime();
      const bTime = new Date(b.completed_at || b.updated_at || b.created_at).getTime();
      return bTime - aTime;
    });
    for (const task of ordered) {
      const mode = classifyMissionTask(task);
      if (mode && latest[mode] === null) {
        latest[mode] = task;
      }
    }
    return latest;
  }, [tasks]);
  const latestLiveExecution = useMemo(() => {
    const ordered = [...tasks].sort((a, b) => {
      const aTime = new Date(a.completed_at || a.updated_at || a.created_at).getTime();
      const bTime = new Date(b.completed_at || b.updated_at || b.created_at).getTime();
      return bTime - aTime;
    });
    for (const task of ordered) {
      const proof = extractLiveExecutionProof(task);
      if (proof) return proof;
    }
    return null;
  }, [tasks]);
  const executionDecision = useMemo(
    () =>
      buildExecutionDecision({
        workerOnline,
        meshSummary,
        integrationSummary,
        integrations,
        activationIntegrations,
        zapierDiagnostics,
        trading,
        intakeRunning,
        zapierAppCount,
        zapierActionCount,
      }),
    [
      workerOnline,
      meshSummary,
      integrationSummary,
      integrations,
      activationIntegrations,
      zapierDiagnostics,
      trading,
      intakeRunning,
      zapierAppCount,
      zapierActionCount,
    ],
  );

  function handleExecutionDecisionAction(action: ExecutionDecisionAction) {
    if (action === "run") {
      void startExecutionOsMission();
      return;
    }
    if (action === "activate") {
      setWorkspaceView("tools");
      void startActivationSweep();
      return;
    }
    void loadTasks();
    void loadDetail();
    void loadConnectors();
    void loadTrading();
    void loadIntegrations();
    void loadMeshSummary();
    void loadIntake();
    void loadRuntimeHealth();
    void loadLocalSettings();
    void loadZapierDiagnostics();
  }

  if (!localMode && session === undefined) {
    return <CenteredState icon={Loader2} title="جارٍ التحقق من الجلسة" spin />;
  }

  if (!hasAccess) {
    return (
      <CenteredState icon={ShieldAlert} title="يلزم تسجيل دخول المشغل">
        {error && <p className="mb-4 break-words text-xs text-destructive">{error}</p>}
        <Button asChild>
          <Link to="/agent-login">تسجيل الدخول</Link>
        </Button>
      </CenteredState>
    );
  }

  return (
    <TooltipProvider delayDuration={250}>
      <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
        <header className="sticky top-0 z-30 border-b border-border/60 bg-background/90 backdrop-blur">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md border border-emerald-500/30 bg-emerald-500/10">
                <ListChecks className="h-5 w-5 text-emerald-400" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-sm font-bold">فتحية</h1>
                  <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                    التداول
                  </Badge>
                  <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-300">
                    صيد الثغرات
                  </Badge>
                  {localMode && (
                    <Badge variant="outline" className="font-mono">
                      LOCAL
                    </Badge>
                  )}
                </div>
                <p className="break-all text-[11px] text-muted-foreground">
                  {localMode ? `${localAgentRuntimeUrl} · ` : ""}
                  {activeCount} نشطة من {tasks.length} مهمة
                  {localMode &&
                    ` · ${localExecutionReady ? "المحرك المحلي جاهز" : "المحرك ينتظر فحص"} · ${readyLaneLabel}`}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => {
                      void loadTasks();
                      void loadDetail();
                      void loadConnectors();
                      void loadTrading();
                      void loadIntegrations();
                      void loadMeshSummary();
                      void loadIntake();
                      void loadRuntimeHealth();
                      void loadLocalSettings();
                    }}
                  >
                    <RefreshCw />
                    <span className="sr-only">تحديث</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>تحديث فتحية</TooltipContent>
              </Tooltip>
              {!localMode && (
                <Button variant="ghost" size="icon" onClick={() => void signOut()}>
                  <LogOut />
                  <span className="sr-only">تسجيل الخروج</span>
                </Button>
              )}
            </div>
          </div>
        </header>

        <main className="mx-auto min-w-0 max-w-7xl px-4 py-5 sm:px-6">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <CircleAlert />
              <AlertTitle>تعذر إكمال الطلب</AlertTitle>
              <AlertDescription className="break-all">{error}</AlertDescription>
            </Alert>
          )}

          <ExecutionDecisionPanel
            decision={executionDecision}
            runningPrimary={startingExecutionOs || startingActivationSweep}
            onPrimary={() => handleExecutionDecisionAction(executionDecision.primaryAction)}
            onSecondary={
              executionDecision.secondaryAction
                ? () => handleExecutionDecisionAction(executionDecision.secondaryAction!)
                : undefined
            }
          />

          {localMode && (
            <AgentLiveCommandStrip
              activeCount={activeCount}
              blockingActionCount={blockingActionCount}
              commandCenter={commandCenter}
              intakeRunning={intakeRunning}
              localExecutionReady={localExecutionReady}
              readyLaneLabel={readyLaneLabel}
              runtimeHealth={runtimeHealth}
              startingBugBounty={startingBugBountyHunt || startingCommandCenterId === "lane_bug_bounty"}
              startingEngine={startingExecutionOs || startingCommandCenterId === "agent_os_full_execute"}
              startingTrading={tradingActing || startingCommandCenterId === "lane_trading"}
              tasksCount={tasks.length}
              trading={trading}
              upgradeActionCount={upgradeActionCount}
              workerOnline={workerOnline}
              onOpenReports={() => setWorkspaceView("reports")}
              onOpenTools={() => setWorkspaceView("tools")}
              onRunBugBounty={() => {
                setWorkspaceView("bug-bounty");
                void runCommandCenterCommandById("lane_bug_bounty", () => startBugBountyHunt("hunt"));
              }}
              onRunEngine={() => {
                void runCommandCenterCommandById("agent_os_full_execute", startExecutionOsMission);
              }}
              onRunTrading={() => {
                setWorkspaceView("trading");
                if (!trading?.running) {
                  void tradingAction("start");
                }
                void runCommandCenterCommandById("lane_trading", () => undefined);
              }}
            />
          )}

          {latestLiveExecution && (
            <section className="mb-3 rounded-md border border-emerald-500/25 bg-emerald-500/[0.045] p-3">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="mb-1 flex flex-wrap items-center gap-2">
                    <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                      تنفيذ حي مؤكد
                    </Badge>
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {latestLiveExecution.receiptId || latestLiveExecution.task.id.slice(0, 8)}
                    </Badge>
                  </div>
                  <h2 className="break-words text-sm font-semibold">
                    {latestLiveExecution.task.title}
                  </h2>
                  <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                    {latestLiveExecution.summary}
                  </p>
                </div>
                <div className="flex flex-wrap justify-end gap-2">
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedId(latestLiveExecution.task.id);
                      setWorkspaceView("reports");
                    }}
                  >
                    <FileCheck2 />
                    فتح الإيصال
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    onClick={() => void startExecutionOsMission()}
                    disabled={startingExecutionOs}
                  >
                    {startingExecutionOs ? <Loader2 className="animate-spin" /> : <Play />}
                    تشغيل جديد
                  </Button>
                </div>
              </div>
              <div className="mt-3 grid gap-2 sm:grid-cols-3">
                <InfoField label="الأدوات" value={latestLiveExecution.tools.join(" · ")} />
                <InfoField label="الجولات" value={String(latestLiveExecution.roundCount)} />
                <InfoField label="آخر تحديث" value={formatDate(latestLiveExecution.completedAt)} />
              </div>
            </section>
          )}

          <Card className="hidden">
            <CardContent className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(320px,0.9fr)]">
              <div className="min-w-0 space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle className="text-base">محرك الوكلاء المحلي</CardTitle>
                      <Badge
                        className={cn(
                          workerOnline
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                            : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                        )}
                      >
                        {workerOnline ? "يعمل الآن" : "ينتظر المشغّل"}
                      </Badge>
                    </div>
                    <CardDescription className="mt-1">
                      {meshActivation?.primary_message ||
                        meshSummary?.headline ||
                        "شغّل فتحية كشبكة وكلاء: تفهم المعرفة، تختار النموذج، تنفذ الداخلي الجاهز، وتترك العالي الأثر كخطوة تفعيل واضحة."}
                    </CardDescription>
                  </div>
                  <Badge variant="outline" className="font-mono">
                    {meshActivation
                      ? `${meshActivation.ready_lane_count}/${meshActivation.lane_count} مسارات`
                      : meshSummary
                        ? `${meshSummary.summary.integration_ready}/${meshSummary.summary.integration_total}`
                      : `${engineReadyCount}/${integrationSummary?.total ?? integrations.length}`}
                  </Badge>
                </div>

                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                  <InfoField
                    label="جاهز الآن"
                    value={meshActivation?.ready_headline || `${engineReadyCount} تكاملات`}
                  />
                  <InfoField
                    label="الأدوات"
                    value={`${meshActivation?.safe_tool_count ?? meshSummary?.summary.tool_count ?? "--"} أداة · n8n ${integrationStatusShort(integrations, "n8n_local")}`}
                  />
                  <InfoField
                    label="وكلاء التطبيقات"
                    value={`${meshAgentProviderCount} وكلاء · ${integrationStatusShort(integrations, "zapier_mcp")}`}
                  />
                  <InfoField label="التداول" value={trading?.running ? `${trading.symbol} · ثانية` : "Paper جاهز"} />
                </div>

                {meshSummary?.lanes.length ? (
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                    {meshSummary.lanes.map((lane) => (
                      <div key={lane.id} className="rounded-md border border-border/50 bg-background/35 p-2">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="truncate text-[11px] font-semibold">{lane.label}</span>
                          <Badge className={meshStatusBadgeClass(lane.status)}>
                            {meshStatusLabel(lane.status)}
                          </Badge>
                        </div>
                        <p className="line-clamp-2 text-[10px] text-muted-foreground">
                          {lane.signal}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : null}

                {meshAgentProviders.length ? (
                  <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
                    {meshAgentProviders.slice(0, 4).map((provider) => (
                      <div
                        key={provider.app}
                        className="rounded-md border border-border/50 bg-background/30 p-2"
                      >
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="truncate text-[11px] font-semibold">
                            {provider.app}
                          </span>
                          <Badge
                            className={
                              provider.status === "ready"
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                : "border-amber-500/30 bg-amber-500/10 text-amber-300"
                            }
                          >
                            {provider.status === "ready" ? "تنفيذ" : "OAuth"}
                          </Badge>
                        </div>
                        <p className="text-[10px] text-muted-foreground">
                          قراءة {provider.read_count} · كتابة {provider.write_count}
                        </p>
                        <div className="mt-2 grid grid-cols-2 gap-1">
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 text-[10px]"
                            disabled={startingAgentProviderProbe === provider.app}
                            onClick={() => void startAgentProviderProbe(provider.app)}
                          >
                            {startingAgentProviderProbe === provider.app ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <Play />
                            )}
                            فحص
                          </Button>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 text-[10px]"
                            disabled={startingAgentProviderPrepare === provider.app}
                            onClick={() => void startAgentProviderPrepare(provider.app)}
                          >
                            {startingAgentProviderPrepare === provider.app ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <Activity />
                            )}
                            حضّر
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}

                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    className="min-w-[170px]"
                    onClick={() => void startExecutionOsMission()}
                    disabled={startingExecutionOs}
                  >
                    {startingExecutionOs ? <Loader2 className="animate-spin" /> : <Play />}
                    تشغيل المحرك
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void startKnowledgeExecution()}
                    disabled={startingKnowledgeExecution}
                  >
                    {startingKnowledgeExecution ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <FolderSearch />
                    )}
                    استيعاب وتشغيل
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void startActivationSweep()}
                    disabled={startingActivationSweep}
                  >
                    {startingActivationSweep ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <Settings2 />
                    )}
                    تفعيل الناقص
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void handleZapierCommand()}
                    disabled={zapierCommandDisabled}
                  >
                    {startingIntegrationTask === "zapier_mcp" ||
                    probingIntegration === "zapier_mcp" ? (
                      <Loader2 className="animate-spin" />
                    ) : zapierNeedsOAuth ? (
                      <KeyRound />
                    ) : (
                      <RefreshCw />
                    )}
                    {zapierCommandLabel}
                  </Button>
                </div>
              </div>

              <div className="min-w-0 rounded-md border border-border/60 bg-background/35 p-3">
                <div className="mb-2 flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold">ما الذي يمنع التفعيل الكامل؟</p>
                  <Badge
                    className={cn(
                      (meshActivation?.blocking_action_count ?? 0) > 0 ||
                        (meshActivation?.upgrade_action_count ?? enginePartialCount) > 0
                        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
                        : "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
                    )}
                  >
                    {meshActivation?.blocking_action_count
                      ? `${meshActivation.blocking_action_count} مانعة`
                      : meshActivation?.upgrade_action_count
                        ? `${meshActivation.upgrade_action_count} ترقيات`
                      : enginePartialCount
                        ? `${enginePartialCount} جزئية`
                        : "مستقر"}
                  </Badge>
                </div>
                <div className="grid gap-2">
                  {activationIntegrations.slice(0, 4).map((integration) => (
                    <div
                      key={integration.id}
                      className="grid gap-2 rounded-md border border-border/50 bg-card/35 p-2 sm:grid-cols-[minmax(0,1fr)_auto]"
                    >
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="text-[11px] font-semibold">{integration.name}</p>
                          <IntegrationStatusBadge status={integration.status} />
                        </div>
                        <p className="mt-1 line-clamp-2 text-[10px] text-muted-foreground">
                          {activationSummary(integration)}
                        </p>
                      </div>
                      <div className="flex items-center justify-end gap-1">
                        {integration.action_path && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-[10px]"
                            onClick={() => {
                              if (integration.action_path) {
                                window.location.assign(integrationActionHref(integration.action_path));
                              }
                            }}
                          >
                            <KeyRound />
                            {integration.action_label ?? "ربط"}
                          </Button>
                        )}
                        {integration.settings_path && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-[10px]"
                            onClick={() => setSelectedSettingsGroup(integration.id)}
                          >
                            <Settings2 />
                            إعداد
                          </Button>
                        )}
                        {integration.task_prompt && (
                          <Button
                            type="button"
                            size="sm"
                            className="h-7 px-2 text-[10px]"
                            onClick={() => void startIntegrationTask(integration)}
                            disabled={startingIntegrationTask === integration.id}
                          >
                            {startingIntegrationTask === integration.id ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <Play />
                            )}
                            فحص
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>

          <section className="mb-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                id: "request" as const,
                label: "تشغيل",
                icon: BrainCircuit,
                meta: "وكلاء",
              },
              {
                id: "trading" as const,
                label: "التداول",
                icon: TrendingUp,
                meta: trading?.running ? "يعمل" : "تشغيل",
              },
              {
                id: "bug-bounty" as const,
                label: "صيد الثغرات",
                icon: ShieldAlert,
                meta: "مسودة",
              },
              {
                id: "reports" as const,
                label: "التقارير",
                icon: FileCheck2,
                meta: String(focusedTasks.length),
              },
            ].map((item) => {
              const Icon = item.icon;
              const active = workspaceView === item.id;
              return (
                <Button
                  key={item.id}
                  type="button"
                  variant={active ? "default" : "outline"}
                  className={cn(
                    "h-12 justify-between rounded-md px-3",
                    !active && "bg-card/40",
                  )}
                  onClick={() => setWorkspaceView(item.id)}
                >
                  <span className="flex items-center gap-2">
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </span>
                  <span className="font-mono text-[10px] opacity-75">{item.meta}</span>
                </Button>
              );
            })}
          </section>

          <section className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-md border border-border/50 bg-card/35 px-3 py-2">
            <p className="text-[10px] text-muted-foreground">
              المعرفة والأدوات مسارات مساعدة للمحرك، وليست صفحات التشغيل اليومية.
            </p>
            <div className="flex flex-wrap gap-1.5">
              {[
                {
                  id: "knowledge" as const,
                  label: "المعرفة",
                  icon: FolderSearch,
                  meta: intakeRunning ? "يراقب" : `${intake?.tracked_files ?? 0} ملفات`,
                },
                {
                  id: "tools" as const,
                  label: "الأدوات",
                  icon: Settings2,
                  meta: `${zapierAppCount || engineReadyCount}`,
                },
              ].map((item) => {
                const Icon = item.icon;
                const active = workspaceView === item.id;
                return (
                  <Button
                    key={item.id}
                    type="button"
                    size="sm"
                    variant={active ? "default" : "outline"}
                    className={cn("h-8 rounded-md px-2 text-[10px]", !active && "bg-background/35")}
                    onClick={() => setWorkspaceView(item.id)}
                  >
                    <Icon className="h-3.5 w-3.5" />
                    {item.label}
                    <span className="font-mono opacity-70">{item.meta}</span>
                  </Button>
                );
              })}
            </div>
          </section>

          {localMode && workspaceView === "tools" && commandCenter && (
            <CommandCenterLauncherPanel
              commandCenter={commandCenter}
              startingCommandId={startingCommandCenterId}
              onRunCommand={(command) => void runCommandCenterCommand(command)}
            />
          )}

          {workspaceView === "request" && (
            <section className="hidden">
              <button
                type="button"
                onClick={() => void startExecutionOsMission()}
                disabled={startingExecutionOs}
                className={cn(
                  "group rounded-md border border-emerald-500/25 bg-emerald-500/[0.06] p-4 text-right transition-colors hover:border-emerald-500/40 hover:bg-emerald-500/[0.09]",
                  startingExecutionOs && "cursor-wait opacity-70",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">تشغيل فتحية</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      HF · OpenRouter · Zapier · n8n · Kali · Codespaces
                    </p>
                  </div>
                  {startingExecutionOs ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-emerald-300" />
                  ) : (
                    <Play className="h-4 w-4 shrink-0 text-emerald-300" />
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-[9px]">
                    {workerOnline ? "Worker online" : "Worker check"}
                  </Badge>
                  <Badge variant="outline" className="text-[9px]">
                    {engineReadyCount}/{integrationSummary?.total ?? integrations.length}
                  </Badge>
                </div>
              </button>

              <button
                type="button"
                onClick={() => {
                  if (trading?.running) {
                    setWorkspaceView("trading");
                    return;
                  }
                  void tradingAction("start");
                }}
                disabled={tradingActing || !trading}
                className={cn(
                  "group rounded-md border border-emerald-500/20 bg-card/55 p-4 text-right transition-colors hover:border-emerald-500/35 hover:bg-emerald-500/[0.06]",
                  (tradingActing || !trading) && "cursor-wait opacity-70",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">وكيل التداول</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      {trading?.symbol || "BTC-USD"} · {trading?.running ? "ينبض" : "تشغيل"}
                    </p>
                  </div>
                  {tradingActing ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-emerald-300" />
                  ) : (
                    <TrendingUp className="h-4 w-4 shrink-0 text-emerald-300" />
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge
                    className={cn(
                      "text-[9px]",
                      trading?.running
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-border bg-muted/30 text-muted-foreground",
                    )}
                  >
                    {trading?.running ? "يعمل الآن" : "Paper"}
                  </Badge>
                  <Badge variant="outline" className="text-[9px]">
                    {formatSeconds(trading?.execution_cadence.latest_interval_seconds ?? null)}
                  </Badge>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setWorkspaceView("bug-bounty")}
                className="group rounded-md border border-sky-500/20 bg-card/55 p-4 text-right transition-colors hover:border-sky-500/35 hover:bg-sky-500/[0.06]"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">صيد الثغرات</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      HackerOne · Bugcrowd · Draft
                    </p>
                  </div>
                  <ShieldAlert className="h-4 w-4 shrink-0 text-sky-300" />
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-[9px]">
                    Kali {integrationStatusShort(integrations, "kali_wsl")}
                  </Badge>
                  <Badge variant="outline" className="text-[9px]">
                    Zapier {zapierAppCount}
                  </Badge>
                </div>
              </button>

              <button
                type="button"
                onClick={() => void startCodespacesAgent()}
                disabled={startingCodespacesAgent}
                className={cn(
                  "group rounded-md border border-slate-400/20 bg-card/55 p-4 text-right transition-colors hover:border-slate-300/35 hover:bg-slate-400/[0.06]",
                  startingCodespacesAgent && "cursor-wait opacity-70",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">وكيل Codespaces</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      GitHub · Remote agent
                    </p>
                  </div>
                  {startingCodespacesAgent ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-slate-300" />
                  ) : (
                    <Cable className="h-4 w-4 shrink-0 text-slate-300" />
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-[9px]">
                    Codespaces {integrationStatusShort(integrations, "github_codespaces")}
                  </Badge>
                </div>
              </button>

              <button
                type="button"
                onClick={() => void startOpenRouterStrategy()}
                disabled={startingOpenRouterStrategy}
                className={cn(
                  "group rounded-md border border-fuchsia-500/20 bg-card/55 p-4 text-right transition-colors hover:border-fuchsia-500/35 hover:bg-fuchsia-500/[0.06]",
                  startingOpenRouterStrategy && "cursor-wait opacity-70",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">استراتيجية النماذج</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      Fusion · Advisor · Subagent
                    </p>
                  </div>
                  {startingOpenRouterStrategy ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin text-fuchsia-300" />
                  ) : (
                    <BrainCircuit className="h-4 w-4 shrink-0 text-fuchsia-300" />
                  )}
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="max-w-full truncate text-[9px]">
                    {runtimeHealth?.agent_loop.openrouter_model || "free route"}
                  </Badge>
                  <Badge variant="outline" className="text-[9px]">
                    بحث عميق
                  </Badge>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setWorkspaceView("knowledge")}
                className={cn(
                  "group rounded-md border border-violet-500/20 bg-card/55 p-4 text-right transition-colors hover:border-violet-500/35 hover:bg-violet-500/[0.06]",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">استيعاب وتشغيل</p>
                    <p className="mt-1 truncate text-[10px] text-muted-foreground">
                      معرفة · أدوات · تنفيذ
                    </p>
                  </div>
                  <FolderSearch className="h-4 w-4 shrink-0 text-violet-300" />
                </div>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge variant="outline" className="text-[9px]">
                    {intakeRunning ? "المراقبة تعمل" : "تشغيل الآن"}
                  </Badge>
                  <Badge variant="outline" className="text-[9px]">
                    {intake?.tracked_files ?? 0} ملفات
                  </Badge>
                </div>
              </button>
            </section>
          )}

          {workspaceView === "request" && (
            <Card className="mb-4 border-emerald-500/25 bg-emerald-500/[0.035]">
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <CardTitle className="text-sm">تشغيل فتحية كوكلاء</CardTitle>
                    <CardDescription>
                      مسار واحد يفهم الهدف، يختار النماذج والأدوات، ينفذ الداخلي الجاهز، ثم يعيد إيصالًا.
                    </CardDescription>
                  </div>
                  <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
                    {MISSION_MODE_LABELS[missionMode]} · {MISSION_AUTONOMY_LABELS[missionAutonomyMode]}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3 lg:grid-cols-[minmax(0,0.95fr)_minmax(320px,1.05fr)]">
                <div className="min-w-0 space-y-3">
                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                    {missionModeItems.map((item) => {
                      const Icon = item.icon;
                      const active = missionMode === item.id;
                      return (
                        <Button
                          key={item.id}
                          type="button"
                          variant={active ? "default" : "outline"}
                          className={cn(
                            "h-16 justify-between rounded-md px-3 text-right",
                            !active && "bg-background/35",
                          )}
                          onClick={() => setMissionMode(item.id)}
                        >
                          <span className="flex min-w-0 flex-col items-start gap-1">
                            <span className="text-xs font-semibold">
                              {MISSION_MODE_LABELS[item.id]}
                            </span>
                            <span className="max-w-full truncate font-mono text-[9px] opacity-75">
                              {item.meta}
                            </span>
                          </span>
                          <Icon className="h-4 w-4 shrink-0" />
                        </Button>
                      );
                    })}
                  </div>
                  <div className="rounded-md border border-border/60 bg-background/35 p-2">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="text-[10px] font-semibold">وضع التنفيذ</span>
                      <Badge variant="outline" className="text-[9px] font-normal">
                        {MISSION_AUTONOMY_LABELS[missionAutonomyMode]}
                      </Badge>
                    </div>
                    <div className="grid gap-2 sm:grid-cols-3">
                      {missionAutonomyItems.map((item) => {
                        const active = missionAutonomyMode === item.id;
                        return (
                          <Button
                            key={item.id}
                            type="button"
                            variant={active ? "default" : "outline"}
                            className={cn(
                              "h-auto min-h-12 items-start justify-start rounded-md px-3 py-2 text-right",
                              !active && "bg-card/30",
                            )}
                            onClick={() => setMissionAutonomyMode(item.id)}
                          >
                            <span className="min-w-0">
                              <span className="block text-[11px] font-semibold">
                                {item.label}
                              </span>
                              <span className="block text-[9px] font-normal opacity-75">
                                {item.description}
                              </span>
                            </span>
                          </Button>
                        );
                      })}
                    </div>
                    <p className="mt-2 text-[10px] leading-relaxed text-muted-foreground">
                      الداخلي والقراءة والنماذج المحلية تعمل مباشرة؛ OAuth والمال والإرسال الخارجي
                      تظهر كمتابعات قابلة للتشغيل بدل تعطيل المهمة.
                    </p>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[10px]">
                    <InfoField label="Worker" value={workerOnline ? "online" : "check"} />
                    <InfoField
                      label="Models"
                      value={`${integrationStatusShort(integrations, "huggingface_local")} · ${integrationStatusShort(integrations, "openrouter")}`}
                    />
                    <InfoField
                      label="Tools"
                      value={`${integrationStatusShort(integrations, "zapier_mcp")} · ${integrationStatusShort(integrations, "n8n_local")} · ${integrationStatusShort(integrations, "kali_wsl")}`}
                    />
                  </div>
                </div>
                <div className="min-w-0 space-y-2">
                  <div className="space-y-1">
                    <Label htmlFor="mission-objective">الهدف</Label>
                    <Textarea
                      id="mission-objective"
                      value={missionObjective}
                      onChange={(event) => setMissionObjective(event.target.value)}
                      rows={4}
                      placeholder="مثال: استوعب آخر تقارير المعرفة ثم شغّل الأدوات الداخلية المناسبة وسجل الإيصال"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="mission-sources">مصادر اختيارية</Label>
                    <Textarea
                      id="mission-sources"
                      dir="ltr"
                      value={missionSources}
                      onChange={(event) => setMissionSources(event.target.value)}
                      rows={3}
                      className="font-mono text-[10px]"
                      placeholder="رابط أو مسار لكل سطر"
                    />
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      type="button"
                      className="min-w-[180px] flex-1"
                      onClick={() => void startMissionLauncher()}
                      disabled={startingMission}
                    >
                      {startingMission ? <Loader2 className="animate-spin" /> : <Play />}
                      شغّل فتحية الآن
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="min-w-[150px] flex-1"
                      onClick={() => setWorkspaceView("reports")}
                    >
                      <FileCheck2 />
                      التقارير
                    </Button>
                  </div>
                </div>
                <div className="lg:col-span-2">
                  <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-5">
                    {missionModeItems.map((item) => (
                      <MissionResultCard
                        key={item.id}
                        mode={item.id}
                        task={latestMissionTasks[item.id]}
                        fallback={
                          item.id === "trading" && trading
                            ? {
                                status: trading.running ? "يعمل" : "متوقف",
                                summary: [
                                  `${trading.symbol} · ${trading.mode}`,
                                  trading.latest_cycle
                                    ? `${tradingActionLabel(trading.latest_cycle.prediction.action)} · ${trading.latest_cycle.risk.reason}`
                                    : "لم تبدأ دورة التنبؤ بعد.",
                                  trading.latest_receipt_id
                                    ? `إيصال ${trading.latest_receipt_id}`
                                    : "",
                                ]
                                  .filter(Boolean)
                                  .join(" · "),
                                time: formatDate(trading.latest_cycle?.created_at ?? null),
                                actionLabel: "التداول",
                              }
                            : undefined
                        }
                        onOpen={(taskId) => {
                          setSelectedId(taskId);
                          setWorkspaceView("reports");
                        }}
                        onFallbackOpen={() => setWorkspaceView("trading")}
                        onRun={() => void startMissionFollowUp(item.id)}
                        running={startingMissionMode === item.id}
                      />
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {workspaceView === "tools" && (
            <Card className="mb-4 border-emerald-500/25 bg-card/70">
            <CardHeader className="pb-2">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="min-w-0">
                  <CardTitle className="text-sm">حالة المحرك الحي</CardTitle>
                  <CardDescription>
                    نبض العامل، النماذج، الأدوات، وآخر إيصال تشغيل.
                  </CardDescription>
                </div>
                <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                  محرك الوكلاء
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-3 p-4 pt-0 lg:grid-cols-[minmax(0,1fr)_auto]">
              <div className="min-w-0">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <Badge variant="outline">
                    {engineReadyCount}/{integrationSummary?.total ?? integrations.length} جاهزة
                  </Badge>
                  <Badge
                    className={cn(
                      workerOnline
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                    )}
                  >
                    العامل {workerOnline ? "online" : "غير مؤكد"}
                  </Badge>
                  <Badge
                    className={cn(
                      trading?.running
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : "border-border bg-muted/30 text-muted-foreground",
                    )}
                  >
                    التداول {trading?.running ? "ينبض" : "متوقف"}
                  </Badge>
                  <Badge variant="outline">
                    Zapier {zapierAppCount} تطبيق · {zapierActionCount} إجراء
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[10px] sm:grid-cols-3 xl:grid-cols-6">
                  <InfoField
                    label="API"
                    value={runtimeHealth?.status === "ok" ? "online" : "تحقق"}
                  />
                  <InfoField
                    label="Worker"
                    value={runtimeHealth?.worker_id ? `${runtimeHealth.worker_id}` : "--"}
                  />
                  <InfoField
                    label="Loop"
                    value={loopBudget}
                  />
                  <InfoField
                    label="Hugging Face"
                    value={
                      integrations.find((item) => item.id === "huggingface_local")?.status ===
                      "ready"
                        ? "جاهز"
                        : "تحقق"
                    }
                  />
                  <InfoField
                    label="OpenRouter"
                    value={
                      integrations.find((item) => item.id === "openrouter")?.status === "ready"
                        ? "جاهز"
                        : "تحقق"
                    }
                  />
                  <InfoField
                    label="Deep Research"
                    value={runtimeHealth?.agent_loop.openrouter_research_model || "--"}
                  />
                  <InfoField
                    label="Safety"
                    value={runtimeHealth?.agent_loop.openrouter_safety_model || "--"}
                  />
                  <InfoField
                    label="n8n / Kali"
                    value={`${integrationStatusShort(integrations, "n8n_local")} · ${integrationStatusShort(integrations, "kali_wsl")}`}
                  />
                  <InfoField
                    label="Intake"
                    value={intakeRunning ? "يراقب" : "متوقف"}
                  />
                  <InfoField
                    label="آخر إيصال تداول"
                    value={runtimeHealth?.trading.latest_receipt_id || trading?.latest_receipt_id || "--"}
                  />
                </div>
                <AgentActivationQueue
                  className="mt-3"
                  integrations={activationIntegrations}
                  readyCount={engineReadyCount}
                  totalCount={integrationSummary?.total ?? integrations.length}
                  probingIntegration={probingIntegration}
                  startingIntegrationTask={startingIntegrationTask}
                  onOAuth={(integration) => {
                    if (!integration.action_path) return;
                    window.location.assign(integrationActionHref(integration.action_path));
                  }}
                  onSettings={(integration) => setSelectedSettingsGroup(integration.id)}
                  onProbe={(integration) => void probeIntegration(integration)}
                  onTask={(integration) => void startIntegrationTask(integration)}
                />
                {latestMeshRuntime && (
                  <div className="mt-3 rounded-md border border-emerald-500/20 bg-background/35 p-3">
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold">آخر تشغيل فعلي للمحرك</p>
                        <p className="truncate text-[10px] text-muted-foreground">
                          {latestMeshRuntime.task.title} · {formatDate(latestMeshRuntime.task.completed_at)}
                        </p>
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-8 shrink-0 text-[10px]"
                        onClick={() => {
                          setSelectedId(latestMeshRuntime.task.id);
                          setWorkspaceView("reports");
                        }}
                      >
                        <FileCheck2 />
                        التقرير
                      </Button>
                    </div>
                    <AgentMeshRuntimePanel value={latestMeshRuntime.runtime} />
                  </div>
                )}
              </div>
              <div className="grid min-w-[220px] gap-2 sm:grid-cols-2 lg:grid-cols-1">
                <Button
                  type="button"
                  onClick={() => void startExecutionOsMission()}
                  disabled={startingExecutionOs}
                  className="h-11 justify-center"
                >
                  {startingExecutionOs ? <Loader2 className="animate-spin" /> : <Play />}
                  تشغيل المحرك التنفيذي
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void startKnowledgeExecution()}
                  disabled={startingKnowledgeExecution}
                  className="h-11 justify-center"
                >
                  {startingKnowledgeExecution ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <FolderSearch />
                  )}
                  استيعاب وتشغيل
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void startOpenRouterStrategy()}
                  disabled={startingOpenRouterStrategy}
                  className="h-11 justify-center"
                >
                  {startingOpenRouterStrategy ? (
                    <Loader2 className="animate-spin" />
                  ) : (
                    <BrainCircuit />
                  )}
                  استراتيجية النماذج
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => void startAgentMeshExecute()}
                  disabled={startingMeshExecute}
                  className="h-11 justify-center"
                >
                  {startingMeshExecute ? <Loader2 className="animate-spin" /> : <Activity />}
                  فحص شبكة الوكلاء
                </Button>
              </div>
            </CardContent>
            </Card>
          )}

          {workspaceView === "knowledge" && (
            <Card className="mb-4 border-sky-500/25 bg-sky-500/[0.035]">
              <CardHeader className="pb-3">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <FolderSearch className="h-4 w-4 text-sky-300" />
                      المعرفة إلى تنفيذ
                    </CardTitle>
                    <CardDescription className="mt-1">
                      مراقب محلي يحول التقارير والملفات إلى مهام استيعاب وتنفيذ بإيصالات.
                    </CardDescription>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge
                      className={cn(
                        intakeRunning
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                          : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                      )}
                    >
                      {intakeRunning ? "يراقب الآن" : "متوقف"}
                    </Badge>
                    <Badge variant="outline">{intake?.enqueued_count ?? 0} مهمة معرفة</Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
                <div className="min-w-0 space-y-3">
                  <div className="grid gap-2 text-[10px] sm:grid-cols-2 xl:grid-cols-4">
                    <InfoField label="ملفات متتبعة" value={String(intake?.tracked_files ?? 0)} />
                    <InfoField label="آخر مسح" value={formatDate(intake?.last_scan_at ?? null)} />
                    <InfoField
                      label="صيغة الملفات"
                      value={intake?.supported_extensions?.join(" ") || "--"}
                    />
                    <InfoField
                      label="آخر مهمة"
                      value={intake?.last_enqueued?.task_status || "--"}
                    />
                  </div>
                  <div className="rounded-md border border-border/50 bg-background/35 p-2">
                    <p className="text-[10px] font-semibold text-muted-foreground">
                      مجلد المراقبة
                    </p>
                    <p dir="ltr" className="mt-1 break-all text-left font-mono text-[10px]">
                      {intake?.watch_root || "--"}
                    </p>
                  </div>
                  {intake?.last_enqueued && (
                    <div className="rounded-md border border-border/50 bg-background/35 p-2">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-[11px] font-semibold">
                            {intake.last_enqueued.source_name}
                          </p>
                          <p dir="ltr" className="mt-0.5 truncate text-left font-mono text-[9px] text-muted-foreground">
                            {intake.last_enqueued.path}
                          </p>
                        </div>
                        <Badge variant="outline" className="shrink-0 text-[9px]">
                          {intake.last_enqueued.task_progress ?? 0}%
                        </Badge>
                      </div>
                      <p className="mt-1 truncate text-[10px] text-muted-foreground">
                        {intake.last_enqueued.task_current_step || "بانتظار التنفيذ"}
                      </p>
                    </div>
                  )}
                  {intake?.last_error && (
                    <p className="break-words text-[10px] text-destructive">
                      {intake.last_error}
                    </p>
                  )}
                </div>
                <div className="grid min-w-[220px] gap-2 sm:grid-cols-2 lg:grid-cols-1">
                  <Button
                    type="button"
                    onClick={() => void startKnowledgeExecution()}
                    disabled={startingKnowledgeExecution}
                    className="h-10 justify-center"
                  >
                    {startingKnowledgeExecution ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <FolderSearch />
                    )}
                    استيعاب وتشغيل
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void intakeAction("scan")}
                    disabled={intakeActing}
                    className="h-10 justify-center"
                  >
                    {intakeActing ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                    امسح الآن
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => void intakeAction(intakeRunning ? "stop" : "start")}
                    disabled={intakeActing}
                    className="h-10 justify-center"
                  >
                    {intakeRunning ? <Square /> : <Play />}
                    {intakeRunning ? "إيقاف المراقبة" : "تشغيل المراقبة"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!intake?.last_enqueued?.task_id}
                    className="h-10 justify-center"
                    onClick={() => {
                      const taskId = intake?.last_enqueued?.task_id;
                      if (!taskId) return;
                      setSelectedId(taskId);
                      setWorkspaceView("reports");
                    }}
                  >
                    <FileCheck2 />
                    آخر تقرير
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}

          <div
            className={cn(
              "grid min-w-0 gap-4",
              workspaceView === "reports"
                ? "xl:grid-cols-[420px_minmax(0,1fr)]"
                : "xl:grid-cols-1",
            )}
          >
            <div className="min-w-0 space-y-4">
              {workspaceView === "tools" && (
                <Card className="border-border/60 bg-card/50">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-sm">بوابات التنفيذ</CardTitle>
                      <Badge variant="outline">
                        {engineReadyCount}/{integrationSummary?.total ?? integrations.length}
                      </Badge>
                    </div>
                    <CardDescription>
                      اختبر كل بوابة أو أنشئ مهمة فحص لها من نفس المحرك المحلي.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {integrations.map((integration) => (
                      <div
                        key={integration.id}
                        className="rounded-md border border-border/60 bg-background/30 p-3"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="text-xs font-semibold">{integration.name}</p>
                              <IntegrationStatusBadge status={integration.status} />
                            </div>
                            <p className="mt-1 line-clamp-2 text-[10px] text-muted-foreground">
                              {integration.summary}
                            </p>
                          </div>
                          <div className="flex shrink-0 gap-1">
                            {integration.probe_path && (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="icon"
                                    className="h-8 w-8"
                                    onClick={() => void probeIntegration(integration)}
                                    disabled={probingIntegration === integration.id}
                                  >
                                    {probingIntegration === integration.id ? (
                                      <Loader2 className="animate-spin" />
                                    ) : (
                                      <RefreshCw />
                                    )}
                                    <span className="sr-only">اختبار التكامل</span>
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>{integration.probe_label ?? "اختبار"}</TooltipContent>
                              </Tooltip>
                            )}
                            {integration.task_prompt && (
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <Button
                                    type="button"
                                    variant="outline"
                                    size="icon"
                                    className="h-8 w-8"
                                    onClick={() => void startIntegrationTask(integration)}
                                    disabled={startingIntegrationTask === integration.id}
                                  >
                                    {startingIntegrationTask === integration.id ? (
                                      <Loader2 className="animate-spin" />
                                    ) : (
                                      <Play />
                                    )}
                                    <span className="sr-only">تشغيل مهمة التكامل</span>
                                  </Button>
                                </TooltipTrigger>
                                <TooltipContent>{integration.task_label ?? "تشغيل"}</TooltipContent>
                              </Tooltip>
                            )}
                          </div>
                        </div>
                        {integrationProbes[integration.id] && (
                          <IntegrationProbeNotice probe={integrationProbes[integration.id]} />
                        )}
                      </div>
                    ))}
                  </CardContent>
                </Card>
              )}

              {workspaceView === "tools" && (
                <Card className="border-violet-500/25 bg-violet-500/[0.035]">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between gap-3">
                      <CardTitle className="text-sm">وكلاء وتطبيقات متصلة</CardTitle>
                      <Badge className="border-violet-500/30 bg-violet-500/10 text-violet-300">
                        Zapier {zapierAppCount} · {zapierActionCount}
                      </Badge>
                    </div>
                    <CardDescription>
                      مخزون أدوات Zapier ومزودو الوكلاء. التنفيذ الحي يحتاج OAuth محلي مفعل.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {zapierDiagnostics && (
                      <div className="rounded-md border border-amber-500/25 bg-amber-500/[0.06] p-3">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="text-xs font-semibold">تشخيص Zapier MCP</p>
                              <Badge
                                className={cn(
                                  "text-[9px]",
                                  zapierDiagnostics.activation_state === "live"
                                    ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                    : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                                )}
                              >
                                {zapierDiagnostics.activation_state === "live"
                                  ? "متصل حي"
                                  : zapierDiagnostics.activation_state === "reconnect_required"
                                    ? "إعادة ربط"
                                    : zapierDiagnostics.activation_state === "inventory_only"
                                      ? "مخزون فقط"
                                      : "غير متصل"}
                              </Badge>
                            </div>
                            <p className="mt-1 text-[10px] leading-5 text-muted-foreground">
                              {zapierDiagnostics.headline}
                            </p>
                            <div className="mt-2 grid grid-cols-2 gap-2 text-[10px] md:grid-cols-4">
                              <InfoField
                                label="التطبيقات"
                                value={`${zapierDiagnostics.app_count} / ${zapierDiagnostics.action_count}`}
                              />
                              <InfoField
                                label="وكلاء التطبيقات"
                                value={`${zapierDiagnostics.agent_provider_count} · ${zapierDiagnostics.agent_provider_write_action_count} كتابة`}
                              />
                              <InfoField
                                label="Refresh"
                                value={
                                  zapierDiagnostics.refresh_credential_saved
                                    ? "موجود"
                                    : "غير محفوظ"
                                }
                              />
                              <InfoField
                                label="Callback"
                                value="127.0.0.1"
                              />
                            </div>
                            {zapierDiagnostics.last_refresh_error && (
                              <p className="mt-2 rounded-md border border-amber-500/20 bg-background/40 p-2 text-[10px] text-amber-200">
                                آخر تجديد فشل: {zapierDiagnostics.last_refresh_error}
                                {zapierDiagnostics.last_refresh_status_code
                                  ? ` · HTTP ${zapierDiagnostics.last_refresh_status_code}`
                                  : ""}
                              </p>
                            )}
                            {zapierDiagnostics.agent_providers.length > 0 && (
                              <p className="mt-2 break-words text-[10px] text-muted-foreground">
                                يفتح الربط:{" "}
                                {zapierDiagnostics.agent_providers
                                  .slice(0, 6)
                                  .map((provider) => provider.app)
                                  .join(" · ")}
                              </p>
                            )}
                          </div>
                          <div className="flex shrink-0 flex-wrap gap-2">
                            {zapierDiagnostics.activation_state !== "live" && (
                              <Button
                                type="button"
                                size="sm"
                                className="h-8 text-[10px]"
                                onClick={() =>
                                  window.location.assign(
                                    integrationActionHref(
                                      zapierDiagnostics.activation_state ===
                                        "reconnect_required" &&
                                        zapierDiagnostics.fresh_start_path
                                        ? zapierDiagnostics.fresh_start_path
                                        : zapierDiagnostics.start_path,
                                    ),
                                  )
                                }
                              >
                                <KeyRound />
                                {zapierDiagnostics.activation_state === "reconnect_required"
                                  ? "إعادة ربط كاملة"
                                  : "ربط Zapier الآن"}
                              </Button>
                            )}
                            {zapierIntegration?.task_prompt && (
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="h-8 text-[10px]"
                                disabled={startingIntegrationTask === "zapier_mcp"}
                                onClick={() => void startIntegrationTask(zapierIntegration)}
                              >
                                {startingIntegrationTask === "zapier_mcp" ? (
                                  <Loader2 className="animate-spin" />
                                ) : (
                                  <RefreshCw />
                                )}
                                فحص Zapier
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    )}
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <InfoField
                        label="OAuth مباشر"
                        value={
                          connectedInventory?.direct_zapier_mcp?.connected
                            ? "متصل"
                            : zapierAppCount
                              ? "مخزون فقط"
                              : "غير متصل"
                        }
                      />
                      <InfoField
                        label="تنفيذ مباشر"
                        value={
                          zapierLiveExecutionReady
                            ? "مفعل"
                            : "ينتظر OAuth"
                        }
                      />
                    </div>

                    {visibleZapierApps.length > 0 && (
                      <div className="space-y-2 rounded-md border border-border/60 bg-background/30 p-2">
                        <div className="flex flex-wrap items-end gap-2">
                          <div className="min-w-[180px] flex-1 space-y-1">
                            <Label className="text-[10px]">مستكشف إجراءات Zapier</Label>
                            <Select
                              value={selectedZapierApp}
                              onValueChange={(value) => {
                                setSelectedZapierApp(value);
                                setZapierCatalog(null);
                              }}
                            >
                              <SelectTrigger className="h-9 text-xs">
                                <SelectValue placeholder="اختر تطبيقًا" />
                              </SelectTrigger>
                              <SelectContent>
                                {visibleZapierApps.map((app) => (
                                  <SelectItem key={app.app} value={app.app}>
                                    {app.app} · {app.action_count}
                                  </SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            className="h-9 shrink-0 text-[10px]"
                            disabled={!selectedZapierApp || loadingZapierCatalog}
                            onClick={() => void loadZapierCatalog(selectedZapierApp, true)}
                          >
                            {loadingZapierCatalog ? (
                              <Loader2 className="animate-spin" />
                            ) : (
                              <RefreshCw />
                            )}
                            جلب الإجراءات
                          </Button>
                        </div>

                        {zapierCatalog && (
                          <div className="space-y-2">
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <p className="text-[10px] text-muted-foreground">
                                {zapierCatalog.available
                                  ? `${zapierCatalog.app || selectedZapierApp}: ${zapierCatalog.action_count} إجراء`
                                  : zapierCatalog.error || "تعذر قراءة الكتالوج"}
                              </p>
                              <Badge variant="outline" className="text-[9px]">
                                {zapierCatalogLive
                                  ? "OAuth حي"
                                  : zapierCatalogInventoryOnly
                                    ? "مخزون فقط"
                                    : "غير متصل"}
                              </Badge>
                            </div>
                            {zapierCatalogInventoryOnly && !zapierCatalogLive && (
                              <p className="rounded-md border border-amber-500/20 bg-amber-500/10 p-2 text-[10px] leading-5 text-amber-200">
                                هذه الإجراءات ظاهرة من مخزون Zapier المحفوظ. اربط OAuth المحلي لتشغيلها فعليًا من فتحية.
                              </p>
                            )}
                            <div className="grid gap-2">
                              <div className="space-y-1">
                                <Label htmlFor="zapier-action-params" className="text-[10px]">
                                  مدخلات JSON
                                </Label>
                                <Textarea
                                  id="zapier-action-params"
                                  dir="ltr"
                                  value={zapierActionParams}
                                  onChange={(event) => setZapierActionParams(event.target.value)}
                                  rows={3}
                                  className="font-mono text-[10px]"
                                  placeholder='{"query":"fathiya"}'
                                />
                              </div>
                              <div className="space-y-1">
                                <Label htmlFor="zapier-action-instructions" className="text-[10px]">
                                  تعليمات
                                </Label>
                                <Textarea
                                  id="zapier-action-instructions"
                                  value={zapierActionInstructions}
                                  onChange={(event) =>
                                    setZapierActionInstructions(event.target.value)
                                  }
                                  rows={2}
                                  className="text-[10px]"
                                  placeholder="اختصر النتيجة وسجل معرفات آمنة فقط"
                                />
                              </div>
                            </div>
                            {zapierCatalog.actions?.length ? (
                              <div className="space-y-2">
                                {zapierCatalog.actions.slice(0, 8).map((action) => {
                                  const actionId = `${selectedZapierApp}:${action.name}`;
                                  const isRead = action.mode === "read";
                                  const inventoryOnly = Boolean(
                                    action.inventory_only || zapierCatalog.live_available === false,
                                  );
                                  return (
                                    <div
                                      key={action.key || actionId}
                                      className="rounded-md border border-border/50 bg-background/35 p-2"
                                    >
                                      <div className="flex flex-wrap items-center justify-between gap-2">
                                        <div className="min-w-0">
                                          <div className="flex items-center gap-1.5">
                                            <p className="truncate text-[11px] font-semibold">
                                              {action.name}
                                            </p>
                                            <Badge
                                              className={cn(
                                                "shrink-0 text-[9px]",
                                                isRead
                                                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                                  : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                                              )}
                                            >
                                              {isRead ? "قراءة" : "كتابة"}
                                            </Badge>
                                            {inventoryOnly && (
                                              <Badge
                                                variant="outline"
                                                className="shrink-0 border-amber-500/30 text-[9px] text-amber-300"
                                              >
                                                مخزون
                                              </Badge>
                                            )}
                                          </div>
                                          {action.tool_name && (
                                            <p dir="ltr" className="mt-0.5 truncate text-left font-mono text-[9px] text-muted-foreground">
                                              {action.tool_name}
                                            </p>
                                          )}
                                        </div>
                                        <Button
                                          type="button"
                                          variant="outline"
                                          size="sm"
                                          className="h-8 shrink-0 text-[10px]"
                                          disabled={
                                            inventoryOnly ||
                                            startingZapierCatalogAction === actionId
                                          }
                                          onClick={() => void startZapierCatalogAction(action)}
                                        >
                                          {startingZapierCatalogAction === actionId ? (
                                            <Loader2 className="animate-spin" />
                                          ) : (
                                            <Play />
                                          )}
                                          {inventoryOnly ? "اربط OAuth" : "مهمة"}
                                        </Button>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            ) : (
                              <p className="text-[10px] text-muted-foreground">
                                الكتالوج الحي غير مفصل لهذا التطبيق حاليًا، لكن عدد الإجراءات معروف من الجرد.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {agentProviderSummaries.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-[11px] font-semibold">مزودو الوكلاء</p>
                        <div className="grid gap-2 sm:grid-cols-2">
                          {agentProviderSummaries.map((provider) => (
                            <div
                              key={provider.app}
                              className="rounded-md border border-border/60 bg-background/30 p-2"
                            >
                              <div className="flex items-center justify-between gap-2">
                                <p className="truncate text-[11px] font-semibold">
                                  {provider.app}
                                </p>
                                <Badge variant="outline" className="shrink-0 text-[9px]">
                                  {provider.readCount + provider.writeCount}
                                </Badge>
                              </div>
                              <p className="mt-1 text-[10px] text-muted-foreground">
                                قراءة {provider.readCount} · كتابة {provider.writeCount}
                              </p>
                              <p className="mt-1 truncate text-[9px] text-muted-foreground">
                                {[...provider.readActions, ...provider.writeActions][0] ||
                                  "لا توجد أفعال مسماة"}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {zapierReadActions.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <p className="text-[11px] font-semibold">أفعال قراءة آمنة</p>
                          {!zapierLiveExecutionReady && (
                            <Badge
                              variant="outline"
                              className="border-amber-500/30 text-[9px] text-amber-300"
                            >
                              تحتاج OAuth
                            </Badge>
                          )}
                        </div>
                        <div className="space-y-2">
                          {zapierReadActions.map((action) => (
                            <div
                              key={action.id}
                              className="rounded-md border border-border/60 bg-background/30 p-2"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="min-w-0">
                                  <p className="truncate text-[11px] font-semibold">
                                    {action.app}
                                  </p>
                                  <p className="truncate text-[10px] text-muted-foreground">
                                    {action.action}
                                  </p>
                                </div>
                                <Button
                                  type="button"
                                  variant="outline"
                                  size="sm"
                                  className="h-8 shrink-0 text-[10px]"
                                  disabled={
                                    !zapierLiveExecutionReady ||
                                    startingZapierReadAction === action.id
                                  }
                                  onClick={() => void startZapierReadTask(action)}
                                >
                                  {startingZapierReadAction === action.id ? (
                                    <Loader2 className="animate-spin" />
                                  ) : (
                                    <Play />
                                  )}
                                  {zapierLiveExecutionReady ? "تشغيل" : "اربط OAuth"}
                                </Button>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {topZapierApps.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-[11px] font-semibold">أعلى تطبيقات Zapier</p>
                        <div className="flex flex-wrap gap-1.5">
                          {topZapierApps.map((app) => (
                            <Badge key={app.app} variant="outline" className="text-[9px]">
                              {app.app} · {app.action_count}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              {workspaceView === "trading" && (
              <Card className="border-emerald-500/25 bg-emerald-500/[0.04]">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <CardTitle className="flex items-center gap-2 text-sm">
                        <TrendingUp className="h-4 w-4 text-emerald-300" />
                        وكيل التداول
                      </CardTitle>
                      <CardDescription className="mt-1">
                        تنبؤ وتنفيذ Paper/Testnet بنبض سريع، مع إيصالات لكل دورة.
                      </CardDescription>
                    </div>
                    <Badge
                      className={cn(
                        "shrink-0",
                        trading?.running
                          ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                          : "border-border bg-muted/30 text-muted-foreground",
                      )}
                    >
                      {trading?.running ? "يعمل" : "متوقف"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="rounded-md border border-emerald-500/25 bg-background/35 p-3">
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
                      <div className="min-w-0">
                        <div className="mb-1 flex flex-wrap items-center gap-2">
                          <Badge
                            className={
                              trading?.running
                                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                                : "border-border bg-muted/30 text-muted-foreground"
                            }
                          >
                            {trading?.running ? "ينبض الآن" : "جاهز للتشغيل"}
                          </Badge>
                          <Badge variant="outline" className="font-mono text-[10px]">
                            {trading?.symbol || "BTC-USD"}
                          </Badge>
                          <Badge variant="outline" className="text-[10px]">
                            {formatSeconds(trading?.execution_cadence.latest_interval_seconds ?? null)}
                          </Badge>
                        </div>
                        <p className="text-sm font-semibold">المسار السريع للتداول</p>
                        <p className="mt-1 text-[10px] leading-5 text-muted-foreground">
                          زر واحد يشغل أو يوقف وكيل Paper، والمستشار يتجدد عبر النماذج بدون فتح إعدادات.
                        </p>
                      </div>
                      <div className="flex min-w-[220px] flex-wrap gap-2 lg:justify-end">
                        <Button
                          type="button"
                          className="min-w-[150px] flex-1"
                          onClick={() => void tradingAction(trading?.running ? "stop" : "start")}
                          disabled={tradingActing || !trading}
                        >
                          {tradingActing ? (
                            <Loader2 className="animate-spin" />
                          ) : trading?.running ? (
                            <Square />
                          ) : (
                            <Play />
                          )}
                          {trading?.running ? "إيقاف الوكيل" : "تشغيل الوكيل"}
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="icon"
                          onClick={() => void tradingAction("strategy-refresh")}
                          disabled={tradingActing || !trading}
                        >
                          <BrainCircuit />
                          <span className="sr-only">تحديث المستشار</span>
                        </Button>
                      </div>
                    </div>
                  </div>
                  {localMode && trading ? (
                    <>
                      <div className="grid grid-cols-2 gap-2 text-[10px]">
                        <InfoField label="الرمز" value={trading.symbol} />
                        <InfoField label="النمط" value={trading.mode === "paper" ? "Paper" : trading.mode} />
                        <InfoField
                          label="آخر نبضة"
                          value={cadenceLatestLabel(trading.execution_cadence)}
                        />
                        <InfoField
                          label="متوسط النبض"
                          value={formatSeconds(trading.execution_cadence.average_interval_seconds)}
                        />
                        <InfoField
                          label="دقة التنبؤ"
                          value={
                            trading.prediction_quality.directional_accuracy === null
                              ? "--"
                              : formatPercent(trading.prediction_quality.directional_accuracy)
                          }
                        />
                        <InfoField label="PnL" value={formatNumber(trading.portfolio.net_pnl)} />
                      </div>
                      <div className="rounded-md border border-border/50 bg-background/30 p-3 text-[10px]">
                        <div className="mb-1 flex items-center justify-between gap-2">
                          <span className="font-semibold">آخر قرار</span>
                          <span className="font-mono text-muted-foreground">
                            {trading.latest_cycle
                              ? `${trading.latest_cycle.latency_ms.toFixed(2)} ms`
                              : "--"}
                          </span>
                        </div>
                        <p className="break-words text-muted-foreground">
                          {trading.latest_cycle
                            ? `${tradingActionLabel(trading.latest_cycle.prediction.action)} · ${trading.latest_cycle.risk.reason}`
                            : "لم تبدأ دورة التنبؤ بعد."}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          className="flex-1"
                          size="sm"
                          onClick={() => void tradingAction(trading.running ? "stop" : "start")}
                          disabled={tradingActing}
                        >
                          {tradingActing ? (
                            <Loader2 className="animate-spin" />
                          ) : trading.running ? (
                            <Square />
                          ) : (
                            <Play />
                          )}
                          {trading.running ? "إيقاف" : "تشغيل"}
                        </Button>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => void tradingAction("tick")}
                              disabled={tradingActing || trading.running}
                            >
                              <RefreshCw />
                              <span className="sr-only">نبضة تداول واحدة</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>تنفيذ نبضة Paper واحدة</TooltipContent>
                        </Tooltip>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              variant="outline"
                              size="icon"
                              onClick={() => void tradingAction("strategy-refresh")}
                              disabled={tradingActing}
                            >
                              <BrainCircuit />
                              <span className="sr-only">تحديث المستشار</span>
                            </Button>
                          </TooltipTrigger>
                          <TooltipContent>تحديث مستشار نموذج التداول</TooltipContent>
                        </Tooltip>
                      </div>
                      <p
                        className={cn(
                          "text-[10px]",
                          trading.current_market_source === "coinbase_spot"
                            ? "text-emerald-400"
                            : trading.current_market_source
                              ? "text-amber-300"
                              : "text-muted-foreground",
                        )}
                      >
                        {marketNotice(trading.current_market_source)}
                      </p>
                      {tradingReceipts.length > 0 && (
                        <div className="rounded-md border border-emerald-500/20 bg-background/35 p-3">
                          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                            <p className="text-[11px] font-semibold">آخر نبضات التداول</p>
                            <Badge variant="outline" className="text-[9px]">
                              {tradingReceipts.length}
                            </Badge>
                          </div>
                          <div className="grid gap-2">
                            {tradingReceipts.slice(0, 5).map((cycle) => (
                              <div
                                key={cycle.receipt_id}
                                className="grid gap-2 rounded-md border border-border/50 bg-card/35 p-2 text-[10px] sm:grid-cols-[minmax(0,1fr)_auto]"
                              >
                                <div className="min-w-0">
                                  <p className="truncate font-semibold">
                                    {tradingActionLabel(cycle.prediction.action)} ·{" "}
                                    {cycle.symbol}
                                  </p>
                                  <p className="mt-0.5 line-clamp-2 text-muted-foreground">
                                    {cycle.risk.reason}
                                  </p>
                                </div>
                                <div className="flex flex-wrap items-center gap-1.5 sm:justify-end">
                                  <Badge variant="outline" className="text-[9px]">
                                    {cycle.latency_ms.toFixed(1)} ms
                                  </Badge>
                                  <Badge variant="outline" className="max-w-[170px] truncate text-[9px]">
                                    {cycle.receipt_id}
                                  </Badge>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="rounded-md border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
                      شغّل المشغل المحلي حتى تظهر حالة وكيل التداول.
                    </div>
                  )}
                </CardContent>
              </Card>
              )}

              {workspaceView === "bug-bounty" && (
              <Card className="border-sky-500/25 bg-sky-500/[0.04]">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <CardTitle className="flex items-center gap-2 text-sm">
                        <ShieldAlert className="h-4 w-4 text-sky-300" />
                        صيد الثغرات
                      </CardTitle>
                      <CardDescription className="mt-1">
                        نطاق، dedupe، دليل، ثم Draft داخلي قابل للمراجعة قبل أي رفع خارجي.
                      </CardDescription>
                    </div>
                    <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-300">
                      Draft
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="rounded-md border border-sky-500/25 bg-background/35 p-3">
                    <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
                      <div className="min-w-0">
                        <div className="mb-1 flex flex-wrap items-center gap-2">
                          <Badge className="border-sky-500/30 bg-sky-500/10 text-sky-300">
                            مسار سريع
                          </Badge>
                          <Badge variant="outline" className="text-[10px]">
                            Kali {integrationStatusShort(integrations, "kali_wsl")}
                          </Badge>
                          <Badge variant="outline" className="text-[10px]">
                            Dedupe أولًا
                          </Badge>
                        </div>
                        <p className="text-sm font-semibold">صيد ثغرات بزر واحد</p>
                        <p className="mt-1 text-[10px] leading-5 text-muted-foreground">
                          يختار تلقائيًا برنامجًا مصرحًا أو يستخدم الرابط المدخل، يفحص التكرار، ثم يكتب Draft داخلي بدليل.
                        </p>
                      </div>
                      <div className="flex min-w-[260px] flex-wrap gap-2 lg:justify-end">
                        <Button
                          type="button"
                          className="min-w-[150px] flex-1 justify-center"
                          onClick={() => void startBugBountyHunt("hunt")}
                          disabled={startingBugBountyHunt}
                        >
                          {startingBugBountyAction === "hunt" ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <FileCheck2 />
                          )}
                          ابدأ الصيد
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="min-w-[120px] flex-1 justify-center"
                          onClick={() => void startBugBountyHunt("dedupe")}
                          disabled={startingBugBountyHunt}
                        >
                          {startingBugBountyAction === "dedupe" ? (
                            <Loader2 className="animate-spin" />
                          ) : (
                            <ListChecks />
                          )}
                          Dedupe
                        </Button>
                      </div>
                    </div>
                  </div>
                  <div className="grid gap-2 text-[10px] sm:grid-cols-2 xl:grid-cols-4">
                    {[
                      ["1. النطاق", "حدد البرنامج والأصول المسموحة."],
                      ["2. Dedupe", "افحص الجدة قبل التقرير."],
                      ["3. الدليل", "أثر قابل للعرض لا ادعاء نصي."],
                      ["4. Draft", "مسودة داخل فتحية فقط."],
                    ].map(([title, text]) => (
                      <div
                        key={title}
                        className="rounded-md border border-sky-500/20 bg-background/35 p-3"
                      >
                        <p className="font-semibold text-foreground">{title}</p>
                        <p className="mt-1 leading-4 text-muted-foreground">{text}</p>
                      </div>
                    ))}
                  </div>
                  <details className="group rounded-md border border-border/60 bg-background/25 p-3">
                    <summary className="flex cursor-pointer list-none items-center justify-between gap-3 text-xs font-semibold">
                      إعدادات الصيد المتقدمة
                      <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
                    </summary>
                    <div className="mt-3 space-y-3">
                  <div className="grid gap-3 sm:grid-cols-[130px_minmax(0,1fr)]">
                    <div className="space-y-1.5">
                      <Label htmlFor="bug-platform">المنصة</Label>
                      <Select
                        value={bugBountyPlatform}
                        onValueChange={(value) => setBugBountyPlatform(value as BugBountyPlatform)}
                      >
                        <SelectTrigger id="bug-platform" className="h-9">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="auto">تلقائي</SelectItem>
                          <SelectItem value="hackerone">HackerOne</SelectItem>
                          <SelectItem value="bugcrowd">Bugcrowd</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bug-program-url">رابط البرنامج</Label>
                      <Input
                        id="bug-program-url"
                        dir="ltr"
                        value={bugBountyProgramUrl}
                        onChange={(event) => setBugBountyProgramUrl(event.target.value)}
                        placeholder="https://hackerone.com/... أو https://bugcrowd.com/..."
                        maxLength={500}
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="bug-repo-url">GitHub repo اختياري</Label>
                    <Input
                      id="bug-repo-url"
                      dir="ltr"
                      value={bugBountyRepoUrl}
                      onChange={(event) => setBugBountyRepoUrl(event.target.value)}
                      placeholder="https://github.com/org/repo"
                      maxLength={500}
                    />
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="bug-scope-allow">النطاق المسموح</Label>
                      <Textarea
                        id="bug-scope-allow"
                        value={bugBountyAllowedScope}
                        onChange={(event) => setBugBountyAllowedScope(event.target.value)}
                        placeholder="الأصول أو المسارات أو repos المصرح بها. اتركه فارغًا لاستخدام نطاق البرنامج."
                        rows={3}
                        maxLength={1200}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bug-scope-exclude">استبعادات البرنامج</Label>
                      <Textarea
                        id="bug-scope-exclude"
                        value={bugBountyExclusions}
                        onChange={(event) => setBugBountyExclusions(event.target.value)}
                        placeholder="مثال: لا فحص حي، لا DoS، لا social engineering، لا بيانات مستخدمين."
                        rows={3}
                        maxLength={1200}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bug-focus">تركيز الصيد</Label>
                      <Textarea
                        id="bug-focus"
                        value={bugBountyFocus}
                        onChange={(event) => setBugBountyFocus(event.target.value)}
                        placeholder="مثال: CI supply-chain، SSRF، OIDC/JWT، auth bypass، cache poisoning"
                        rows={3}
                        maxLength={1000}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bug-evidence-plan">الإثبات المطلوب</Label>
                      <Textarea
                        id="bug-evidence-plan"
                        value={bugBountyEvidencePlan}
                        onChange={(event) => setBugBountyEvidencePlan(event.target.value)}
                        placeholder="مثال: خطوات إعادة إنتاج، لقطة شاشة، PoC محلي، أثر واضح، سبب severity."
                        rows={3}
                        maxLength={1200}
                      />
                    </div>
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="bug-dedupe-notes">ملاحظات dedupe أو تقارير سابقة</Label>
                    <Textarea
                      id="bug-dedupe-notes"
                      value={bugBountyDedupeNotes}
                      onChange={(event) => setBugBountyDedupeNotes(event.target.value)}
                      placeholder="ضع report IDs أو أسماء دوال أو CVEs أو روابط disclosed reports التي يجب استبعادها قبل الصياغة."
                      rows={3}
                      maxLength={1600}
                    />
                  </div>
                    </div>
                  </details>
                  <div className="grid gap-2 sm:grid-cols-3">
                    <Button
                      type="button"
                      className="justify-center"
                      onClick={() => void startBugBountyHunt("hunt")}
                      disabled={startingBugBountyHunt}
                    >
                      {startingBugBountyAction === "hunt" ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <FileCheck2 />
                      )}
                      صيد + Draft
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="justify-center"
                      onClick={() => void startBugBountyHunt("dedupe")}
                      disabled={startingBugBountyHunt}
                    >
                      {startingBugBountyAction === "dedupe" ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <ListChecks />
                      )}
                      Dedupe فقط
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      className="justify-center"
                      onClick={() => void startBugBountyHunt("draft-gate")}
                      disabled={startingBugBountyHunt}
                    >
                      {startingBugBountyAction === "draft-gate" ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <CheckCircle2 />
                      )}
                      تحقق Draft
                    </Button>
                  </div>
                  <p className="text-[10px] leading-5 text-muted-foreground">
                    هذا المسار يكتب تقريرًا داخليًا فقط. الجدة والأثر العملي مطلوبة قبل أي تصعيد أو رفع خارجي.
                  </p>
                </CardContent>
              </Card>
              )}

              {false && workspaceView === "request" && (
              <Card className="border-violet-500/25 bg-violet-500/[0.04]">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <CardTitle className="flex items-center gap-2 text-sm">
                        <BrainCircuit className="h-4 w-4 text-violet-300" />
                        طلب تنفيذ
                      </CardTitle>
                      <CardDescription className="mt-1">
                        أرسل طلبًا مباشرًا أو حوّل تقريرًا إلى مهمة يفهمها الوكيل وينفذها.
                      </CardDescription>
                    </div>
                    <Badge className="border-violet-500/30 bg-violet-500/10 text-violet-300">
                      Agent
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <form className="space-y-3" onSubmit={createTask}>
                    <div className="space-y-1.5">
                      <Label htmlFor="task-title">العنوان</Label>
                      <Input
                        id="task-title"
                        value={title}
                        onChange={(event) => setTitle(event.target.value)}
                        placeholder="اختياري"
                        maxLength={120}
                      />
                    </div>
                    <Tabs
                      value={composerMode}
                      onValueChange={(value) => setComposerMode(value as "direct" | "knowledge")}
                    >
                      <TabsList className="grid w-full grid-cols-2 rounded-md">
                        <TabsTrigger value="direct">طلب مباشر</TabsTrigger>
                        <TabsTrigger value="knowledge">تقرير إلى تنفيذ</TabsTrigger>
                      </TabsList>
                      <TabsContent value="direct" className="space-y-1.5">
                        <Label htmlFor="task-prompt">الطلب</Label>
                        <Textarea
                          id="task-prompt"
                          value={prompt}
                          onChange={(event) => setPrompt(event.target.value)}
                          placeholder="اكتب الهدف فقط؛ مثل: تحقق من مستودع GitHub fathya-core/fathiya-core، ابحث في Gmail عن OpenRouter Fusion، Search Outlook for invoice 2026، أو اعرض مهام Manus الحالية."
                          rows={7}
                          maxLength={20_000}
                        />
                        <p className="text-[10px] leading-5 text-muted-foreground">
                          فتحية تختار تلقائيًا قراءة Zapier المناسبة، تنفذ الجاهز، وتحول غير المربوط إلى متابعة تشغيلية بإيصال.
                        </p>
                      </TabsContent>
                      <TabsContent value="knowledge" className="space-y-3">
                        <div className="space-y-1.5">
                          <Label htmlFor="report-source">اسم المصدر</Label>
                          <Input
                            id="report-source"
                            value={reportSource}
                            onChange={(event) => setReportSource(event.target.value)}
                            placeholder="مثال: تقرير تدريب أو معرفة جديدة"
                            maxLength={MAX_KNOWLEDGE_SOURCE_CHARACTERS}
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="report-objective">الهدف التنفيذي</Label>
                          <Textarea
                            id="report-objective"
                            value={reportObjective}
                            onChange={(event) => setReportObjective(event.target.value)}
                            placeholder="مثال: استوعب التقرير وشغّل الفحوصات الداخلية المناسبة وسجل الدليل"
                            rows={3}
                            maxLength={MAX_KNOWLEDGE_OBJECTIVE_CHARACTERS}
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="report-references">روابط أو مسارات معرفة</Label>
                          <Textarea
                            id="report-references"
                            value={reportReferences}
                            onChange={(event) => setReportReferences(event.target.value)}
                            placeholder="كل سطر رابط أو مسار محلي، مثال: services/agent-runtime/runtime/knowledge-inbox/openrouter-fusion-email-2026-06-17.md"
                            rows={4}
                            maxLength={2_000}
                            dir="ltr"
                          />
                          <p className="text-[10px] leading-5 text-muted-foreground">
                            فتحية ستحول المسارات إلى source_path وتستوعبها قبل تشغيل الأدوات.
                          </p>
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="report-content">محتوى التقرير</Label>
                          <Textarea
                            id="report-content"
                            value={reportContent}
                            onChange={(event) => setReportContent(event.target.value)}
                            placeholder="ألصق التقرير هنا، أو اتركه فارغًا إذا وضعت روابط/مسارات أعلاه"
                            rows={8}
                            maxLength={MAX_KNOWLEDGE_REPORT_CHARACTERS}
                          />
                        </div>
                      </TabsContent>
                    </Tabs>
                    <Button className="w-full" type="submit" disabled={creating || !canCreateTask}>
                      {creating ? <Loader2 className="animate-spin" /> : <Play />}
                      {composerMode === "knowledge" ? "استيعاب وتنفيذ" : "إرسال للمشغّل"}
                    </Button>
                  </form>
                </CardContent>
              </Card>
              )}

              {workspaceView === "reports" && (
              <Card className="border-border/60 bg-card/50">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between gap-3">
                    <CardTitle className="text-sm">التقارير والمهام</CardTitle>
                    <Badge variant="outline">{focusedTasks.length}</Badge>
                  </div>
                </CardHeader>
                <CardContent className="p-0">
                  <ScrollArea className="h-[360px]">
                    {focusedTasks.length === 0 ? (
                      <p className="px-5 py-8 text-center text-xs text-muted-foreground">
                        لا توجد مهام بعد. ابدأ من التداول أو صيد الثغرات.
                      </p>
                    ) : (
                      <div className="divide-y divide-border/50">
                        {focusedTasks.map((task) => (
                          <button
                            key={task.id}
                            type="button"
                            onClick={() => setSelectedId(task.id)}
                            className={cn(
                              "w-full px-4 py-3 text-right transition-colors hover:bg-muted/40",
                              selectedId === task.id && "bg-muted/50",
                            )}
                          >
                            <div className="mb-1.5 flex items-start justify-between gap-2">
                              <span className="line-clamp-2 text-xs font-semibold">
                                {task.title}
                              </span>
                              <StatusBadge status={task.status} />
                            </div>
                            <Progress value={task.progress} className="mb-1.5 h-1" />
                            <p className="truncate text-[10px] text-muted-foreground">
                              {task.current_step || "لم يبدأ"}
                            </p>
                            {task.latest_receipt_id && (
                              <p className="mt-1 truncate font-mono text-[10px] text-emerald-300">
                                {task.latest_receipt_id}
                              </p>
                            )}
                          </button>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
              )}
            </div>

            {workspaceView === "reports" && (
              <TaskDetail
                detail={detail}
                acting={acting}
                startingFollowUpPrompt={startingFollowUpPrompt}
                onApprove={() => void taskAction("approve")}
                onCancel={() => void taskAction("cancel")}
                onStartFollowUp={(action) => void handleFollowUpAction(action)}
              />
            )}
          </div>
        </main>

        <IntegrationSettingsSheet
          group={activeSettingsGroup}
          writeAllowed={Boolean(localSettings?.write_allowed)}
          onClose={() => setSelectedSettingsGroup(null)}
          onSaved={async () => {
            await Promise.all([loadLocalSettings(), loadIntegrations(), loadConnectors()]);
          }}
          onRunProbe={startLocalSettingsProbe}
        />
      </div>
    </TooltipProvider>
  );
}

function IntegrationSettingsSheet({
  group,
  writeAllowed,
  onClose,
  onSaved,
  onRunProbe,
}: {
  group: AgentLocalSettingsGroup | null;
  writeAllowed: boolean;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onRunProbe: (group: AgentLocalSettingsGroup) => Promise<AgentTask | null>;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [clearFields, setClearFields] = useState<Set<string>>(new Set());
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [sheetError, setSheetError] = useState("");

  useEffect(() => {
    setValues({});
    setClearFields(new Set());
    setVisibleSecrets(new Set());
    setMessage("");
    setSheetError("");
  }, [group?.id]);

  const hasChanges =
    Object.values(values).some((value) => value.trim()) || clearFields.size > 0;

  async function saveSettings(event: FormEvent) {
    event.preventDefault();
    if (!group || !writeAllowed || !hasChanges) return;
    setSaving(true);
    setMessage("");
    setSheetError("");
    try {
      const cleanValues = Object.fromEntries(
        Object.entries(values)
          .map(([name, value]) => [name, value.trim()])
          .filter(([, value]) => Boolean(value)),
      );
      const result = await agentApi<{
        updated_fields: string[];
        cleared_fields: string[];
        restart_required: boolean;
      }>(null, `/api/agent/settings/${group.id}`, {
        method: "POST",
        body: JSON.stringify({
          values: cleanValues,
          clear: [...clearFields],
        }),
      });
      setValues({});
      setClearFields(new Set());
      setMessage(
        result.restart_required
          ? "حُفظ الإعداد محليًا. يلزم إعادة تشغيل المشغّل لتفعيله بالكامل."
          : "حُفظ الإعداد وطُبق على المحرك المحلي.",
      );
      await onSaved();
      const probeTask = await onRunProbe(group);
      if (probeTask) {
        setMessage(`حُفظ الإعداد وبدأ فحص داخلي: ${probeTask.title}`);
      }
    } catch (saveError) {
      setSheetError(String(saveError));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet open={Boolean(group)} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="left" dir="rtl" className="w-full overflow-y-auto sm:max-w-md">
        {group && (
          <>
            <SheetHeader className="text-right">
              <SheetTitle className="flex items-center gap-2 text-base">
                <KeyRound className="h-4 w-4" />
                {group.name}
              </SheetTitle>
              <SheetDescription>{group.description}</SheetDescription>
            </SheetHeader>

            {!writeAllowed && (
              <Alert variant="destructive" className="mt-5">
                <CircleAlert className="h-4 w-4" />
                <AlertTitle>الإعداد المحلي مقفل</AlertTitle>
                <AlertDescription>
                  افتح صفحة الوكلاء من عنوان 127.0.0.1 على هذا الجهاز.
                </AlertDescription>
              </Alert>
            )}

            <form className="mt-6 space-y-5" onSubmit={saveSettings}>
              {group.fields.map((field) => {
                const clearing = clearFields.has(field.name);
                const visible = visibleSecrets.has(field.name);
                return (
                  <div key={field.name} className="space-y-2">
                    <div className="flex items-center justify-between gap-3">
                      <Label htmlFor={`local-setting-${field.name}`} className="text-xs">
                        {field.label}
                      </Label>
                      <div className="flex items-center gap-1.5">
                        {field.configured && (
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[9px]",
                              clearing
                                ? "border-red-500/30 text-red-300"
                                : "border-emerald-500/30 text-emerald-300",
                            )}
                          >
                            {clearing
                              ? "سيُمسح"
                              : field.source === "local_store"
                                ? "محفوظ محليًا"
                                : "من بيئة التشغيل"}
                          </Badge>
                        )}
                        {field.clearable && (
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <Button
                                type="button"
                                size="icon"
                                variant="ghost"
                                className={cn("h-7 w-7", clearing && "text-red-300")}
                                onClick={() =>
                                  setClearFields((current) => {
                                    const next = new Set(current);
                                    if (next.has(field.name)) next.delete(field.name);
                                    else next.add(field.name);
                                    return next;
                                  })
                                }
                                disabled={!writeAllowed || saving}
                              >
                                <Trash2 />
                                <span className="sr-only">مسح القيمة المحلية</span>
                              </Button>
                            </TooltipTrigger>
                            <TooltipContent>
                              {clearing ? "إلغاء المسح" : "مسح القيمة المحلية عند الحفظ"}
                            </TooltipContent>
                          </Tooltip>
                        )}
                      </div>
                    </div>
                    <div className="relative">
                      <Input
                        id={`local-setting-${field.name}`}
                        dir="ltr"
                        type={field.kind === "secret" && !visible ? "password" : "text"}
                        value={values[field.name] ?? ""}
                        placeholder={
                          field.configured
                            ? "اتركه فارغًا للإبقاء على القيمة الحالية"
                            : field.placeholder || field.name
                        }
                        onChange={(event) =>
                          setValues((current) => ({
                            ...current,
                            [field.name]: event.target.value,
                          }))
                        }
                        disabled={!writeAllowed || saving || clearing}
                        autoComplete="off"
                        className={cn("text-left text-xs", field.kind === "secret" && "pl-10")}
                      />
                      {field.kind === "secret" && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="absolute left-1 top-1 h-7 w-7"
                          onClick={() =>
                            setVisibleSecrets((current) => {
                              const next = new Set(current);
                              if (next.has(field.name)) next.delete(field.name);
                              else next.add(field.name);
                              return next;
                            })
                          }
                          disabled={!writeAllowed || saving || clearing}
                        >
                          {visible ? <EyeOff /> : <Eye />}
                          <span className="sr-only">إظهار أو إخفاء القيمة</span>
                        </Button>
                      )}
                    </div>
                    <p dir="ltr" className="break-all text-left font-mono text-[9px] text-muted-foreground">
                      {field.name}
                    </p>
                  </div>
                );
              })}

              {group.restart_required && (
                <p className="text-[10px] text-amber-300">يتطلب التفعيل الكامل إعادة تشغيل المشغّل.</p>
              )}
              {message && <p className="text-[10px] text-emerald-300">{message}</p>}
              {sheetError && <p className="break-words text-[10px] text-destructive">{sheetError}</p>}

              <Button type="submit" className="w-full" disabled={!writeAllowed || saving || !hasChanges}>
                {saving ? <Loader2 className="animate-spin" /> : <Save />}
                حفظ محليًا
              </Button>
            </form>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function TaskDetail({
  detail,
  acting,
  startingFollowUpPrompt,
  onApprove,
  onCancel,
  onStartFollowUp,
}: {
  detail: AgentTaskDetail | null;
  acting: boolean;
  startingFollowUpPrompt: string | null;
  onApprove: () => void;
  onCancel: () => void;
  onStartFollowUp: (action: AgentMeshNextAction) => void;
}) {
  if (!detail) {
    return (
      <Card className="flex min-h-[500px] items-center justify-center border-border/60 bg-card/40">
        <div className="text-center text-muted-foreground">
          <Activity className="mx-auto mb-3 h-7 w-7" />
          <p className="text-sm">اختر مهمة لعرض تقدمها وإيصالاتها.</p>
        </div>
      </Card>
    );
  }

  const { task, events, receipts } = detail;
  const canCancel = ACTIVE_STATUSES.has(task.status);

  return (
    <div className="min-w-0 space-y-4">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="mb-2 flex items-center gap-2">
                <StatusBadge status={task.status} />
                <Badge variant="outline">{riskLabel(task.risk_class)}</Badge>
              </div>
              <CardTitle className="break-words text-base">{task.title}</CardTitle>
              <TaskPrompt prompt={task.prompt} />
            </div>
            <div className="flex items-center gap-2">
              {task.status === "awaiting_approval" && (
                <Button size="sm" onClick={onApprove} disabled={acting}>
                  {acting ? <Loader2 className="animate-spin" /> : <CheckCircle2 />}
                  موافقة
                </Button>
              )}
              {canCancel && (
                <Button variant="outline" size="sm" onClick={onCancel} disabled={acting}>
                  <Square />
                  إلغاء
                </Button>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <div className="mb-2 flex items-center justify-between text-xs">
              <span>{task.current_step || "لم يبدأ"}</span>
              <span className="font-mono">{task.progress}%</span>
            </div>
            <Progress value={task.progress} />
          </div>
          <div className="grid gap-3 text-xs sm:grid-cols-2 lg:grid-cols-4">
            <InfoField label="المشغّل" value={task.worker_id || "لم يُستلم"} />
            <InfoField label="آخر heartbeat" value={formatDate(task.last_heartbeat_at)} />
            <InfoField label="بدأت" value={formatDate(task.started_at)} />
            <InfoField
              label="آخر إيصال"
              value={task.latest_receipt_id || (receipts[0]?.receipt_id ?? "لم يصدر بعد")}
            />
          </div>
          {task.error_message && (
            <Alert variant="destructive">
              <XCircle />
              <AlertTitle>خطأ التنفيذ</AlertTitle>
              <AlertDescription>{task.error_message}</AlertDescription>
            </Alert>
          )}
          {task.status === "awaiting_approval" && <ExecutionCheckpointNotice value={task.result} />}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Clock3 className="h-4 w-4" />
              سجل التقدم
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-auto [&_[data-radix-scroll-area-viewport]]:h-auto lg:h-[420px] lg:[&_[data-radix-scroll-area-viewport]]:h-full">
              <div className="space-y-4 pl-3">
                {events.length === 0 ? (
                  <p className="text-xs text-muted-foreground">لا توجد أحداث بعد.</p>
                ) : (
                  events.map((event, index) => (
                    <div key={event.id}>
                      <div className="flex items-start gap-3">
                        <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-sky-400" />
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <span className="text-xs font-semibold">{event.message}</span>
                            <span className="text-[10px] text-muted-foreground">
                              {formatDate(event.created_at)}
                            </span>
                          </div>
                          <p className="mt-1 text-[10px] text-muted-foreground">
                            {event.step || event.event_type}
                            {event.progress !== null ? ` · ${event.progress}%` : ""}
                          </p>
                        </div>
                      </div>
                      {index < events.length - 1 && <Separator className="mt-4" />}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <FileCheck2 className="h-4 w-4" />
              الإيصالات والنتيجة
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-auto [&_[data-radix-scroll-area-viewport]]:h-auto lg:h-[420px] lg:[&_[data-radix-scroll-area-viewport]]:h-full">
              <div className="space-y-4 pl-3">
                {receipts.map((receipt) => (
                  <div
                    key={receipt.id}
                    className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3"
                  >
                    <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                      <span className="break-all font-mono text-[11px] text-emerald-400">
                        {receipt.receipt_id}
                      </span>
                      <Badge variant="outline">{receipt.status}</Badge>
                    </div>
                    <p className="whitespace-pre-wrap text-xs">{receipt.summary}</p>
                    <ReceiptEvidenceSummary evidence={receipt.evidence} />
                    <TechnicalDetails label="دليل الإيصال التقني" value={receipt.evidence} />
                  </div>
                ))}
                {task.result !== null && (
                  <div>
                    <p className="mb-2 text-xs font-semibold">النتيجة النهائية</p>
                    <TaskResultSummary
                      value={task.result}
                      startingFollowUpPrompt={startingFollowUpPrompt}
                      onStartFollowUp={onStartFollowUp}
                    />
                    <TechnicalDetails label="النتيجة التقنية الكاملة" value={task.result} />
                  </div>
                )}
                {receipts.length === 0 && task.result === null && (
                  <p className="text-xs text-muted-foreground">
                    سيظهر الإيصال هنا بعد اكتمال التنفيذ والتقييم.
                  </p>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function TaskPrompt({ prompt }: { prompt: string }) {
  const mission = parseKnowledgeMissionPrompt(prompt);
  if (!mission) {
    return (
      <CardDescription className="mt-2 whitespace-pre-wrap break-words">{prompt}</CardDescription>
    );
  }
  return (
    <div className="mt-3 space-y-2">
      <Badge variant="outline">تقرير إلى تنفيذ</Badge>
      <p className="text-[11px] text-muted-foreground">{mission.source_name}</p>
      <p className="whitespace-pre-wrap break-words text-sm">{mission.objective}</p>
    </div>
  );
}

function StatusBadge({ status }: { status: AgentTaskStatus }) {
  const tone: Record<AgentTaskStatus, string> = {
    queued: "border-sky-500/30 bg-sky-500/10 text-sky-400",
    running: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    awaiting_approval: "border-violet-500/30 bg-violet-500/10 text-violet-300",
    completed: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    failed: "border-red-500/30 bg-red-500/10 text-red-400",
    stalled: "border-orange-500/30 bg-orange-500/10 text-orange-400",
    canceled: "border-border bg-muted/30 text-muted-foreground",
  };
  return <Badge className={cn("shrink-0", tone[status])}>{STATUS_LABELS[status]}</Badge>;
}

function IntegrationStatusBadge({ status }: { status: AgentIntegrationStatus }) {
  const labels: Record<AgentIntegrationStatus, string> = {
    ready: "جاهز",
    partial: "متصل جزئيًا",
    needs_setup: "يحتاج ربطًا",
    needs_operator: "ينتظر اختيارك",
  };
  const tone: Record<AgentIntegrationStatus, string> = {
    ready: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
    partial: "border-amber-500/30 bg-amber-500/10 text-amber-400",
    needs_setup: "border-orange-500/30 bg-orange-500/10 text-orange-400",
    needs_operator: "border-violet-500/30 bg-violet-500/10 text-violet-300",
  };
  return <Badge className={cn("shrink-0", tone[status])}>{labels[status]}</Badge>;
}

function AgentLiveCommandStrip({
  activeCount,
  blockingActionCount,
  commandCenter,
  intakeRunning,
  localExecutionReady,
  readyLaneLabel,
  runtimeHealth,
  startingBugBounty,
  startingEngine,
  startingTrading,
  tasksCount,
  trading,
  upgradeActionCount,
  workerOnline,
  onOpenReports,
  onOpenTools,
  onRunBugBounty,
  onRunEngine,
  onRunTrading,
}: {
  activeCount: number;
  blockingActionCount: number;
  commandCenter: AgentCommandCenter | null;
  intakeRunning: boolean;
  localExecutionReady: boolean;
  readyLaneLabel: string;
  runtimeHealth: AgentRuntimeHealth | null;
  startingBugBounty: boolean;
  startingEngine: boolean;
  startingTrading: boolean;
  tasksCount: number;
  trading: AgentTradingStatus | null;
  upgradeActionCount: number;
  workerOnline: boolean;
  onOpenReports: () => void;
  onOpenTools: () => void;
  onRunBugBounty: () => void;
  onRunEngine: () => void;
  onRunTrading: () => void;
}) {
  const localModel = runtimeHealth?.agent_loop.local_model || "HF local";
  const openRouterModel = runtimeHealth?.agent_loop.openrouter_model || "OpenRouter";
  const latestReceipt =
    trading?.latest_receipt_id || runtimeHealth?.trading.latest_receipt_id || "لم يصدر بعد";
  const commandCount = commandCenter?.summary.ready_command_count ?? commandCenter?.commands.length ?? 0;
  const toolCount = commandCenter?.summary.tool_count ?? 0;
  const powershellCommands = [
    "powershell -ExecutionPolicy Bypass -File .\\scripts\\fathiya.ps1 -RunEngine",
    "powershell -ExecutionPolicy Bypass -File .\\scripts\\fathiya.ps1 -RunTrading",
    "powershell -ExecutionPolicy Bypass -File .\\scripts\\fathiya.ps1 -RunBugBounty",
  ];

  return (
    <Card className="mb-4 overflow-hidden border-border/70 bg-card/80">
      <CardContent className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
        <div className="min-w-0">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge
              className={
                localExecutionReady
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                  : "border-amber-500/30 bg-amber-500/10 text-amber-300"
              }
            >
              {localExecutionReady ? "فتحية حية" : "تحتاج فحص"}
            </Badge>
            <Badge variant="outline" className="font-mono text-[10px]">
              {workerOnline ? "worker online" : "worker offline"}
            </Badge>
            <Badge variant="outline" className="text-[10px]">
              {readyLaneLabel}
            </Badge>
          </div>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg font-bold">غرفة قيادة فتحية</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
                شغّل الوكلاء من هنا مباشرة: فهم المعرفة محليًا عبر Hugging Face، تخطيط وتقييم
                عبر OpenRouter، وتنفيذ داخلي عبر الأدوات والجسور المتاحة.
              </p>
            </div>
            <Button type="button" size="sm" variant="outline" onClick={onOpenTools}>
              <Settings2 />
              الأدوات
            </Button>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <Button type="button" onClick={onRunEngine} disabled={startingEngine}>
              {startingEngine ? <Loader2 className="animate-spin" /> : <Play />}
              تشغيل الوكلاء
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onRunTrading}
              disabled={startingTrading}
            >
              {startingTrading ? <Loader2 className="animate-spin" /> : <TrendingUp />}
              وكيل التداول
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={onRunBugBounty}
              disabled={startingBugBounty}
            >
              {startingBugBounty ? <Loader2 className="animate-spin" /> : <ShieldAlert />}
              صيد الثغرات
            </Button>
            <Button type="button" variant="outline" onClick={onOpenReports}>
              <FileCheck2 />
              التقارير
            </Button>
          </div>

          <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <InfoField label="النماذج" value={`${localModel} · ${openRouterModel}`} />
            <InfoField
              label="المعرفة"
              value={intakeRunning ? "تراقب الملفات الآن" : "متوقفة"}
            />
            <InfoField
              label="التداول"
              value={
                trading?.running
                  ? `${trading.symbol} · ${trading.cycle_target_seconds}s`
                  : "Paper جاهز"
              }
            />
            <InfoField label="آخر إيصال" value={latestReceipt} />
          </div>
        </div>

        <div className="min-w-0 rounded-md border border-border/60 bg-background/35 p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="text-xs font-semibold">تشغيل من PowerShell</p>
              <p className="mt-1 text-[10px] text-muted-foreground">
                افتح المشروع وشغّل أي أمر من هذه الأوامر.
              </p>
            </div>
            <Badge variant="outline" className="text-[10px]">
              {commandCount} أوامر جاهزة
            </Badge>
          </div>
          <div className="space-y-2">
            {powershellCommands.map((command) => (
              <code
                key={command}
                className="block break-all rounded-md border border-border/50 bg-muted/25 px-2 py-2 text-[10px]"
              >
                {command}
              </code>
            ))}
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <InfoField label="المهام" value={`${activeCount} نشطة / ${tasksCount}`} />
            <InfoField label="الأدوات" value={`${toolCount} أداة`} />
            <InfoField label="ترقيات" value={String(upgradeActionCount)} />
            <InfoField label="أقفال" value={String(blockingActionCount)} />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ExecutionDecisionPanel({
  decision,
  runningPrimary,
  onPrimary,
  onSecondary,
}: {
  decision: ExecutionDecision;
  runningPrimary: boolean;
  onPrimary: () => void;
  onSecondary?: () => void;
}) {
  const tone =
    decision.state === "fully_ready"
      ? "border-emerald-500/25 bg-emerald-500/[0.07]"
      : decision.state === "activation_required"
        ? "border-amber-500/25 bg-amber-500/[0.06]"
        : decision.state === "local_ready"
          ? "border-sky-500/25 bg-sky-500/[0.055]"
          : "border-red-500/25 bg-red-500/[0.045]";
  const badgeTone =
    decision.state === "fully_ready"
      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
      : decision.state === "activation_required"
        ? "border-amber-500/30 bg-amber-500/10 text-amber-300"
        : decision.state === "local_ready"
          ? "border-sky-500/30 bg-sky-500/10 text-sky-300"
          : "border-red-500/30 bg-red-500/10 text-red-300";
  return (
    <Card className={cn("mb-4 overflow-hidden", tone)}>
      <CardContent className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.75fr)]">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge className={badgeTone}>{decision.badge}</Badge>
            <span className="text-[10px] text-muted-foreground">حكم التشغيل الحالي</span>
          </div>
          <h2 className="text-base font-bold">{decision.title}</h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
            {decision.summary}
          </p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {decision.facts.map((fact) => (
              <Badge key={fact} variant="outline" className="max-w-full truncate text-[10px]">
                {fact}
              </Badge>
            ))}
          </div>
        </div>
        <div className="min-w-0 rounded-md border border-border/50 bg-background/35 p-3">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs font-semibold">الخطوة الصحيحة الآن</p>
            <Badge variant="outline" className="text-[10px]">
              {decision.blockers.length
                ? `${decision.blockers.length} ${decision.attentionLabel ?? "قفل"}`
                : "جاهز"}
            </Badge>
          </div>
          <div className="mb-3 space-y-1.5">
            {decision.blockers.length ? (
              decision.blockers.slice(0, 4).map((blocker) => (
                <div key={blocker} className="flex items-start gap-2 text-[10px] text-muted-foreground">
                  <CircleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />
                  <span className="min-w-0 break-words">{blocker}</span>
                </div>
              ))
            ) : (
              <div className="flex items-start gap-2 text-[10px] text-muted-foreground">
                <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-300" />
                <span>لا يوجد قفل محلي يمنع تنفيذ المهام الداخلية الآن.</span>
              </div>
            )}
          </div>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
            <Button type="button" onClick={onPrimary} disabled={runningPrimary}>
              {runningPrimary ? (
                <Loader2 className="animate-spin" />
              ) : decision.primaryAction === "activate" ? (
                <Settings2 />
              ) : decision.primaryAction === "refresh" ? (
                <RefreshCw />
              ) : (
                <Play />
              )}
              {decision.primaryLabel}
            </Button>
            {decision.secondaryAction && decision.secondaryLabel && onSecondary ? (
              <Button type="button" variant="outline" onClick={onSecondary}>
                {decision.secondaryAction === "activate" ? <Settings2 /> : <Play />}
                {decision.secondaryLabel}
              </Button>
            ) : null}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function AgentActivationQueue({
  className,
  integrations,
  readyCount,
  totalCount,
  probingIntegration,
  startingIntegrationTask,
  onOAuth,
  onSettings,
  onProbe,
  onTask,
}: {
  className?: string;
  integrations: AgentIntegrationReadiness[];
  readyCount: number;
  totalCount: number;
  probingIntegration: string | null;
  startingIntegrationTask: string | null;
  onOAuth: (integration: AgentIntegrationReadiness) => void;
  onSettings: (integration: AgentIntegrationReadiness) => void;
  onProbe: (integration: AgentIntegrationReadiness) => void;
  onTask: (integration: AgentIntegrationReadiness) => void;
}) {
  return (
    <div className={cn("rounded-md border border-border/60 bg-background/35 p-3", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold">طابور تفعيل الوكلاء</p>
          <p className="mt-1 text-[10px] text-muted-foreground">
            الجاهز يعمل الآن، والناقص يظهر مع خطوة التفعيل بدل التحميل الغامض.
          </p>
        </div>
        <Badge
          className={cn(
            readyCount === totalCount
              ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
              : "border-amber-500/30 bg-amber-500/10 text-amber-300",
          )}
        >
          {readyCount}/{totalCount || integrations.length} جاهزة
        </Badge>
      </div>

      <div className="mt-3 grid gap-2">
        {integrations.length ? (
          integrations.map((integration) => (
            <div
              key={integration.id}
              className={cn(
                "grid gap-2 rounded-md border p-3 sm:grid-cols-[minmax(0,1fr)_auto]",
                integration.status === "ready" &&
                  "border-emerald-500/20 bg-emerald-500/[0.035]",
                integration.status === "partial" &&
                  "border-amber-500/25 bg-amber-500/[0.04]",
                integration.status !== "ready" &&
                  integration.status !== "partial" &&
                  "border-orange-500/25 bg-orange-500/[0.035]",
              )}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-xs font-semibold">{integration.name}</p>
                  <IntegrationStatusBadge status={integration.status} />
                </div>
                <p className="mt-1 text-[10px] text-muted-foreground">
                  {activationSummary(integration)}
                </p>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-1.5">
                {integration.action_path && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 text-[10px]"
                    onClick={() => onOAuth(integration)}
                  >
                    <KeyRound />
                    {integration.action_label ?? "إعادة الربط"}
                  </Button>
                )}
                {integration.settings_path && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 text-[10px]"
                    onClick={() => onSettings(integration)}
                  >
                    <Settings2 />
                    {integration.settings_label ?? "الإعداد"}
                  </Button>
                )}
                {integration.probe_path && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-8 text-[10px]"
                    onClick={() => onProbe(integration)}
                    disabled={probingIntegration === integration.id}
                  >
                    {probingIntegration === integration.id ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <RefreshCw />
                    )}
                    {integration.probe_label ?? "اختبار"}
                  </Button>
                )}
                {integration.task_prompt && (
                  <Button
                    type="button"
                    size="sm"
                    className="h-8 text-[10px]"
                    onClick={() => onTask(integration)}
                    disabled={startingIntegrationTask === integration.id}
                  >
                    {startingIntegrationTask === integration.id ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <Play />
                    )}
                    {integration.task_label ?? "تشغيل"}
                  </Button>
                )}
              </div>
            </div>
          ))
        ) : (
          <p className="text-[10px] text-muted-foreground">
            لا توجد بوابات ظاهرة بعد. حدّث الصفحة أو شغّل فحص شبكة الوكلاء.
          </p>
        )}
      </div>
    </div>
  );
}

function buildActivationQueue(integrations: AgentIntegrationReadiness[]) {
  const attention = integrations
    .filter((integration) => integration.status !== "ready")
    .sort((a, b) => activationRank(a) - activationRank(b));
  if (attention.length) return attention.slice(0, 7);
  return integrations
    .filter((integration) =>
      [
        "local_execution_mesh",
        "huggingface_local",
        "openrouter",
        "n8n_local",
        "kali_wsl",
      ].includes(integration.id),
    )
    .slice(0, 5);
}

function buildExecutionDecision({
  workerOnline,
  meshSummary,
  integrationSummary,
  integrations,
  activationIntegrations,
  zapierDiagnostics,
  trading,
  intakeRunning,
  zapierAppCount,
  zapierActionCount,
}: {
  workerOnline: boolean;
  meshSummary: AgentMeshSummary | null;
  integrationSummary: AgentIntegrationSummary | null;
  integrations: AgentIntegrationReadiness[];
  activationIntegrations: AgentIntegrationReadiness[];
  zapierDiagnostics: AgentZapierDiagnostics | null;
  trading: AgentTradingStatus | null;
  intakeRunning: boolean;
  zapierAppCount: number;
  zapierActionCount: number;
}): ExecutionDecision {
  const total = integrationSummary?.total ?? integrations.length;
  const ready = integrationSummary?.ready ?? integrations.filter((item) => item.status === "ready").length;
  const toolCount = meshSummary?.summary.tool_count ?? null;
  const canRunLocal = Boolean(workerOnline && (meshSummary?.ready_to_execute ?? ready > 0));
  const activationOverview = meshSummary?.activation_overview;
  const blockingActions = activationOverview?.blocking_actions ?? [];
  const upgradeActions = activationOverview?.upgrade_actions ?? [];
  const readyLaneFact = activationOverview
    ? `${activationOverview.ready_lane_count}/${activationOverview.lane_count} مسارات تعمل`
    : `${ready}/${total || integrations.length} تكاملات جاهزة`;
  const incomplete = activationIntegrations.filter((item) => item.status !== "ready");
  const fallbackAttention = incomplete.map((item) => `${item.name}: ${activationSummary(item)}`);
  const blockingAttention = blockingActions.map(
    (item) => `${item.name}: ${item.summary || item.next_step || "يحتاج إجراء قبل التنفيذ."}`,
  );
  const upgradeAttention = upgradeActions.map(
    (item) => `${item.name}: ${item.summary || item.next_step || "ترقية اختيارية للتنفيذ الخارجي."}`,
  );
  const zapierState = zapierDiagnostics?.activation_state ?? "unknown";
  const facts = [
    workerOnline ? "Worker online" : "Worker offline",
    readyLaneFact,
    blockingActions.length ? `${blockingActions.length} قفل محلي` : "لا قفل محلي",
    upgradeActions.length ? `${upgradeActions.length} ترقيات اختيارية` : "الترقيات مكتملة أو غير مطلوبة",
    toolCount ? `${toolCount} أداة محلية` : "الأدوات قيد الفحص",
    `Zapier ${zapierAppCount || zapierDiagnostics?.app_count || 0}/${zapierActionCount || zapierDiagnostics?.action_count || 0}`,
    trading?.running ? `${trading.symbol} paper · ثانية` : "Paper trading ينتظر",
    intakeRunning ? "المعرفة تراقب" : "المعرفة تحتاج تشغيل",
  ];

  if (!workerOnline) {
    return {
      state: "offline",
      title: "المشغّل المحلي غير مثبت كمتصل الآن",
      summary:
        "لا أقدر أعتبر فتحية محركًا حيًا قبل رجوع العامل المحلي. أول حركة صحيحة هي تحديث الحالة أو تشغيل المشغّل، ثم إعادة فحص البوابات.",
      badge: "متوقف",
      primaryAction: "refresh",
      primaryLabel: "إعادة الفحص",
      facts,
      blockers: ["العامل المحلي غير متصل أو لم يرجع health بعد."],
      attentionLabel: "قفل",
    };
  }

  if (canRunLocal && blockingAttention.length) {
    return {
      state: "activation_required",
      title: "فتحية تحتاج إزالة قفل قبل التشغيل الكامل",
      summary:
        "العامل المحلي موجود، لكن توجد بوابة مصنفة كمانعة للتنفيذ. عالجها أولًا ثم شغّل المحرك.",
      badge: "قفل تشغيل",
      primaryAction: "activate",
      primaryLabel: "إزالة القفل",
      secondaryAction: "refresh",
      secondaryLabel: "إعادة الفحص",
      facts,
      blockers: blockingAttention,
      attentionLabel: "قفل",
    };
  }

  if (canRunLocal && (upgradeAttention.length || incomplete.length)) {
    const zapierNeedsReconnect =
      zapierDiagnostics?.needs_reconnect || zapierState === "reconnect_required";
    return {
      state: "local_ready",
      title: "فتحية تعمل الآن؛ الباقي ترقيات خارجية",
      summary: zapierNeedsReconnect
        ? "المحرك ينفذ المعرفة، النماذج، n8n، Kali، Codespaces، والتداول الورقي الآن. Zapier ظاهر كمخزون أدوات، وإعادة OAuth ترقية للتنفيذ الحي في Manus/Cursor/Gmail وغيرها."
        : "المحرك المحلي جاهز للتنفيذ الداخلي. قناة الإنتاج أو Testnet أو OAuth تظهر كترقيات واضحة ولا تمنع تشغيل الوكلاء المحليين.",
      badge: "جاهز محليًا",
      primaryAction: "run",
      primaryLabel: "شغّل الداخلي الآن",
      secondaryAction: "activate",
      secondaryLabel: "افتح الترقيات",
      facts,
      blockers: upgradeAttention.length ? upgradeAttention : fallbackAttention,
      attentionLabel: "ترقية",
    };
  }

  if (canRunLocal) {
    return {
      state: "fully_ready",
      title: "فتحية جاهزة للتشغيل من هذه الصفحة",
      summary:
        "المحرك المحلي متصل، المسارات الأساسية جاهزة، وتقدر تطلب هدفًا واحدًا ليختار النماذج والأدوات وينفذ الداخلي الجاهز ثم يسجل إيصالًا.",
      badge: "جاهز",
      primaryAction: "run",
      primaryLabel: "تشغيل المحرك",
      facts,
      blockers: [],
      attentionLabel: "ترقية",
    };
  }

  return {
    state: "local_ready",
    title: "فتحية تحتاج فحص شبكة قبل الحكم النهائي",
    summary:
      "العامل ظاهر، لكن ملخص شبكة الوكلاء غير كافٍ لإثبات الجاهزية. شغّل فحص المحرك ليحدد الأدوات الجاهزة وما يحتاج ربطًا.",
    badge: "فحص مطلوب",
    primaryAction: "run",
    primaryLabel: "فحص وتشغيل",
    facts,
    blockers: ["لا توجد نتيجة حديثة كافية من agent mesh summary."],
    attentionLabel: "قفل",
  };
}

function activationRank(integration: AgentIntegrationReadiness) {
  const priority: Record<string, number> = {
    zapier_mcp: 1,
    github_codespaces: 2,
    supabase: 3,
    broker_testnet: 4,
    local_execution_mesh: 5,
  };
  const statusRank: Record<AgentIntegrationStatus, number> = {
    partial: 1,
    needs_setup: 2,
    needs_operator: 3,
    ready: 4,
  };
  return (priority[integration.id] ?? 50) + statusRank[integration.status];
}

function activationSummary(integration: AgentIntegrationReadiness) {
  if (integration.status === "ready") return integration.summary || "جاهز للتنفيذ.";
  if (integration.id === "zapier_mcp") {
    return "Zapier عنده مخزون أدوات، لكن التشغيل الحي يحتاج OAuth جديد.";
  }
  if (integration.id === "github_codespaces") {
    return integration.next_step || "Codespaces يحتاج صلاحية GitHub CLI.";
  }
  if (integration.id === "supabase") {
    return "قناة الموقع الإنتاجية غير مربوطة؛ المشغّل المحلي يعمل على SQLite.";
  }
  if (integration.id === "broker_testnet") {
    return "التداول يعمل Paper، والتنفيذ التجريبي ينتظر مفاتيح Testnet.";
  }
  return integration.next_step || integration.summary || "يحتاج تفعيلًا قبل التنفيذ.";
}

function integrationStatusShort(integrations: AgentIntegrationReadiness[], id: string) {
  const status = integrations.find((item) => item.id === id)?.status;
  if (status === "ready") return "جاهز";
  if (status === "partial") return "جزئي";
  if (status === "needs_operator") return "ينتظر";
  return "تحقق";
}

function meshStatusLabel(status: string) {
  if (status === "ready") return "جاهز";
  if (status === "partial") return "جزئي";
  if (status === "needs_operator") return "ينتظر";
  if (status === "needs_setup") return "إعداد";
  return "تحقق";
}

function meshStatusBadgeClass(status: string) {
  if (status === "ready") {
    return "border-emerald-500/30 bg-emerald-500/10 text-emerald-300";
  }
  if (status === "needs_setup" || status === "needs_operator") {
    return "border-rose-500/30 bg-rose-500/10 text-rose-300";
  }
  return "border-amber-500/30 bg-amber-500/10 text-amber-300";
}

function credentialPolicyLabel(integration: AgentIntegrationReadiness) {
  if (!integration.account_required) return "لا يحتاج حسابًا";
  if (integration.credential_policy === "oauth_managed") return "OAuth آمن";
  if (integration.credential_policy === "local_server_only") return "مفتاح محلي فقط";
  return "لا توجد بيانات دخول";
}

function IntegrationProbeNotice({ probe }: { probe: AgentIntegrationProbeResult }) {
  return (
    <div
      className={cn(
        "mt-2 rounded-md border p-2 text-[10px]",
        probe.ok
          ? "border-emerald-500/20 bg-emerald-500/5 text-emerald-300"
          : "border-amber-500/20 bg-amber-500/5 text-amber-200",
      )}
    >
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="font-semibold">{probe.ok ? "اختبار ناجح" : "اختبار يحتاج إجراء"}</span>
        <span dir="ltr" className="font-mono text-[9px] opacity-75">
          {formatDate(probe.checked_at)}
        </span>
      </div>
      <p className="mt-1 break-words">{probe.summary}</p>
      <p dir="ltr" className="mt-1 break-all text-left font-mono text-[9px] opacity-70">
        {probe.action}
      </p>
      <TechnicalDetails label="تفاصيل اختبار الاتصال" value={probe.details} />
    </div>
  );
}

function integrationActionHref(path: string) {
  const returnTo =
    typeof window === "undefined" ? "http://127.0.0.1:5180/agent-tasks" : window.location.href;
  const separator = path.includes("?") ? "&" : "?";
  return `${localAgentRuntimeUrl}${path}${separator}return_to=${encodeURIComponent(returnTo)}`;
}

function CenteredState({
  icon: Icon,
  title,
  spin = false,
  children,
}: {
  icon: typeof Loader2;
  title: string;
  spin?: boolean;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4 text-foreground">
      <Card className="w-full max-w-sm border-border/60 bg-card/60 p-8 text-center">
        <Icon
          className={cn("mx-auto mb-3 h-7 w-7 text-muted-foreground", spin && "animate-spin")}
        />
        <p className="mb-5 text-sm font-semibold">{title}</p>
        {children}
      </Card>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border/50 bg-muted/20 p-3">
      <div className="mb-1 text-[10px] text-muted-foreground">{label}</div>
      <div className="break-all text-[11px]">{value}</div>
    </div>
  );
}

function MissionResultCard({
  mode,
  task,
  fallback,
  onOpen,
  onFallbackOpen,
  onRun,
  running = false,
}: {
  mode: MissionMode;
  task: AgentTask | null;
  fallback?: {
    status: string;
    summary: string;
    time: string;
    actionLabel: string;
  };
  onOpen: (taskId: string) => void;
  onFallbackOpen?: () => void;
  onRun: () => void;
  running?: boolean;
}) {
  const hasFallback = Boolean(fallback);
  const summary = task
    ? taskSummaryText(task)
    : fallback?.summary || "لا توجد نتيجة لهذا المسار بعد.";
  const time = task
    ? formatDate(task.completed_at || task.updated_at || task.created_at)
    : fallback?.time || "--";
  return (
    <div className="rounded-md border border-border/50 bg-background/35 p-3">
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-[11px] font-semibold">{MISSION_MODE_LABELS[mode]}</p>
          <p className="mt-0.5 truncate text-[9px] text-muted-foreground">
            {time}
          </p>
        </div>
        {task ? (
          <StatusBadge status={task.status} />
        ) : fallback ? (
          <Badge
            className={cn(
              "text-[9px]",
              fallback.status === "يعمل"
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "border-border bg-muted/30 text-muted-foreground",
            )}
          >
            {fallback.status}
          </Badge>
        ) : (
          <Badge variant="outline" className="text-[9px]">
            جديد
          </Badge>
        )}
      </div>
      <p className="line-clamp-3 min-h-[42px] text-[10px] leading-5 text-muted-foreground">
        {summary}
      </p>
      <div className="mt-2 grid grid-cols-2 gap-1.5">
        <Button
          type="button"
          size="sm"
          className="h-8 text-[10px]"
          disabled={running}
          onClick={onRun}
        >
          {running ? <Loader2 className="animate-spin" /> : <Play />}
          تشغيل
        </Button>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 text-[10px]"
          disabled={!task && !hasFallback}
          onClick={() => {
            if (task) {
              onOpen(task.id);
              return;
            }
            onFallbackOpen?.();
          }}
        >
          <FileCheck2 />
          {task ? "التقرير" : fallback?.actionLabel || "فتح"}
        </Button>
      </div>
    </div>
  );
}

function ReceiptEvidenceSummary({ evidence }: { evidence: unknown }) {
  const record = asRecord(evidence);
  if (!record) return null;

  const tools = Array.isArray(record.tools)
    ? record.tools.filter((tool): tool is string => typeof tool === "string")
    : [];
  const evaluation = asRecord(record.evaluation);
  const evaluationSummary =
    typeof evaluation?.summary === "string" ? evaluation.summary : "لم يُسجل ملخص تقييم.";
  const sourceCount = typeof record.source_count === "number" ? record.source_count : 0;
  const roundCount = typeof record.round_count === "number" ? record.round_count : 0;
  const terminationReason =
    typeof record.termination_reason === "string" ? record.termination_reason : null;
  const worker = typeof record.worker_id === "string" ? record.worker_id : "غير مسجل";

  return (
    <div className="mt-3 space-y-2 border-t border-emerald-500/15 pt-3">
      <div className="grid gap-2 text-[10px] sm:grid-cols-3">
        <InfoField label="المشغّل" value={worker} />
        <InfoField label="مصادر المعرفة" value={String(sourceCount)} />
        <InfoField label="جولات الوكيل" value={String(roundCount)} />
      </div>
      {tools.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tools.map((tool) => (
            <Badge key={tool} variant="outline" className="font-mono text-[9px] font-normal">
              {tool}
            </Badge>
          ))}
        </div>
      )}
      <p className="text-[10px] text-muted-foreground">{evaluationSummary}</p>
      {terminationReason && (
        <p className="text-[10px] text-muted-foreground">قرار الإنهاء: {terminationReason}</p>
      )}
    </div>
  );
}

function TaskResultSummary({
  value,
  startingFollowUpPrompt,
  onStartFollowUp,
}: {
  value: unknown;
  startingFollowUpPrompt: string | null;
  onStartFollowUp: (action: AgentMeshNextAction) => void;
}) {
  const result = asRecord(value);
  if (!result) {
    return <p className="text-xs text-muted-foreground">النتيجة غير قابلة للعرض المختصر.</p>;
  }

  const meshResult = extractAgentMeshRuntimeResult(result);
  const nextActions = extractAgentMeshNextActions(result);
  const synthesis = typeof result.synthesis === "string" ? result.synthesis : null;
  const evaluation = asRecord(result.evaluation);
  const evaluationPassed = typeof evaluation?.passed === "boolean" ? evaluation.passed : null;
  const evaluationSummary = typeof evaluation?.summary === "string" ? evaluation.summary : null;
  const sourceCount = Array.isArray(result.sources) ? result.sources.length : 0;
  const terminationReason =
    typeof result.termination_reason === "string" ? result.termination_reason : null;
  const agentRounds = Array.isArray(result.agent_rounds)
    ? result.agent_rounds.flatMap((item) => {
        const round = asRecord(item);
        if (!round) return [];
        const tools = Array.isArray(round.tools)
          ? round.tools.filter((tool): tool is string => typeof tool === "string")
          : [];
        return [
          {
            number: typeof round.round === "number" ? round.round : 0,
            reason: typeof round.reason === "string" ? round.reason : "",
            planner: typeof round.planner_mode === "string" ? round.planner_mode : "",
            tools,
          },
        ];
      })
    : [];
  const toolRows = Array.isArray(result.tool_results)
    ? result.tool_results.flatMap((item) => {
        const row = asRecord(item);
        const toolResult = asRecord(row?.result);
        const tool = typeof toolResult?.tool === "string" ? toolResult.tool : null;
        if (!tool) return [];
        return [
          {
            tool,
            description:
              typeof row?.description === "string" ? row.description : "اكتمل تنفيذ الأداة.",
          },
        ];
      })
    : [];

  return (
    <div className="space-y-3">
      {synthesis && <p className="whitespace-pre-wrap break-words text-xs">{synthesis}</p>}
      {meshResult && (
        <AgentMeshRuntimePanel
          value={meshResult}
          startingFollowUpPrompt={startingFollowUpPrompt}
          onStartFollowUp={onStartFollowUp}
        />
      )}
      {nextActions.length > 0 && (
        <div className="rounded-md border border-sky-500/20 bg-sky-500/5 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold">متابعات قابلة للتنفيذ</span>
            <Badge variant="outline" className="text-[9px] font-normal">
              {nextActions.length} أوامر
            </Badge>
          </div>
          <div className="space-y-2">
            {nextActions.map((action) => {
              const mode = followUpActionMode(action);
              const starting = mode === "task" && startingFollowUpPrompt === action.prompt;
              return (
                <div
                  key={`${action.id}-${action.prompt}`}
                  className="rounded-md border border-border/50 bg-background/35 p-2"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="break-words text-[11px] font-semibold">{action.title}</p>
                      <p className="mt-1 break-words text-[10px] text-muted-foreground">
                        {action.reason}
                      </p>
                      <p
                        dir="ltr"
                        className="mt-1 break-all text-left font-mono text-[9px] text-muted-foreground"
                      >
                        {action.prompt}
                      </p>
                    </div>
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="h-7 shrink-0 text-[10px]"
                      onClick={() => onStartFollowUp(action)}
                      disabled={starting}
                    >
                      {starting ? (
                        <Loader2 className="animate-spin" />
                      ) : mode === "settings" ? (
                        <Settings2 />
                      ) : mode === "oauth" ? (
                        <KeyRound />
                      ) : (
                        <Play />
                      )}
                      {followUpActionLabel(action)}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
      {(evaluationSummary || sourceCount > 0) && (
        <div className="flex flex-wrap items-center gap-2 text-[10px] text-muted-foreground">
          {evaluationPassed !== null && (
            <Badge
              className={cn(
                "font-normal",
                evaluationPassed
                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                  : "border-red-500/30 bg-red-500/10 text-red-400",
              )}
            >
              {evaluationPassed ? "اجتاز التقييم" : "لم يجتز التقييم"}
            </Badge>
          )}
          {sourceCount > 0 && <span>{sourceCount} مصادر معرفة</span>}
          {evaluationSummary && <span className="break-words">{evaluationSummary}</span>}
        </div>
      )}
      {agentRounds.length > 0 && (
        <div className="border-y border-border/50">
          <div className="flex items-center justify-between gap-3 py-2">
            <span className="text-[10px] font-semibold">جولات قرار وتنفيذ الوكيل</span>
            <Badge variant="outline" className="text-[9px] font-normal">
              {agentRounds.length} جولات
            </Badge>
          </div>
          <div className="divide-y divide-border/50">
            {agentRounds.map((round) => (
              <div key={`${round.number}-${round.planner}`} className="py-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border-sky-500/30 bg-sky-500/10 text-[9px] text-sky-300">
                    الجولة {round.number}
                  </Badge>
                  {round.planner && (
                    <span className="font-mono text-[9px] text-muted-foreground">
                      {round.planner}
                    </span>
                  )}
                </div>
                {round.reason && (
                  <p className="mt-1.5 break-words text-[10px] text-muted-foreground">
                    {round.reason}
                  </p>
                )}
                {round.tools.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {round.tools.map((tool) => (
                      <Badge
                        key={tool}
                        variant="outline"
                        className="font-mono text-[9px] font-normal"
                      >
                        {tool}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
          {terminationReason && (
            <p className="border-t border-border/50 py-2 text-[10px] text-muted-foreground">
              قرار الإنهاء: {terminationReason}
            </p>
          )}
        </div>
      )}
      {toolRows.length > 0 && (
        <div className="divide-y divide-border/50 border-y border-border/50">
          {toolRows.map((row, index) => (
            <div key={`${row.tool}-${index}`} className="flex items-start gap-3 py-2">
              <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
              <div className="min-w-0">
                <p className="break-all font-mono text-[10px] text-foreground">{row.tool}</p>
                <p className="mt-0.5 break-words text-[10px] text-muted-foreground">
                  {row.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CommandCenterLauncherPanel({
  commandCenter,
  startingCommandId,
  onRunCommand,
}: {
  commandCenter: AgentCommandCenter;
  startingCommandId: string | null;
  onRunCommand: (command: AgentCommandCenterCommand) => void;
}) {
  const commandRank = new Map([
    ["execute_mesh", 0],
    ["lane_trading", 1],
    ["lane_bug_bounty", 2],
    ["learn_and_execute", 3],
    ["activate_tools", 4],
    ["verify_github_zapier_read", 5],
  ]);
  const rankCommand = (command: AgentCommandCenterCommand) => {
    if (commandRank.has(command.id)) return commandRank.get(command.id) ?? 50;
    if (command.id.startsWith("agent_provider_")) return 10;
    if (command.id.startsWith("connected_app_")) return 12;
    if (command.id.startsWith("lane_")) return 30;
    return 50;
  };
  const rankedCommands = [...commandCenter.commands]
    .sort((left, right) => rankCommand(left) - rankCommand(right))
    .slice(0, 8);
  const groups = commandCenter.command_groups?.length
    ? commandCenter.command_groups.slice(0, 6)
    : [
        {
          id: "execution",
          label: "غرف التشغيل",
          ready_count: rankedCommands.length,
          command_count: rankedCommands.length,
          commands: rankedCommands,
        },
      ];
  return (
    <section className="mb-4 rounded-md border border-emerald-500/20 bg-emerald-500/[0.04] p-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-sm font-semibold">مركز أوامر فتحية</p>
            <Badge className="border-emerald-500/30 bg-emerald-500/10 text-[9px] text-emerald-300">
              {commandCenter.ready_to_execute ? "ينفذ محليًا" : "يفحص الجاهزية"}
            </Badge>
          </div>
          <p className="mt-1 line-clamp-2 text-[10px] text-muted-foreground">
            {commandCenter.headline || "أوامر تشغيل مباشرة من المشغّل المحلي."}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[10px]">
          <Badge variant="outline" className="font-normal">
            {commandCenter.summary.ready_command_count}/{commandCenter.summary.command_count} أوامر
          </Badge>
          <Badge variant="outline" className="font-normal">
            {commandCenter.summary.command_group_count ?? groups.length} غرف
          </Badge>
          <Badge variant="outline" className="font-normal">
            {commandCenter.summary.tool_count ?? "--"} أداة
          </Badge>
          <Badge variant="outline" className="font-normal">
            طابور {commandCenter.summary.operator_queue_count}
          </Badge>
        </div>
      </div>
      <div className="mt-3 grid gap-2 lg:grid-cols-3">
        {groups.map((group) => {
          const commands = group.commands.slice(0, 3);
          return (
            <div
              key={group.id}
              className="min-w-0 rounded-md border border-border/60 bg-background/35 p-2"
            >
              <div className="mb-2 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-[11px] font-semibold">
                    {group.label || group.id}
                  </p>
                  <p className="mt-1 line-clamp-2 text-[9px] text-muted-foreground">
                    {commandCenterGroupHint(group.id)}
                  </p>
                </div>
                <Badge
                  className={cn(
                    "shrink-0 text-[9px]",
                    group.ready_count > 0
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                  )}
                >
                  {group.ready_count}/{group.command_count}
                </Badge>
              </div>
              <div className="grid gap-1.5">
                {commands.length ? (
                  commands.map((command) => {
                    const running = startingCommandId === command.id;
                    const commandReady = command.status === "ready";
                    const primary =
                      commandReady &&
                      (command.id === "execute_mesh" || command.id === "lane_trading");
                    return (
                      <Button
                        key={command.id}
                        type="button"
                        variant={primary ? "default" : "outline"}
                        className={cn(
                          "h-auto min-h-10 justify-between gap-2 rounded-md px-2 py-1.5 text-right text-[10px]",
                          !primary && "bg-card/35",
                        )}
                        onClick={() => onRunCommand(command)}
                        disabled={running}
                      >
                        <span className="flex min-w-0 items-center gap-1.5">
                          <span className="min-w-0 truncate">
                            {command.title || command.label || command.id}
                          </span>
                          {!commandReady ? (
                            <span className="shrink-0 rounded border border-amber-500/30 px-1 py-0.5 text-[8px] text-amber-300">
                              تحضير
                            </span>
                          ) : null}
                        </span>
                        {running ? (
                          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                        ) : (
                          <Play className="h-3.5 w-3.5 shrink-0" />
                        )}
                      </Button>
                    );
                  })
                ) : (
                  <p className="text-[10px] text-muted-foreground">لا توجد أوامر جاهزة.</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 grid gap-1">
        {[commandCenter.powershell.run_agent_os, commandCenter.powershell.run_execute_mesh]
          .filter((command): command is string => Boolean(command))
          .map((command) => (
            <p
              key={command}
              dir="ltr"
              className="truncate font-mono text-[9px] text-muted-foreground"
            >
              {command}
            </p>
          ))}
      </div>
    </section>
  );
}

function commandCenterGroupHint(id: string) {
  const hints: Record<string, string> = {
    execution: "تشغيل شبكة الوكلاء المحلية وجمع الإيصال.",
    trading: "نبض التداول الورقي ومستشار OpenRouter.",
    bug_bounty: "صيد مصرح ينتج Draft داخلي.",
    knowledge: "استيعاب التقارير ثم تشغيل الأدوات المناسبة.",
    tools: "Zapier وn8n وKali والجسور الناقصة.",
    connected_apps: "تحضير Manus وCursor وGmail وGitHub عبر Zapier.",
  };
  return hints[id] ?? "أوامر مساعدة مرتبطة بالمحرك.";
}

function AgentMeshRuntimePanel({
  value,
  startingFollowUpPrompt = null,
  onStartFollowUp,
}: {
  value: Record<string, unknown>;
  startingFollowUpPrompt?: string | null;
  onStartFollowUp?: (action: AgentMeshNextAction) => void;
}) {
  const summary = asRecord(value.summary) ?? {};
  const probes = asRecord(value.integration_probes) ?? {};
  const activationPlan = asRecord(value.activation_plan);
  const executionCenter = asRecord(value.execution_command_center);
  const operatorStatus = asRecord(value.operator_status);
  const executionCenterSummary = asRecord(executionCenter?.summary);
  const operatorHeadline =
    typeof operatorStatus?.headline === "string" ? operatorStatus.headline : "";
  const operatorState = typeof operatorStatus?.state === "string" ? operatorStatus.state : "";
  const operatorNextStep =
    typeof operatorStatus?.next_step === "string" ? operatorStatus.next_step : "";
  const readyCommands = Array.isArray(executionCenter?.ready_commands)
    ? executionCenter.ready_commands.flatMap((item) => {
        const command = asRecord(item);
        const id = typeof command?.id === "string" ? command.id.trim() : "";
        const title = typeof command?.title === "string" ? command.title.trim() : "";
        const prompt = typeof command?.prompt === "string" ? command.prompt.trim() : "";
        const reason = typeof command?.reason === "string" ? command.reason.trim() : "";
        const uiAction = parseFollowUpUiAction(command?.ui_action);
        const lane = typeof command?.lane === "string" ? command.lane.trim() : "";
        const tool = typeof command?.tool === "string" ? command.tool.trim() : "";
        if (!id || !title || !prompt) return [];
        const action: AgentMeshNextAction = {
          id,
          title,
          prompt,
          reason: reason || "أمر جاهز من مركز تنفيذ فتحية.",
          ...(uiAction ? { ui_action: uiAction } : {}),
        };
        return [{ id, title, reason, lane, tool, action }];
      })
    : [];
  const operatorQueue = Array.isArray(executionCenter?.operator_queue)
    ? executionCenter.operator_queue.flatMap((item) => {
        const row = asRecord(item);
        const title = typeof row?.title === "string" ? row.title.trim() : "";
        const state = typeof row?.state === "string" ? row.state.trim() : "";
        const reason = typeof row?.reason === "string" ? row.reason.trim() : "";
        return title ? [{ title, state, reason }] : [];
      })
    : [];
  const activationEntries = Array.isArray(activationPlan?.entries)
    ? activationPlan.entries.flatMap((item) => {
        const entry = asRecord(item);
        if (!entry) return [];
        const action = asRecord(entry.next_action);
        const prompt = typeof action?.prompt === "string" ? action.prompt.trim() : "";
        const title = typeof action?.title === "string" ? action.title.trim() : "";
        const id = typeof action?.id === "string" ? action.id.trim() : "";
        const reason = typeof action?.reason === "string" ? action.reason.trim() : "";
        const uiAction = parseFollowUpUiAction(action?.ui_action);
        const settingsGroup =
          typeof action?.settings_group === "string" ? action.settings_group.trim() : "";
        const actionPath = typeof action?.action_path === "string" ? action.action_path.trim() : "";
        const actionLabel =
          typeof action?.action_label === "string" ? action.action_label.trim() : "";
        const nextAction =
          id && title && prompt
            ? {
                id,
                title,
                prompt,
                reason: reason || "تشغيل المتابعة عبر نفس مشغّل المهام والإيصالات.",
                ...(uiAction ? { ui_action: uiAction } : {}),
                ...(settingsGroup ? { settings_group: settingsGroup } : {}),
                ...(actionPath ? { action_path: actionPath } : {}),
                ...(actionLabel ? { action_label: actionLabel } : {}),
              }
            : null;
        return [
          {
            integrationId:
              typeof entry.integration_id === "string" ? entry.integration_id : "unknown",
            status: typeof entry.status === "string" ? entry.status : "unknown",
            state: typeof entry.state === "string" ? entry.state : "unknown",
            summary: typeof entry.summary === "string" ? entry.summary : "",
            actionTitle: typeof action?.title === "string" ? action.title : "",
            actionMode: typeof action?.ui_action === "string" ? action.ui_action : "",
            nextAction,
          },
        ];
      })
    : [];
  const safeExecutions = Array.isArray(value.safe_executions)
    ? value.safe_executions.flatMap((item) => {
        const row = asRecord(item);
        const tool = typeof row?.tool === "string" ? row.tool : "";
        return tool ? [tool] : [];
      })
    : [];
  const skippedCount = Array.isArray(value.skipped_high_risk)
    ? value.skipped_high_risk.length
    : 0;
  const probeRows = Object.entries(probes).flatMap(([id, raw]) => {
    const probe = asRecord(raw);
    if (!probe) return [];
    return [
      {
        id,
        ok: Boolean(probe.ok),
        status: typeof probe.status === "string" ? probe.status : "unknown",
        summary: typeof probe.summary === "string" ? probe.summary : "",
      },
    ];
  });

  return (
    <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-semibold">ملخص تشغيل المحرك</span>
        <Badge className="border-emerald-500/30 bg-emerald-500/10 text-[9px] text-emerald-300">
          {String(value.action ?? "agent_mesh_execute")}
        </Badge>
      </div>
      {operatorHeadline && (
        <div className="mb-3 rounded-md border border-emerald-500/20 bg-background/40 p-2">
          <div className="mb-1 flex flex-wrap items-center justify-between gap-2">
            <span className="text-[11px] font-semibold">حالة التنفيذ الفعلية</span>
            <Badge variant="outline" className="font-mono text-[9px] font-normal">
              {operatorState || "operator"}
            </Badge>
          </div>
          <p className="break-words text-[10px] leading-5 text-muted-foreground">
            {operatorHeadline}
          </p>
          {operatorNextStep && (
            <p className="mt-1 break-words text-[10px] leading-5 text-muted-foreground">
              {operatorNextStep}
            </p>
          )}
        </div>
      )}
      <div className="grid gap-2 text-[10px] sm:grid-cols-4">
        <InfoField label="خطوات منفذة" value={String(summary.safe_execution_count ?? "--")} />
        <InfoField label="فحوصات تكامل" value={String(summary.integration_probe_count ?? "--")} />
        <InfoField
          label="التداول الورقي"
          value={
            summary.paper_trading_running
              ? "يعمل"
              : summary.paper_trading_started
                ? "بدأ"
                : "لم يبدأ"
          }
        />
        <InfoField label="تخطيات مخاطر" value={String(skippedCount)} />
      </div>
      {executionCenter && (
        <div className="mt-3 rounded-md border border-sky-500/20 bg-sky-500/5 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold">مركز أوامر التنفيذ</span>
            <Badge variant="outline" className="text-[9px] font-normal">
              {String(executionCenterSummary?.ready_command_count ?? readyCommands.length)} أوامر ·{" "}
              {String(executionCenterSummary?.operator_queue_count ?? operatorQueue.length)} طابور
            </Badge>
          </div>
          {readyCommands.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {readyCommands.slice(0, 6).map((command) => (
                <div
                  key={command.id}
                  className="rounded-md border border-border/50 bg-background/35 p-2"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-[10px] font-semibold">{command.title}</span>
                    <Badge variant="outline" className="text-[9px] font-normal">
                      {command.lane || command.tool || "execution"}
                    </Badge>
                  </div>
                  {command.reason && (
                    <p className="mt-1 break-words text-[10px] text-muted-foreground">
                      {command.reason}
                    </p>
                  )}
                  {onStartFollowUp && (
                    <Button
                      type="button"
                      size="sm"
                      variant="outline"
                      className="mt-2 h-7 w-full justify-center text-[10px]"
                      onClick={() => onStartFollowUp(command.action)}
                      disabled={startingFollowUpPrompt === command.action.prompt}
                    >
                      {startingFollowUpPrompt === command.action.prompt ? (
                        <Loader2 className="animate-spin" />
                      ) : (
                        <Play />
                      )}
                      تشغيل الأمر
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
          {operatorQueue.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {operatorQueue.slice(0, 6).map((item, index) => (
                <Badge
                  key={`${item.title}-${index}`}
                  className="border-amber-500/30 bg-amber-500/10 text-[9px] font-normal text-amber-300"
                >
                  {item.state || "operator"} · {item.title}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}
      {activationEntries.length > 0 && (
        <div className="mt-3 rounded-md border border-violet-500/20 bg-violet-500/5 p-3">
          <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
            <span className="text-xs font-semibold">خطة تفعيل الوكلاء</span>
            <Badge variant="outline" className="text-[9px] font-normal">
              {String(activationPlan?.ready_count ?? "--")} جاهزة ·{" "}
              {String(activationPlan?.activation_required_count ?? "--")} تحتاج تفعيل
            </Badge>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            {activationEntries.map((entry) => (
              <div
                key={entry.integrationId}
                className="rounded-md border border-border/50 bg-background/35 p-2"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span dir="ltr" className="break-all text-left font-mono text-[10px]">
                    {entry.integrationId}
                  </span>
                  <Badge
                    className={cn(
                      "text-[9px] font-normal",
                      entry.state === "ready"
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                        : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                    )}
                  >
                    {entry.state === "ready" ? "جاهز" : "تفعيل"}
                  </Badge>
                </div>
                <p className="mt-1 break-words text-[10px] text-muted-foreground">
                  {entry.actionTitle || entry.summary || entry.status}
                </p>
                {entry.actionMode && (
                  <p className="mt-1 font-mono text-[9px] text-muted-foreground">
                    {entry.actionMode}
                  </p>
                )}
                {entry.nextAction && onStartFollowUp && (
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    className="mt-2 h-7 w-full justify-center text-[10px]"
                    onClick={() => onStartFollowUp(entry.nextAction)}
                    disabled={
                      followUpActionMode(entry.nextAction) === "task" &&
                      startingFollowUpPrompt === entry.nextAction.prompt
                    }
                  >
                    {followUpActionMode(entry.nextAction) === "settings" ? (
                      <Settings2 />
                    ) : followUpActionMode(entry.nextAction) === "oauth" ? (
                      <KeyRound />
                    ) : startingFollowUpPrompt === entry.nextAction.prompt ? (
                      <Loader2 className="animate-spin" />
                    ) : (
                      <Play />
                    )}
                    {followUpActionLabel(entry.nextAction)}
                  </Button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {probeRows.length > 0 && (
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {probeRows.map((probe) => (
            <div key={probe.id} className="rounded-md border border-border/50 bg-background/35 p-2">
              <div className="flex items-center justify-between gap-2">
                <span dir="ltr" className="break-all text-left font-mono text-[10px]">
                  {probe.id}
                </span>
                <Badge
                  className={cn(
                    "shrink-0 text-[9px] font-normal",
                    probe.ok
                      ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                      : "border-amber-500/30 bg-amber-500/10 text-amber-300",
                  )}
                >
                  {probe.status}
                </Badge>
              </div>
              {probe.summary && (
                <p className="mt-1 break-words text-[10px] text-muted-foreground">
                  {probe.summary}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
      {safeExecutions.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {safeExecutions.map((tool, index) => (
            <Badge
              key={`${tool}-${index}`}
              variant="outline"
              className="font-mono text-[9px] font-normal"
            >
              {tool}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function ExecutionCheckpointNotice({ value }: { value: unknown }) {
  const result = asRecord(value);
  const checkpoint = asRecord(result?.execution_checkpoint);
  if (!checkpoint) return null;

  const round = typeof checkpoint.round_number === "number" ? checkpoint.round_number : 1;
  const completedTools = Array.isArray(checkpoint.tool_results)
    ? checkpoint.tool_results.length
    : 0;
  const nextSteps = Array.isArray(checkpoint.next_steps) ? checkpoint.next_steps.length : 0;

  return (
    <Alert className="border-violet-500/30 bg-violet-500/5">
      <Clock3 className="text-violet-300" />
      <AlertTitle>نقطة استئناف محفوظة</AlertTitle>
      <AlertDescription>
        بعد الموافقة سيستأنف الوكيل الجولة {round} وينفذ {nextSteps} خطوات معلقة دون إعادة{" "}
        {completedTools} خطوات مكتملة.
      </AlertDescription>
    </Alert>
  );
}

function TechnicalDetails({ label, value }: { label: string; value: unknown }) {
  return (
    <details className="group mt-3">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 text-[10px] text-muted-foreground transition-colors hover:text-foreground">
        <ChevronDown className="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
        {label}
      </summary>
      <JsonBlock value={value} />
    </details>
  );
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function classifyMissionTask(task: AgentTask): MissionMode | null {
  const text = `${task.title}\n${task.prompt}`.toLowerCase();
  if (
    text.includes("fathiya_trading_agent_mission") ||
    task.title.includes("وكيل التداول")
  ) {
    return "trading";
  }
  if (
    text.includes("bug bounty") ||
    text.includes("hackerone") ||
    text.includes("bugcrowd") ||
    text.includes("صيد ثغرات") ||
    text.includes("صيد الثغرات")
  ) {
    return "bug-bounty";
  }
  if (
    text.includes("fathiya_knowledge_execution") ||
    text.includes("knowledge execution mission") ||
    text.includes("openrouter model strategy") ||
    text.includes("fusion") ||
    task.title.includes("استيعاب")
  ) {
    return "knowledge";
  }
  if (
    text.includes("fathiya_tool_orchestration") ||
    task.title.includes("أدوات") ||
    task.title.includes("Zapier")
  ) {
    return "tools";
  }
  if (
    text.includes("fathiya_execution_os") ||
    text.includes("agent mesh execute") ||
    task.title.includes("تشغيل محرك") ||
    task.title.includes("تشغيل فتحية")
  ) {
    return "execution";
  }
  return null;
}

function taskSummaryText(task: AgentTask): string {
  const result = asRecord(task.result);
  const synthesis = typeof result?.synthesis === "string" ? result.synthesis.trim() : "";
  const fallback = task.error_message || task.current_step || "لا يوجد ملخص بعد.";
  const text = synthesis || fallback;
  return text.length > 220 ? `${text.slice(0, 217)}...` : text;
}

function extractLiveExecutionProof(task: AgentTask): LiveExecutionProof | null {
  const result = asRecord(task.result);
  if (!result || task.status !== "completed") return null;
  const toolResults = Array.isArray(result.tool_results) ? result.tool_results : [];
  const tools: string[] = [];
  let hasLiveAction = false;
  for (const item of toolResults) {
    const row = asRecord(item);
    const toolResult = asRecord(row?.result);
    const tool = typeof toolResult?.tool === "string" ? toolResult.tool : null;
    if (!tool) continue;
    if (!tools.includes(tool)) tools.push(tool);
    if (tool === "zapier_action" && toolResult.executed === true) {
      hasLiveAction = true;
    }
    if (tool === "agent_mesh_execute") {
      hasLiveAction = true;
    }
  }
  if (!hasLiveAction) return null;
  const roundCount = Array.isArray(result.agent_rounds)
    ? result.agent_rounds.length
    : Math.max(1, tools.length);
  const summary =
    task.latest_receipt_summary ||
    (typeof result.synthesis === "string" ? result.synthesis : task.current_step || task.title);
  return {
    task,
    receiptId: task.latest_receipt_id ?? null,
    summary,
    tools: tools.length ? tools : ["agent"],
    roundCount,
    completedAt: task.completed_at || task.updated_at || task.created_at,
  };
}

function extractAgentMeshNextActions(result: Record<string, unknown>): AgentMeshNextAction[] {
  const toolResults = Array.isArray(result.tool_results) ? result.tool_results : [];
  const actions: AgentMeshNextAction[] = [];
  const seen = new Set<string>();
  for (const item of toolResults) {
    const row = asRecord(item);
    const toolResult = asRecord(row?.result);
    if (
      toolResult?.tool === "agent_provider_action_prepare" ||
      toolResult?.tool === "zapier_action_preflight"
    ) {
      const provider =
        typeof toolResult.provider === "string"
          ? toolResult.provider.trim()
          : typeof toolResult.app === "string"
            ? toolResult.app.trim()
            : "";
      const selectedAction = asRecord(toolResult.selected_action);
      const actionName =
        typeof selectedAction?.name === "string"
          ? selectedAction.name.trim()
          : typeof toolResult.action === "string"
            ? toolResult.action.trim()
            : "";
      const missingParams = Array.isArray(toolResult.missing_params)
        ? toolResult.missing_params
            .map((value) => (typeof value === "string" ? value.trim() : String(value || "").trim()))
            .filter(Boolean)
        : [];
      const missingReason = missingParams.length
        ? `أكمل الحقول المطلوبة: ${missingParams.join(", ")}`
        : "";
      const paramsReady = toolResult.params_ready === true;
      const oauthPath =
        typeof toolResult.oauth_action_path === "string"
          ? toolResult.oauth_action_path.trim()
          : "";
      if (paramsReady && toolResult.requires_oauth === true && oauthPath) {
        const key = `oauth:${oauthPath}`;
        if (!seen.has(key)) {
          seen.add(key);
          actions.push({
            id: `agent-provider-oauth-${provider || "zapier"}`,
            title: `ربط ${provider || "وكيل التطبيق"} عبر Zapier`,
            prompt: `agent provider oauth: ${provider || "Zapier"}`,
            reason:
              missingReason ||
              "تحضير الإجراء وجد أن OAuth مطلوب قبل تنفيذ أي إجراء خارجي.",
            ui_action: "oauth",
            action_path: oauthPath,
            action_label: "ربط Zapier OAuth",
          });
        }
      }

      const suggestedTask = asRecord(toolResult.suggested_task);
      const suggestedTitle =
        typeof suggestedTask?.title === "string" ? suggestedTask.title.trim() : "";
      const suggestedPrompt =
        typeof suggestedTask?.prompt === "string" ? suggestedTask.prompt.trim() : "";
      if (paramsReady && suggestedPrompt && !seen.has(suggestedPrompt)) {
        seen.add(suggestedPrompt);
        actions.push({
          id: `agent-provider-task-${provider || "zapier"}-${actionName || "action"}`,
          title:
            suggestedTitle ||
            `تشغيل ${provider || "وكيل التطبيق"}: ${actionName || "إجراء مقترح"}`,
          prompt: suggestedPrompt,
          reason:
            missingReason ||
            (typeof toolResult.next_step === "string"
              ? toolResult.next_step
              : "المشغّل حضّر إجراء Zapier الصحيح؛ شغّل المهمة المقترحة بعد التحقق من OAuth."),
          ui_action: "task",
        });
      }
      continue;
    }
    if (toolResult?.tool !== "agent_mesh_audit" && toolResult?.tool !== "agent_mesh_execute") {
      continue;
    }
    const executionCenter = asRecord(toolResult.execution_command_center);
    const centerActionSources = [
      ...(Array.isArray(executionCenter?.ready_commands) ? executionCenter.ready_commands : []),
      ...(Array.isArray(executionCenter?.operator_queue) ? executionCenter.operator_queue : []),
    ];
    for (const rawAction of centerActionSources) {
      const action = asRecord(rawAction);
      const id = typeof action?.id === "string" ? action.id.trim() : "";
      const title = typeof action?.title === "string" ? action.title.trim() : "";
      const prompt = typeof action?.prompt === "string" ? action.prompt.trim() : "";
      const reason = typeof action?.reason === "string" ? action.reason.trim() : "";
      const uiAction = parseFollowUpUiAction(action?.ui_action);
      const settingsGroup =
        typeof action?.settings_group === "string" ? action.settings_group.trim() : "";
      const integrationId =
        typeof action?.integration_id === "string" ? action.integration_id.trim() : "";
      const actionPath = typeof action?.action_path === "string" ? action.action_path.trim() : "";
      const actionLabel =
        typeof action?.action_label === "string" ? action.action_label.trim() : "";
      if (!id || !title || !prompt || seen.has(prompt)) continue;
      seen.add(prompt);
      actions.push({
        id,
        title,
        prompt,
        reason: reason || "أمر جاهز من مركز تنفيذ فتحية.",
        ...(uiAction ? { ui_action: uiAction } : {}),
        ...(settingsGroup ? { settings_group: settingsGroup } : {}),
        ...(integrationId ? { integration_id: integrationId } : {}),
        ...(actionPath ? { action_path: actionPath } : {}),
        ...(actionLabel ? { action_label: actionLabel } : {}),
      });
    }
    const rawActions = Array.isArray(toolResult.next_actions) ? toolResult.next_actions : [];
    for (const rawAction of rawActions) {
      const action = asRecord(rawAction);
      const id = typeof action?.id === "string" ? action.id.trim() : "";
      const title = typeof action?.title === "string" ? action.title.trim() : "";
      const prompt = typeof action?.prompt === "string" ? action.prompt.trim() : "";
      const reason = typeof action?.reason === "string" ? action.reason.trim() : "";
      const uiAction = parseFollowUpUiAction(action?.ui_action);
      const settingsGroup =
        typeof action?.settings_group === "string" ? action.settings_group.trim() : "";
      const integrationId =
        typeof action?.integration_id === "string" ? action.integration_id.trim() : "";
      const actionPath = typeof action?.action_path === "string" ? action.action_path.trim() : "";
      const actionLabel =
        typeof action?.action_label === "string" ? action.action_label.trim() : "";
      if (!id || !title || !prompt || seen.has(prompt)) continue;
      seen.add(prompt);
      actions.push({
        id,
        title,
        prompt,
        reason: reason || "تشغيل المتابعة عبر نفس مشغّل المهام والإيصالات.",
        ...(uiAction ? { ui_action: uiAction } : {}),
        ...(settingsGroup ? { settings_group: settingsGroup } : {}),
        ...(integrationId ? { integration_id: integrationId } : {}),
        ...(actionPath ? { action_path: actionPath } : {}),
        ...(actionLabel ? { action_label: actionLabel } : {}),
      });
    }
  }
  return actions.slice(0, 8);
}

function extractAgentMeshRuntimeResult(
  result: Record<string, unknown>,
): Record<string, unknown> | null {
  const toolResults = Array.isArray(result.tool_results) ? result.tool_results : [];
  for (const item of toolResults) {
    const row = asRecord(item);
    const toolResult = asRecord(row?.result);
    if (toolResult?.tool === "agent_mesh_execute" || toolResult?.tool === "agent_mesh_audit") {
      return toolResult;
    }
  }
  return null;
}

function parseFollowUpUiAction(value: unknown): AgentMeshNextAction["ui_action"] | undefined {
  return value === "settings" || value === "oauth" || value === "task" ? value : undefined;
}

function followUpActionMode(action: AgentMeshNextAction): "task" | "settings" | "oauth" {
  if (action.ui_action === "settings" && action.settings_group) return "settings";
  if (action.ui_action === "oauth" && action.action_path) return "oauth";
  return "task";
}

function followUpActionLabel(action: AgentMeshNextAction) {
  const mode = followUpActionMode(action);
  if (mode === "settings") return "فتح الإعداد";
  if (mode === "oauth") return action.action_label || "ربط OAuth";
  return "تشغيل المتابعة";
}

function buildZapierReadActions(inventory: AgentConnectedToolInventory | null): ZapierReadAction[] {
  if (!inventory?.agent_provider_actions) return [];
  return Object.entries(inventory.agent_provider_actions)
    .filter(([app]) => isVisibleAgentProviderApp(app))
    .flatMap(([app, actionSet]) =>
      (actionSet.read ?? []).map((action) => ({
        id: `${app}:${action}`,
        app,
        action,
      })),
    )
    .slice(0, 6);
}

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre
      dir="ltr"
      className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-all rounded-md border border-border/50 bg-background/50 p-3 text-left font-mono text-[10px]"
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function formatDate(value: string | null) {
  if (!value) return "--";
  return new Intl.DateTimeFormat("ar-SA", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

function riskLabel(value: AgentTask["risk_class"]) {
  const labels: Record<AgentTask["risk_class"], string> = {
    internal_owned: "داخلي مملوك",
    financial: "مالي",
    live_security: "فحص أمني حي",
    destructive: "حذف أو تدمير",
    external: "إجراء خارجي",
  };
  return labels[value];
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("ar-SA", {
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(value);
}

function formatPercent(value: number) {
  return new Intl.NumberFormat("ar-SA", {
    style: "percent",
    maximumFractionDigits: 1,
  }).format(value);
}

function formatSeconds(value: number | null) {
  if (value === null) return "--";
  return `${formatNumber(value)} ث`;
}

function cadenceLatestLabel(cadence: AgentTradingStatus["execution_cadence"]) {
  const latest = formatSeconds(cadence.latest_interval_seconds);
  if (cadence.within_target === null) return latest;
  return `${latest} · ${cadence.within_target ? "ضمن الهدف" : "متأخرة"}`;
}

function isFallbackMarket(source: string | null) {
  return Boolean(source?.includes(":fallback_for:"));
}

function marketSourceLabel(source: string | null) {
  if (!source) return "--";
  if (source === "coinbase_spot") return "Coinbase Spot";
  if (isFallbackMarket(source)) return "احتياطي آمن";
  if (source === "synthetic_second_market") return "محاكاة";
  return source;
}

function marketNotice(source: string | null) {
  if (!source) return "بانتظار أول نبضة سوق. التنفيذ الحقيقي يبقى مقفلاً.";
  if (isFallbackMarket(source)) {
    return "المصدر العام متعذر مؤقتًا؛ تستمر المراقبة الاحتياطية وتُحظر أي تعبئة Paper لهذه النبضة.";
  }
  if (source === "synthetic_second_market") {
    return "بيانات محاكاة للاختبار، والتنفيذ Paper فقط.";
  }
  return "بيانات سوق عامة مباشرة، والتنفيذ Paper فقط. التداول الحقيقي يبقى مقفلاً حتى ربط حساب تجريبي واعتماده.";
}

function advisoryLabel(advisory: AgentTradingStatus["strategy_advisory"]) {
  if (!advisory) return "--";
  const state = advisory.active ? "نشطة" : "منتهية";
  return `${advisory.action} · ${formatPercent(advisory.confidence)} · ${state}`;
}

function tradingActionLabel(action: AgentTradingCycle["prediction"]["action"]) {
  const labels: Record<AgentTradingCycle["prediction"]["action"], string> = {
    buy: "شراء",
    sell: "بيع",
    hold: "انتظار",
  };
  return labels[action];
}
