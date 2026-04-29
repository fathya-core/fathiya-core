import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card } from "@/components/ui/card";
import { LayerSection } from "@/components/ops/LayerSection";
import { TaskDetailSheet } from "@/components/ops/TaskDetailSheet";
import { N8nStatusPanel } from "@/components/ops/N8nStatusPanel";
import { SecurityToolsPanel } from "@/components/ops/SecurityToolsPanel";
import { RunAllButton } from "@/components/ops/RunAllButton";
import { ArtifactViewer } from "@/components/ops/ArtifactViewer";
import { Toaster } from "@/components/ui/sonner";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useArtifactIndex } from "@/hooks/use-artifact-index";
import {
  LAYERS,
  TASKS,
  type LayerId,
  type Owner,
  type Task,
} from "@/lib/ops/tasks";
import { Activity, Database, Sparkles, CircleCheck as CheckCircle2, Clock, TriangleAlert as AlertTriangle, TrendingUp, Shield } from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
} from "recharts";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "FATHIYA Ops Console — Subscriptions Drain" },
      {
        name: "description",
        content:
          "لوحة تشغيل الـ Task Stack لاستنزاف الاشتراكات المؤقتة وبناء أصول دائمة فوق نواة فتحية الأمنية.",
      },
    ],
  }),
  component: OpsConsole,
});

const OWNERS: Array<"All" | Owner> = ["All", "Claude", "GPT", "Perplexity", "Manus", "n8n", "Zapier"];

const LAYER_CHART_COLORS: Record<LayerId, string> = {
  A: "#34d399",
  B: "#38bdf8",
  C: "#fbbf24",
  D: "#2dd4bf",
  E: "#fb7185",
};

function OpsConsole() {
  const [layerTab, setLayerTab] = useState<"All" | LayerId>("All");
  const [ownerFilter, setOwnerFilter] = useState<"All" | Owner>("All");
  const [openTask, setOpenTask] = useState<Task | null>(null);
  const [viewArtifact, setViewArtifact] = useState<string | null>(null);
  const { idx, isDone } = useArtifactIndex();

  const visibleLayers = layerTab === "All" ? LAYERS : LAYERS.filter((l) => l.id === layerTab);

  const overall = useMemo(() => {
    const total = TASKS.length;
    const done = TASKS.filter(
      (t) => t.status === "done" || isDone(t.id, t.artifacts.map((a) => a.path)),
    ).length;
    const inProgress = TASKS.filter((t) => t.status === "in_progress").length;
    const highPriority = TASKS.filter((t) => t.priority === 3).length;
    return { done, total, pct: total ? Math.round((done / total) * 100) : 0, inProgress, highPriority };
  }, [isDone]);

  const ownerCounts = useMemo(() => {
    const m = new Map<Owner, number>();
    TASKS.forEach((t) => t.owners.forEach((o) => m.set(o, (m.get(o) ?? 0) + 1)));
    return m;
  }, []);

  const layerChartData = useMemo(() => {
    return LAYERS.map((l) => {
      const tasks = TASKS.filter((t) => t.layer === l.id);
      const done = tasks.filter(
        (t) => t.status === "done" || isDone(t.id, t.artifacts.map((a) => a.path)),
      ).length;
      return { name: l.name, id: l.id, value: tasks.length, done };
    });
  }, [isDone]);

  return (
    <TooltipProvider delayDuration={300}>
      <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
        {/* Top bar */}
        <header className="sticky top-0 z-30 border-b border-border/50 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30">
                  <Shield className="h-4.5 w-4.5 text-emerald-400" />
                </div>
                <div>
                  <h1 className="text-sm font-bold tracking-tight">FATHIYA Ops Console</h1>
                  <p className="text-[10px] text-muted-foreground leading-tight">
                    وضع استنزاف الاشتراكات -- كل مهمة = artifact دائم
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <RunAllButton index={idx} />
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link
                      to="/ai-console"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-3 py-1.5 text-[11px] font-medium text-primary hover:bg-primary/20 transition-colors duration-150"
                    >
                      <Sparkles className="h-3.5 w-3.5" />
                      AI Console
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent>ملعب توليد الـ Artifacts عبر AI</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Link
                      to="/ai-runs"
                      className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30 px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors duration-150"
                    >
                      <Activity className="h-3.5 w-3.5" />
                      Runs
                    </Link>
                  </TooltipTrigger>
                  <TooltipContent>سجل استدعاءات AI</TooltipContent>
                </Tooltip>
                <span className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-[11px] font-medium text-emerald-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Drain Mode
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Status strip */}
        <div className="border-b border-border/40 bg-card/30">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px]">
            <span className="inline-flex items-center gap-1.5 text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              bridge
              <span className="text-muted-foreground">: 6/6 smoke -- 4/4 control</span>
            </span>
            <span className="text-muted-foreground/50">--</span>
            <span className="inline-flex items-center gap-1.5 text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
              wrapper + bridge ready
            </span>
            <span className="text-muted-foreground/50">--</span>
            <span className="inline-flex items-center gap-1.5 text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
              artifacts: {idx?.tasks.length ?? 0} saved
            </span>
            <span className="text-muted-foreground/50 mr-auto" />
            <span className="inline-flex items-center gap-1.5 text-muted-foreground">
              <Database className="h-3 w-3" />
              artifacts/_index.json
            </span>
          </div>
        </div>

        <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <StatsCard
              label="الإنجاز الكلي"
              value={`${overall.pct}%`}
              sub={`${overall.done} من ${overall.total}`}
              icon={TrendingUp}
              accent="text-emerald-400"
              bgAccent="bg-emerald-500/10 border-emerald-500/20"
            />
            <StatsCard
              label="مكتملة"
              value={String(overall.done)}
              sub="مهمة"
              icon={CheckCircle2}
              accent="text-emerald-400"
              bgAccent="bg-emerald-500/10 border-emerald-500/20"
            />
            <StatsCard
              label="قيد التنفيذ"
              value={String(overall.inProgress)}
              sub="مهمة"
              icon={Clock}
              accent="text-sky-400"
              bgAccent="bg-sky-500/10 border-sky-500/20"
            />
            <StatsCard
              label="أولوية عالية"
              value={String(overall.highPriority)}
              sub="★★★"
              icon={AlertTriangle}
              accent="text-amber-400"
              bgAccent="bg-amber-500/10 border-amber-500/20"
            />
          </div>

          {/* Chart + N8n side by side on desktop */}
          <div className="grid md:grid-cols-2 gap-4 mb-6">
            <Card className="p-4 bg-card/40 border-border/60 animate-fade-in-up">
              <h3 className="text-xs font-semibold text-foreground mb-3">توزيع المهام حسب الطبقة</h3>
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={layerChartData}
                      cx="50%"
                      cy="50%"
                      innerRadius={45}
                      outerRadius={70}
                      paddingAngle={3}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {layerChartData.map((entry) => (
                        <Cell key={entry.id} fill={LAYER_CHART_COLORS[entry.id as LayerId]} fillOpacity={0.85} />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: "oklch(0.208 0.042 265.755)",
                        border: "1px solid oklch(1 0 0 / 10%)",
                        borderRadius: "8px",
                        fontSize: "11px",
                        direction: "rtl",
                      }}
                      formatter={(value: number, _name: string, props: { payload: { name: string; done: number } }) => [
                        `${value} مهمة (${props.payload.done} مكتملة)`,
                        props.payload.name,
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2">
                {layerChartData.map((l) => (
                  <div key={l.id} className="flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span
                      className="h-2 w-2 rounded-sm"
                      style={{ backgroundColor: LAYER_CHART_COLORS[l.id as LayerId] }}
                    />
                    {l.id}: {l.name.split(" ")[0]}
                  </div>
                ))}
              </div>
            </Card>

            <div className="animate-fade-in-up stagger-2">
              <N8nStatusPanel />
            </div>

            <div className="animate-fade-in-up stagger-3">
              <SecurityToolsPanel />
            </div>
          </div>

          {/* Filters */}
          <div className="mb-6 space-y-3 animate-fade-in-up">
            <Tabs value={layerTab} onValueChange={(v) => setLayerTab(v as "All" | LayerId)}>
              <TabsList className="h-auto flex-wrap bg-muted/30 p-1">
                <TabsTrigger value="All" className="text-xs data-[state=active]:bg-background">
                  كل الطبقات
                </TabsTrigger>
                {LAYERS.map((l) => (
                  <TabsTrigger key={l.id} value={l.id} className="text-xs data-[state=active]:bg-background">
                    {l.id} -- {l.name}
                  </TabsTrigger>
                ))}
              </TabsList>
            </Tabs>

            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[10px] text-muted-foreground ml-1">المالك:</span>
              {OWNERS.map((o) => {
                const active = ownerFilter === o;
                const count = o === "All" ? TASKS.length : ownerCounts.get(o as Owner) ?? 0;
                return (
                  <button
                    key={o}
                    onClick={() => setOwnerFilter(o)}
                    className={
                      "inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-[10px] font-medium transition-all duration-150 " +
                      (active
                        ? "border-primary/50 bg-primary/15 text-primary shadow-sm"
                        : "border-border/60 bg-muted/20 text-muted-foreground hover:border-primary/30 hover:text-foreground")
                    }
                  >
                    {o}
                    <span className="font-mono opacity-60">{count}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Layers */}
          {visibleLayers.map((layer) => (
            <LayerSection
              key={layer.id}
              layer={layer}
              ownerFilter={ownerFilter}
              onOpenTask={setOpenTask}
              onViewArtifact={setViewArtifact}
            />
          ))}

          <footer className="mt-10 pt-6 border-t border-border/40 text-center animate-fade-in">
            <p className="text-[10px] text-muted-foreground/70 leading-relaxed">
              القاعدة الحاكمة: أي مهمة مع الاشتراكات المؤقتة يجب أن تنتج Artifact دائم تحت{" "}
              <code className="font-mono text-foreground/70">artifacts/</code>
            </p>
          </footer>
        </main>

        <TaskDetailSheet task={openTask} onClose={() => setOpenTask(null)} />
        <ArtifactViewer path={viewArtifact} onClose={() => setViewArtifact(null)} />
        <Toaster position="bottom-left" />
      </div>
    </TooltipProvider>
  );
}

function StatsCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  bgAccent,
}: {
  label: string;
  value: string;
  sub: string;
  icon: React.ElementType;
  accent: string;
  bgAccent: string;
}) {
  return (
    <Card className="p-4 bg-card/40 border-border/60 animate-fade-in-up hover:bg-card/60 transition-colors duration-200">
      <div className="flex items-start justify-between mb-2">
        <span className="text-[10px] text-muted-foreground font-medium">{label}</span>
        <div className={`flex h-7 w-7 items-center justify-center rounded-lg border ${bgAccent}`}>
          <Icon className={`h-3.5 w-3.5 ${accent}`} />
        </div>
      </div>
      <div className="font-mono text-2xl font-bold text-foreground leading-none mb-1">{value}</div>
      <span className="text-[10px] text-muted-foreground">{sub}</span>
    </Card>
  );
}
