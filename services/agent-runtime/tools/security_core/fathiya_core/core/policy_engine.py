"""
core/policy_engine.py — محرك تطبيق السياسات

يطبّق السياسات المعرّفة في config/policies.py على المدخلات والمخرجات.
يعمل كطبقة وسيطة بين الوكلاء والـ orchestrator.

الاستخدام:
    from core.policy_engine import PolicyEngine, PolicyCheckResult

    engine = PolicyEngine()
    result = engine.check_input("سؤال المستخدم")
    result = engine.check_output("سؤال", "الرد", "direct_execution")
"""

import importlib.util
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple, Type


def _load_policies_module() -> Tuple[object, Type[object]]:
    """
    تحميل السياسات بطريقة import-safe.

    نحاول أولاً الاستيراد الاعتيادي، وإذا فشل بسبب مهيئ الحزمة أو
    اعتمادات اختيارية مثل dotenv، نحمّل الملف config/policies.py مباشرة.
    """
    try:
        from config.policies import policies, FathiyaPolicies
        return policies, FathiyaPolicies
    except Exception:
        policies_path = Path(__file__).resolve().parents[1] / "config" / "policies.py"
        spec = importlib.util.spec_from_file_location(
            "fathiya_safe_config_policies",
            policies_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"تعذر تحميل ملف السياسات من: {policies_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.policies, module.FathiyaPolicies


policies, FathiyaPolicies = _load_policies_module()


@dataclass
class PolicyCheckResult:
    """نتيجة فحص السياسات"""
    passed: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    action: str = "allow"  # "allow", "warn", "block"

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


class PolicyEngine:
    """
    محرك السياسات — يطبّق قواعد config/policies.py.

    الفحوصات المتاحة:
    - check_input()  — فحص المدخلات قبل المعالجة
    - check_output() — فحص المخرجات قبل التسليم
    - check_strategy() — فحص صلاحية الاستراتيجية
    - check_revision() — فحص جودة المراجعة
    """

    def __init__(self, custom_policies: Optional[FathiyaPolicies] = None) -> None:
        self._policies = custom_policies or policies

    def check_input(self, user_input: str) -> PolicyCheckResult:
        """
        فحص المدخلات وفقاً لسياسات المدخلات.

        يفحص:
        - الفراغ
        - الحد الأدنى للطول
        - الحد الأقصى للطول
        - الحد الأدنى لعدد الكلمات
        """
        violations: List[str] = []
        warnings: List[str] = []

        if not user_input or not user_input.strip():
            violations.append("المدخل فارغ")
            return PolicyCheckResult(
                passed=False,
                violations=violations,
                action="block"
            )

        stripped = user_input.strip()
        char_count = len(stripped)
        word_count = len(stripped.split())

        if char_count < self._policies.input.min_input_length:
            violations.append(
                f"المدخل أقصر من الحد الأدنى "
                f"({char_count} < {self._policies.input.min_input_length} حرف)"
            )

        if char_count > self._policies.input.max_input_length:
            violations.append(
                f"المدخل أطول من الحد الأقصى "
                f"({char_count} > {self._policies.input.max_input_length} حرف)"
            )

        if word_count < self._policies.input.min_input_words:
            warnings.append("المدخل يحتوي كلمة واحدة فقط — قد يكون غامضاً")

        action = "block" if violations else ("warn" if warnings else "allow")
        passed = len(violations) == 0

        return PolicyCheckResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            action=action
        )

    def check_output(
        self,
        user_input: str,
        answer: str,
        strategy: str = "direct_execution"
    ) -> PolicyCheckResult:
        """
        فحص المخرجات وفقاً لسياسات المخرجات واللغة.

        يفحص:
        - الفراغ
        - التناسب (طول الرد مقابل السؤال)
        - خلط اللغات
        - صلاحية الاستراتيجية
        """
        violations: List[str] = []
        warnings: List[str] = []

        if not answer or not answer.strip():
            violations.append("الرد فارغ")
            return PolicyCheckResult(
                passed=False,
                violations=violations,
                action="block"
            )

        q_words = len(user_input.split())
        a_words = len(answer.split())

        if self._policies.is_overlong_answer(q_words, a_words):
            warnings.append(
                f"الرد طويل ({a_words} كلمة) مقارنة بالسؤال ({q_words} كلمة)"
            )

        for pattern in self._policies.language.suspicious_patterns:
            if re.search(pattern, answer):
                warnings.append("خلط لغات مشبوه في الرد")
                break

        if not self._policies.is_valid_strategy(strategy):
            warnings.append(f"استراتيجية غير معروفة: {strategy}")

        action = "block" if violations else ("warn" if warnings else "allow")
        passed = len(violations) == 0

        return PolicyCheckResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            action=action
        )

    def check_strategy(self, strategy: str) -> PolicyCheckResult:
        """فحص صلاحية استراتيجية التعامل"""
        if self._policies.is_valid_strategy(strategy):
            return PolicyCheckResult(passed=True, action="allow")

        return PolicyCheckResult(
            passed=False,
            violations=[f"استراتيجية غير معروفة: {strategy}"],
            action="block"
        )

    def check_revision(
        self,
        revised_answer: str,
        original_answer: str
    ) -> PolicyCheckResult:
        """
        فحص جودة المراجعة.

        يفحص:
        - الفراغ
        - الانكماش المفرط
        """
        violations: List[str] = []
        warnings: List[str] = []

        if not revised_answer or not revised_answer.strip():
            violations.append("الرد المعدل فارغ")
            return PolicyCheckResult(
                passed=False,
                violations=violations,
                action="block"
            )

        revised_len = len(revised_answer.strip())
        original_len = len(original_answer.strip())

        if self._policies.is_revision_too_short(revised_len, original_len):
            warnings.append(
                f"الرد المعدل انكمش كثيراً "
                f"({revised_len} حرف من أصل {original_len})"
            )

        action = "block" if violations else ("warn" if warnings else "allow")
        passed = len(violations) == 0

        return PolicyCheckResult(
            passed=passed,
            violations=violations,
            warnings=warnings,
            action=action
        )

    @property
    def max_revision_rounds(self) -> int:
        """الحد الأقصى لجولات المراجعة"""
        return self._policies.revision.max_revision_rounds

    @property
    def current_policies(self) -> FathiyaPolicies:
        """استرجاع السياسات الحالية"""
        return self._policies
