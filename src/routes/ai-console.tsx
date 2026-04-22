import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, Loader2, Save, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AI_MODELS, DEFAULT_GPT_MODEL } from "@/lib/ai/models";
import { toast } from "sonner";

export const Route = createFileRoute("/ai-console")({
  head: () => ({
    meta: [
      { title: "AI Console — FATHIYA" },
      { name: "description", content: "ملعب Lovable AI الحر — جرّب prompts واحفظها كـ artifacts." },
    ],
  }),
  component: AiConsole,
});

function AiConsole() {
  const [model, setModel] = useState<string>(DEFAULT_GPT_MODEL);
  const [system, setSystem] = useState(
    "أنت محرك توليد artifacts نهائية. أرجع المحتوى المطلوب فقط دون مقدمات.",
  );
  const [user, setUser] = useState("");
  const [savePath, setSavePath] = useState("");
  const [saveKind, setSaveKind] = useState<"json" | "md">("md");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);

  const run = async () => {
    if (!user.trim()) {
      toast.error("اكتب prompt");
      return;
    }
    setLoading(true);
    setOutput("");
    try {
      const r = await fetch("/api/ai/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model,
          systemOverride: system,
          userOverride: user,
          saveAs: savePath || undefined,
          saveKind,
        }),
      });
      const j = await r.json();
      if (!r.ok || !j.ok) {
        toast.error(j.error ?? `فشل ${r.status}`);
        setOutput(JSON.stringify(j, null, 2));
        return;
      }
      setOutput(j.content);
      if (j.saved) toast.success(`حُفظ في ${j.savedPath}`);
      else toast.success("تم — لم يُحفظ (أضف saveAs للحفظ)");
    } catch (e) {
      toast.error(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border/50 bg-background/85 backdrop-blur sticky top-0 z-30">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h1 className="text-sm font-bold">AI Console</h1>
            <span className="text-[10px] text-muted-foreground">· Lovable AI Gateway</span>
          </div>
          <Link
            to="/"
            className="text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1"
          >
            <ArrowRight className="h-3 w-3" /> Ops Console
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 sm:px-6 py-6 grid gap-4 md:grid-cols-2">
        <Card className="p-4 space-y-3">
          <div>
            <label className="text-[10px] text-muted-foreground mb-1 block">Model</label>
            <Select value={model} onValueChange={setModel}>
              <SelectTrigger className="h-8 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {AI_MODELS.map((m) => (
                  <SelectItem key={m.id} value={m.id} className="text-xs">
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-[10px] text-muted-foreground mb-1 block">System</label>
            <Textarea
              value={system}
              onChange={(e) => setSystem(e.target.value)}
              rows={3}
              className="text-xs font-mono resize-none"
            />
          </div>

          <div>
            <label className="text-[10px] text-muted-foreground mb-1 block">Prompt</label>
            <Textarea
              value={user}
              onChange={(e) => setUser(e.target.value)}
              rows={10}
              placeholder="اكتب طلبك… (مثلاً: صمّم routing matrix لمهام الكريبتو)"
              className="text-xs font-mono resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground mb-1 block">
                حفظ في (اختياري)
              </label>
              <Input
                value={savePath}
                onChange={(e) => setSavePath(e.target.value)}
                placeholder="prompts/router.md"
                className="h-8 text-xs font-mono"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground mb-1 block">النوع</label>
              <Select value={saveKind} onValueChange={(v) => setSaveKind(v as "json" | "md")}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="md">Markdown</SelectItem>
                  <SelectItem value="json">JSON</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            onClick={run}
            disabled={loading}
            className="w-full gap-2"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            تشغيل {savePath && "+ حفظ"}
          </Button>
        </Card>

        <Card className="p-4">
          <div className="text-[10px] text-muted-foreground mb-2 flex items-center justify-between">
            <span>Output</span>
            {output && (
              <button
                onClick={() => {
                  navigator.clipboard.writeText(output);
                  toast.success("نُسخ");
                }}
                className="hover:text-foreground"
              >
                نسخ
              </button>
            )}
          </div>
          <pre className="text-[11px] font-mono whitespace-pre-wrap break-words text-foreground/90 max-h-[600px] overflow-auto">
            {output || (loading ? "…" : "النتيجة ستظهر هنا")}
          </pre>
        </Card>
      </main>
    </div>
  );
}
