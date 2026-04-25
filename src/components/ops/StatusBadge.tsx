import { cn } from "@/lib/utils";
import type { TaskStatus } from "@/lib/ops/tasks";

const LABELS: Record<TaskStatus, string> = {
  todo: "بانتظار",
  in_progress: "قيد التنفيذ",
  done: "مكتملة",
};

const STYLES: Record<TaskStatus, string> = {
  todo: "bg-muted text-muted-foreground border-border",
  in_progress: "bg-sky-500/15 text-sky-300 border-sky-500/30",
  done: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30",
};

export function StatusBadge({ status, className }: { status: TaskStatus; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-medium tracking-wide transition-colors duration-150",
        STYLES[status],
        className,
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          status === "todo" && "bg-muted-foreground/50",
          status === "in_progress" && "bg-sky-400 animate-pulse",
          status === "done" && "bg-emerald-400",
        )}
      />
      {LABELS[status]}
    </span>
  );
}
