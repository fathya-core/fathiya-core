import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/lib/ops/tasks";

const LABELS: Record<TaskStatus, string> = {
  todo: "بانتظار",
  in_progress: "قيد التنفيذ",
  done: "مكتملة",
};

const STYLES: Record<TaskStatus, string> = {
  todo: "bg-muted text-muted-foreground border-border",
  in_progress: "bg-primary/15 text-primary border-primary/30",
  done: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
};

export function StatusBadge({ status, className }: { status: TaskStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-medium tracking-wide",
        STYLES[status],
        className,
      )}
    >
      {LABELS[status]}
    </span>
  );
}
