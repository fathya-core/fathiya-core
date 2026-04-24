import { ChevronLeft, FileJson, FileText, Workflow, Eye } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "./StatusBadge";
import { OwnerBadges } from "./OwnerBadges";
import { GenerateButton } from "./GenerateButton";
import { priorityStars, type Task } from "@/lib/ops/tasks";
import { useArtifactIndex } from "@/hooks/use-artifact-index";
import { cn } from "@/lib/utils";

interface TaskCardProps {
  task: Task;
  onOpen: (task: Task) => void;
  onViewArtifact?: (path: string) => void;
}

const KIND_ICON = {
  json: FileJson,
  md: FileText,
  yaml: FileJson,
  workflow: Workflow,
} as const;

export function TaskCard({ task, onOpen, onViewArtifact }: TaskCardProps) {
  const stars = priorityStars(task.priority);
  const { entriesForTask, isDone } = useArtifactIndex();
  const savedEntries = entriesForTask(task.id);
  const expectedPaths = task.artifacts.map((a) => a.path);
  const taskDone = task.status === "done" || isDone(task.id, expectedPaths);
  const partial = savedEntries.length > 0 && !taskDone;

  return (
    <Card
      className={cn(
        "group cursor-pointer border-border/60 bg-card/40 p-4 transition-all hover:border-primary/40 hover:bg-card/70",
        taskDone && "border-emerald-500/30 bg-emerald-500/5",
        partial && "border-amber-500/30",
      )}
      onClick={() => onOpen(task)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-[10px] text-muted-foreground">{task.id}</span>
            <span className="font-mono text-[10px] text-muted-foreground/60">{task.code}</span>
            {stars && <span className="text-[10px] text-amber-400 tracking-tight">{stars}</span>}
            {taskDone && (
              <span className="text-[10px] text-emerald-400 font-bold">✓ done</span>
            )}
          </div>
          <h3 className="text-sm font-semibold text-foreground leading-snug mb-2">
            {task.title}
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2 mb-3">
            {task.description}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={taskDone ? "done" : task.status} />
            <OwnerBadges owners={task.owners} />
            {!taskDone && <GenerateButton taskId={task.id} />}
          </div>
        </div>
        <ChevronLeft className="h-4 w-4 text-muted-foreground/50 transition-transform group-hover:-translate-x-0.5 group-hover:text-primary" />
      </div>

      {(savedEntries.length > 0 || task.artifacts.length > 0) && (
        <div className="mt-3 pt-3 border-t border-border/40">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-muted-foreground/70 ml-1">
              {savedEntries.length > 0 ? "محفوظ:" : "متوقع:"}
            </span>
            {(savedEntries.length > 0 ? savedEntries : task.artifacts.map((a) => ({ path: a.path, kind: a.kind }))).map((a) => {
              const Icon = KIND_ICON[a.kind as keyof typeof KIND_ICON] ?? FileJson;
              const isSaved = savedEntries.some((s) => s.path === a.path || s.path === `artifacts/${a.path}`);
              return (
                <button
                  key={a.path}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (isSaved && onViewArtifact) onViewArtifact(a.path);
                  }}
                  disabled={!isSaved}
                  className={cn(
                    "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-mono transition-colors",
                    isSaved
                      ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 hover:bg-emerald-500/20 cursor-pointer"
                      : "bg-muted/40 text-muted-foreground border border-transparent",
                  )}
                  title={isSaved ? "اضغطي للعرض" : "لم يُولَّد بعد"}
                >
                  <Icon className="h-2.5 w-2.5" />
                  {a.path.split("/").pop()}
                  {isSaved && <Eye className="h-2.5 w-2.5 mr-0.5" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}
