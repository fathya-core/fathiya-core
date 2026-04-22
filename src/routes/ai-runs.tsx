import { createFileRoute, Link, useRouter } from "@tanstack/react-router";
import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ArrowRight, RefreshCw, AlertCircle, CheckCircle2, Clock } from "lucide-react";

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
        <p className="text-destructive mb-3">خطأ: {error.message}</p>
        <Button
          onClick={() => {
            router.invalidate();
            reset();
          }}
        >
          إعادة المحاولة
        </Button>
      </div>
    );
  },
  component: AiRunsPage,
});

function fmtDuration(ms: number | null) {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function fmtDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString("ar", { dateStyle: "short", timeStyle: "medium" });
}

function AiRunsPage() {
  const { runs } = Route.useLoaderData();
  const router = useRouter();
  const [filter, setFilter] = useState<"all" | "ok" | "error">("all");
  const [open, setOpen] = useState<AiRun | null>(null);

  const filtered = runs.filter((r) => filter === "all" || r.status === filter);
  const okCount = runs.filter((r) => r.status === "ok").length;
  const errCount = runs.filter((r) => r.status === "error").length;

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-30 border-b border-border/50 bg-background/85 backdrop-blur">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              to="/"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
            >
              <ArrowRight className="h-3 w-3" />
              العودة
            </Link>
            <div className="h-4 w-px bg-border" />
            <div>
              <h1 className="text-sm font-bold">AI Runs History</h1>
              <p className="text-[10px] text-muted-foreground">
                سجل كل استدعاءات Generate · آخر 200
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
              <CheckCircle2 className="h-3 w-3" /> {okCount}
            </span>
            <span className="inline-flex items-center gap-1 text-[11px] text-destructive">
              <AlertCircle className="h-3 w-3" /> {errCount}
            </span>
            <Button
              size="sm"
              variant="outline"
              onClick={() => router.invalidate()}
              className="h-7 text-[10px]"
            >
              <RefreshCw className="h-3 w-3 ml-1" />
              تحديث
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 sm:px-6 py-6">
        <div className="mb-4 flex items-center gap-2">
          {(["all", "ok", "error"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={
                "rounded border px-3 py-1 text-[11px] font-medium transition-colors " +
                (filter === f
                  ? "border-primary/50 bg-primary/15 text-primary"
                  : "border-border/60 bg-muted/20 text-muted-foreground hover:border-primary/30")
              }
            >
              {f === "all" ? "الكل" : f === "ok" ? "ناجح" : "أخطاء"}
              <span className="font-mono opacity-60 mr-1.5">
                {f === "all" ? runs.length : f === "ok" ? okCount : errCount}
              </span>
            </button>
          ))}
        </div>

        {filtered.length === 0 ? (
          <Card className="p-8 text-center text-sm text-muted-foreground">
            لا يوجد استدعاءات بعد. اضغط Generate من الصفحة الرئيسية لبدء التسجيل.
          </Card>
        ) : (
          <Card className="overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead className="bg-muted/30 border-b border-border/50">
                  <tr className="text-right">
                    <th className="px-3 py-2 font-medium text-muted-foreground">الوقت</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Task</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Model</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Status</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">HTTP</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">المدة</th>
                    <th className="px-3 py-2 font-medium text-muted-foreground">Artifact</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r) => (
                    <tr
                      key={r.id}
                      onClick={() => setOpen(r)}
                      className="border-b border-border/30 hover:bg-muted/20 cursor-pointer transition-colors"
                    >
                      <td className="px-3 py-2 font-mono text-muted-foreground whitespace-nowrap">
                        {fmtDate(r.created_at)}
                      </td>
                      <td className="px-3 py-2 font-mono">{r.task_id ?? "—"}</td>
                      <td className="px-3 py-2 font-mono text-muted-foreground">{r.model}</td>
                      <td className="px-3 py-2">
                        {r.status === "ok" ? (
                          <Badge
                            variant="outline"
                            className="border-emerald-500/40 bg-emerald-500/10 text-emerald-300 text-[10px]"
                          >
                            ok
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className="border-destructive/40 bg-destructive/10 text-destructive text-[10px]"
                          >
                            error
                          </Badge>
                        )}
                      </td>
                      <td className="px-3 py-2 font-mono">{r.http_status ?? "—"}</td>
                      <td className="px-3 py-2 font-mono text-muted-foreground">
                        <Clock className="inline h-3 w-3 ml-1" />
                        {fmtDuration(r.duration_ms)}
                      </td>
                      <td className="px-3 py-2 font-mono text-muted-foreground truncate max-w-[200px]">
                        {r.saved_path ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </main>

      <Sheet open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <SheetContent side="left" className="w-full sm:max-w-2xl overflow-hidden flex flex-col" dir="rtl">
          {open && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2 text-sm">
                  <span className="font-mono">{open.task_id ?? "(no task)"}</span>
                  {open.status === "ok" ? (
                    <Badge className="bg-emerald-500/15 text-emerald-300 border-emerald-500/30 text-[10px]">
                      ok
                    </Badge>
                  ) : (
                    <Badge variant="destructive" className="text-[10px]">
                      error
                    </Badge>
                  )}
                </SheetTitle>
              </SheetHeader>
              <ScrollArea className="flex-1 mt-4">
                <div className="space-y-4 pl-3 text-[11px]">
                  <Field label="ID" value={open.id} mono />
                  <Field label="الوقت" value={fmtDate(open.created_at)} />
                  <Field label="Model" value={open.model} mono />
                  <Field label="HTTP Status" value={String(open.http_status ?? "—")} mono />
                  <Field label="المدة" value={fmtDuration(open.duration_ms)} mono />
                  <Field label="Saved Path" value={open.saved_path ?? "—"} mono />
                  <Field label="Save Kind" value={open.save_kind ?? "—"} mono />
                  {open.error_message && (
                    <div>
                      <div className="text-[10px] text-destructive mb-1 font-semibold">
                        رسالة الخطأ
                      </div>
                      <pre className="bg-destructive/10 border border-destructive/30 text-destructive p-2 rounded text-[10px] whitespace-pre-wrap">
                        {open.error_message}
                      </pre>
                    </div>
                  )}
                  {open.system_prompt && (
                    <div>
                      <div className="text-[10px] text-muted-foreground mb-1">System</div>
                      <pre className="bg-muted/30 border border-border/40 p-2 rounded text-[10px] whitespace-pre-wrap font-mono max-h-40 overflow-auto">
                        {open.system_prompt}
                      </pre>
                    </div>
                  )}
                  {open.user_prompt && (
                    <div>
                      <div className="text-[10px] text-muted-foreground mb-1">User Prompt</div>
                      <pre className="bg-muted/30 border border-border/40 p-2 rounded text-[10px] whitespace-pre-wrap font-mono max-h-60 overflow-auto">
                        {open.user_prompt}
                      </pre>
                    </div>
                  )}
                  {open.output && (
                    <div>
                      <div className="text-[10px] text-muted-foreground mb-1">Output</div>
                      <pre className="bg-muted/30 border border-border/40 p-2 rounded text-[10px] whitespace-pre-wrap font-mono max-h-96 overflow-auto">
                        {open.output}
                      </pre>
                    </div>
                  )}
                </div>
              </ScrollArea>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-3">
      <div className="text-[10px] text-muted-foreground w-24 shrink-0 pt-0.5">{label}</div>
      <div className={"flex-1 break-all " + (mono ? "font-mono" : "")}>{value}</div>
    </div>
  );
}
