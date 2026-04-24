import { useState } from "react";
import { Sparkles, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { TASK_PROMPTS } from "@/lib/ai/prompts";
import { supabase } from "@/integrations/supabase/client";

// بعد 504 من Worker، نتحقق من ai_runs لمدة ~60s لمعرفة هل اكتمل التوليد فعلاً
async function pollForCompletion(
  taskId: string,
  startedAtIso: string,
  maxAttempts = 20,
  intervalMs = 3000,
): Promise<{ ok: true; savedPath: string | null } | { ok: false; error?: string } | null> {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, intervalMs));
    const { data, error } = await supabase
      .from("ai_runs")
      .select("status,saved_path,error_message,created_at")
      .eq("task_id", taskId)
      .gte("created_at", startedAtIso)
      .order("created_at", { ascending: false })
      .limit(1);
    if (error) continue;
    const row = data?.[0];
    if (!row) continue;
    if (row.status === "ok") return { ok: true, savedPath: row.saved_path };
    if (row.status === "error") return { ok: false, error: row.error_message ?? "error" };
  }
  return null;
}

interface GenerateButtonProps {
  taskId: string;
  onGenerated?: (path: string) => void;
}

export function GenerateButton({ taskId, onGenerated }: GenerateButtonProps) {
  const [state, setState] = useState<"idle" | "loading" | "ok" | "err">("idle");
  const spec = TASK_PROMPTS[taskId];
  if (!spec) return null;

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    setState("loading");
    toast.info(`توليد ${taskId} عبر Lovable AI…`, { duration: 4000 });
    try {
      const r = await fetch("/api/ai/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ taskId }),
      });

      // 504 من Worker: النموذج تجاوز 30s — لكن السجل يكتمل في الخلفية
      if (r.status === 504) {
        setState("err");
        toast.warning(
          `انتهت مهلة الاتصال (504) — قد يكون التوليد اكتمل. افحصي /ai-runs للتأكد.`,
          { duration: 8000 },
        );
        return;
      }

      const data = (await r.json()) as { ok?: boolean; savedPath?: string; error?: string };
      if (!r.ok || !data.ok) {
        setState("err");
        toast.error(data.error ?? `فشل ${r.status}`);
        return;
      }
      setState("ok");
      toast.success(`تم حفظ ${data.savedPath}`);
      onGenerated?.(data.savedPath ?? "");
    } catch (e) {
      setState("err");
      toast.error(String(e));
    }
  };

  return (
    <Button
      size="sm"
      variant="outline"
      onClick={handleClick}
      disabled={state === "loading"}
      className="h-7 px-2 text-[10px] gap-1 border-primary/40 hover:bg-primary/10"
    >
      {state === "loading" ? (
        <Loader2 className="h-3 w-3 animate-spin" />
      ) : state === "ok" ? (
        <CheckCircle2 className="h-3 w-3 text-emerald-400" />
      ) : state === "err" ? (
        <AlertCircle className="h-3 w-3 text-rose-400" />
      ) : (
        <Sparkles className="h-3 w-3 text-primary" />
      )}
      Generate
    </Button>
  );
}
