"""
core/verifier.py — التحقق من المخرجات النهائية

يفحص الرد النهائي قبل تسليمه للمستخدم ويتأكد من:
- أنه غير فارغ
- أنه يحترم سياسات اللغة
- أنه لا يحتوي معلومات داخلية مسرّبة
- أنه متناسب مع حجم الطلب
- أنه لا يحتوي مخرجات أو أوامر خطيرة في المسار الأمني

الاستخدام:
    from core.verifier import OutputVerifier, VerificationResult

    verifier = OutputVerifier()
    result = verifier.verify(user_input="سؤال", final_answer="الرد", flow="security")
"""

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


def _load_policies() -> object:
    """
    تحميل السياسات بطريقة آمنة دون الاعتماد القسري على config/__init__.py.
    """
    try:
        from config.policies import policies
        return policies
    except Exception:
        policies_path = Path(__file__).resolve().parents[1] / "config" / "policies.py"
        spec = importlib.util.spec_from_file_location(
            "fathiya_safe_verifier_policies",
            policies_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"تعذر تحميل ملف السياسات من: {policies_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.policies


policies = _load_policies()


@dataclass
class VerificationResult:
    """نتيجة التحقق من المخرجات"""
    passed: bool
    issues: List[str] = field(default_factory=list)
    severity: str = "none"  # "none", "warning", "critical"
    cleaned_answer: Optional[str] = None

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    # ── backward-compatible adapter properties ──────────────────────
    # طبقة main.py والإخراج القديمة تتوقع verdict / reason / revision_note
    # كما في EvaluationResult القديم. هذه الخصائص تُوفّر التوافق بدون
    # تغيير أي منطق في phase-3 أو في المسار الأمني.

    @property
    def verdict(self) -> str:
        """توافق عكسي: passed=True -> 'approve', False -> 'revise'"""
        return "approve" if self.passed else "revise"

    @property
    def reason(self) -> str:
        """توافق عكسي: ملخص المشكلات أو رسالة نجاح"""
        if self.issues:
            return "؛ ".join(self.issues)
        return "نجح التحقق النهائي بدون مشكلات"

    @property
    def revision_note(self) -> str:
        """توافق عكسي: ملاحظة المراجعة (فارغة عند النجاح)"""
        if self.passed:
            return ""
        if self.issues:
            return "؛ ".join(self.issues)
        return "فشل التحقق — راجع المشكلات المسجلة"


class OutputVerifier:
    """
    محقق المخرجات — يفحص الرد النهائي قبل التسليم.

    الفحوصات:
    1. فحص الفراغ
    2. فحص تسريب المعلومات الداخلية
    3. فحص خلط اللغات
    4. فحص التناسب (طول الرد مقابل طول السؤال)
    5. فحص خاص بالمسار (security, sast, crypto)
    """

    INTERNAL_LEAK_PATTERNS: List[str] = [
        r"\bFramer\b",
        r"\bSolver\b",
        r"\bEvaluator\b",
        r"\bhandling_strategy\b",
        r"\bclarity_score\b",
        r"\bproblem_type\b",
        r"\bsub_tasks\b",
        r"\bFramedProblem\b",
        r"\bFATHIYA[\s_]CORE\b",
        r"\borchestrator\b",
        r"\bpipeline\b",
        r"\brevision_note\b",
        r"\bverdict\b.*\bapprove\b",
        r"\bverdict\b.*\brevise\b",
    ]

    SECURITY_DANGEROUS_PATTERNS: List[str] = [
        r"rm\s+-rf\s+/",
        r":\(\)\s*\{\s*:\|:&\s*\};:",
        r"dd\s+if=/dev/zero",
        r"mkfs\.[a-z0-9]+",
        r"chmod\s+-R\s+777\s+/",
        r"curl\s+[^\n]*\|\s*(?:sh|bash)",
        r"wget\s+[^\n]*\|\s*(?:sh|bash)",
        r"nc\s+-e\s+/bin/(?:sh|bash)",
        r"bash\s+-i\s+>&\s+/dev/tcp/",
        r"powershell(?:\.exe)?\s+-enc\b",
    ]

    SECURITY_DANGEROUS_TEXT_PATTERNS: List[str] = [
        r"نف[ّذذ].*بدون\s+تحقق",
        r"تجاوز\s+التحكم\s+بالوصول",
        r"استغلال\s+مباشر\s+للثغرة",
        r"شغ[ّّل] هذا الأمر كما هو",
        r"delete\s+everything",
        r"wipe\s+the\s+disk",
    ]

    def __init__(self) -> None:
        self._policies = policies

    def verify(
        self,
        user_input: str,
        final_answer: str,
        flow: str = "general"
    ) -> VerificationResult:
        """
        التحقق الشامل من الرد النهائي.

        المعاملات:
            user_input   — الطلب الأصلي
            final_answer — الرد النهائي
            flow         — المسار (security, sast, crypto, general)

        يرجع:
            VerificationResult مع حالة التحقق والمشاكل المكتشفة
        """
        issues: List[str] = []
        severity = "none"
        cleaned = final_answer.strip() if final_answer else None

        if not final_answer or not final_answer.strip():
            return VerificationResult(
                passed=False,
                issues=["الرد النهائي فارغ"],
                severity="critical"
            )

        leak_issues = self._check_internal_leaks(final_answer)
        if leak_issues:
            issues.extend(leak_issues)
            severity = self._max_severity(severity, "critical")

        lang_issues = self._check_language_mixing(final_answer)
        if lang_issues:
            issues.extend(lang_issues)
            severity = self._max_severity(severity, "warning")

        proportion_issue = self._check_proportion(user_input, final_answer)
        if proportion_issue:
            issues.append(proportion_issue)
            severity = self._max_severity(severity, "warning")

        flow_issues, flow_severity = self._check_flow_specific(final_answer, flow)
        if flow_issues:
            issues.extend(flow_issues)
            severity = self._max_severity(severity, flow_severity)

        passed = severity == "none" or severity == "warning"
        if flow == "security" and flow_severity == "critical":
            passed = False

        return VerificationResult(
            passed=passed,
            issues=issues,
            severity=severity,
            cleaned_answer=cleaned
        )

    def _check_internal_leaks(self, text: str) -> List[str]:
        """فحص تسريب المعلومات الداخلية"""
        found: List[str] = []
        for pattern in self.INTERNAL_LEAK_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                found.append(f"تسريب محتمل: تطابق مع النمط {pattern}")
        return found

    def _check_language_mixing(self, text: str) -> List[str]:
        """فحص خلط اللغات غير المرغوب"""
        found: List[str] = []
        for pattern in self._policies.language.suspicious_patterns:
            if re.search(pattern, text):
                found.append(f"خلط لغات مشبوه: تطابق مع {pattern}")
        return found

    def _check_proportion(self, user_input: str, answer: str) -> Optional[str]:
        """فحص تناسب طول الرد مع طول السؤال"""
        q_words = len(user_input.split())
        a_words = len(answer.split())

        if self._policies.is_overlong_answer(q_words, a_words):
            return f"الرد طويل جداً ({a_words} كلمة) مقارنة بالسؤال ({q_words} كلمة)"

        return None

    def _check_flow_specific(self, text: str, flow: str) -> tuple[List[str], str]:
        """فحوصات خاصة بالمسار"""
        issues: List[str] = []
        severity = "none"

        if flow == "security":
            for pattern in self.SECURITY_DANGEROUS_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append(f"خطر أمني حرج: الرد يحتوي أمراً خطيراً ({pattern})")

            for pattern in self.SECURITY_DANGEROUS_TEXT_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    issues.append(f"خطر أمني حرج: الرد يحتوي توجيهاً خطيراً ({pattern})")

            if issues:
                severity = "critical"

        elif flow == "crypto":
            financial_advice = [
                r"اشتر[يِ]?\s+الآن",
                r"بيع\s+فور",
                r"ستصعد\s+حتم",
                r"مضمون\s+الربح",
            ]
            for pattern in financial_advice:
                if re.search(pattern, text):
                    issues.append("تحذير: الرد يحتوي نصيحة مالية مباشرة بدون إخلاء مسؤولية")
                    severity = "warning"
                    break

        return issues, severity

    def _max_severity(self, current: str, new: str) -> str:
        """اختيار الشدة الأعلى بين قيمتين."""
        order = {"none": 0, "warning": 1, "critical": 2}
        return new if order[new] > order[current] else current

    def quick_verify(self, final_answer: str) -> bool:
        """فحص سريع — يرجع True إذا الرد صالح أساسياً"""
        if not final_answer or not final_answer.strip():
            return False
        if len(final_answer.strip()) < 10:
            return False
        return True
