import type { Session } from "@supabase/supabase-js";
import { createFileRoute, Link } from "@tanstack/react-router";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  CircleAlert,
  Clock3,
  FileCheck2,
  ListChecks,
  Loader2,
  LogOut,
  Play,
  RefreshCw,
  ShieldAlert,
  Square,
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
import { Textarea } from "@/components/ui/textarea";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { getSupabaseConfigurationError, supabase } from "@/integrations/supabase/client";
import { agentApi, isLocalAgentRuntime, localAgentRuntimeUrl } from "@/lib/agent/client";
import type {
  AgentTask,
  AgentTaskDetail,
  AgentTaskStatus,
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AgentTaskDetail | null>(null);
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [creating, setCreating] = useState(false);
  const [acting, setActing] = useState(false);
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

  useEffect(() => {
    if (!hasAccess) return;
    void loadTasks();
    const timer = window.setInterval(() => void loadTasks(), 5000);
    return () => window.clearInterval(timer);
  }, [hasAccess, loadTasks]);

  useEffect(() => {
    if (!hasAccess || !selectedId) return;
    void loadDetail();
    const timer = window.setInterval(() => void loadDetail(), 2000);
    return () => window.clearInterval(timer);
  }, [hasAccess, loadDetail, selectedId]);

  async function createTask(event: FormEvent) {
    event.preventDefault();
    if (!hasAccess || !prompt.trim()) return;
    setCreating(true);
    setError("");
    try {
      const body: CreateAgentTaskBody = { prompt: prompt.trim(), title: title.trim() || undefined };
      const data = await agentApi<{ task: AgentTask }>(session ?? null, "/api/agent/tasks", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPrompt("");
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
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-md border border-emerald-500/30 bg-emerald-500/10">
                <ListChecks className="h-5 w-5 text-emerald-400" />
              </div>
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <h1 className="text-sm font-bold">مهام وكلاء فتحية</h1>
                  {localMode && (
                    <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-400">
                      LOCAL RUNTIME
                    </Badge>
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground">
                  {localMode ? `${localAgentRuntimeUrl} · ` : ""}
                  {activeCount} نشطة من {tasks.length} مهمة
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button variant="outline" size="icon" onClick={() => void loadTasks()}>
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

        <main className="mx-auto max-w-7xl px-4 py-5 sm:px-6">
          {error && (
            <Alert variant="destructive" className="mb-4">
              <CircleAlert />
              <AlertTitle>تعذر إكمال الطلب</AlertTitle>
              <AlertDescription className="break-all">{error}</AlertDescription>
            </Alert>
          )}

          <div className="grid gap-4 xl:grid-cols-[340px_minmax(0,1fr)]">
            <div className="space-y-4">
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
                    <div className="space-y-1.5">
                      <Label htmlFor="task-prompt">الطلب</Label>
                      <Textarea
                        id="task-prompt"
                        value={prompt}
                        onChange={(event) => setPrompt(event.target.value)}
                        placeholder="مثال: اعرض حالة المستودع وسجل إيصال التنفيذ"
                        rows={5}
                        maxLength={20_000}
                        required
                      />
                    </div>
                    <Button className="w-full" type="submit" disabled={creating || !prompt.trim()}>
                      {creating ? <Loader2 className="animate-spin" /> : <Play />}
                      إرسال للمشغّل
                    </Button>
                  </form>
                </CardContent>
              </Card>

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
      </div>
    </TooltipProvider>
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
    <div className="space-y-4">
      <Card className="border-border/60 bg-card/50">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="mb-2 flex items-center gap-2">
                <StatusBadge status={task.status} />
                <Badge variant="outline">{riskLabel(task.risk_class)}</Badge>
              </div>
              <CardTitle className="break-words text-base">{task.title}</CardTitle>
              <CardDescription className="mt-2 whitespace-pre-wrap">{task.prompt}</CardDescription>
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
            <ScrollArea className="h-[420px]">
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
            <ScrollArea className="h-[420px]">
              <div className="space-y-4 pl-3">
                {receipts.map((receipt) => (
                  <div
                    key={receipt.id}
                    className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2">
                      <span className="font-mono text-[11px] text-emerald-400">
                        {receipt.receipt_id}
                      </span>
                      <Badge variant="outline">{receipt.status}</Badge>
                    </div>
                    <p className="whitespace-pre-wrap text-xs">{receipt.summary}</p>
                    <JsonBlock value={receipt.evidence} />
                  </div>
                ))}
                {task.result !== null && (
                  <div>
                    <p className="mb-2 text-xs font-semibold">النتيجة النهائية</p>
                    <JsonBlock value={task.result} />
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

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre
      dir="ltr"
      className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words rounded-md border border-border/50 bg-background/50 p-3 text-left font-mono text-[10px]"
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
