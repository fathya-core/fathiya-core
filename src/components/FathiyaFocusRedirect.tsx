import { Link, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { ArrowRight, ShieldAlert, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function FathiyaFocusRedirect({ source }: { source: string }) {
  const navigate = useNavigate();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void navigate({ to: "/agent-tasks", replace: true });
    }, 150);
    return () => window.clearTimeout(timer);
  }, [navigate]);

  return (
    <div dir="rtl" lang="ar" className="min-h-screen bg-background text-foreground">
      <main className="mx-auto flex min-h-screen max-w-4xl flex-col justify-center px-4 py-10 sm:px-6">
        <div className="border-y border-border/60 py-8">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="border-emerald-500/30 bg-emerald-500/10 text-emerald-300">
              FATHIYA Focus
            </Badge>
            <Badge variant="outline">{source}</Badge>
          </div>

          <h1 className="mt-5 text-2xl font-bold tracking-tight sm:text-3xl">
            تم نقل فتحية إلى التداول وصيد الثغرات فقط
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-7 text-muted-foreground">
            الصفحات القديمة لم تعد الواجهة الرئيسية. سيتم تحويلك الآن إلى شاشة العمل المركزة.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <div className="border border-emerald-500/25 bg-emerald-500/[0.04] p-4">
              <TrendingUp className="mb-3 h-5 w-5 text-emerald-300" />
              <h2 className="text-sm font-semibold">وكيل التداول</h2>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                مراقبة، تنبؤ، نبضات Paper/Testnet، وإيصالات تنفيذ واضحة.
              </p>
            </div>
            <div className="border border-sky-500/25 bg-sky-500/[0.04] p-4">
              <ShieldAlert className="mb-3 h-5 w-5 text-sky-300" />
              <h2 className="text-sm font-semibold">صيد الثغرات</h2>
              <p className="mt-2 text-xs leading-6 text-muted-foreground">
                اختيار HackerOne أو Bugcrowd، مراجعة معرفة، تصعيد بالدليل، ومسودة تقرير.
              </p>
            </div>
          </div>

          <Button asChild className="mt-6">
            <Link to="/agent-tasks">
              <ArrowRight />
              فتح واجهة فتحية
            </Link>
          </Button>
        </div>
      </main>
    </div>
  );
}
