"""
domains/security/test_planner.py — مخطط اختبارات الأمان

يبني خطة اختبار أمني بناءً على الملف التعريفي للهدف (TargetProfile).
يحدد أنواع الاختبارات المناسبة وأولوياتها.

الاستخدام:
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner, TestPlan

    profiler = TargetProfiler()
    profile = profiler.profile("example.com")

    planner = SecurityTestPlanner()
    plan = planner.plan(profile)
    for step in plan.steps:
        print(f"{step.priority}: {step.name}")
"""

from dataclasses import dataclass, field
from typing import Dict, List

from domains.security.target_profiler import TargetProfile


@dataclass
class TestStep:
    """خطوة اختبار واحدة"""
    name: str
    description: str
    category: str  # "recon", "scan", "vuln", "exploit", "report"
    priority: int  # 1 = أعلى أولوية، 5 = أدنى
    tools: List[str] = field(default_factory=list)
    estimated_time: str = ""  # مثال: "5-10 دقائق"
    prerequisites: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


@dataclass
class TestPlan:
    """خطة اختبار أمني كاملة"""
    target_summary: str
    target_type: str
    steps: List[TestStep] = field(default_factory=list)
    total_estimated_time: str = ""
    warnings: List[str] = field(default_factory=list)
    scope_notes: List[str] = field(default_factory=list)

    @property
    def step_count(self) -> int:
        return len(self.steps)

    def get_steps_by_category(self, category: str) -> List[TestStep]:
        """استرجاع الخطوات حسب الفئة"""
        return [s for s in self.steps if s.category == category]

    def get_steps_by_priority(self, max_priority: int = 3) -> List[TestStep]:
        """استرجاع الخطوات ذات الأولوية العالية"""
        return [s for s in self.steps if s.priority <= max_priority]


class SecurityTestPlanner:
    """
    مخطط اختبارات الأمان — يبني خطة اختبار بناءً على نوع الهدف.

    المسارات:
    - domain/url → خطة اختبار ويب كاملة
    - ip → خطة فحص شبكي
    - cidr → خطة مسح نطاق
    - unknown → خطة استطلاع أولي
    """

    def __init__(self) -> None:
        pass

    def plan(self, profile: TargetProfile) -> TestPlan:
        """
        بناء خطة اختبار بناءً على الملف التعريفي.

        المعاملات:
            profile — الملف التعريفي من TargetProfiler

        يرجع:
            TestPlan مع الخطوات والتقديرات
        """
        if not profile.is_valid:
            return self._plan_unknown(profile)

        planners: Dict[str, callable] = {
            "domain": self._plan_web_test,
            "url": self._plan_web_test,
            "ip": self._plan_network_test,
            "cidr": self._plan_range_scan,
        }

        planner_func = planners.get(profile.target_type, self._plan_unknown)
        plan = planner_func(profile)
        plan.warnings = self._merge_unique_warnings(list(plan.warnings), list(profile.risk_notes))
        return plan

    def _merge_unique_warnings(self, current: List[str], extra: List[str]) -> List[str]:
        """دمج التحذيرات دون تعديل الأصل ودون تكرار."""
        merged: List[str] = []
        seen = set()

        for warning in current + extra:
            if warning and warning not in seen:
                seen.add(warning)
                merged.append(warning)

        return merged

    def _plan_web_test(self, profile: TargetProfile) -> TestPlan:
        """خطة اختبار ويب"""
        steps: List[TestStep] = [
            TestStep(
                name="استطلاع أولي (Reconnaissance)",
                description="جمع معلومات عامة عن الهدف: DNS, WHOIS, تقنيات مستخدمة",
                category="recon",
                priority=1,
                tools=["whois", "dig", "nslookup", "whatweb", "wappalyzer"],
                estimated_time="10-15 دقيقة",
            ),
            TestStep(
                name="اكتشاف النطاقات الفرعية",
                description="البحث عن نطاقات فرعية مرتبطة بالهدف",
                category="recon",
                priority=2,
                tools=["subfinder", "amass", "assetfinder"],
                estimated_time="15-30 دقيقة",
                prerequisites=["استطلاع أولي"],
            ),
            TestStep(
                name="فحص المنافذ والخدمات",
                description="مسح المنافذ المفتوحة وتحديد الخدمات العاملة",
                category="scan",
                priority=1,
                tools=["nmap", "masscan"],
                estimated_time="10-20 دقيقة",
            ),
            TestStep(
                name="فحص SSL/TLS",
                description="فحص شهادة SSL وإعدادات التشفير",
                category="scan",
                priority=2,
                tools=["sslyze", "testssl.sh", "sslscan"],
                estimated_time="5-10 دقائق",
            ),
            TestStep(
                name="اكتشاف المسارات والملفات",
                description="البحث عن مسارات وملفات مخفية أو حساسة",
                category="scan",
                priority=2,
                tools=["dirsearch", "gobuster", "ffuf"],
                estimated_time="20-40 دقيقة",
                prerequisites=["فحص المنافذ والخدمات"],
            ),
            TestStep(
                name="فحص ثغرات الويب",
                description="فحص ثغرات OWASP Top 10: XSS, SQLi, CSRF, إلخ",
                category="vuln",
                priority=1,
                tools=["burpsuite", "zap", "nikto", "sqlmap"],
                estimated_time="1-3 ساعات",
                prerequisites=["اكتشاف المسارات والملفات"],
            ),
            TestStep(
                name="فحص Headers الأمنية",
                description="التحقق من ترويسات الأمان: CSP, HSTS, X-Frame-Options",
                category="vuln",
                priority=3,
                tools=["securityheaders.com", "curl"],
                estimated_time="5-10 دقائق",
            ),
            TestStep(
                name="إعداد التقرير",
                description="توثيق النتائج وتصنيف الثغرات حسب الخطورة",
                category="report",
                priority=1,
                tools=["markdown", "latex"],
                estimated_time="30-60 دقيقة",
                prerequisites=["فحص ثغرات الويب"],
            ),
        ]

        return TestPlan(
            target_summary=f"اختبار أمني لموقع: {profile.normalized_target}",
            target_type=profile.target_type,
            steps=steps,
            total_estimated_time="3-6 ساعات",
            scope_notes=[
                "يجب الحصول على تصريح كتابي قبل بدء الاختبار",
                "الاختبار يشمل الطبقة التطبيقية (Layer 7) فقط",
            ],
        )

    def _plan_network_test(self, profile: TargetProfile) -> TestPlan:
        """خطة فحص شبكي لعنوان IP"""
        steps: List[TestStep] = [
            TestStep(
                name="فحص المنافذ الشامل",
                description="مسح جميع المنافذ (1-65535) وتحديد الخدمات",
                category="scan",
                priority=1,
                tools=["nmap", "masscan"],
                estimated_time="15-30 دقيقة",
            ),
            TestStep(
                name="تحديد نظام التشغيل",
                description="محاولة تحديد نظام التشغيل والإصدار",
                category="recon",
                priority=2,
                tools=["nmap -O", "p0f"],
                estimated_time="5-10 دقائق",
                prerequisites=["فحص المنافذ الشامل"],
            ),
            TestStep(
                name="فحص الخدمات المكتشفة",
                description="فحص كل خدمة مكتشفة بحثاً عن ثغرات معروفة",
                category="vuln",
                priority=1,
                tools=["nmap scripts", "metasploit", "searchsploit"],
                estimated_time="30-60 دقيقة",
                prerequisites=["فحص المنافذ الشامل"],
            ),
            TestStep(
                name="فحص كلمات المرور الافتراضية",
                description="اختبار كلمات المرور الافتراضية للخدمات المكتشفة",
                category="vuln",
                priority=3,
                tools=["hydra", "medusa", "ncrack"],
                estimated_time="15-30 دقيقة",
                prerequisites=["تحديد نظام التشغيل"],
                notes=["يتطلب تصريح خاص — قد يؤدي لقفل الحسابات"],
            ),
            TestStep(
                name="إعداد التقرير",
                description="توثيق النتائج والتوصيات",
                category="report",
                priority=1,
                tools=["markdown"],
                estimated_time="20-30 دقيقة",
            ),
        ]

        return TestPlan(
            target_summary=f"فحص شبكي لعنوان: {profile.normalized_target}",
            target_type=profile.target_type,
            steps=steps,
            total_estimated_time="1.5-3 ساعات",
            scope_notes=[
                "يجب الحصول على تصريح كتابي",
                "الفحص يشمل طبقة الشبكة والخدمات",
            ],
        )

    def _plan_range_scan(self, profile: TargetProfile) -> TestPlan:
        """خطة مسح نطاق شبكة"""
        steps: List[TestStep] = [
            TestStep(
                name="اكتشاف الأجهزة النشطة",
                description="تحديد الأجهزة المتصلة في النطاق",
                category="recon",
                priority=1,
                tools=["nmap -sn", "arp-scan", "fping"],
                estimated_time="10-20 دقيقة",
            ),
            TestStep(
                name="فحص سريع للمنافذ الشائعة",
                description="مسح المنافذ الأكثر شيوعاً (Top 100) لكل جهاز نشط",
                category="scan",
                priority=1,
                tools=["nmap", "masscan"],
                estimated_time="20-60 دقيقة",
                prerequisites=["اكتشاف الأجهزة النشطة"],
            ),
            TestStep(
                name="تصنيف الأجهزة والخدمات",
                description="تصنيف الأجهزة حسب النوع والخدمات المكتشفة",
                category="recon",
                priority=2,
                tools=["nmap -sV"],
                estimated_time="15-30 دقيقة",
                prerequisites=["فحص سريع للمنافذ الشائعة"],
            ),
            TestStep(
                name="إعداد التقرير",
                description="خريطة الشبكة وتوصيات أمنية",
                category="report",
                priority=1,
                tools=["markdown"],
                estimated_time="20-30 دقيقة",
            ),
        ]

        return TestPlan(
            target_summary=f"مسح نطاق شبكة: {profile.normalized_target}",
            target_type=profile.target_type,
            steps=steps,
            total_estimated_time="1-2.5 ساعة",
            scope_notes=[
                "يجب الحصول على تصريح لمسح النطاق الكامل",
                "قد يؤثر المسح على أداء الشبكة",
            ],
            warnings=list(profile.risk_notes),
        )

    def _plan_unknown(self, profile: TargetProfile) -> TestPlan:
        """خطة استطلاع أولي لهدف غير محدد"""
        steps: List[TestStep] = [
            TestStep(
                name="تحديد الهدف",
                description="توضيح وتحديد الهدف بشكل دقيق قبل البدء",
                category="recon",
                priority=1,
                tools=[],
                estimated_time="5-10 دقائق",
                notes=["يجب تحديد الهدف بوضوح: نطاق، IP، أو رابط"],
            ),
            TestStep(
                name="جمع معلومات أولية",
                description="البحث عن معلومات متاحة علنياً عن الهدف",
                category="recon",
                priority=2,
                tools=["google", "shodan", "censys"],
                estimated_time="15-30 دقيقة",
                prerequisites=["تحديد الهدف"],
            ),
        ]

        return TestPlan(
            target_summary=f"استطلاع أولي: {profile.raw_input[:50]}",
            target_type="unknown",
            steps=steps,
            total_estimated_time="20-40 دقيقة",
            scope_notes=["يجب تحديد الهدف بدقة قبل وضع خطة اختبار كاملة"],
            warnings=["الهدف غير محدد بوضوح — الخطة أولية فقط"],
        )
