import { useState } from "react";
import { Play, Loader2, CheckCircle2, AlertCircle, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { TASKS } from "@/lib/ops/tasks";
import { TASK_PROMPTS } from "@/lib/ai/prompts";
import { refreshArtifactIndex, type ArtifactIndex } from "@/hooks/use-artifact-index";

interface RunAllButtonProps {
  index: ArtifactIndex | null;
}

// المهام التي لها prompt جاهز ويمكن توليدها تلقائياً
function getRunnableTasks() {
  return TASKS.filter((t) => TASK_PROMPTS[t.id]).map((t) => t.id);
}

function isTaskDone(taskId: string, idx: ArtifactIndex | null): boolean {
  const task = TASKS.find((t) => t.id === taskId);
  if (!task || task.artifacts.length === 0) return false;
  const have = new Set((idx?.tasks ?? []).filter((t) => t.task_id === taskId).map((t) => t.path));
  return task.artifacts.every((a) => have.has(`artifacts/${a.path}`) || have.has(a.path));
}

function depsSatisfied(taskId: string, idx: ArtifactIndex | null): boolean {
  const task = TASKS.find((t) => t.id === taskId);
  if (!task) return false;
  return task.depends_on.every((dep) => isTaskDone(dep, idx));
}

export function RunAllButton({ index }: RunAllButtonProps) {
  const [state, setState] = useState<"idle" | "running" | "ok" | "err">("idle");
  const [progress, setProgress] = useState({ done: 0, total: 0, current: "" });
  const [stopRequested, setStopRequested] = useState(false);

  const runOne = async (taskId: string): Promise<{ ok: boolean; error?: string }> => {
    const startedAtIso = new Date().toISOString();
    try {
      const r = await fetch("/api/ai/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId }),
      });

      if (r.status === 504) {
        // poll for up to 60s
        for (let i = 0; i < 20; i++) {
          await new Promise((res) => setTimeout(res, 3000));
          const probe = await fetch("/api/artifacts/", { cache: "no-store" });
          const probeData = (await probe.json()) as ArtifactIndex;
          const recent = probeData.tasks.find(
            (t) => t.task_id === taskId && t.saved_at >= startedAtIso,
          );
          if (recent) return { ok: true };
        }
        return { ok: false, error: "504 + لم يكتمل خلال 60s" };
      }

      const data = (await r.json()) as { ok?: boolean; error?: string };
      if (!r.ok || !data.ok) return { ok: false, error: data.error ?? `HTTP ${r.status}` };
      return { ok: true };
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  };

  const handleRun = async () => {
    setState("running");
    setStopRequested(false);

    const runnable = getRunnableTasks();
    // ابن قائمة المهام غير المكتملة، بترتيب يحترم depends_on
    const queue: string[] = [];
    let currentIdx = index;
    let safety = 50;
    while (safety-- > 0) {
      const next = runnable.find(
        (id) =>
          !queue.includes(id) &&
          !isTaskDone(id, currentIdx) &&
          depsSatisfied(id, currentIdx),
      );
      if (!next) break;
      queue.push(next);
      // simulate that "next" will become done so deps unlock
      const fakeEntry = {
        task_id: next,
        path: `artifacts/${TASK_PROMPTS[next].artifactPath}`,
        kind: TASK_PROMPTS[next].artifactKind,
        saved_at: new Date().toISOString(),
        bytes: 0,
      };
      currentIdx = {
        version: 1,
        tasks: [...(currentIdx?.tasks ?? []), fakeEntry],
      };
    }

    if (queue.length === 0) {
      toast.success("كل المهام القابلة للتشغيل مكتملة ✓");
      setState("ok");
      return;
    }

    setProgress({ done: 0, total: queue.length, current: queue[0] });
    toast.info(`بدء تنفيذ ${queue.length} مهام بالتسلسل…`, { duration: 4000 });

    let okCount = 0;
    let errCount = 0;
    for (let i = 0; i < queue.length; i++) {
      if (stopRequested) {
        toast.warning("تم الإيقاف يدوياً.");
        break;
      }
      const taskId = queue[i];
      setProgress({ done: i, total: queue.length, current: taskId });
      const result = await runOne(taskId);
      if (result.ok) {
        okCount++;
        toast.success(`✓ ${taskId}`);
      } else {
        errCount++;
        toast.error(`✗ ${taskId}: ${result.error}`);
      }
      await refreshArtifactIndex();
      // small breath between calls
      await new Promise((r) => setTimeout(r, 800));
    }

    setProgress({ done: queue.length, total: queue.length, current: "" });
    if (errCount === 0) {
      setState("ok");
      toast.success(`اكتمل التشغيل: ${okCount}/${queue.length} ✓`);
    } else {
      setState("err");
      toast.error(`اكتمل مع أخطاء: ${okCount} نجاح · ${errCount} فشل`);
    }
  };

  if (state === "running") {
    return (
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          onClick={() => setStopRequested(true)}
          className="h-7 px-2 text-[10px] gap-1 border-rose-500/40 hover:bg-rose-500/10"
        >
          <Square className="h-3 w-3 text-rose-400" />
          إيقاف
        </Button>
        <span className="inline-flex items-center gap-1.5 rounded border border-primary/40 bg-primary/10 px-2 py-1 text-[10px] text-primary">
          <Loader2 className="h-3 w-3 animate-spin" />
          {progress.current} ({progress.done}/{progress.total})
        </span>
      </div>
    );
  }

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={handleRun}
      className="h-7 px-2 text-[10px] gap-1 border-primary/40 hover:bg-primary/10"
    >
      {state === "ok" ? (
        <CheckCircle2 className="h-3 w-3 text-emerald-400" />
      ) : state === "err" ? (
        <AlertCircle className="h-3 w-3 text-rose-400" />
      ) : (
        <Play className="h-3 w-3 text-primary" />
      )}
      تشغيل الكل
    </Button>
  );
}
