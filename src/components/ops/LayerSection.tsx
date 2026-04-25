import { TaskCard } from "./TaskCard";
import { tasksByLayer, type Layer, type LayerId, type Task } from "@/lib/ops/tasks";
import { useArtifactIndex } from "@/hooks/use-artifact-index";
import { Shield, Users, Search, Cpu, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

interface LayerSectionProps {
  layer: Layer;
  ownerFilter: string;
  onOpenTask: (task: Task) => void;
  onViewArtifact?: (path: string) => void;
}

const LAYER_ICON: Record<LayerId, React.ElementType> = {
  A: Shield,
  B: Users,
  C: Search,
  D: Cpu,
  E: BookOpen,
};

const LAYER_COLOR: Record<LayerId, { bar: string; icon: string; bg: string }> = {
  A: { bar: "bg-emerald-500", icon: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  B: { bar: "bg-sky-500", icon: "text-sky-400", bg: "bg-sky-500/10 border-sky-500/20" },
  C: { bar: "bg-amber-500", icon: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
  D: { bar: "bg-teal-500", icon: "text-teal-400", bg: "bg-teal-500/10 border-teal-500/20" },
  E: { bar: "bg-rose-500", icon: "text-rose-400", bg: "bg-rose-500/10 border-rose-500/20" },
};

export function LayerSection({ layer, ownerFilter, onOpenTask, onViewArtifact }: LayerSectionProps) {
  const all = tasksByLayer(layer.id);
  const tasks = ownerFilter === "All" ? all : all.filter((t) => t.owners.includes(ownerFilter as never));
  const { isDone } = useArtifactIndex();

  const total = all.length;
  const done = all.filter(
    (t) => t.status === "done" || isDone(t.id, t.artifacts.map((a) => a.path)),
  ).length;
  const pct = total ? Math.round((done / total) * 100) : 0;

  const Icon = LAYER_ICON[layer.id];
  const colors = LAYER_COLOR[layer.id];

  return (
    <section className="mb-10 animate-fade-in-up">
      <div className="mb-5">
        <div className="flex items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <div className={cn("flex h-8 w-8 items-center justify-center rounded-lg border", colors.bg)}>
              <Icon className={cn("h-4 w-4", colors.icon)} />
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="font-mono text-xs text-muted-foreground/80">[{layer.id}]</span>
                <h2 className="text-base font-bold text-foreground">{layer.name}</h2>
              </div>
              <span className="text-[11px] text-muted-foreground">{layer.subtitle}</span>
            </div>
          </div>
          <div className="text-left">
            <span className="font-mono text-xs font-semibold text-foreground">
              {done}<span className="text-muted-foreground/60">/{total}</span>
            </span>
            <span className="font-mono text-[10px] text-muted-foreground mr-1.5">{pct}%</span>
          </div>
        </div>
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted/40">
          <div
            className={cn("h-full rounded-full transition-all duration-700 ease-out", colors.bar, pct > 0 && pct < 100 && "progress-bar-animated")}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {tasks.length === 0 ? (
        <p className="text-xs text-muted-foreground/60 italic px-2 py-4">
          لا توجد مهام تطابق الفلتر في هذه الطبقة.
        </p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {tasks.map((task, i) => (
            <div key={task.id} className={cn("animate-fade-in-up", `stagger-${Math.min(i + 1, 5)}`)}>
              <TaskCard task={task} onOpen={onOpenTask} onViewArtifact={onViewArtifact} />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
