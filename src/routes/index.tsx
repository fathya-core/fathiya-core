import { createFileRoute, Link } from "@tanstack/react-router";
import { useMemo, useState } from "react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LayerSection } from "@/components/ops/LayerSection";
import { TaskDetailSheet } from "@/components/ops/TaskDetailSheet";
import { N8nStatusPanel } from "@/components/ops/N8nStatusPanel";
import { RunAllButton } from "@/components/ops/RunAllButton";
import { ArtifactViewer } from "@/components/ops/ArtifactViewer";
import { Toaster } from "@/components/ui/sonner";
import { useArtifactIndex } from "@/hooks/use-artifact-index";
import {
  LAYERS,
  TASKS,
  type LayerId,
  type Owner,
  type Task,
} from "@/lib/ops/tasks";
import { Activity, Database, Sparkles } from "lucide-react";

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

function OpsConsole() {
  const [layerTab, setLayerTab] = useState<"All" | LayerId>("All");
  const [ownerFilter, setOwnerFilter] = useState<"All" | Owner>("All");
  const [openTask, setOpenTask] = useState<Task | null>(null);
  const [viewArtifact, setViewArtifact] = useState<string | null>(null);
  const { idx, isDone } = useArtifactIndex();

  const visibleLayers = layerTab === "All" ? LAYERS : LAYERS.filter((l) => l.id === layerTab);

  // dynamic overall progress reading from _index.json
  const overall = useMemo(() => {
    const total = TASKS.length;
    const done = TASKS.filter(
      (t) => t.status === "done" || isDone(t.id, t.artifacts.map((a) => a.path)),
    ).length;
    return { done, total, pct: total ? Math.round((done / total) * 100) : 0 };
  }, [isDone]);

  const ownerCounts = useMemo(() => {
    const m = new Map<Owner, number>();
    TASKS.forEach((t) => t.owners.forEach((o) => m.set(o, (m.get(o) ?? 0) + 1)));
    return m;
  }, []);

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
      {/* Top bar */}
      <header className="sticky top-0 z-30 border-b border-border/50 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/15 text-primary border border-primary/30">
                <Activity className="h-4 w-4" />
              </div>
              <div>
                <h1 className="text-sm font-bold tracking-tight">FATHIYA Ops Console</h1>
                <p className="text-[10px] text-muted-foreground leading-tight">
                  وضع استنزاف الاشتراكات · كل مهمة = artifact دائم
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3 flex-wrap">
              <div className="text-right">
                <div className="text-[10px] text-muted-foreground">الإنجاز الكلي</div>
                <div className="font-mono text-sm font-semibold">
                  {overall.done}
                  <span className="text-muted-foreground/60">/{overall.total}</span>
                  <span className="text-primary mr-1.5">{overall.pct}%</span>
                </div>
              </div>
              <RunAllButton index={idx} />
              <Link
                to="/ai-console"
                className="inline-flex items-center gap-1 rounded border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] text-primary hover:bg-primary/20"
              >
                <Sparkles className="h-3 w-3" />
                AI Console
              </Link>
              <Link
                to="/ai-runs"
                className="inline-flex items-center gap-1 rounded border border-border/60 bg-muted/30 px-2 py-1 text-[10px] text-muted-foreground hover:text-foreground hover:border-primary/30"
              >
                <Activity className="h-3 w-3" />
                Runs
              </Link>
              <span className="inline-flex items-center gap-1.5 rounded border border-emerald-500/30 bg-emerald-500/10 px-2 py-1 text-[10px] text-emerald-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Drain Mode
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Status strip */}
      <div className="border-b border-border/40 bg-card/30">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-2.5 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px]">
          <span className="inline-flex items-center gap-1.5 text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            bridge
            <span className="text-muted-foreground">: 6/6 smoke · 4/4 control</span>
          </span>
          <span className="text-muted-foreground/50">·</span>
          <span className="inline-flex items-center gap-1.5 text-emerald-400">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            wrapper + bridge ready
          </span>
          <span className="text-muted-foreground/50">·</span>
          <span className="inline-flex items-center gap-1.5 text-amber-400">
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
            artifacts: {idx?.tasks.length ?? 0} مسجّل
          </span>
          <span className="text-muted-foreground/50 mr-auto" />
          <span className="inline-flex items-center gap-1.5 text-muted-foreground">
            <Database className="h-3 w-3" />
            artifacts/_index.json
          </span>
        </div>
      </div>

      <main className="mx-auto max-w-6xl px-4 sm:px-6 py-6">
        <N8nStatusPanel />

        {/* Filters */}
        <div className="mb-6 space-y-3">
          <Tabs value={layerTab} onValueChange={(v) => setLayerTab(v as "All" | LayerId)}>
            <TabsList className="h-auto flex-wrap">
              <TabsTrigger value="All" className="text-xs">
                كل الطبقات
              </TabsTrigger>
              {LAYERS.map((l) => (
                <TabsTrigger key={l.id} value={l.id} className="text-xs">
                  {l.id} · {l.name}
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
                    "inline-flex items-center gap-1.5 rounded border px-2 py-0.5 text-[10px] font-medium transition-colors " +
                    (active
                      ? "border-primary/50 bg-primary/15 text-primary"
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

        <footer className="mt-10 pt-6 border-t border-border/40 text-center">
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
  );
}
