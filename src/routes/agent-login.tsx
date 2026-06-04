import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, KeyRound, Loader2, LogIn, ShieldCheck } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getSupabaseConfigurationError, supabase } from "@/integrations/supabase/client";

export const Route = createFileRoute("/agent-login")({
  head: () => ({
    meta: [
      { title: "تسجيل دخول المشغل - FATHIYA" },
      { name: "description", content: "تسجيل دخول آمن لتشغيل ومراقبة وكلاء فتحية." },
    ],
  }),
  component: AgentLoginPage,
});

function AgentLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const configurationError = getSupabaseConfigurationError();
    if (configurationError) {
      setError(configurationError);
      return;
    }
    try {
      void supabase.auth.getSession().then(({ data }) => {
        if (data.session) void navigate({ to: "/agent-tasks" });
      });
    } catch (sessionError) {
      setError(String(sessionError));
    }
  }, [navigate]);

  async function signIn(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    const configurationError = getSupabaseConfigurationError();
    if (configurationError) {
      setError(configurationError);
      setLoading(false);
      return;
    }
    try {
      const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
      if (signInError) {
        setError(signInError.message);
        return;
      }
      await navigate({ to: "/agent-tasks" });
    } catch (signInError) {
      setError(String(signInError));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border/60 bg-background/90">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md border border-emerald-500/30 bg-emerald-500/10">
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold">FATHIYA Agent Runtime</h1>
              <p className="text-[11px] text-muted-foreground">دخول المشغل</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" asChild>
            <Link to="/">
              <ArrowRight />
              لوحة التشغيل
            </Link>
          </Button>
        </div>
      </header>

      <main className="mx-auto flex min-h-[calc(100vh-73px)] max-w-5xl items-center px-4 py-10 sm:px-6">
        <Card className="mx-auto w-full max-w-md border-border/60 bg-card/60">
          <CardHeader>
            <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-md border border-sky-500/30 bg-sky-500/10">
              <KeyRound className="h-5 w-5 text-sky-400" />
            </div>
            <CardTitle className="text-base">تسجيل دخول المشغل</CardTitle>
            <CardDescription>
              الجلسة مطلوبة لإنشاء المهام، الموافقة عليها، ومشاهدة الإيصالات.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={signIn}>
              {error && (
                <Alert variant="destructive">
                  <AlertTitle>تعذر تسجيل الدخول</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="email">البريد الإلكتروني</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password">كلمة المرور</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>
              <Button className="w-full" type="submit" disabled={loading}>
                {loading ? <Loader2 className="animate-spin" /> : <LogIn />}
                دخول
              </Button>
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
