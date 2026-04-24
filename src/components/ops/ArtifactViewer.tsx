import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Loader2, Copy, Check, FileText } from "lucide-react";
import { toast } from "sonner";

interface ArtifactViewerProps {
  path: string | null;
  onClose: () => void;
}

export function ArtifactViewer({ path, onClose }: ArtifactViewerProps) {
  const [content, setContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!path) return;
    setLoading(true);
    setContent("");
    fetch("/api/artifacts/read", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: path.replace(/^artifacts\//, "") }),
    })
      .then((r) => r.json())
      .then((data: { ok?: boolean; content?: string; error?: string }) => {
        if (data.ok && data.content) setContent(data.content);
        else toast.error(data.error ?? "تعذّر القراءة");
      })
      .catch((e) => toast.error(String(e)))
      .finally(() => setLoading(false));
  }, [path]);

  const copy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const isJson = path?.endsWith(".json");
  let pretty = content;
  if (isJson && content) {
    try {
      pretty = JSON.stringify(JSON.parse(content), null, 2);
    } catch {
      // leave as-is
    }
  }

  return (
    <Sheet open={!!path} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="left" className="w-full sm:max-w-2xl flex flex-col" dir="rtl">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2 text-sm">
            <FileText className="h-4 w-4 text-primary" />
            <span className="font-mono text-xs">{path}</span>
          </SheetTitle>
        </SheetHeader>
        <div className="flex items-center justify-between mt-3">
          <span className="text-[10px] text-muted-foreground">
            {loading ? "جارِ التحميل…" : `${content.length} حرف`}
          </span>
          <Button size="sm" variant="outline" onClick={copy} disabled={!content} className="h-7 text-[10px]">
            {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
            نسخ
          </Button>
        </div>
        <ScrollArea className="flex-1 mt-3 rounded border border-border/40 bg-muted/20">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <pre className="p-3 text-[11px] font-mono leading-relaxed whitespace-pre-wrap break-all" dir="ltr">
              {pretty}
            </pre>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
