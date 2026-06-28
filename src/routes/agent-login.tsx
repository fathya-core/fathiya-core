import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, KeyRound, LogIn, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { localAgentRuntimeUrl } from "@/lib/agent/client";

const OPERATOR_SESSION_KEY = "fathiya.operator.session.v2";

export const Route = createFileRoute("/agent-login")({
  head: () => ({
    meta: [
      { title: "FATHIYA - المنطقة السيادية الذكية" },
      { name: "description", content: "دخول المشغل الخاص لسطح تشغيل فتحية." },
    ],
  }),
  component: AgentLoginPage,
});

function AgentLoginPage() {
  const navigate = useNavigate();
  const [operatorName, setOperatorName] = useState("oyasaa");
  const [passphrase, setPassphrase] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (typeof window === "undefined") return;
    const session = window.localStorage.getItem(OPERATOR_SESSION_KEY);
    if (session) void navigate({ to: "/agent-tasks" });
  }, [navigate]);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    setError("");

    if (passphrase.trim().length < 4) {
      setError("اكتب رمز تشغيل محلي لا يقل عن 4 أحرف.");
      return;
    }

    window.localStorage.setItem(
      OPERATOR_SESSION_KEY,
      JSON.stringify({
        operatorName: operatorName.trim() || "operator",
        runtime: localAgentRuntimeUrl,
        createdAt: new Date().toISOString(),
      }),
    );
    await navigate({ to: "/agent-tasks" });
  }

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-[#05090d] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(20,184,166,0.12),transparent_32%),radial-gradient(circle_at_80%_5%,rgba(56,189,248,0.1),transparent_28%)]" />
      <header className="relative border-b border-white/10 bg-[#071019]/90">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-emerald-400/40 bg-emerald-400/10">
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-normal">FATHIYA - المنطقة السيادية الذكية</h1>
              <p className="text-xs text-slate-400">سطح تشغيل خاص للتداول الورقي وصيد الثغرات والمعرفة</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" asChild className="text-slate-300 hover:bg-white/10">
            <Link to="/">
              <ArrowRight className="h-4 w-4" />
              الرئيسية
            </Link>
          </Button>
        </div>
      </header>

      <main className="relative mx-auto grid min-h-[calc(100vh-73px)] max-w-6xl items-center gap-8 px-5 py-10 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-6">
          <div className="max-w-xl space-y-4">
            <h2 className="text-4xl font-semibold leading-tight tracking-normal text-white">
              دخول المشغل إلى مركز القرار
            </h2>
            <p className="text-base leading-7 text-slate-300">
              واجهة واحدة محلية وخفيفة تشغل وكلاء فتحية، تفصل التداول عن صيد الثغرات، وتحافظ على
              التقارير والطلبات في مسارات واضحة بلا تشتيت.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            {[
              ["Paper", "التداول الورقي بالثانية"],
              ["Bounty", "ديدوب وإثبات قبل الرفع"],
              ["Reports", "إيصالات وسجل تقدم"],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-white/10 bg-white/[0.04] p-4">
                <p className="text-xs uppercase text-slate-500">{label}</p>
                <p className="mt-2 text-sm font-medium text-slate-100">{value}</p>
              </div>
            ))}
          </div>
        </section>

        <Card className="border-white/10 bg-[#0b121a]/90 text-slate-100 shadow-2xl shadow-black/30">
          <CardHeader>
            <div className="mb-2 flex h-11 w-11 items-center justify-center rounded-lg border border-cyan-400/35 bg-cyan-400/10">
              <KeyRound className="h-5 w-5 text-cyan-300" />
            </div>
            <CardTitle className="text-lg">تسجيل دخول محلي</CardTitle>
            <CardDescription className="text-slate-400">
              الاتصال الحالي موجّه إلى {localAgentRuntimeUrl}. الرمز يبقى في هذا المتصفح فقط.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={signIn}>
              {error && (
                <div className="rounded-md border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">
                  {error}
                </div>
              )}
              <div className="space-y-2">
                <Label htmlFor="operator">اسم المشغل</Label>
                <Input
                  id="operator"
                  value={operatorName}
                  onChange={(event) => setOperatorName(event.target.value)}
                  className="border-white/10 bg-white/[0.04]"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="passphrase">رمز التشغيل المحلي</Label>
                <Input
                  id="passphrase"
                  type="password"
                  value={passphrase}
                  onChange={(event) => setPassphrase(event.target.value)}
                  className="border-white/10 bg-white/[0.04]"
                  autoComplete="current-password"
                />
              </div>
              <Button className="w-full bg-emerald-400 text-emerald-950 hover:bg-emerald-300" type="submit">
                <LogIn className="h-4 w-4" />
                دخول إلى فتحية
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
