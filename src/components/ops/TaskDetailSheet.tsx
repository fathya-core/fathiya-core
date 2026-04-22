import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StatusBadge } from "./StatusBadge";
import { OwnerBadges } from "./OwnerBadges";
import { priorityStars, TASKS, type Task } from "@/lib/ops/tasks";
import { FileJson, FileText, Workflow } from "lucide-react";

interface TaskDetailSheetProps {
  task: Task | null;
  onClose: () => void;
}

const KIND_ICON = { json: FileJson, md: FileText, yaml: FileJson, workflow: Workflow } as const;

export function TaskDetailSheet({ task, onClose }: TaskDetailSheetProps) {
  return (
    <Sheet open={!!task} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="left" className="w-full sm:max-w-md overflow-hidden flex flex-col">
        {task && (
          <>
            <SheetHeader className="text-right">
              <div className="flex items-center gap-2 justify-end mb-1">
                {priorityStars(task.priority) && (
                  <span className="text-xs text-amber-400">{priorityStars(task.priority)}</span>
                )}
                <span className="font-mono text-[10px] text-muted-foreground">{task.id}</span>
                <span className="font-mono text-[10px] text-muted-foreground/60">·</span>
                <span className="font-mono text-[10px] text-muted-foreground/60">{task.code}</span>
              </div>
              <SheetTitle className="text-right text-base">{task.title}</SheetTitle>
              <SheetDescription className="text-right text-xs leading-relaxed">
                {task.description}
              </SheetDescription>
            </SheetHeader>

            <ScrollArea className="flex-1 -mx-6 px-6 mt-4">
              <div className="space-y-5 pb-6">
                <Field label="الحالة">
                  <StatusBadge status={task.status} />
                </Field>

                <Field label="المالكون">
                  <OwnerBadges owners={task.owners} />
                </Field>

                {task.depends_on.length > 0 && (
                  <Field label="يعتمد على">
                    <div className="flex flex-wrap gap-1.5">
                      {task.depends_on.map((depId) => {
                        const dep = TASKS.find((t) => t.id === depId);
                        return (
                          <span
                            key={depId}
                            className="inline-flex items-center gap-1 rounded border border-border/60 bg-muted/30 px-2 py-0.5 text-[10px]"
                          >
                            <span className="font-mono text-muted-foreground">{depId}</span>
                            {dep && <span className="text-foreground">{dep.title}</span>}
                          </span>
                        );
                      })}
                    </div>
                  </Field>
                )}

                <Field label="المخرجات الدائمة المتوقعة">
                  <div className="space-y-1.5">
                    {task.artifacts.map((a) => {
                      const Icon = KIND_ICON[a.kind];
                      return (
                        <div
                          key={a.path}
                          className="flex items-start gap-2 rounded border border-border/50 bg-muted/20 p-2"
                        >
                          <Icon className="h-3.5 w-3.5 text-primary mt-0.5 shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="font-mono text-[10px] text-foreground break-all">
                              artifacts/{a.path}
                            </div>
                            <div className="text-[10px] text-muted-foreground mt-0.5">
                              {a.description}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </Field>

                {task.notes && (
                  <Field label="ملاحظات">
                    <p className="text-xs text-muted-foreground leading-relaxed bg-amber-500/5 border border-amber-500/20 rounded p-2">
                      {task.notes}
                    </p>
                  </Field>
                )}

                <div className="rounded border border-dashed border-border/60 bg-muted/10 p-3 text-[10px] text-muted-foreground leading-relaxed">
                  <strong className="text-foreground/80">قاعدة الإغلاق:</strong> هذه المهمة لا
                  تُحسب <code className="font-mono text-emerald-400">done</code> إلا بعد نشر كل
                  الـ artifacts أعلاه تحت <code className="font-mono">artifacts/</code> وتسجيلها
                  في <code className="font-mono">_index.json</code>.
                </div>
              </div>
            </ScrollArea>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="text-right">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70 mb-1.5">
        {label}
      </div>
      {children}
    </div>
  );
}
