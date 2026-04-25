import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { ArrowRight, RefreshCw, CircleAlert as AlertCircle, CircleCheck as CheckCircle2, Clock, History, Copy, Check } from "lucide-react";
import { toast } from "sonner";

interface AiRun {
  id: string;
  task_id: string | null;
  model: string;
  system_prompt: string | null;
  user_prompt: string | null;
  output: string | null;
  saved_path: string | null;
  save_kind: string | null;
  status: string;
  error_message: string | null;
  http_status: number | null;
  duration_ms: number | null;
  created_at: string;
}

export const Route = createFileRoute("/ai-runs")({
  head: () => ({
    meta: [
      { title: "AI Runs History — FATHIYA Ops" },
      { name: "description", content: "سجل كل استدعاءات Generate (المدخلات، المخرجات، status)." },
    ],
  }),
  loader: async () => {
    const { data, error } = await supabase
      .from("ai_runs")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(200);
    if (error) throw new Error(error.message);
    return { runs: (data ?? []) as AiRun[] };
  },
  errorComponent: ({ error, reset }) => {
    const router = useRouter();
    return (
      <div dir="rtl" className="min-h-screen bg-background text-foreground p-6">
        <Card className="max-w-lg mx-auto p-6 text-center">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
          <p className="text-destructive text-sm mb-4">{error.message}</p>
          <Button
            onClick={() => {
              router.invalidate();
              reset();
            }}
          >
            إعادة المحاولة
          </Button>
        </Card>
      </div>
    );
  },
  component: AiRunsPage,
});

function fmtDuration(ms: number | null) {
  if (ms == null) return "--";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("ar", { dateStyle: "short", timeStyle: "medium" });
}

function AiRunsPage() {
  const data = Route.useLoaderData() as { runs: AiRun[] };
  const runs = data.runs;
  const router = useRouter();
  const [filter, setFilter] = useState<"all" | "ok" | "error">("all");
  const [open, setOpen] = useState<AiRun | null>(null);

  const filtered = runs.filter((r: AiRun) => filter === "all" || r.status === filter);
  const okCount = runs.filter((r: AiRun) => r.status === "ok").length;
  const errCount = runs.filter((r: AiRun) => r.status === "error").length;

  return (
    <TooltipProvider delayDuration={300}>
      <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
        <header className="sticky top-0 z-30 border-b border-border/50 bg-background/85 backdrop-blur">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Link
                to="/"
                className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30 px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors duration-150"
              >
                <ArrowRight className="h-3.5 w-3.5" />
                العودة
              </Link>
              <div className="h-5 w-px bg-border/50" />
              <div className="flex items-center gap-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 border border-amber-500/30">
                  <History className="h-4 w-4 text-amber-400" />
                </div>
                <div>
                  <h1 className="text-sm font-bold">AI Runs History</h1>
                  <p className="text-[10px] text-muted-foreground">
                    سجل كل استدعاءات Generate -- آخر 200
                  </p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {/* Summary stats */}
              <div className="hidden sm:flex items-center gap-3">
                <div className="flex items-center gap-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[11px] text-emerald-400 font-medium">
                  <CheckCircle2 className="h-3.5 w-3.5" /> {okCount}
                </div>
                <div className="flex items-center gap-1.5 rounded-lg border border-destructive/20 bg-destructive/10 px-2.5 py-1 text-[11px] text-destructive font-medium">
                  <AlertCircle className="h-3.5 w-3.5" /> {errCount}
                </div>
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => router.invalidate()}
                    className="h-8 gap-1.5 text-[11px]"
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    تحديث
                  </Button>
                </TooltipTrigger>
                <TooltipContent>تحديث البيانات</TooltipContent>
              </Tooltip>
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 animate-fade-in-up">
          {/* Filters */}
          <div className="mb-5 flex items-center gap-2">
            {(["all", "ok", "error"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={
                  "inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-[11px] font-medium transition-all duration-150 " +
                  (filter === f
                    ? "border-primary/50 bg-primary/15 text-primary shadow-sm"
                    : "border-border/60 bg-muted/20 text-muted-foreground hover:border-primary/30 hover:text-foreground")
                }
              >
                {f === "all" && <History className="h-3 w-3" />}
                {f === "ok" && <CheckCircle2 className="h-3 w-3" />}
                {f === "error" && <AlertCircle className="h-3 w-3" />}
                {f === "all" ? "الكل" : f === "ok" ? "ناجح" : "أخطاء"}
                <span className="font-mono opacity-60">
                  {f === "all" ? runs.length : f === "ok" ? okCount : errCount}
                </span>
              </button>
            ))}
          </div>

          {filtered.length === 0 ? (
            <Card className="p-12 text-center bg-card/40 border-border/60">
              <History className="h-10 w-10 text-muted-foreground/30 mx-auto mb-3" />
              <p className="text-sm text-muted-foreground">
                لا يوجد استدعاءات بعد. اضغط Generate من الصفحة الرئيسية لبدء التسجيل.
              </p>
            </Card>
          ) : (
            <Card className="overflow-hidden bg-card/40 border-border/60">
              <div className="overflow-x-auto">
                <table className="w-full text-[11px]">
                  <thead className="bg-muted/30 border-b border-border/50">
                    <tr className="text-right">
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">الوقت</th>
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Task</th>
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Model</th>
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Status</th>
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">HTTP</th>
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">المدة</th>
                      <th className="px-4 py-3 font-semibold text-muted-foreground text-[10px] uppercase tracking-wider">Artifact</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((r, i) => (
                      <tr
                        key={r.id}
                        onClick={() => setOpen(r)}
                        className={
                          "border-b border-border/30 cursor-pointer transition-all duration-150 " +
                          "hover:bg-primary/5 " +
                          (i % 2 === 0 ? "bg-transparent" : "bg-muted/10")
                        }
                      >
                        <td className="px-4 py-3 font-mono text-muted-foreground whitespace-nowrap">
                          {fmtDate(r.created_at)}
                        </td>
                        <td className="px-4 py-3 font-mono font-medium">{r.task_id ?? "--"}</td>
                        <td className="px-4 py-3 font-mono text-muted-foreground text-[10px]">{r.model}</td>
                        <td className="px-4 py-3">
                          {r.status === "ok" ? (
                            <Badge
                              variant="outline"
                              className="border-emerald-500/40 bg-emerald-500/10 text-emerald-300 text-[10px] gap-1"
                            >
                              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                              ok
                            </Badge>
                          ) : (
                            <Badge
                              variant="outline"
                              className="border-destructive/40 bg-destructive/10 text-destructive text-[10px] gap-1"
                            >
                              <span className="h-1.5 w-1.5 rounded-full bg-destructive" />
                              error
                            </Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 font-mono">{r.http_status ?? "--"}</td>
                        <td className="px-4 py-3 font-mono text-muted-foreground">
                          <span className="inline-flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {fmtDuration(r.duration_ms)}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono text-muted-foreground truncate max-w-[200px]">
                          {r.saved_path ?? "--"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </main>

        <RunDetailSheet run={open} onClose={() => setOpen(null)} />
      </div>
    </TooltipProvider>
  );
}

function RunDetailSheet({ run, onClose }: { run: AiRun | null; onClose: () => void }) {
  const [copied, setCopied] = useState<string | null>(null);

  const copyText = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(label);
    toast.success("نُسخ");
    setTimeout(() => setCopied(null), 1500);
  };

  return (
    <Sheet open={!!run} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="left" className="w-full sm:max-w-2xl overflow-hidden flex flex-col" dir="rtl">
        {run && (
          <>
            <SheetHeader>
              <SheetTitle className="flex items-center gap-2 text-sm">
                <span className="font-mono">{run.task_id ?? "(no task)"}</span>
                {run.status === "ok" ? (
                  <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-[10px] gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                    ok
                  </Badge>
                ) : (
                  <Badge variant="destructive" className="text-[10px] gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-destructive-foreground" />
                    error
                  </Badge>
                )}
              </SheetTitle>
            </SheetHeader>
            <ScrollArea className="flex-1 mt-4">
              <div className="space-y-4 pl-3 text-[11px]">
                <div className="grid grid-cols-2 gap-3">
                  <DetailField label="ID" value={run.id} mono />
                  <DetailField label="الوقت" value={fmtDate(run.created_at)} />
                  <DetailField label="Model" value={run.model} mono />
                  <DetailField label="HTTP Status" value={String(run.http_status ?? "--")} mono />
                  <DetailField label="المدة" value={fmtDuration(run.duration_ms)} mono />
                  <DetailField label="Saved Path" value={run.saved_path ?? "--"} mono />
                </div>

                {run.error_message && (
                  <div>
                    <div className="text-[10px] text-destructive mb-1.5 font-semibold">
                      رسالة الخطأ
                    </div>
                    <pre className="bg-destructive/10 border border-destructive/30 text-destructive p-3 rounded-lg text-[10px] whitespace-pre-wrap">
                      {run.error_message}
                    </pre>
                  </div>
                )}

                {run.system_prompt && (
                  <CodeBlock
                    label="System"
                    content={run.system_prompt}
                    onCopy={() => copyText(run.system_prompt!, "system")}
                    copied={copied === "system"}
                  />
                )}
                {run.user_prompt && (
                  <CodeBlock
                    label="User Prompt"
                    content={run.user_prompt}
                    onCopy={() => copyText(run.user_prompt!, "user")}
                    copied={copied === "user"}
                  />
                )}
                {run.output && (
                  <CodeBlock
                    label="Output"
                    content={run.output}
                    maxH="max-h-96"
                    onCopy={() => copyText(run.output!, "output")}
                    copied={copied === "output"}
                  />
                )}
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function DetailField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="rounded-lg border border-border/40 bg-muted/20 p-2.5">
      <div className="text-[9px] text-muted-foreground/70 uppercase tracking-wider mb-1">{label}</div>
      <div className={"text-[11px] break-all " + (mono ? "font-mono" : "")}>{value}</div>
    </div>
  );
}

function CodeBlock({
  label,
  content,
  maxH = "max-h-60",
  onCopy,
  copied,
}: {
  label: string;
  content: string;
  maxH?: string;
  onCopy: () => void;
  copied: boolean;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] text-muted-foreground font-medium">{label}</span>
        <button
          onClick={onCopy}
          className="inline-flex items-center gap-1 text-[9px] text-muted-foreground hover:text-foreground transition-colors"
        >
          {copied ? <Check className="h-2.5 w-2.5 text-emerald-400" /> : <Copy className="h-2.5 w-2.5" />}
          نسخ
        </button>
      </div>
      <pre className={`bg-muted/30 border border-border/40 p-3 rounded-lg text-[10px] whitespace-pre-wrap font-mono ${maxH} overflow-auto leading-relaxed`}>
        {content}
      </pre>
    </div>
  );
}
