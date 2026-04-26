import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { Sparkles, Loader as Loader2, Save, ArrowRight, Copy, Check, Zap, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AI_MODELS, DEFAULT_MODEL, getModelProvider } from "@/lib/ai/models";
import { toast } from "sonner";

export const Route = createFileRoute("/ai-console")({
  head: () => ({
    meta: [
      { title: "AI Console — FATHIYA" },
      { name: "description", content: "ملعب FATHIYA AI — جرّب prompts واحفظها كـ artifacts." },
    ],
  }),
  component: AiConsole,
});

function AiConsole() {
  const [model, setModel] = useState<string>(DEFAULT_MODEL);
  const [system, setSystem] = useState(
    "أنت محرك توليد artifacts نهائية. أرجع المحتوى المطلوب فقط دون مقدمات.",
  );
  const [user, setUser] = useState("");
  const [savePath, setSavePath] = useState("");
  const [saveKind, setSaveKind] = useState<"json" | "md">("md");
  const [output, setOutput] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

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

  const handleCopy = async () => {
    await navigator.clipboard.writeText(output);
    setCopied(true);
    toast.success("نُسخ");
    setTimeout(() => setCopied(false), 1500);
  };

  const selectedModel = AI_MODELS.find((m) => m.id === model);

  return (
    <TooltipProvider delayDuration={300}>
      <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
        <header className="border-b border-border/50 bg-background/85 backdrop-blur sticky top-0 z-30">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-sky-500/20 to-teal-500/20 border border-sky-500/30">
                <Sparkles className="h-4 w-4 text-sky-400" />
              </div>
              <div>
                <h1 className="text-sm font-bold">AI Console</h1>
                <span className="text-[10px] text-muted-foreground">FATHIYA AI Gateway</span>
              </div>
            </div>
            <Link
              to="/"
              className="inline-flex items-center gap-1.5 rounded-lg border border-border/60 bg-muted/30 px-3 py-1.5 text-[11px] font-medium text-muted-foreground hover:text-foreground hover:border-primary/30 transition-colors duration-150"
            >
              <ArrowRight className="h-3.5 w-3.5" /> Ops Console
            </Link>
          </div>
        </header>

        <main className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-6 grid gap-5 md:grid-cols-2">
          {/* Input Panel */}
          <Card className="p-5 space-y-4 bg-card/40 border-border/60 animate-fade-in-up">
            <div className="flex items-center gap-2 mb-1">
              <Brain className="h-4 w-4 text-primary" />
              <h2 className="text-xs font-bold text-foreground">بناء الطلب</h2>
            </div>

            <div>
              <label className="text-[10px] text-muted-foreground mb-1.5 block font-medium">Model</label>
              <Select value={model} onValueChange={setModel}>
                <SelectTrigger className="h-9 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <div className="px-2 py-1 text-[9px] font-semibold text-muted-foreground uppercase tracking-wider">OpenRouter</div>
                  {AI_MODELS.filter((m) => m.provider === "openrouter").map((m) => (
                    <SelectItem key={m.id} value={m.id} className="text-xs">
                      <div className="flex items-center gap-2">
                        <span className={
                          "h-1.5 w-1.5 rounded-full " +
                          (m.tier === "premium" ? "bg-amber-400" : "bg-emerald-400")
                        } />
                        {m.label}
                      </div>
                    </SelectItem>
                  ))}
                  <div className="px-2 py-1 mt-1 text-[9px] font-semibold text-muted-foreground uppercase tracking-wider border-t border-border/40">Hugging Face</div>
                  {AI_MODELS.filter((m) => m.provider === "huggingface").map((m) => (
                    <SelectItem key={m.id} value={m.id} className="text-xs">
                      <div className="flex items-center gap-2">
                        <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                        {m.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedModel && (
                <div className="flex items-center gap-1.5 mt-1.5">
                  <span className={
                    "inline-flex items-center gap-1 text-[9px] font-medium rounded px-1.5 py-0.5 " +
                    (selectedModel.provider === "openrouter"
                      ? "bg-teal-500/10 text-teal-400 border border-teal-500/20"
                      : "bg-sky-500/10 text-sky-400 border border-sky-500/20")
                  }>
                    {selectedModel.provider === "openrouter" ? "OpenRouter" : "HuggingFace"}
                  </span>
                  <span className={
                    "inline-flex items-center gap-1 text-[9px] font-medium rounded px-1.5 py-0.5 " +
                    (selectedModel.tier === "premium"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : selectedModel.tier === "free"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20")
                  }>
                    <Zap className="h-2.5 w-2.5" />
                    {selectedModel.tier === "premium" ? "Premium" : selectedModel.tier === "free" ? "Free" : "Fast"}
                  </span>
                </div>
              )}
            </div>

            <div>
              <label className="text-[10px] text-muted-foreground mb-1.5 block font-medium">System Prompt</label>
              <Textarea
                value={system}
                onChange={(e) => setSystem(e.target.value)}
                rows={3}
                className="text-xs font-mono resize-none bg-muted/20 focus:bg-muted/30 transition-colors"
              />
            </div>

            <div>
              <label className="text-[10px] text-muted-foreground mb-1.5 block font-medium">User Prompt</label>
              <Textarea
                value={user}
                onChange={(e) => setUser(e.target.value)}
                rows={10}
                placeholder="اكتب طلبك... (مثلاً: صمّم routing matrix لمهام الكريبتو)"
                className="text-xs font-mono resize-none bg-muted/20 focus:bg-muted/30 transition-colors"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[10px] text-muted-foreground mb-1.5 block font-medium">
                  حفظ في (اختياري)
                </label>
                <Input
                  value={savePath}
                  onChange={(e) => setSavePath(e.target.value)}
                  placeholder="prompts/router.md"
                  className="h-9 text-xs font-mono bg-muted/20"
                />
              </div>
              <div>
                <label className="text-[10px] text-muted-foreground mb-1.5 block font-medium">النوع</label>
                <Select value={saveKind} onValueChange={(v) => setSaveKind(v as "json" | "md")}>
                  <SelectTrigger className="h-9 text-xs">
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
              disabled={loading || !user.trim()}
              className="w-full gap-2 h-10 text-sm font-semibold"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  جارِ التوليد...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4" />
                  تشغيل {savePath && "+ حفظ"}
                </>
              )}
            </Button>
          </Card>

          {/* Output Panel */}
          <Card className="p-5 bg-card/40 border-border/60 flex flex-col animate-fade-in-up stagger-2">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-primary" />
                <h2 className="text-xs font-bold text-foreground">المخرجات</h2>
              </div>
              {output && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button size="sm" variant="outline" onClick={handleCopy} className="h-7 text-[10px] gap-1">
                      {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                      نسخ
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>نسخ المخرجات</TooltipContent>
                </Tooltip>
              )}
            </div>

            <div className="flex-1 rounded-lg border border-border/40 bg-muted/20 overflow-hidden">
              {loading ? (
                <div className="flex flex-col items-center justify-center h-64 gap-3">
                  <div className="relative">
                    <Loader2 className="h-8 w-8 animate-spin text-primary/60" />
                    <span className="absolute inset-0 flex items-center justify-center">
                      <Sparkles className="h-3 w-3 text-primary" />
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground animate-pulse">جارِ التوليد...</span>
                </div>
              ) : output ? (
                <pre className="p-4 text-[11px] font-mono whitespace-pre-wrap break-words text-foreground/90 max-h-[600px] overflow-auto leading-relaxed" dir="ltr">
                  {output}
                </pre>
              ) : (
                <div className="flex flex-col items-center justify-center h-64 gap-3 text-muted-foreground/50">
                  <Sparkles className="h-8 w-8" />
                  <span className="text-xs">النتيجة ستظهر هنا</span>
                </div>
              )}
            </div>
          </Card>
        </main>
      </div>
    </TooltipProvider>
  );
}
