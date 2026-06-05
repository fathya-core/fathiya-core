import type { Session } from "@supabase/supabase-js";
import { createFileRoute, Link } from "@tanstack/react-router";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
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
  AgentConnectorBridge,
  AgentConnectorProfile,
  AgentIntegrationReadiness,
  AgentIntegrationProbeResult,
  AgentIntegrationStatus,
  AgentIntegrationSummary,
  AgentKnowledgeIntakeStatus,
  AgentLocalSettingsGroup,
  AgentLocalSettingsResponse,
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

function AgentTasksPage() {
  const localMode = isLocalAgentRuntime;
  const [session, setSession] = useState<Session | null | undefined>(undefined);
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [connectors, setConnectors] = useState<AgentConnectorProfile[]>([]);
  const [connectorBridge, setConnectorBridge] = useState<AgentConnectorBridge | null>(null);
  const [integrations, setIntegrations] = useState<AgentIntegrationReadiness[]>([]);
  const [integrationSummary, setIntegrationSummary] = useState<AgentIntegrationSummary | null>(
    null,
  );
  const [localSettings, setLocalSettings] = useState<AgentLocalSettingsResponse | null>(null);
  const [selectedSettingsGroup, setSelectedSettingsGroup] = useState<string | null>(null);
  const [integrationProbes, setIntegrationProbes] = useState<
    Record<string, AgentIntegrationProbeResult>
  >({});
  const [probingIntegration, setProbingIntegration] = useState<string | null>(null);
  const [trading, setTrading] = useState<AgentTradingStatus | null>(null);
  const [intake, setIntake] = useState<AgentKnowledgeIntakeStatus | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AgentTaskDetail | null>(null);
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [composerMode, setComposerMode] = useState<"direct" | "knowledge">("direct");
  const [reportSource, setReportSource] = useState("");
  const [reportObjective, setReportObjective] = useState("");
  const [reportContent, setReportContent] = useState("");
  const [creating, setCreating] = useState(false);
  const [acting, setActing] = useState(false);
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
      }>(null, "/api/agent/connectors");
      setConnectors(data.connectors);
      setConnectorBridge(data.bridge);
    } catch (loadError) {
      setError(String(loadError));
    }
  }, [localMode]);

  const loadTrading = useCallback(async () => {
    if (!localMode) return;
    try {
      const data = await agentApi<{ trading: AgentTradingStatus }>(
        null,
        "/api/agent/trading/status",
      );
      setTrading(data.trading);
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
              objective: reportObjective,
              content: reportContent,
            })
          : prompt.trim();
      if (!taskPrompt) return;
      const body: CreateAgentTaskBody = {
        prompt: taskPrompt,
        title:
          title.trim() ||
          (composerMode === "knowledge" ? `تنفيذ من تقرير: ${reportSource.trim()}` : undefined),
      };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPrompt("");
      setReportSource("");
      setReportObjective("");
      setReportContent("");
      setTitle("");
      setSelectedId(data.task.id);
      await loadTasks();
    } catch (createError) {
      setError(String(createError));
    } finally {
      setCreating(false);
    }
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

  async function tradingAction(action: "start" | "stop" | "tick") {
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
      await Promise.all([loadIntake(), loadTasks()]);
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
  const activeSettingsGroup = useMemo(
    () =>
      localSettings?.groups.find((group) => group.id === selectedSettingsGroup) ?? null,
    [localSettings, selectedSettingsGroup],
  );
  const canCreateTask =
    composerMode === "knowledge"
      ? Boolean(reportSource.trim() && reportObjective.trim() && reportContent.trim())
      : Boolean(prompt.trim());

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
                  <h1 className="text-sm font-bold">مهام وكلاء فتحية</h1>
                  {localMode && (
                    <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                      LOCAL RUNTIME
                    </Badge>
                  )}
                </div>
                <p className="break-all text-[11px] text-muted-foreground">
                  {localMode ? `${localAgentRuntimeUrl} · ` : ""}
                  {activeCount} نشطة من {tasks.length} مهمة
                  {localMode && ` · ${configuredConnectorCount}/${connectors.length} موصلات جاهزة`}
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
                      void loadConnectors();
                      void loadIntegrations();
                      void loadIntake();
                      void loadLocalSettings();
                    }}
                  >
                    <RefreshCw />
                    <span className="sr-only">تحديث</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>تحديث المهام</TooltipContent>
              </Tooltip>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/command-center">
                  <ArrowRight />
                  مركز القيادة
                </Link>
              </Button>
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

          <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
            <div className="min-w-0 space-y-4">
              <Card className="border-border/60 bg-card/50">
                <CardHeader>
                  <CardTitle className="text-sm">مهمة جديدة</CardTitle>
                  <CardDescription>
                    العمليات الداخلية تبدأ تلقائيًا. المال والفحص الحي والحذف والنشر تحتاج موافقة.
                  </CardDescription>
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
                          placeholder="مثال: اعرض حالة المستودع وسجل إيصال التنفيذ"
                          rows={5}
                          maxLength={20_000}
                        />
                      </TabsContent>
                      <TabsContent value="knowledge" className="space-y-3">
                        <div className="space-y-1.5">
                          <Label htmlFor="report-source">اسم المصدر</Label>
                          <Input
                            id="report-source"
                            value={reportSource}
                            onChange={(event) => setReportSource(event.target.value)}
                            placeholder="مثال: تقرير جاهزية الأتمتة"
                            maxLength={MAX_KNOWLEDGE_SOURCE_CHARACTERS}
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="report-objective">الهدف التنفيذي</Label>
                          <Textarea
                            id="report-objective"
                            value={reportObjective}
                            onChange={(event) => setReportObjective(event.target.value)}
                            placeholder="مثال: نفّذ الفحوصات الداخلية المناسبة وسجل الأدلة"
                            rows={3}
                            maxLength={MAX_KNOWLEDGE_OBJECTIVE_CHARACTERS}
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="report-content">محتوى التقرير</Label>
                          <Textarea
                            id="report-content"
                            value={reportContent}
                            onChange={(event) => setReportContent(event.target.value)}
                            placeholder="ألصق المعلومات أو التقرير هنا"
                            rows={7}
                            maxLength={MAX_KNOWLEDGE_REPORT_CHARACTERS}
                          />
                        </div>
                        <p className="text-[10px] text-muted-foreground">
                          يُحفظ التقرير كدليل غير موثوق؛ لا يمنح صلاحية لتنفيذ أوامر مخفية.
                        </p>
                      </TabsContent>
                    </Tabs>
                    <Button className="w-full" type="submit" disabled={creating || !canCreateTask}>
                      {creating ? <Loader2 className="animate-spin" /> : <Play />}
                      {composerMode === "knowledge" ? "استيعاب وتنفيذ" : "إرسال للمشغّل"}
                    </Button>
                  </form>
                </CardContent>
              </Card>

              {localMode && intake && (
                <Card className="border-border/60 bg-card/50">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <CardTitle className="flex items-center gap-2 text-sm">
                          <FolderSearch className="h-4 w-4" />
                          محرك الاستيعاب المستمر
                        </CardTitle>
                        <CardDescription className="mt-1">
                          يلتقط التقارير المحلية ويحوّلها تلقائيًا إلى مهام وإيصالات.
                        </CardDescription>
                      </div>
                      <Badge
                        className={cn(
                          "shrink-0",
                          intake.running
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                            : "border-border bg-muted/30 text-muted-foreground",
                        )}
                      >
                        {intake.running ? "يراقب" : intake.enabled ? "متوقف" : "معطّل"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <InfoField label="تقارير متتبعة" value={String(intake.tracked_files)} />
                      <InfoField label="مهام أنشئت" value={String(intake.enqueued_count)} />
                      <InfoField
                        label="دورية الفحص"
                        value={`${intake.scan_interval_seconds} ثانية`}
                      />
                      <InfoField label="آخر فحص" value={formatDate(intake.last_scan_at)} />
                    </div>
                    <div className="rounded-md border border-border/50 bg-muted/20 p-3 text-[10px]">
                      <p className="mb-1 font-semibold">آخر تقرير</p>
                      <p className="break-words text-muted-foreground">
                        {intake.last_enqueued?.source_name || "لم يلتقط تقريرًا جديدًا بعد."}
                      </p>
                      {intake.last_enqueued && (
                        <p className="mt-1 break-words text-[9px] text-emerald-400">
                          {STATUS_LABELS[intake.last_enqueued.task_status]} ·{" "}
                          {intake.last_enqueued.task_progress ?? 0}%
                        </p>
                      )}
                      <p
                        dir="ltr"
                        className="mt-2 break-all text-left font-mono text-[9px] text-muted-foreground"
                      >
                        {intake.watch_root}
                      </p>
                    </div>
                    {intake.last_error && (
                      <p className="break-words text-[10px] text-destructive">
                        {intake.last_error}
                      </p>
                    )}
                    <div className="flex gap-2">
                      <Button
                        className="flex-1"
                        size="sm"
                        onClick={() => void intakeAction(intake.running ? "stop" : "start")}
                        disabled={intakeActing || !intake.enabled}
                      >
                        {intakeActing ? (
                          <Loader2 className="animate-spin" />
                        ) : intake.running ? (
                          <Square />
                        ) : (
                          <Play />
                        )}
                        {intake.running ? "إيقاف المراقبة" : "تشغيل المراقبة"}
                      </Button>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => void intakeAction("scan")}
                            disabled={intakeActing || !intake.enabled}
                          >
                            <RefreshCw />
                            <span className="sr-only">فحص مجلد التقارير الآن</span>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>فحص المجلد الآن</TooltipContent>
                      </Tooltip>
                    </div>
                  </CardContent>
                </Card>
              )}

              {localMode && trading && (
                <Card className="border-border/60 bg-card/50">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <CardTitle className="flex items-center gap-2 text-sm">
                          <TrendingUp className="h-4 w-4" />
                          وكيل التداول الأساسي
                        </CardTitle>
                        <CardDescription className="mt-1 break-words">
                          {trading.symbol} · نبضة كل {trading.cycle_target_seconds} ثانية ·{" "}
                          {trading.signal_model}
                        </CardDescription>
                      </div>
                      <Badge
                        className={cn(
                          "shrink-0",
                          trading.running
                            ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                            : "border-border bg-muted/30 text-muted-foreground",
                        )}
                      >
                        {trading.running ? "يعمل" : "متوقف"}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <InfoField
                        label="الوضع"
                        value={trading.mode === "paper" ? "Paper فقط" : trading.mode}
                      />
                      <InfoField label="الدورات" value={String(trading.cycle_count)} />
                      <InfoField
                        label="مصدر السوق"
                        value={marketSourceLabel(trading.current_market_source)}
                      />
                      <InfoField
                        label="دقة التنبؤ"
                        value={
                          trading.prediction_quality.directional_accuracy === null
                            ? "--"
                            : formatPercent(trading.prediction_quality.directional_accuracy)
                        }
                      />
                      <InfoField
                        label="تنبؤات مقاسة"
                        value={String(trading.prediction_quality.evaluated_count)}
                      />
                      <InfoField
                        label="عائد نظري"
                        value={`${formatNumber(
                          trading.prediction_quality.cumulative_strategy_return_bps,
                        )} bps`}
                      />
                      <InfoField
                        label="مستشار النموذج"
                        value={trading.strategy_advisory?.provider || "لم يُحدّث"}
                      />
                      <InfoField
                        label="إشارة المستشار"
                        value={advisoryLabel(trading.strategy_advisory)}
                      />
                      <InfoField label="الرصيد" value={formatNumber(trading.portfolio.equity)} />
                      <InfoField label="صافي PnL" value={formatNumber(trading.portfolio.net_pnl)} />
                    </div>
                    <div className="rounded-md border border-border/50 bg-muted/20 p-3 text-[10px]">
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
                          ? `${trading.latest_cycle.prediction.action} · ${trading.latest_cycle.risk.reason}`
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
                            <span className="sr-only">تنفيذ نبضة تداول paper</span>
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>تنفيذ نبضة paper واحدة</TooltipContent>
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
                  </CardContent>
                </Card>
              )}

              {localMode && (
                <Card className="border-border/60 bg-card/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <KeyRound className="h-4 w-4" />
                      الحسابات والاتصالات
                    </CardTitle>
                    <CardDescription>
                      {integrationSummary
                        ? `${integrationSummary.ready} جاهزة · ${integrationSummary.partial} جزئية · ${integrationSummary.needs_setup + integrationSummary.needs_operator} تحتاج إجراء`
                        : "جارٍ التحقق من حالة الربط الآمن"}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {integrations.length === 0 ? (
                      <p className="px-5 py-6 text-center text-xs text-muted-foreground">
                        لم تُحمّل حالة الحسابات بعد.
                      </p>
                    ) : (
                      <div className="divide-y divide-border/50">
                        {integrations.map((integration) => (
                          <div key={integration.id} className="px-4 py-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="min-w-0">
                                <p className="text-xs font-semibold">{integration.name}</p>
                                <p className="mt-1 break-words text-[10px] text-muted-foreground">
                                  {integration.summary}
                                </p>
                              </div>
                              <IntegrationStatusBadge status={integration.status} />
                            </div>
                            <div className="mt-2 flex flex-wrap items-center gap-1.5">
                              <Badge
                                variant="outline"
                                className="border-border/60 text-[9px] font-normal text-muted-foreground"
                              >
                                {credentialPolicyLabel(integration)}
                              </Badge>
                              {integration.account_required && (
                                <span className="text-[9px] text-muted-foreground">
                                  {integration.status === "ready"
                                    ? "الحساب مربوط"
                                    : "الربط يتم خارج المحادثة"}
                                </span>
                              )}
                            </div>
                            {integration.connected_apps.length > 0 && (
                              <p className="mt-2 line-clamp-2 text-[10px] text-sky-300">
                                {integration.connected_apps.join(" · ")}
                              </p>
                            )}
                            {integration.status !== "ready" && (
                              <p className="mt-2 break-words text-[10px] text-amber-300">
                                {integration.next_step}
                              </p>
                            )}
                            {integration.action_path && integration.action_label && (
                              <Button
                                asChild
                                variant="outline"
                                size="sm"
                                className="mt-2 h-7 text-[10px]"
                              >
                                <a href={integrationActionHref(integration.action_path)}>
                                  <KeyRound />
                                  {integration.action_label}
                                </a>
                              </Button>
                            )}
                            {integration.settings_path && integration.settings_label && (
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="mt-2 h-7 text-[10px]"
                                onClick={() => setSelectedSettingsGroup(integration.id)}
                              >
                                <Settings2 />
                                {integration.settings_label}
                              </Button>
                            )}
                            {integration.probe_path && (
                              <Button
                                type="button"
                                variant="outline"
                                size="sm"
                                className="mt-2 h-7 text-[10px]"
                                disabled={probingIntegration === integration.id}
                                onClick={() => void probeIntegration(integration)}
                              >
                                {probingIntegration === integration.id ? (
                                  <Loader2 className="animate-spin" />
                                ) : (
                                  <Activity />
                                )}
                                {integration.probe_label ?? "اختبار الاتصال"}
                              </Button>
                            )}
                            {integrationProbes[integration.id] && (
                              <IntegrationProbeNotice probe={integrationProbes[integration.id]} />
                            )}
                            {integration.missing_env.length > 0 && (
                              <p
                                dir="ltr"
                                className="mt-1 break-all text-left font-mono text-[9px] text-muted-foreground"
                              >
                                {integration.missing_env.join(" · ")}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                    <p className="border-t border-border/50 px-4 py-3 text-[10px] text-muted-foreground">
                      لا تُرسل كلمات المرور أو مفاتيح API في المحادثة. حسابات OAuth يديرها مزودها،
                      ومفاتيح الخادم تبقى على الجهاز أو الخادم فقط.
                    </p>
                  </CardContent>
                </Card>
              )}

              {localMode && (
                <Card className="border-border/60 bg-card/50">
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <Cable className="h-4 w-4" />
                      الموصلات
                    </CardTitle>
                    <CardDescription>
                      {configuredConnectorCount} جاهزة من {connectors.length}
                      {connectorBridge &&
                        ` · جسر n8n ${
                          connectorBridge.configured
                            ? `جاهز (${connectorBridge.ready_profile_count}/${connectorBridge.allowed_profile_count})`
                            : "يحتاج تهيئة"
                        }`}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    {connectors.length === 0 ? (
                      <p className="px-5 py-6 text-center text-xs text-muted-foreground">
                        لم تُحمّل ملفات الموصلات بعد.
                      </p>
                    ) : (
                      <div className="divide-y divide-border/50">
                        {connectors.map((connector) => (
                          <div
                            key={connector.name}
                            className="flex items-center justify-between gap-3 px-4 py-2.5"
                          >
                            <div className="min-w-0">
                              <p className="truncate text-xs font-semibold">
                                {connector.provider} · {connector.name}
                              </p>
                              <p className="mt-0.5 text-[10px] text-muted-foreground">
                                {connector.method}
                                {connector.requires_approval ? " · يحتاج موافقة" : " · تلقائي"}
                                {connector.bridge_dispatch_allowed && " · عبر جسر n8n"}
                              </p>
                            </div>
                            <Badge
                              className={cn(
                                "shrink-0",
                                connector.configured
                                  ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                                  : "border-amber-500/30 bg-amber-500/10 text-amber-400",
                              )}
                            >
                              {connector.configured ? "جاهز" : "يحتاج إعداد"}
                            </Badge>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

              <Card className="border-border/60 bg-card/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm">الطابور</CardTitle>
                </CardHeader>
                <CardContent className="p-0">
                  <ScrollArea className="h-[460px]">
                    {tasks.length === 0 ? (
                      <p className="px-5 py-8 text-center text-xs text-muted-foreground">
                        لا توجد مهام بعد.
                      </p>
                    ) : (
                      <div className="divide-y divide-border/50">
                        {tasks.map((task) => (
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
                          </button>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>

            <TaskDetail
              detail={detail}
              acting={acting}
              onApprove={() => void taskAction("approve")}
              onCancel={() => void taskAction("cancel")}
            />
          </div>
        </main>
        <IntegrationSettingsSheet
          group={activeSettingsGroup}
          writeAllowed={Boolean(localSettings?.write_allowed)}
          onClose={() => setSelectedSettingsGroup(null)}
          onSaved={async () => {
            await Promise.all([loadLocalSettings(), loadIntegrations(), loadConnectors()]);
          }}
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
}: {
  group: AgentLocalSettingsGroup | null;
  writeAllowed: boolean;
  onClose: () => void;
  onSaved: () => Promise<void>;
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
  onApprove,
  onCancel,
}: {
  detail: AgentTaskDetail | null;
  acting: boolean;
  onApprove: () => void;
  onCancel: () => void;
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
          <div className="grid gap-3 text-xs sm:grid-cols-3">
            <InfoField label="المشغّل" value={task.worker_id || "لم يُستلم"} />
            <InfoField label="آخر heartbeat" value={formatDate(task.last_heartbeat_at)} />
            <InfoField label="بدأت" value={formatDate(task.started_at)} />
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
                    <TaskResultSummary value={task.result} />
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

function TaskResultSummary({ value }: { value: unknown }) {
  const result = asRecord(value);
  if (!result) {
    return <p className="text-xs text-muted-foreground">النتيجة غير قابلة للعرض المختصر.</p>;
  }

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
