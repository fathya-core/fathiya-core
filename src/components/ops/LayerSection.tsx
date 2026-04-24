import { Progress } from "@/components/ui/progress";
import { TaskCard } from "./TaskCard";
import { tasksByLayer, type Layer, type Task } from "@/lib/ops/tasks";
import { useArtifactIndex } from "@/hooks/use-artifact-index";

interface LayerSectionProps {
  layer: Layer;
  ownerFilter: string;
  onOpenTask: (task: Task) => void;
  onViewArtifact?: (path: string) => void;
}

export function LayerSection({ layer, ownerFilter, onOpenTask, onViewArtifact }: LayerSectionProps) {
  const all = tasksByLayer(layer.id);
  const tasks = ownerFilter === "All" ? all : all.filter((t) => t.owners.includes(ownerFilter as never));
  const { isDone } = useArtifactIndex();

  // dynamic progress: count tasks done either by status or by artifacts on disk
  const total = all.length;
  const done = all.filter(
    (t) => t.status === "done" || isDone(t.id, t.artifacts.map((a) => a.path)),
  ).length;
  const pct = total ? Math.round((done / total) * 100) : 0;

  return (
    <section className="mb-8">
      <div className="mb-4">
        <div className="flex items-baseline justify-between gap-3 mb-2">
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-xs text-primary">[{layer.id}]</span>
            <h2 className="text-base font-semibold text-foreground">{layer.name}</h2>
            <span className="text-xs text-muted-foreground">— {layer.subtitle}</span>
          </div>
          <span className="font-mono text-[11px] text-muted-foreground">
            {done}/{total}
          </span>
        </div>
        <Progress value={pct} className="h-1" />
      </div>

      {tasks.length === 0 ? (
        <p className="text-xs text-muted-foreground/60 italic px-2 py-4">
          لا توجد مهام تطابق الفلتر في هذه الطبقة.
        </p>
      ) : (
        <div className="grid gap-3 md:grid-cols-2">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onOpen={onOpenTask} onViewArtifact={onViewArtifact} />
          ))}
        </div>
      )}
    </section>
  );
}
