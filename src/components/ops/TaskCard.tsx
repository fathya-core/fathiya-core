import { ChevronLeft, FileJson, FileText, Workflow } from "lucide-react";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "./StatusBadge";
import { OwnerBadges } from "./OwnerBadges";
import { priorityStars, type Task } from "@/lib/ops/tasks";
import { cn } from "@/lib/utils";

interface TaskCardProps {
  task: Task;
  onOpen: (task: Task) => void;
}

const KIND_ICON = {
  json: FileJson,
  md: FileText,
  yaml: FileJson,
  workflow: Workflow,
} as const;

export function TaskCard({ task, onOpen }: TaskCardProps) {
  const stars = priorityStars(task.priority);
  return (
    <Card
      className={cn(
        "group cursor-pointer border-border/60 bg-card/40 p-4 transition-all hover:border-primary/40 hover:bg-card/70",
        task.status === "done" && "opacity-70",
      )}
      onClick={() => onOpen(task)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="font-mono text-[10px] text-muted-foreground">{task.id}</span>
            <span className="font-mono text-[10px] text-muted-foreground/60">{task.code}</span>
            {stars && <span className="text-[10px] text-amber-400 tracking-tight">{stars}</span>}
          </div>
          <h3 className="text-sm font-semibold text-foreground leading-snug mb-2">
            {task.title}
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2 mb-3">
            {task.description}
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={task.status} />
            <OwnerBadges owners={task.owners} />
          </div>
        </div>
        <ChevronLeft className="h-4 w-4 text-muted-foreground/50 transition-transform group-hover:-translate-x-0.5 group-hover:text-primary" />
      </div>

      {task.artifacts.length > 0 && (
        <div className="mt-3 pt-3 border-t border-border/40">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-muted-foreground/70 ml-1">Artifacts:</span>
            {task.artifacts.map((a) => {
              const Icon = KIND_ICON[a.kind];
              return (
                <span
                  key={a.path}
                  className="inline-flex items-center gap-1 rounded bg-muted/40 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground"
                >
                  <Icon className="h-2.5 w-2.5" />
                  {a.path.split("/").pop()}
                </span>
              );
            })}
          </div>
        </div>
      )}
    </Card>
  );
}
