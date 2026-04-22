import { useEffect, useState } from "react";
import { Workflow, RefreshCw, ExternalLink, Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

interface WfState {
  id: string;
  name: string;
  active: boolean;
  updatedAt?: string;
  lastExecution?: {
    id: string;
    status: string;
    startedAt: string;
    finished: boolean;
  } | null;
}

export function N8nStatusPanel() {
  const [data, setData] = useState<{ configured: boolean; workflows: WfState[]; snapshot?: WfState[]; message?: string } | null>(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/n8n/workflows");
      const j = await r.json();
      setData(j);
    } catch (e) {
      setData({ configured: false, workflows: [], message: String(e) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const list = data?.configured ? data.workflows : data?.snapshot ?? [];

  return (
    <Card className="border-rose-500/20 bg-rose-500/5 p-4 mb-6">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded bg-rose-500/15 border border-rose-500/30">
            <Workflow className="h-3.5 w-3.5 text-rose-300" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-foreground">n8n Bridge</h3>
            <p className="text-[10px] text-muted-foreground">
              {data?.configured
                ? "متصل مباشرة بـ n8n REST API"
                : "وضع snapshot — أضف N8N_BASE_URL و N8N_API_KEY للجسر المباشر"}
            </p>
          </div>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={load}
          disabled={loading}
          className="h-7 px-2 text-[10px]"
        >
          {loading ? <Loader2 className="h-3 w-3 animate-spin" /> : <RefreshCw className="h-3 w-3" />}
          تحديث
        </Button>
      </div>

      {data?.message && (
        <p className="text-[10px] text-amber-300/80 mb-2 leading-relaxed">{data.message}</p>
      )}

      <div className="grid gap-1.5 sm:grid-cols-2">
        {list.map((wf) => (
          <div
            key={wf.id}
            className="flex items-center justify-between gap-2 rounded border border-border/50 bg-card/50 px-2 py-1.5"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span
                  className={
                    "h-1.5 w-1.5 rounded-full " +
                    (wf.active ? "bg-emerald-400 animate-pulse" : "bg-muted-foreground/40")
                  }
                />
                <span className="text-[11px] font-medium truncate">{wf.name}</span>
              </div>
              {wf.lastExecution && (
                <div className="text-[9px] text-muted-foreground mt-0.5 font-mono truncate">
                  last: {wf.lastExecution.status} · {new Date(wf.lastExecution.startedAt).toLocaleString("ar")}
                </div>
              )}
            </div>
            <a
              href={`https://app.n8n.cloud/workflow/${wf.id}`}
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-foreground"
              onClick={(e) => e.stopPropagation()}
            >
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        ))}
      </div>
    </Card>
  );
}
