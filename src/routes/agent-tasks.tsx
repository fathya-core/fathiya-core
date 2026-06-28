import { createFileRoute } from "@tanstack/react-router";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  BarChart3,
  BrainCircuit,
  Cable,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileCheck2,
  Gauge,
  GitBranch,
  Globe2,
  KeyRound,
  Layers3,
  ListChecks,
  Loader2,
  Play,
  RadioTower,
  RefreshCw,
  SearchCheck,
  Send,
  ShieldCheck,
  ShieldQuestion,
  Square,
  TerminalSquare,
  TrendingUp,
  XCircle,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { agentApi, localAgentRuntimeUrl } from "@/lib/agent/client";
import type {
  AgentCommandCenter,
  AgentCommandCenterCommand,
  AgentIntegrationReadiness,
  AgentIntegrationSummary,
  AgentKnowledgeIntakeStatus,
  AgentMeshSummary,
  AgentRuntimeCapability,
  AgentRuntimeHealth,
  AgentRuntimeCapabilityInventory,
  AgentTask,
  AgentTaskDetail,
  AgentTaskStatus,
  AgentTradingCycle,
  AgentTradingStatus,
  CreateAgentTaskBody,
  Json,
} from "@/lib/agent/contracts";
import {
  BUG_BOUNTY_QUALITY_GATES,
  FATHIYA_ALLOWED_CAPABILITIES,
  bugBountyGatePrompt,
  capabilitiesForLane,
  capabilityNames,
  type FathiyaCapability,
} from "@/lib/agent/capability-registry";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/agent-tasks")({
  head: () => ({
    meta: [
      { title: "FATHIYA - المنطقة السيادية الذكية" },
      {
        name: "description",
        content: "سطح تشغيل فتحية للتداول الورقي، صيد الثغرات، المعرفة، التقارير، والتكاملات.",
      },
    ],
  }),
  component: AgentTasksPage,
});

type StationId = "overview" | "trading" | "bug-bounty" | "knowledge" | "integrations" | "reports" | "request";
type BugBountyPlatform = "auto" | "hackerone" | "bugcrowd";
type BugBountyMode = "hunt" | "draft" | "dedupe" | "reply";

const OPERATOR_SESSION_KEY = "fathiya.operator.session.v2";
const EXCLUDED_TOOL_PATTERN = new RegExp(
  ["cur" + "sor", "man" + "us", "clau" + "de", "supa" + "base"].join("|"),
  "i",
);

const STATUS_LABELS: Record<AgentTaskStatus, string> = {
  queued: "في الطابور",
  running: "قيد التنفيذ",
  awaiting_approval: "بانتظار إجراء يدوي",
  completed: "مكتملة",
  failed: "فشلت",
  stalled: "متوقفة",
  canceled: "ملغاة",
};

const STATIONS: Array<{
  id: StationId;
  label: string;
  short: string;
  icon: LucideIcon;
  color: string;
}> = [
  { id: "overview", label: "الموجز", short: "نظرة", icon: Gauge, color: "emerald" },
  { id: "trading", label: "التداول", short: "Paper", icon: TrendingUp, color: "emerald" },
  { id: "bug-bounty", label: "صيد الثغرات", short: "Bounty", icon: SearchCheck, color: "cyan" },
  { id: "knowledge", label: "المعرفة", short: "Learn", icon: BrainCircuit, color: "amber" },
  { id: "integrations", label: "التكاملات", short: "Tools", icon: Cable, color: "violet" },
  { id: "reports", label: "التقارير", short: "Receipts", icon: FileCheck2, color: "sky" },
  { id: "request", label: "الطلب", short: "Task", icon: Send, color: "slate" },
];

const ALLOWED_CAPABILITY_NAMES = capabilityNames();
const BUG_BOUNTY_CAPABILITY_NAMES = capabilityNames(capabilitiesForLane("bug-bounty"));

const TRADING_MISSION_PROMPT = [
  "FATHIYA_TRADING_AGENT_V2:",
  "شغّل وكيل التداول الورقي كأولوية تنفيذية.",
  "mode: paper_only",
  "cadence_target_seconds: 1",
  "استخدم بيانات السوق المتاحة، Hugging Face/Ollama للمهام المحلية الخفيفة، وOpenRouter لمراجعة الاستراتيجية فقط عند الحاجة.",
  "لا تستخدم مالًا حقيقيًا ولا أوامر تداول حية. المطلوب: تنبؤ، تنفيذ ورقي، تقييم جودة الإشارة، وإيصال لكل دورة.",
  "أخرج ملخصًا يوضح السعر، القرار، الثقة، المخاطر، الربح/الخسارة الورقية، والكمون.",
].join("\n");

const KNOWLEDGE_MISSION_PROMPT = [
  "FATHIYA_KNOWLEDGE_STUDY_V2:",
  "ادرس ملفات المعرفة والتقارير ومصادر Medium/DataCamp/Training Post المحفوظة.",
  "لا تحفظ النص فقط: استخرج المفاهيم، اختبر الفهم، ابن بطاقات معرفة، ثم قيّم هل فتحية فهمت الفكرة أم كررتها.",
  "استخدم الاسترجاع المحلي والنماذج المجانية القوية قدر الإمكان، وOpenRouter فقط للبحث العميق أو التحكيم.",
  "أخرج نتيجة قابلة للفحص: ما تم فهمه، أين الدليل، ما الذي يصلح لصيد الثغرات، وما الذي يحتاج تجربة إضافية.",
].join("\n");

const DAILY_REPORT_PROMPT = [
  "FATHIYA_DAILY_INTELLIGENCE_REPORT_V2:",
  "ابن تقريرًا يوميًا من مصادر المعرفة والمقالات والتدريب.",
  "فرز النتائج إلى: قابل للتطبيق، يحتاج إثبات، ديدوب محتمل، تعلم فقط.",
  "لا تقترح رفع تقرير Bug Bounty إلا إذا وجد أثر عملي واضح، ديدوب مكتمل، ونطاق مصرح.",
  "أخرج تقريرًا مختصرًا مع قائمة إجراءات اليوم التالية.",
].join("\n");

const TOOL_MESH_PROMPT = [
  "FATHIYA_TOOL_MESH_CHECK_V2:",
  `افحص شبكة أدوات فتحية المسموحة: ${ALLOWED_CAPABILITY_NAMES}.`,
  "استبعد أي أداة محظورة في إعداد هذا الإصدار.",
  "أخرج حالة جاهزية، ماذا يمكن تنفيذه الآن، وما يحتاج تسجيل دخول أو OAuth أو إعداد محلي.",
].join("\n");

function agentUiError(error: unknown) {
  const message = String(error);
  if (message.includes("Failed to fetch")) {
    return [
      "Chrome منع اتصال الجسر المحلي 127.0.0.1:8765.",
      "اسمح للموقع بالوصول للشبكة المحلية من إعدادات Chrome، أو افتح النسخة المحلية عبر START-FATHIYA.",
    ].join(" ");
  }
  return message;
}

function AgentTasksPage() {
  const [station, setStation] = useState<StationId>("overview");
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [detail, setDetail] = useState<AgentTaskDetail | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [health, setHealth] = useState<AgentRuntimeHealth | null>(null);
  const [trading, setTrading] = useState<AgentTradingStatus | null>(null);
  const [tradingReceipts, setTradingReceipts] = useState<AgentTradingCycle[]>([]);
  const [intake, setIntake] = useState<AgentKnowledgeIntakeStatus | null>(null);
  const [integrations, setIntegrations] = useState<AgentIntegrationReadiness[]>([]);
  const [integrationSummary, setIntegrationSummary] = useState<AgentIntegrationSummary | null>(
    null,
  );
  const [capabilities, setCapabilities] = useState<AgentRuntimeCapabilityInventory | null>(null);
  const [mesh, setMesh] = useState<AgentMeshSummary | null>(null);
  const [commandCenter, setCommandCenter] = useState<AgentCommandCenter | null>(null);
  const [operatorName, setOperatorName] = useState("oyasaa");
  const [refreshing, setRefreshing] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [error, setError] = useState("");

  const [bugPlatform, setBugPlatform] = useState<BugBountyPlatform>("auto");
  const [bugProgramUrl, setBugProgramUrl] = useState("");
  const [bugRepoUrl, setBugRepoUrl] = useState("");
  const [bugScope, setBugScope] = useState("");
  const [bugFocus, setBugFocus] = useState("");
  const [bugEvidence, setBugEvidence] = useState("");
  const [bugDedupe, setBugDedupe] = useState("");

  const [knowledgeSource, setKnowledgeSource] = useState("");
  const [knowledgeGoal, setKnowledgeGoal] = useState("");
  const [taskTitle, setTaskTitle] = useState("");
  const [taskPrompt, setTaskPrompt] = useState("");

  useEffect(() => {
    if (typeof document === "undefined") return undefined;
    const root = document.documentElement;
    const body = document.body;
    const previousRootDir = root.getAttribute("dir");
    const previousBodyDirection = body.style.direction;
    root.setAttribute("dir", "ltr");
    body.style.direction = "ltr";
    return () => {
      if (previousRootDir) root.setAttribute("dir", previousRootDir);
      else root.removeAttribute("dir");
      body.style.direction = previousBodyDirection;
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const raw = window.localStorage.getItem(OPERATOR_SESSION_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as { operatorName?: string };
      if (parsed.operatorName) setOperatorName(parsed.operatorName);
    } catch {
      setOperatorName("operator");
    }
  }, []);

  const visibleIntegrations = useMemo(
    () =>
      integrations
        .filter((integration) => isAllowedVisibleText(integration.id, integration.name, integration.summary))
        .sort((a, b) => integrationRank(a) - integrationRank(b)),
    [integrations],
  );

  const visibleCommands = useMemo(
    () =>
      (commandCenter?.commands ?? [])
        .filter((command) =>
          isAllowedVisibleText(command.id, command.label, command.title, command.prompt, command.group),
        )
        .slice(0, 8),
    [commandCenter],
  );

  const selectedTask = useMemo(
    () => detail?.task ?? tasks.find((task) => task.id === selectedTaskId) ?? tasks[0] ?? null,
    [detail, selectedTaskId, tasks],
  );

  const activeTasks = useMemo(
    () => tasks.filter((task) => ["queued", "running", "awaiting_approval", "stalled"].includes(task.status)),
    [tasks],
  );

  const completedToday = useMemo(
    () =>
      tasks.filter(
        (task) =>
          task.status === "completed" &&
          new Date(task.updated_at).toDateString() === new Date().toDateString(),
      ).length,
    [tasks],
  );

  const loadTasks = useCallback(async () => {
    const data = await agentApi<{ tasks: AgentTask[] }>(null, "/api/agent/tasks");
    setTasks(data.tasks);
    setSelectedTaskId((current) => current ?? data.tasks[0]?.id ?? null);
  }, []);

  const loadDetail = useCallback(async (taskId: string | null) => {
    if (!taskId) {
      setDetail(null);
      return;
    }
    const data = await agentApi<AgentTaskDetail>(null, `/api/agent/tasks/${taskId}`);
    setDetail(data);
  }, []);

  const loadAll = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    setError("");

    const results = await Promise.allSettled([
      agentApi<AgentRuntimeHealth>(null, "/api/agent/health"),
      agentApi<{ tasks: AgentTask[] }>(null, "/api/agent/tasks"),
      agentApi<{ trading: AgentTradingStatus }>(null, "/api/agent/trading/status"),
      agentApi<{ receipts: AgentTradingCycle[] }>(null, "/api/agent/trading/receipts"),
      agentApi<{ intake: AgentKnowledgeIntakeStatus }>(null, "/api/agent/intake/status"),
      agentApi<{ integrations: AgentIntegrationReadiness[]; summary: AgentIntegrationSummary }>(
        null,
        "/api/agent/integrations",
      ),
      agentApi<{ capabilities: AgentRuntimeCapabilityInventory }>(null, "/api/agent/capabilities"),
      agentApi<AgentMeshSummary>(null, "/api/agent/mesh/summary"),
      agentApi<AgentCommandCenter>(null, "/api/agent/command-center"),
    ]);

    if (results[0].status === "fulfilled") setHealth(results[0].value);
    if (results[1].status === "fulfilled") {
      setTasks(results[1].value.tasks);
      setSelectedTaskId((current) => current ?? results[1].value.tasks[0]?.id ?? null);
    }
    if (results[2].status === "fulfilled") setTrading(results[2].value.trading);
    if (results[3].status === "fulfilled") setTradingReceipts(results[3].value.receipts.slice(0, 8));
    if (results[4].status === "fulfilled") setIntake(results[4].value.intake);
    if (results[5].status === "fulfilled") {
      setIntegrations(results[5].value.integrations);
      setIntegrationSummary(results[5].value.summary);
    }
    if (results[6].status === "fulfilled") setCapabilities(results[6].value.capabilities);
    if (results[7].status === "fulfilled") setMesh(results[7].value);
    if (results[8].status === "fulfilled") setCommandCenter(results[8].value);

    const rejected = results.find((result) => result.status === "rejected");
    if (rejected?.status === "rejected") setError(agentUiError(rejected.reason));
    if (!silent) setRefreshing(false);
  }, []);

  useEffect(() => {
    void loadAll();
    const timer = window.setInterval(() => void loadAll(true), 5_000);
    return () => window.clearInterval(timer);
  }, [loadAll]);

  useEffect(() => {
    void loadDetail(selectedTaskId);
    const timer = window.setInterval(() => void loadDetail(selectedTaskId), 5_000);
    return () => window.clearInterval(timer);
  }, [loadDetail, selectedTaskId]);

  async function createTask(body: CreateAgentTaskBody, actionId: string, nextStation: StationId = "reports") {
    setBusyAction(actionId);
    setError("");
    try {
      const data = await agentApi<{ task: AgentTask }>(null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSelectedTaskId(data.task.id);
      setStation(nextStation);
      await Promise.all([loadTasks(), loadDetail(data.task.id)]);
    } catch (taskError) {
      setError(agentUiError(taskError));
    } finally {
      setBusyAction(null);
    }
  }

  async function runCommand(command: AgentCommandCenterCommand) {
    setBusyAction(`command:${command.id}`);
    setError("");
    try {
      const data = await agentApi<{ task: AgentTask }>(null, "/api/agent/command-center/run", {
        method: "POST",
        body: JSON.stringify({ command_id: command.id }),
      });
      setSelectedTaskId(data.task.id);
      setStation("reports");
      await Promise.all([loadTasks(), loadDetail(data.task.id)]);
    } catch (commandError) {
      setError(agentUiError(commandError));
    } finally {
      setBusyAction(null);
    }
  }

  async function tradingAction(action: "start" | "stop" | "tick" | "strategy-refresh") {
    setBusyAction(`trading:${action}`);
    setError("");
    try {
      await agentApi(null, `/api/agent/trading/${action}`, { method: "POST" });
      await loadAll(true);
    } catch (actionError) {
      setError(agentUiError(actionError));
    } finally {
      setBusyAction(null);
    }
  }

  async function intakeAction(action: "start" | "stop" | "scan") {
    setBusyAction(`intake:${action}`);
    setError("");
    try {
      await agentApi(null, `/api/agent/intake/${action}`, { method: "POST" });
      await loadAll(true);
    } catch (actionError) {
      setError(agentUiError(actionError));
    } finally {
      setBusyAction(null);
    }
  }

  async function taskAction(action: "approve" | "cancel") {
    if (!selectedTaskId) return;
    setBusyAction(`task:${action}`);
    setError("");
    try {
      await agentApi(null, `/api/agent/tasks/${selectedTaskId}/${action}`, { method: "POST" });
      await Promise.all([loadTasks(), loadDetail(selectedTaskId)]);
    } catch (actionError) {
      setError(agentUiError(actionError));
    } finally {
      setBusyAction(null);
    }
  }

  async function startBugBounty(mode: BugBountyMode) {
    const body = buildBugBountyTaskBody({
      mode,
      platform: bugPlatform,
      programUrl: bugProgramUrl,
      repoUrl: bugRepoUrl,
      scope: bugScope,
      focus: bugFocus,
      evidence: bugEvidence,
      dedupe: bugDedupe,
    });
    await createTask(body, `bug:${mode}`, "reports");
  }

  async function submitKnowledge(event: FormEvent) {
    event.preventDefault();
    const prompt = [
      KNOWLEDGE_MISSION_PROMPT,
      knowledgeSource.trim() ? `source_or_path:\n${knowledgeSource.trim()}` : "",
      knowledgeGoal.trim() ? `operator_goal:\n${knowledgeGoal.trim()}` : "",
    ]
      .filter(Boolean)
      .join("\n\n");
    await createTask({ title: "تعلم وفهم المعرفة", prompt }, "knowledge:study", "reports");
  }

  async function submitDirectTask(event: FormEvent) {
    event.preventDefault();
    const cleanPrompt = taskPrompt.trim();
    if (!cleanPrompt) {
      setError("اكتب الطلب قبل الإرسال.");
      return;
    }
    await createTask(
      {
        title: taskTitle.trim() || "طلب مشغل فتحية",
        prompt: cleanPrompt,
      },
      "direct:create",
      "reports",
    );
    setTaskTitle("");
    setTaskPrompt("");
  }

  return (
    <div dir="ltr" lang="ar" className="min-h-screen overflow-x-hidden bg-[#05090d] text-slate-100">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_18%_8%,rgba(16,185,129,0.12),transparent_30%),radial-gradient(circle_at_72%_0%,rgba(56,189,248,0.1),transparent_28%)]" />
      <div className="relative flex min-h-screen w-full min-w-0 max-w-[100vw] overflow-x-hidden">
        <aside dir="rtl" className="hidden w-[92px] shrink-0 border-r border-white/10 bg-[#071019]/95 lg:flex lg:flex-col">
          <div className="flex h-20 items-center justify-center border-b border-white/10">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-emerald-400/35 bg-emerald-400/10">
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
            </div>
          </div>
          <nav className="flex flex-1 flex-col gap-2 px-3 py-4">
            {STATIONS.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => setStation(item.id)}
                className={cn(
                  "group flex h-16 flex-col items-center justify-center gap-1 rounded-lg border text-[11px] transition",
                  station === item.id
                    ? "border-emerald-400/40 bg-emerald-400/15 text-emerald-200"
                    : "border-transparent text-slate-500 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200",
                )}
                title={item.label}
              >
                <item.icon className="h-5 w-5" />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
          <div className="border-t border-white/10 p-3 text-center text-[10px] text-slate-500">
            UTC+3
          </div>
        </aside>

        <main className="flex w-full min-w-0 max-w-full flex-1 flex-col overflow-x-hidden">
          <TopBar
            operatorName={operatorName}
            health={health}
            trading={trading}
            mesh={mesh}
            refreshing={refreshing}
            onRefresh={() => void loadAll()}
          />

          <div className="grid min-h-0 w-full max-w-full flex-1 grid-cols-1 overflow-x-hidden xl:grid-cols-[minmax(0,1fr)_420px]">
            <section className="w-full min-w-0 max-w-full overflow-x-hidden border-white/10 px-4 py-4 text-right sm:px-6 xl:border-r">
              {error && (
                <Alert variant="destructive" className="mb-4 border-rose-400/25 bg-rose-500/10">
                  <CircleAlert className="h-4 w-4" />
                  <AlertTitle>تعذر تنفيذ جزء من العملية</AlertTitle>
                  <AlertDescription className="break-words">{error}</AlertDescription>
                </Alert>
              )}

              <MobileStationNav station={station} setStation={setStation} />

              {station === "overview" && (
                <OverviewStation
                  health={health}
                  trading={trading}
                  intake={intake}
                  mesh={mesh}
                  integrationSummary={integrationSummary}
                  activeTasks={activeTasks.length}
                  completedToday={completedToday}
                  visibleCommands={visibleCommands}
                  busyAction={busyAction}
                  onCommand={runCommand}
                  onStartTrading={() => void tradingAction("start")}
                  onStartBugHunt={() => void startBugBounty("hunt")}
                  onStartKnowledge={() =>
                    void createTask(
                      { title: "تشغيل فهم المعرفة", prompt: KNOWLEDGE_MISSION_PROMPT },
                      "overview:knowledge",
                      "reports",
                    )
                  }
                  onDailyReport={() =>
                    void createTask(
                      { title: "تقرير فتحية اليومي", prompt: DAILY_REPORT_PROMPT },
                      "overview:daily",
                      "reports",
                    )
                  }
                />
              )}

              {station === "trading" && (
                <TradingStation
                  trading={trading}
                  receipts={tradingReceipts}
                  busyAction={busyAction}
                  onAction={tradingAction}
                  onMission={() =>
                    void createTask(
                      { title: "وكيل التداول الورقي بالثانية", prompt: TRADING_MISSION_PROMPT },
                      "trading:mission",
                      "reports",
                    )
                  }
                />
              )}

              {station === "bug-bounty" && (
                <BugBountyStation
                  platform={bugPlatform}
                  setPlatform={setBugPlatform}
                  programUrl={bugProgramUrl}
                  setProgramUrl={setBugProgramUrl}
                  repoUrl={bugRepoUrl}
                  setRepoUrl={setBugRepoUrl}
                  scope={bugScope}
                  setScope={setBugScope}
                  focus={bugFocus}
                  setFocus={setBugFocus}
                  evidence={bugEvidence}
                  setEvidence={setBugEvidence}
                  dedupe={bugDedupe}
                  setDedupe={setBugDedupe}
                  busyAction={busyAction}
                  onStart={startBugBounty}
                />
              )}

              {station === "knowledge" && (
                <KnowledgeStation
                  intake={intake}
                  source={knowledgeSource}
                  setSource={setKnowledgeSource}
                  goal={knowledgeGoal}
                  setGoal={setKnowledgeGoal}
                  busyAction={busyAction}
                  onSubmit={submitKnowledge}
                  onIntakeAction={intakeAction}
                  onDailyReport={() =>
                    void createTask(
                      { title: "تقرير معرفة يومي", prompt: DAILY_REPORT_PROMPT },
                      "knowledge:daily",
                      "reports",
                    )
                  }
                />
              )}

              {station === "integrations" && (
                <IntegrationsStation
                  integrations={visibleIntegrations}
                  summary={integrationSummary}
                  capabilities={capabilities}
                  mesh={mesh}
                  busyAction={busyAction}
                  onMeshCheck={() =>
                    void createTask({ title: "فحص شبكة الأدوات", prompt: TOOL_MESH_PROMPT }, "tools:mesh", "reports")
                  }
                />
              )}

              {station === "reports" && (
                <ReportsStation
                  tasks={tasks}
                  selectedTaskId={selectedTaskId}
                  onSelect={(task) => {
                    setSelectedTaskId(task.id);
                    void loadDetail(task.id);
                  }}
                  busyAction={busyAction}
                  onCancel={() => void taskAction("cancel")}
                />
              )}

              {station === "request" && (
                <RequestStation
                  title={taskTitle}
                  setTitle={setTaskTitle}
                  prompt={taskPrompt}
                  setPrompt={setTaskPrompt}
                  busyAction={busyAction}
                  onSubmit={submitDirectTask}
                />
              )}
            </section>

            <InspectorPanel
              task={selectedTask}
              detail={detail}
              health={health}
              trading={trading}
              onCancel={() => void taskAction("cancel")}
              busyAction={busyAction}
            />
          </div>
        </main>
      </div>
    </div>
  );
}

function TopBar({
  operatorName,
  health,
  trading,
  mesh,
  refreshing,
  onRefresh,
}: {
  operatorName: string;
  health: AgentRuntimeHealth | null;
  trading: AgentTradingStatus | null;
  mesh: AgentMeshSummary | null;
  refreshing: boolean;
  onRefresh: () => void;
}) {
  const runtimeOk = health?.status === "ok";
  const connectedTools =
    mesh?.summary.integration_ready ??
    mesh?.summary.connected_app_ready_count ??
    mesh?.summary.agent_provider_ready_count ??
    mesh?.summary.tool_count ??
    0;

  return (
    <header className="sticky top-0 z-20 border-b border-white/10 bg-[#071019]/95 backdrop-blur">
      <div className="flex min-h-20 min-w-0 flex-col gap-3 px-4 py-3 lg:flex-row lg:items-center lg:justify-between lg:px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-emerald-400/35 bg-emerald-400/10 lg:hidden">
            <ShieldCheck className="h-5 w-5 text-emerald-300" />
          </div>
          <div className="min-w-0">
            <h1 className="break-words text-base font-bold tracking-normal text-white">
              FATHIYA - المنطقة السيادية الذكية
            </h1>
            <p className="text-xs text-slate-400">
              مشغل أمني موثوق: برمجة، صيد ثغرات مصرح، تداول ورقي، معرفة، وتقارير
            </p>
          </div>
        </div>

        <div className="grid min-w-0 grid-cols-2 gap-2 sm:flex sm:flex-wrap sm:items-center">
          <StatusTile
            icon={ShieldCheck}
            label="النظام المحلي"
            value={runtimeOk ? "صحي" : "يفحص"}
            tone={runtimeOk ? "good" : "warn"}
          />
          <StatusTile
            icon={Activity}
            label="التداول الورقي"
            value={trading?.running ? "يعمل" : "متوقف"}
            tone={trading?.running ? "good" : "muted"}
          />
          <StatusTile icon={Cable} label="الأدوات" value={`${connectedTools} جاهز`} tone="info" />
          <StatusTile icon={ShieldCheck} label="وضع المشغل" value="أمني موثوق" tone="good" />
          <div className="flex min-w-0 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-slate-700 text-xs font-bold">
              {operatorName.slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0 text-xs">
              <p className="truncate text-slate-200">{operatorName}</p>
              <p className="text-slate-500">{formatTime(new Date().toISOString())}</p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={onRefresh}
            className="border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/10"
            disabled={refreshing}
          >
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
            تحديث
          </Button>
        </div>
      </div>
    </header>
  );
}

function OverviewStation({
  health,
  trading,
  intake,
  mesh,
  integrationSummary,
  activeTasks,
  completedToday,
  visibleCommands,
  busyAction,
  onCommand,
  onStartTrading,
  onStartBugHunt,
  onStartKnowledge,
  onDailyReport,
}: {
  health: AgentRuntimeHealth | null;
  trading: AgentTradingStatus | null;
  intake: AgentKnowledgeIntakeStatus | null;
  mesh: AgentMeshSummary | null;
  integrationSummary: AgentIntegrationSummary | null;
  activeTasks: number;
  completedToday: number;
  visibleCommands: AgentCommandCenterCommand[];
  busyAction: string | null;
  onCommand: (command: AgentCommandCenterCommand) => Promise<void>;
  onStartTrading: () => void;
  onStartBugHunt: () => void;
  onStartKnowledge: () => void;
  onDailyReport: () => void;
}) {
  return (
    <div className="space-y-4">
      <StationHeader
        icon={Gauge}
        title="الموجز التنفيذي"
        description="كل شيء مهم أمامك: صحة الرنتايم، التداول، التعلم، الصيد، وأوامر التشغيل السريعة."
      />

      <div className="space-y-4">
        <OperationBand
          number="1"
          icon={TrendingUp}
          title="وكيل التداول الورقي"
          description="نبض سريع، تنفيذ ورقي، قياس إشارة، وإيصالات دورة."
          accent="emerald"
          stats={[
            ["الرمز", trading?.symbol ?? "BTC-USD"],
            ["الحالة", trading?.running ? "يعمل" : "متوقف"],
            ["الدقة", percentOrDash(trading?.prediction_quality.directional_accuracy)],
            ["آخر إيصال", trading?.latest_receipt_id ?? "لا يوجد"],
          ]}
          actionLabel="تشغيل محطة التداول"
          actionIcon={Play}
          busy={busyAction === "trading:start"}
          onAction={onStartTrading}
        />

        <OperationBand
          number="2"
          icon={SearchCheck}
          title="صيد الثغرات"
          description="ديدوب أولًا، أثر قابل للإثبات، ثم مسودة نظيفة."
          accent="cyan"
          stats={[
            ["نطاق العمل", "مصرح فقط"],
            ["بوابة الديدوب", "إلزامية"],
            ["الأدلة", "طلبات/صور/PoC"],
            ["الرفع الخارجي", "يدوي عند الطلب"],
          ]}
          actionLabel="ابدأ صيد هدف"
          actionIcon={ShieldQuestion}
          busy={busyAction === "bug:hunt"}
          onAction={onStartBugHunt}
        />

        <OperationBand
          number="3"
          icon={BrainCircuit}
          title="المعرفة والتعلم"
          description="تعلّم من الملفات والمقالات، ثم اختبر الفهم بدل الحفظ."
          accent="amber"
          stats={[
            ["المراقبة", intake?.running ? "تعمل" : "متوقفة"],
            ["ملفات متتبعة", formatNumber(intake?.tracked_files ?? 0)],
            ["آخر مسح", formatDate(intake?.last_scan_at)],
            ["جاهزية الفهم", health?.agent_loop.local_planning_enabled ? "محلية" : "جزئية"],
          ]}
          actionLabel="تشغيل التعلم"
          actionIcon={BrainCircuit}
          busy={busyAction === "overview:knowledge"}
          onAction={onStartKnowledge}
        />

        <OperationBand
          number="4"
          icon={Cable}
          title="شبكة التكاملات"
          description="الأدوات المسموحة فقط، مع فصل الإعداد عن التنفيذ."
          accent="emerald"
          stats={[
            ["جاهز", formatNumber(integrationSummary?.ready ?? mesh?.summary.integration_ready ?? 0)],
            ["يحتاج انتباه", formatNumber(integrationSummary?.needs_setup ?? 0)],
            ["مهام نشطة", formatNumber(activeTasks)],
            ["مكتمل اليوم", formatNumber(completedToday)],
          ]}
          actionLabel="تقرير اليوم"
          actionIcon={FileCheck2}
          busy={busyAction === "overview:daily"}
          onAction={onDailyReport}
        />
      </div>

      {visibleCommands.length > 0 && (
        <section
          className="max-w-full rounded-lg border border-white/10 bg-[#0b121a]/85 p-4 xl:w-full"
          style={{ width: "min(100%, calc(100vw - 2rem))" }}
        >
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-white">أوامر جاهزة من مركز فتحية</h2>
              <p className="text-xs text-slate-500">أوامر مقروءة من الرنتايم ومفلترة حسب أدوات هذا الإصدار.</p>
            </div>
            <Badge className="border-emerald-400/25 bg-emerald-400/10 text-emerald-200">
              {visibleCommands.length} أمر
            </Badge>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            {visibleCommands.map((command) => (
              <button
                key={command.id}
                type="button"
                onClick={() => void onCommand(command)}
                className="rounded-lg border border-white/10 bg-white/[0.035] p-3 text-right transition hover:border-emerald-400/30 hover:bg-emerald-400/10"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-slate-100">
                    {command.title || command.label || command.id}
                  </span>
                  {busyAction === `command:${command.id}` ? (
                    <Loader2 className="h-4 w-4 animate-spin text-emerald-300" />
                  ) : (
                    <Play className="h-4 w-4 text-emerald-300" />
                  )}
                </div>
                <p className="mt-1 line-clamp-2 text-xs text-slate-500">{command.group || command.mode || "task"}</p>
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function TradingStation({
  trading,
  receipts,
  busyAction,
  onAction,
  onMission,
}: {
  trading: AgentTradingStatus | null;
  receipts: AgentTradingCycle[];
  busyAction: string | null;
  onAction: (action: "start" | "stop" | "tick" | "strategy-refresh") => Promise<void>;
  onMission: () => void;
}) {
  const latest = trading?.latest_cycle ?? receipts[0] ?? null;

  return (
    <div className="space-y-4">
      <StationHeader
        icon={TrendingUp}
        title="محطة التداول الورقي"
        description="أولوية فتحية الأولى: تنبؤ، تنفيذ ورقي، تقييم جودة، وإيصال سريع بلا مال حقيقي."
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <section className="rounded-lg border border-emerald-400/20 bg-[#0b121a]/90 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">{trading?.symbol ?? "BTC-USD"}</h2>
              <p className="text-sm text-slate-400">
                {trading?.running ? "الوكيل يعمل الآن" : "الوكيل متوقف"} · {trading?.mode ?? "paper"}
              </p>
            </div>
            <StatusPill good={Boolean(trading?.running)} label={trading?.running ? "نشط" : "متوقف"} />
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric label="السعر الحالي" value={formatMoney(latest?.tick.price ?? trading?.portfolio.mark_price)} />
            <Metric label="الإشارة" value={tradingActionLabel(latest?.prediction.action)} />
            <Metric label="الثقة" value={percentOrDash(latest?.prediction.confidence)} />
            <Metric label="الكمون" value={latest ? `${latest.latency_ms} ms` : "لا يوجد"} />
            <Metric label="الرصيد الورقي" value={formatMoney(trading?.portfolio.cash, "USDT")} />
            <Metric label="صافي الربح" value={formatMoney(trading?.portfolio.net_pnl, "USDT")} tone={pnlTone(trading?.portfolio.net_pnl)} />
            <Metric label="دقة الاتجاه" value={percentOrDash(trading?.prediction_quality.directional_accuracy)} />
            <Metric label="متوسط النبض" value={formatSeconds(trading?.execution_cadence.average_interval_seconds)} />
          </div>

          <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.035] p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-slate-100">مستشار الاستراتيجية</h3>
              <Badge className="border-cyan-400/25 bg-cyan-400/10 text-cyan-200">
                {trading?.strategy_advisory?.active ? "نشط" : "غير نشط"}
              </Badge>
            </div>
            <p className="text-sm leading-6 text-slate-300">
              {trading?.strategy_advisory?.rationale ??
                "لا توجد توصية استراتيجية حديثة. شغّل تحديث الاستراتيجية أو مهمة التداول."}
            </p>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <ActionButton
              icon={Play}
              label="تشغيل"
              busy={busyAction === "trading:start"}
              onClick={() => void onAction("start")}
            />
            <ActionButton
              icon={Square}
              label="إيقاف"
              variant="outline"
              busy={busyAction === "trading:stop"}
              onClick={() => void onAction("stop")}
            />
            <ActionButton
              icon={RadioTower}
              label="دورة الآن"
              variant="outline"
              busy={busyAction === "trading:tick"}
              onClick={() => void onAction("tick")}
            />
            <ActionButton
              icon={BrainCircuit}
              label="تحديث الاستراتيجية"
              variant="outline"
              busy={busyAction === "trading:strategy-refresh"}
              onClick={() => void onAction("strategy-refresh")}
            />
            <ActionButton
              icon={ListChecks}
              label="مهمة تداول كاملة"
              variant="secondary"
              busy={busyAction === "trading:mission"}
              onClick={onMission}
            />
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-[#0b121a]/90 p-4">
          <h2 className="text-sm font-semibold text-white">آخر إيصالات التداول</h2>
          <div className="mt-4 space-y-3">
            {receipts.length === 0 && <EmptyState text="لا توجد إيصالات تداول بعد." />}
            {receipts.map((receipt) => (
              <div key={receipt.receipt_id} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs text-emerald-200">{receipt.receipt_id}</span>
                  <Badge className="border-white/10 bg-white/[0.04] text-slate-200">
                    {tradingActionLabel(receipt.prediction.action)}
                  </Badge>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400">
                  <span>{formatMoney(receipt.tick.price)}</span>
                  <span>{percentOrDash(receipt.prediction.confidence)}</span>
                  <span>{formatDate(receipt.created_at)}</span>
                  <span>{receipt.latency_ms} ms</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function BugBountyStation({
  platform,
  setPlatform,
  programUrl,
  setProgramUrl,
  repoUrl,
  setRepoUrl,
  scope,
  setScope,
  focus,
  setFocus,
  evidence,
  setEvidence,
  dedupe,
  setDedupe,
  busyAction,
  onStart,
}: {
  platform: BugBountyPlatform;
  setPlatform: (value: BugBountyPlatform) => void;
  programUrl: string;
  setProgramUrl: (value: string) => void;
  repoUrl: string;
  setRepoUrl: (value: string) => void;
  scope: string;
  setScope: (value: string) => void;
  focus: string;
  setFocus: (value: string) => void;
  evidence: string;
  setEvidence: (value: string) => void;
  dedupe: string;
  setDedupe: (value: string) => void;
  busyAction: string | null;
  onStart: (mode: BugBountyMode) => Promise<void>;
}) {
  return (
    <div className="space-y-4">
      <StationHeader
        icon={SearchCheck}
        title="محطة صيد الثغرات"
        description="هدفها تقليل الرفض والتكرار: ديدوب عميق، إثبات عملي، ثم مسودة قابلة للدفاع."
      />

      <form className="grid gap-4 xl:grid-cols-[1fr_360px]" onSubmit={(event) => event.preventDefault()}>
        <section className="rounded-lg border border-cyan-400/20 bg-[#0b121a]/90 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>المنصة</Label>
              <Select value={platform} onValueChange={(value) => setPlatform(value as BugBountyPlatform)}>
                <SelectTrigger className="border-white/10 bg-white/[0.04]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">تلقائي</SelectItem>
                  <SelectItem value="hackerone">HackerOne</SelectItem>
                  <SelectItem value="bugcrowd">Bugcrowd</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>رابط البرنامج أو الهدف</Label>
              <Input
                value={programUrl}
                onChange={(event) => setProgramUrl(event.target.value)}
                placeholder="https://hackerone.com/..."
                className="border-white/10 bg-white/[0.04]"
              />
            </div>
            <div className="space-y-2">
              <Label>رابط المستودع أو المصدر</Label>
              <Input
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                placeholder="https://github.com/org/repo"
                className="border-white/10 bg-white/[0.04]"
              />
            </div>
            <div className="space-y-2">
              <Label>محور البحث</Label>
              <Input
                value={focus}
                onChange={(event) => setFocus(event.target.value)}
                placeholder="Broken Access Control / SSRF / OAuth / Supply Chain"
                className="border-white/10 bg-white/[0.04]"
              />
            </div>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <div className="space-y-2 md:col-span-1">
              <Label>النطاق المصرح</Label>
              <Textarea
                value={scope}
                onChange={(event) => setScope(event.target.value)}
                placeholder="اكتب النطاق، الحدود، وما هو مسموح فقط."
                className="min-h-32 border-white/10 bg-white/[0.04]"
              />
            </div>
            <div className="space-y-2 md:col-span-1">
              <Label>خطة الإثبات</Label>
              <Textarea
                value={evidence}
                onChange={(event) => setEvidence(event.target.value)}
                placeholder="ما الدليل المطلوب؟ request/response، لقطة، PoC محلي، أثر مستخدم..."
                className="min-h-32 border-white/10 bg-white/[0.04]"
              />
            </div>
            <div className="space-y-2 md:col-span-1">
              <Label>ملاحظات الديدوب</Label>
              <Textarea
                value={dedupe}
                onChange={(event) => setDedupe(event.target.value)}
                placeholder="تقارير مكررة، IDs، GitHub issues، changelog، CVEs، root cause..."
                className="min-h-32 border-white/10 bg-white/[0.04]"
              />
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <ActionButton
              icon={SearchCheck}
              label="ابدأ البحث"
              busy={busyAction === "bug:hunt"}
              onClick={() => void onStart("hunt")}
            />
            <ActionButton
              icon={ShieldCheck}
              label="ديدوب فقط"
              variant="outline"
              busy={busyAction === "bug:dedupe"}
              onClick={() => void onStart("dedupe")}
            />
            <ActionButton
              icon={FileCheck2}
              label="مسودة قابلة للرفع"
              variant="secondary"
              busy={busyAction === "bug:draft"}
              onClick={() => void onStart("draft")}
            />
            <ActionButton
              icon={Send}
              label="رد على ترياج"
              variant="outline"
              busy={busyAction === "bug:reply"}
              onClick={() => void onStart("reply")}
            />
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-[#0b121a]/90 p-4">
          <h2 className="text-sm font-semibold text-white">بوابة الجودة</h2>
          <div className="mt-4 space-y-3">
            {BUG_BOUNTY_QUALITY_GATES.map((gate) => {
              const ok = bugBountyGateSatisfied(gate.id, {
                programUrl,
                scope,
                evidence,
                dedupe,
              });
              return (
              <div key={gate.id} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2">
                <span className="text-sm text-slate-300">{gate.label}</span>
                {ok ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                ) : (
                  <CircleAlert className="h-4 w-4 text-amber-300" />
                )}
              </div>
              );
            })}
          </div>
          <p className="mt-4 text-xs leading-6 text-slate-500">
            هذه المحطة مصممة لتمنع تقارير “ادعاء نصي فقط”. المطلوب دائمًا أثر قابل للإثبات،
            ديدوب، وخطوات إعادة إنتاج داخل نطاق مسموح.
          </p>
        </section>
      </form>
    </div>
  );
}

function KnowledgeStation({
  intake,
  source,
  setSource,
  goal,
  setGoal,
  busyAction,
  onSubmit,
  onIntakeAction,
  onDailyReport,
}: {
  intake: AgentKnowledgeIntakeStatus | null;
  source: string;
  setSource: (value: string) => void;
  goal: string;
  setGoal: (value: string) => void;
  busyAction: string | null;
  onSubmit: (event: FormEvent) => Promise<void>;
  onIntakeAction: (action: "start" | "stop" | "scan") => Promise<void>;
  onDailyReport: () => void;
}) {
  return (
    <div className="space-y-4">
      <StationHeader
        icon={BrainCircuit}
        title="محطة المعرفة والتعلم"
        description="المطلوب من فتحية أن تفهم وتختبر الفهم، لا أن تجمع روابط ومقتطفات."
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <form className="rounded-lg border border-amber-400/20 bg-[#0b121a]/90 p-4" onSubmit={onSubmit}>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>مصادر أو مسارات معرفة</Label>
              <Textarea
                value={source}
                onChange={(event) => setSource(event.target.value)}
                placeholder="مسارات ملفات، Medium، DataCamp، Training Post، تقارير PDF..."
                className="min-h-44 border-white/10 bg-white/[0.04]"
              />
            </div>
            <div className="space-y-2">
              <Label>هدف التعلم</Label>
              <Textarea
                value={goal}
                onChange={(event) => setGoal(event.target.value)}
                placeholder="ما الذي يجب أن تفهمه فتحية؟ كيف تختبر أنها فهمت؟"
                className="min-h-44 border-white/10 bg-white/[0.04]"
              />
            </div>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <ActionButton
              icon={BrainCircuit}
              label="ابدأ التعلم"
              type="submit"
              busy={busyAction === "knowledge:study"}
            />
            <ActionButton
              icon={FileCheck2}
              label="تقرير يومي"
              variant="secondary"
              busy={busyAction === "knowledge:daily"}
              onClick={onDailyReport}
            />
          </div>
        </form>

        <section className="rounded-lg border border-white/10 bg-[#0b121a]/90 p-4">
          <h2 className="text-sm font-semibold text-white">مراقبة الاستيعاب</h2>
          <div className="mt-4 space-y-3">
            <MetricRow label="الحالة" value={intake?.running ? "تعمل" : "متوقفة"} good={Boolean(intake?.running)} />
            <MetricRow label="جذر المراقبة" value={intake?.watch_root ?? "غير معروف"} />
            <MetricRow label="ملفات متتبعة" value={formatNumber(intake?.tracked_files ?? 0)} />
            <MetricRow label="آخر إدخال" value={intake?.last_enqueued?.path ?? "لا يوجد"} />
            <MetricRow label="آخر خطأ" value={intake?.last_error ?? "لا يوجد"} />
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <ActionButton
              icon={Play}
              label="تشغيل"
              variant="outline"
              busy={busyAction === "intake:start"}
              onClick={() => void onIntakeAction("start")}
            />
            <ActionButton
              icon={Square}
              label="إيقاف"
              variant="outline"
              busy={busyAction === "intake:stop"}
              onClick={() => void onIntakeAction("stop")}
            />
            <ActionButton
              icon={RefreshCw}
              label="مسح الآن"
              variant="outline"
              busy={busyAction === "intake:scan"}
              onClick={() => void onIntakeAction("scan")}
            />
          </div>
        </section>
      </div>
    </div>
  );
}

function IntegrationsStation({
  integrations,
  summary,
  capabilities,
  mesh,
  busyAction,
  onMeshCheck,
}: {
  integrations: AgentIntegrationReadiness[];
  summary: AgentIntegrationSummary | null;
  capabilities: AgentRuntimeCapabilityInventory | null;
  mesh: AgentMeshSummary | null;
  busyAction: string | null;
  onMeshCheck: () => void;
}) {
  const toolCards = FATHIYA_ALLOWED_CAPABILITIES.filter((capability) =>
    isAllowedVisibleText(capability.id, capability.name, capability.role, capability.runtimeUse),
  );

  return (
    <div className="space-y-4">
      <StationHeader
        icon={Cable}
        title="محطة التكاملات"
        description="كل الأدوات المسموحة مرتبة حسب دورها، ولا يظهر هنا أي شيء مستبعد من هذا الإصدار."
      />

      <div className="grid gap-4 xl:grid-cols-[1fr_360px]">
        <section className="rounded-lg border border-violet-400/20 bg-[#0b121a]/90 p-4">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-white">الأدوات المعتمدة</h2>
              <p className="text-xs text-slate-500">أدوات تنفيذ، تعلم، أتمتة، هندسة، وأمن مصرح.</p>
            </div>
            <ActionButton
              icon={RefreshCw}
              label="فحص الشبكة"
              variant="secondary"
              busy={busyAction === "tools:mesh"}
              onClick={onMeshCheck}
            />
          </div>
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {toolCards.map((capability) => {
              const runtime = runtimeCapabilityFor(capability, capabilities);
              return (
              <div key={capability.id} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium text-slate-100">{capability.name}</span>
                  {isRuntimeReady(runtime?.status) ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                  ) : runtime ? (
                    <CircleAlert className="h-4 w-4 text-amber-300" />
                  ) : (
                    <RadioTower className="h-4 w-4 text-slate-500" />
                  )}
                </div>
                <p className="mt-1 text-xs leading-5 text-slate-500">{capability.role}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  <Badge className="border-white/10 bg-white/[0.04] text-[10px] text-slate-300">
                    {capability.primaryLane}
                  </Badge>
                  <Badge className="border-white/10 bg-white/[0.04] text-[10px] text-slate-300">
                    {runtime?.status ? runtimeStatusLabel(runtime.status) : "معتمد"}
                  </Badge>
                </div>
              </div>
              );
            })}
          </div>
        </section>

        <section className="rounded-lg border border-white/10 bg-[#0b121a]/90 p-4">
          <h2 className="text-sm font-semibold text-white">جاهزية الرنتايم</h2>
          <div className="mt-4 grid gap-3">
            <MetricRow label="إجمالي التكاملات" value={formatNumber(summary?.total ?? mesh?.summary.integration_total ?? 0)} />
            <MetricRow label="جاهز" value={formatNumber(summary?.ready ?? mesh?.summary.integration_ready ?? 0)} good />
            <MetricRow label="جزئي" value={formatNumber(summary?.partial ?? 0)} />
            <MetricRow label="يحتاج مشغل" value={formatNumber(summary?.needs_operator ?? 0)} />
            <MetricRow
              label="قدرات API"
              value={`${formatNumber(capabilities?.ready_count ?? 0)} / ${formatNumber(capabilities?.capability_count ?? FATHIYA_ALLOWED_CAPABILITIES.length)}`}
              good={Boolean(capabilities?.ready_count)}
            />
            <MetricRow label="تداول يعمل" value={mesh?.summary.trading_running ? "نعم" : "لا"} good={mesh?.summary.trading_running} />
          </div>
        </section>
      </div>

      <section className="rounded-lg border border-white/10 bg-[#0b121a]/90 p-4">
        <h2 className="text-sm font-semibold text-white">تفاصيل التكاملات من المشغل</h2>
        <div className="mt-4 grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {integrations.length === 0 && <EmptyState text="لا توجد تكاملات ظاهرة بعد التصفية." />}
          {integrations.map((integration) => (
            <div key={integration.id} className="rounded-lg border border-white/10 bg-white/[0.035] p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-slate-100">{integration.name}</span>
                <IntegrationBadge status={integration.status} />
              </div>
              <p className="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">{integration.summary}</p>
              <p className="mt-2 text-xs text-slate-400">{integration.connection_mode}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function ReportsStation({
  tasks,
  selectedTaskId,
  onSelect,
  busyAction,
  onCancel,
}: {
  tasks: AgentTask[];
  selectedTaskId: string | null;
  onSelect: (task: AgentTask) => void;
  busyAction: string | null;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-4">
      <StationHeader
        icon={FileCheck2}
        title="التقارير والإيصالات"
        description="هنا تظهر كل مهمة، حالتها، التقدم، وآخر إيصال بدون إيقاف أوامر التشغيل الداخلية."
      />

      <section className="rounded-lg border border-sky-400/20 bg-[#0b121a]/90 p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-white">سجل المهام</h2>
          <div className="flex gap-2">
            <ActionButton
              icon={XCircle}
              label="إلغاء"
              variant="outline"
              busy={busyAction === "task:cancel"}
              onClick={onCancel}
            />
          </div>
        </div>
        <div className="space-y-2">
          {tasks.length === 0 && <EmptyState text="لا توجد مهام بعد." />}
          {tasks.map((task) => (
            <button
              key={task.id}
              type="button"
              onClick={() => onSelect(task)}
              className={cn(
                "w-full rounded-lg border p-3 text-right transition",
                selectedTaskId === task.id
                  ? "border-sky-400/35 bg-sky-400/10"
                  : "border-white/10 bg-white/[0.035] hover:border-white/20 hover:bg-white/[0.06]",
              )}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={task.status} />
                    <h3 className="truncate text-sm font-medium text-slate-100">{task.title}</h3>
                  </div>
                  <p className="mt-1 line-clamp-1 text-xs text-slate-500">{task.current_step || task.prompt}</p>
                </div>
                <div className="text-left text-xs text-slate-500">
                  <p>{formatDate(task.updated_at)}</p>
                  <p>{task.latest_receipt_id ?? "no receipt"}</p>
                </div>
              </div>
              <Progress value={task.progress ?? 0} className="mt-3 h-1.5" />
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function RequestStation({
  title,
  setTitle,
  prompt,
  setPrompt,
  busyAction,
  onSubmit,
}: {
  title: string;
  setTitle: (value: string) => void;
  prompt: string;
  setPrompt: (value: string) => void;
  busyAction: string | null;
  onSubmit: (event: FormEvent) => Promise<void>;
}) {
  return (
    <div className="space-y-4">
      <StationHeader
        icon={Send}
        title="طلب تشغيل جديد"
        description="لأي مهمة لا تنتمي للتداول أو الصيد أو المعرفة. الطلب يمر على مصنف المخاطر والإيصالات."
      />

      <form className="rounded-lg border border-white/10 bg-[#0b121a]/90 p-4" onSubmit={onSubmit}>
        <div className="grid gap-4 md:grid-cols-[320px_1fr]">
          <div className="space-y-2">
            <Label>عنوان المهمة</Label>
            <Input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="مثال: فحص جاهزية Zapier MCP"
              className="border-white/10 bg-white/[0.04]"
            />
          </div>
          <div className="space-y-2">
            <Label>الطلب</Label>
            <Textarea
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="اكتب الأمر التفصيلي لفتحية..."
              className="min-h-56 border-white/10 bg-white/[0.04]"
            />
          </div>
        </div>
        <div className="mt-5">
          <ActionButton icon={Send} label="إرسال المهمة" type="submit" busy={busyAction === "direct:create"} />
        </div>
      </form>
    </div>
  );
}

function InspectorPanel({
  task,
  detail,
  health,
  trading,
  onCancel,
  busyAction,
}: {
  task: AgentTask | null;
  detail: AgentTaskDetail | null;
  health: AgentRuntimeHealth | null;
  trading: AgentTradingStatus | null;
  onCancel: () => void;
  busyAction: string | null;
}) {
  return (
    <aside dir="rtl" className="min-h-[420px] border-t border-white/10 bg-[#071019]/95 xl:border-l xl:border-t-0">
      <div className="flex h-full flex-col">
        <div className="border-b border-white/10 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-white">المفتش</h2>
              <p className="text-xs text-slate-500">سجل المهمة، الإيصالات، والخطوة التالية</p>
            </div>
            <Badge className="border-white/10 bg-white/[0.04] text-slate-200">
              {health?.worker_online ? "worker online" : "worker check"}
            </Badge>
          </div>
        </div>

        <ScrollArea className="flex-1">
          <div className="space-y-4 p-4">
            {!task && <EmptyState text="اختر مهمة من التقارير أو أنشئ مهمة جديدة." />}
            {task && (
              <>
                <section className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div>
                      <StatusBadge status={task.status} />
                      <h3 className="mt-2 text-sm font-semibold text-white">{task.title}</h3>
                    </div>
                    <span className="font-mono text-[10px] text-slate-500">{task.id.slice(0, 8)}</span>
                  </div>
                  <Progress value={task.progress ?? 0} className="h-1.5" />
                  <p className="mt-3 text-xs leading-5 text-slate-400">
                    {task.current_step || task.error_message || "لا توجد خطوة حالية بعد."}
                  </p>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <InfoBox label="الخطر" value={riskLabel(task.risk_class)} />
                    <InfoBox label="التنفيذ" value={approvalLabel(task.approval_state)} />
                    <InfoBox label="آخر تحديث" value={formatDate(task.updated_at)} />
                    <InfoBox label="آخر إيصال" value={task.latest_receipt_id ?? "لا يوجد"} />
                  </div>
                  <div className="mt-4 flex gap-2">
                    <ActionButton
                      icon={XCircle}
                      label="إلغاء"
                      variant="outline"
                      busy={busyAction === "task:cancel"}
                      onClick={onCancel}
                    />
                  </div>
                </section>

                <section className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
                  <h3 className="text-sm font-semibold text-white">الخط الزمني</h3>
                  <div className="mt-4 space-y-3">
                    {(detail?.events ?? []).slice(0, 10).map((event) => (
                      <div key={event.id} className="grid grid-cols-[22px_1fr] gap-3">
                        <div className="mt-1 flex h-5 w-5 items-center justify-center rounded-full border border-emerald-400/35 bg-emerald-400/10">
                          <CheckCircle2 className="h-3 w-3 text-emerald-300" />
                        </div>
                        <div>
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-xs font-medium text-slate-200">{event.event_type}</p>
                            <p className="text-[10px] text-slate-500">{formatTime(event.created_at)}</p>
                          </div>
                          <p className="mt-1 text-xs leading-5 text-slate-500">{event.message}</p>
                        </div>
                      </div>
                    ))}
                    {(detail?.events ?? []).length === 0 && <EmptyState text="لا توجد أحداث بعد." />}
                  </div>
                </section>

                <section className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
                  <h3 className="text-sm font-semibold text-white">الإيصالات</h3>
                  <div className="mt-4 space-y-3">
                    {(detail?.receipts ?? []).slice(0, 5).map((receipt) => (
                      <div key={receipt.id} className="rounded-lg border border-white/10 bg-[#071019] p-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-mono text-xs text-cyan-200">{receipt.receipt_id}</span>
                          <Badge className="border-white/10 bg-white/[0.04] text-slate-200">
                            {receipt.status}
                          </Badge>
                        </div>
                        <p className="mt-2 text-xs leading-5 text-slate-400">{receipt.summary}</p>
                      </div>
                    ))}
                    {(detail?.receipts ?? []).length === 0 && <EmptyState text="لا توجد إيصالات بعد." />}
                  </div>
                </section>

                <section className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
                  <h3 className="text-sm font-semibold text-white">تشغيل سريع</h3>
                  <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <InfoBox label="الرنتايم" value={localAgentRuntimeUrl} />
                    <InfoBox label="التداول" value={trading?.running ? "نشط" : "متوقف"} />
                  </div>
                </section>
              </>
            )}
          </div>
        </ScrollArea>
      </div>
    </aside>
  );
}

function MobileStationNav({
  station,
  setStation,
}: {
  station: StationId;
  setStation: (station: StationId) => void;
}) {
  return (
    <div className="mb-4 flex gap-2 overflow-x-auto pb-1 lg:hidden">
      {STATIONS.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => setStation(item.id)}
          className={cn(
            "flex shrink-0 items-center gap-2 rounded-lg border px-3 py-2 text-xs",
            station === item.id
              ? "border-emerald-400/40 bg-emerald-400/15 text-emerald-200"
              : "border-white/10 bg-white/[0.04] text-slate-400",
          )}
        >
          <item.icon className="h-4 w-4" />
          {item.label}
        </button>
      ))}
    </div>
  );
}

function StationHeader({
  icon: Icon,
  title,
  description,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <div
      className="flex max-w-full flex-wrap items-center justify-between gap-4 rounded-lg border border-white/10 bg-[#0b121a]/80 p-4 xl:w-full"
      style={{ width: "min(100%, calc(100vw - 2rem))" }}
    >
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-emerald-400/30 bg-emerald-400/10">
          <Icon className="h-5 w-5 text-emerald-300" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <p className="text-sm text-slate-400">{description}</p>
        </div>
      </div>
      <Badge className="border-emerald-400/25 bg-emerald-400/10 text-emerald-200">خاص ومحلي</Badge>
    </div>
  );
}

function MissionCard({
  number,
  icon: Icon,
  title,
  description,
  accent,
  stats,
  actionLabel,
  actionIcon,
  busy,
  onAction,
}: {
  number: string;
  icon: LucideIcon;
  title: string;
  description: string;
  accent: "emerald" | "cyan" | "amber";
  stats: Array<[string, string]>;
  actionLabel: string;
  actionIcon: LucideIcon;
  busy: boolean;
  onAction: () => void;
}) {
  const ActionIcon = actionIcon;
  const accentClass = {
    emerald: "border-r-emerald-400/80",
    cyan: "border-r-cyan-300/80",
    amber: "border-r-amber-300/80",
  }[accent];

  return (
    <section className={cn("rounded-lg border border-white/10 border-r-4 bg-[#0b121a]/90 p-4", accentClass)}>
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-white/[0.04] text-lg font-bold text-white">
          {number}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Icon className="h-5 w-5 text-slate-300" />
            <h3 className="text-base font-semibold text-white">{title}</h3>
          </div>
          <p className="mt-1 text-sm text-slate-400">{description}</p>
        </div>
      </div>
      <div className="mt-5 grid grid-cols-2 gap-2">
        {stats.map(([label, value]) => (
          <InfoBox key={label} label={label} value={value} />
        ))}
      </div>
      <Button
        type="button"
        onClick={onAction}
        disabled={busy}
        className="mt-5 w-full bg-white text-slate-950 hover:bg-slate-200"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ActionIcon className="h-4 w-4" />}
        {actionLabel}
      </Button>
    </section>
  );
}

function OperationBand({
  number,
  icon: Icon,
  title,
  description,
  accent,
  stats,
  actionLabel,
  actionIcon,
  busy,
  onAction,
}: {
  number: string;
  icon: LucideIcon;
  title: string;
  description: string;
  accent: "emerald" | "cyan" | "amber";
  stats: Array<[string, string]>;
  actionLabel: string;
  actionIcon: LucideIcon;
  busy: boolean;
  onAction: () => void;
}) {
  const ActionIcon = actionIcon;
  const accentClass = {
    emerald: "border-r-emerald-400/80",
    cyan: "border-r-cyan-300/80",
    amber: "border-r-amber-300/80",
  }[accent];

  return (
    <section
      className={cn(
        "max-w-full rounded-lg border border-white/10 border-r-4 bg-[#0b121a]/90 p-4 shadow-xl shadow-black/10 xl:w-full",
        accentClass,
      )}
      style={{ width: "min(100%, calc(100vw - 2rem))" }}
    >
      <div className="grid min-w-0 gap-4 xl:grid-cols-[190px_minmax(0,1fr)_260px] xl:items-center">
        <div className="order-1 flex min-w-0 items-center justify-end gap-4 xl:order-3">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-white/[0.05] text-lg font-bold text-white">
            {number}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <Icon className="h-5 w-5 text-slate-300" />
              <h3 className="truncate text-base font-semibold text-white">{title}</h3>
            </div>
            <p className="mt-1 text-sm leading-6 text-slate-400">{description}</p>
          </div>
        </div>

        <div className="order-2 grid min-w-0 gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:order-2">
          {stats.map(([label, value]) => (
            <InfoBox key={label} label={label} value={value} />
          ))}
        </div>

        <Button
          type="button"
          onClick={onAction}
          disabled={busy}
          variant="outline"
          className="order-3 h-12 w-full min-w-0 border-white/10 bg-white/[0.04] text-slate-100 hover:border-emerald-400/35 hover:bg-emerald-400/10 xl:order-1"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ActionIcon className="h-4 w-4" />}
          {actionLabel}
        </Button>
      </div>
    </section>
  );
}

function StatusTile({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone: "good" | "warn" | "info" | "muted";
}) {
  const toneClass = {
    good: "text-emerald-300",
    warn: "text-amber-300",
    info: "text-cyan-300",
    muted: "text-slate-400",
  }[tone];

  return (
    <div className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
      <Icon className={cn("h-4 w-4", toneClass)} />
      <div className="text-xs">
        <p className="text-slate-500">{label}</p>
        <p className={cn("font-medium", toneClass)}>{value}</p>
      </div>
    </div>
  );
}

function ActionButton({
  icon: Icon,
  label,
  busy,
  variant = "default",
  type = "button",
  onClick,
}: {
  icon: LucideIcon;
  label: string;
  busy?: boolean;
  variant?: "default" | "outline" | "secondary";
  type?: "button" | "submit";
  onClick?: () => void;
}) {
  return (
    <Button
      type={type}
      onClick={onClick}
      disabled={busy}
      variant={variant === "default" ? "default" : variant}
      className={cn(
        variant === "default" && "bg-emerald-400 text-emerald-950 hover:bg-emerald-300",
        variant === "outline" && "border-white/10 bg-white/[0.04] text-slate-200 hover:bg-white/10",
        variant === "secondary" && "bg-cyan-400 text-cyan-950 hover:bg-cyan-300",
      )}
    >
      {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
      {label}
    </Button>
  );
}

function Metric({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "good" | "bad" | "neutral";
}) {
  return (
    <div className="min-w-0 rounded-lg border border-white/10 bg-white/[0.035] p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p
        className={cn(
          "mt-2 truncate text-sm font-semibold text-slate-100",
          tone === "good" && "text-emerald-300",
          tone === "bad" && "text-rose-300",
        )}
      >
        {value}
      </p>
    </div>
  );
}

function MetricRow({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="flex min-w-0 items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.035] px-3 py-2">
      <span className="text-xs text-slate-500">{label}</span>
      <span className={cn("truncate text-left text-xs font-medium text-slate-200", good && "text-emerald-300")}>
        {value}
      </span>
    </div>
  );
}

function InfoBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-white/10 bg-white/[0.035] px-3 py-2">
      <p className="text-[10px] text-slate-500">{label}</p>
      <p className="mt-1 min-w-0 truncate text-xs font-medium text-slate-200">{value}</p>
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-lg border border-dashed border-white/10 bg-white/[0.025] p-4 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}

function StatusBadge({ status }: { status: AgentTaskStatus }) {
  const classes: Record<AgentTaskStatus, string> = {
    queued: "border-slate-400/25 bg-slate-400/10 text-slate-200",
    running: "border-cyan-400/25 bg-cyan-400/10 text-cyan-200",
    awaiting_approval: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    completed: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    failed: "border-rose-400/25 bg-rose-400/10 text-rose-200",
    stalled: "border-orange-400/25 bg-orange-400/10 text-orange-200",
    canceled: "border-slate-400/25 bg-slate-400/10 text-slate-300",
  };
  return <Badge className={classes[status]}>{STATUS_LABELS[status] ?? status}</Badge>;
}

function IntegrationBadge({ status }: { status: string }) {
  const good = status === "ready";
  return (
    <Badge
      className={
        good
          ? "border-emerald-400/25 bg-emerald-400/10 text-emerald-200"
          : "border-amber-400/25 bg-amber-400/10 text-amber-200"
      }
    >
      {integrationStatusLabel(status)}
    </Badge>
  );
}

function StatusPill({ good, label }: { good: boolean; label: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium",
        good
          ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-200"
          : "border-slate-400/20 bg-slate-400/10 text-slate-300",
      )}
    >
      <span className={cn("h-2 w-2 rounded-full", good ? "bg-emerald-300" : "bg-slate-500")} />
      {label}
    </span>
  );
}

function buildBugBountyTaskBody(options: {
  mode: BugBountyMode;
  platform: BugBountyPlatform;
  programUrl: string;
  repoUrl: string;
  scope: string;
  focus: string;
  evidence: string;
  dedupe: string;
}): CreateAgentTaskBody {
  const modeLabel: Record<BugBountyMode, string> = {
    hunt: "بحث صيد ثغرات",
    draft: "مسودة تقرير",
    dedupe: "ديدوب عميق",
    reply: "رد ترياج",
  };
  const program = options.programUrl.trim() || "هدف غير محدد";
  const prompt = [
    `FATHIYA_BUG_BOUNTY_${options.mode.toUpperCase()}_V2:`,
    `platform: ${options.platform}`,
    `program_url: ${program}`,
    options.repoUrl.trim() ? `repo_or_source: ${options.repoUrl.trim()}` : "",
    options.focus.trim() ? `focus: ${options.focus.trim()}` : "focus: OWASP Top 10 + business logic + auth + supply chain",
    options.scope.trim() ? `authorized_scope:\n${options.scope.trim()}` : "authorized_scope: require operator supplied program scope before any live testing",
    options.evidence.trim()
      ? `evidence_plan:\n${options.evidence.trim()}`
      : "evidence_plan: collect reproducible request/response, screenshots, local PoC, and realistic impact before draft",
    options.dedupe.trim()
      ? `dedupe_notes:\n${options.dedupe.trim()}`
      : "dedupe_required: disclosed reports, prior duplicate IDs, GitHub issues/PRs/discussions, changelog, CVEs, exact function names, and root-cause terms",
    `allowed_tools: ${BUG_BOUNTY_CAPABILITY_NAMES}, Chrome, local repo review, OpenRouter/Hugging Face for reasoning and retrieval`,
    `quality_gates:\n${bugBountyGatePrompt()}`,
    "submission_gate: no submission-ready report without practical impact, reproducible evidence, authorized scope, and dedupe result.",
    "external_submission: prepare draft only; external send/upload stays approval-gated.",
    "output: candidate verdict, severity rationale, exploitability limits, proof checklist, report draft or rejection reason.",
  ]
    .filter(Boolean)
    .join("\n");

  return {
    title: `${modeLabel[options.mode]}: ${programLabel(options.platform, program)}`,
    prompt,
  };
}

function isAllowedVisibleText(...values: Array<string | null | undefined>) {
  return values.every((value) => !EXCLUDED_TOOL_PATTERN.test(value ?? ""));
}

function runtimeCapabilityFor(
  capability: FathiyaCapability,
  inventory: AgentRuntimeCapabilityInventory | null,
): AgentRuntimeCapability | undefined {
  if (!inventory?.capabilities) return undefined;
  const acceptedIds = new Set([capability.id, ...capability.runtimeIds].map(normalizeRuntimeId));
  return inventory.capabilities.find((item) => acceptedIds.has(normalizeRuntimeId(item.id)));
}

function normalizeRuntimeId(value: string | null | undefined) {
  return (value ?? "").replace(/[-\s]+/g, "_").toLowerCase();
}

function isRuntimeReady(status: string | null | undefined) {
  return ["active", "ready"].includes((status ?? "").toLowerCase());
}

function runtimeStatusLabel(status: string) {
  const labels: Record<string, string> = {
    active: "نشط",
    ready: "جاهز",
    partial: "جزئي",
    degraded: "متدهور",
    unavailable: "غير متاح",
    needs_setup: "إعداد",
  };
  return labels[status.toLowerCase()] ?? status;
}

function bugBountyGateSatisfied(
  gateId: string,
  values: { programUrl: string; scope: string; evidence: string; dedupe: string },
) {
  const hasScope = Boolean(values.scope.trim() || values.programUrl.trim());
  const hasEvidence = Boolean(values.evidence.trim());
  const hasDedupe = Boolean(values.dedupe.trim());
  if (gateId === "authorized-scope") return hasScope;
  if (gateId === "dedupe-first") return hasDedupe;
  if (gateId === "practical-impact") return hasEvidence;
  if (gateId === "reproducible-proof") return hasEvidence;
  if (gateId === "severity-calibration") return hasEvidence && hasDedupe;
  if (gateId === "counter-evidence") return hasDedupe;
  return false;
}

function integrationRank(integration: AgentIntegrationReadiness) {
  const statusRank: Record<string, number> = {
    ready: 0,
    partial: 1,
    needs_operator: 2,
    needs_setup: 3,
  };
  return statusRank[integration.status] ?? 5;
}

function programLabel(platform: BugBountyPlatform, program: string) {
  const prefix = platform === "hackerone" ? "HackerOne" : platform === "bugcrowd" ? "Bugcrowd" : "Auto";
  return `${prefix} / ${program.replace(/^https?:\/\//, "").slice(0, 48)}`;
}

function integrationStatusLabel(status: string) {
  const labels: Record<string, string> = {
    ready: "جاهز",
    partial: "جزئي",
    needs_setup: "إعداد",
    needs_operator: "مشغل",
    failed: "فشل",
  };
  return labels[status] ?? status;
}

function riskLabel(value: AgentTask["risk_class"]) {
  const labels: Record<string, string> = {
    internal_owned: "داخلي",
    financial: "مالي",
    live_security: "أمن حي",
    destructive: "حذف/تدمير",
    external: "خارجي",
  };
  return labels[value] ?? value;
}

function approvalLabel(value: AgentTask["approval_state"]) {
  const labels: Record<string, string> = {
    not_required: "مباشر",
    pending: "مؤجل يدوي",
    approved: "مفعل",
    rejected: "مرفوض",
  };
  return labels[value] ?? value;
}

function tradingActionLabel(action: AgentTradingCycle["prediction"]["action"] | undefined) {
  if (!action) return "لا توجد";
  const labels: Record<string, string> = {
    buy: "شراء ورقي",
    sell: "بيع ورقي",
    hold: "انتظار",
  };
  return labels[action] ?? action;
}

function formatDate(value: string | null | undefined) {
  if (!value) return "لا يوجد";
  return new Intl.DateTimeFormat("ar-SA", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function formatTime(value: string | null | undefined) {
  if (!value) return "--:--";
  return new Intl.DateTimeFormat("ar-SA", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(new Date(value));
}

function formatNumber(value: number) {
  return new Intl.NumberFormat("en-US").format(value);
}

function formatMoney(value: number | null | undefined, suffix = "USD") {
  if (typeof value !== "number" || Number.isNaN(value)) return "لا يوجد";
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(value)} ${suffix}`;
}

function percentOrDash(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) return "لا يوجد";
  return `${Math.round(value * 100)}%`;
}

function formatSeconds(value: number | null | undefined) {
  if (typeof value !== "number" || Number.isNaN(value)) return "لا يوجد";
  return `${value.toFixed(2)} ث`;
}

function pnlTone(value: number | null | undefined): "good" | "bad" | "neutral" {
  if (typeof value !== "number") return "neutral";
  if (value > 0) return "good";
  if (value < 0) return "bad";
  return "neutral";
}

function jsonPreview(value: Json | null | undefined) {
  if (value == null) return "لا يوجد";
  return JSON.stringify(value, null, 2).slice(0, 600);
}
