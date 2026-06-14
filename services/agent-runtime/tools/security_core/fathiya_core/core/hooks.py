import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class HookResult:
    passed: bool
    reason: str = ""
    cleaned_text: Optional[str] = None
    needs_revision: bool = False


class FathiyaHooks:
    def __init__(self):
        # كلمات/رموز شائعة تدل على خلط لغات أو بقايا غير مرغوبة
        self.suspicious_non_arabic_patterns = [
            r"[ぁ-んァ-ン一-龯]",   # ياباني
            r"[가-힣]",           # كوري
            r"[א-ת]",             # عبري
            r"[А-Яа-я]",          # سيريلي
        ]

        # مسموح بها كمصطلحات تقنية شائعة
        self.allowed_technical_words = {
            "Python", "JSON", "API", "CSV", "HTML", "CSS", "JavaScript",
            "pandas", "NumPy", "matplotlib", "VS Code", "Jupyter",
            "GitHub", "SQL", "Flask", "Django", "FastAPI"
        }

    def on_session_start(self, user_input: str) -> HookResult:
        if not user_input or not user_input.strip():
            return HookResult(False, "المدخل فارغ")
        return HookResult(True)

    def pre_solver(self, user_input: str, handling_strategy: str) -> HookResult:
        if handling_strategy not in {
            "clarify_first",
            "research_first",
            "direct_execution",
            "analysis_then_execution",
        }:
            return HookResult(False, f"handling_strategy غير معروف: {handling_strategy}")

        if len(user_input.strip()) < 2:
            return HookResult(False, "المدخل قصير جدًا")

        return HookResult(True)

    def post_solver(self, user_input: str, solver_answer: str) -> HookResult:
        if not solver_answer or not solver_answer.strip():
            return HookResult(False, "رد Solver فارغ")

        cleaned = self._basic_cleanup(solver_answer)

        suspicious = self._detect_suspicious_foreign_text(cleaned)
        if suspicious:
            return HookResult(
                True,
                reason="يوجد خلط لغات غير مرغوب ويجب إعادة صياغة الرد بالعربية النظيفة",
                cleaned_text=cleaned,
                needs_revision=True
            )

        if self._looks_overlong(user_input, cleaned):
            return HookResult(
                True,
                reason="الرد أطول من اللازم ويحتاج اختصارًا",
                cleaned_text=cleaned,
                needs_revision=True
            )

        if self._has_broken_day_count(user_input, cleaned):
            return HookResult(
                True,
                reason="الرد خالف عدد الأيام المطلوب ويحتاج تصحيحًا",
                cleaned_text=cleaned,
                needs_revision=True
            )

        return HookResult(True, cleaned_text=cleaned)

    def post_revision(self, revised_answer: str, original_answer: str) -> HookResult:
        if not revised_answer or not revised_answer.strip():
            return HookResult(False, "الرد المعدل فارغ")

        cleaned = self._basic_cleanup(revised_answer)

        suspicious = self._detect_suspicious_foreign_text(cleaned)
        if suspicious:
            return HookResult(False, f"الرد المعدل ما زال يحتوي خلط لغات غير مرغوب: {suspicious}", cleaned)

        if len(cleaned.strip()) < max(20, int(len(original_answer.strip()) * 0.25)):
            return HookResult(False, "الرد المعدل انكمش أكثر من اللازم", cleaned)

        return HookResult(True, cleaned_text=cleaned)

    def _basic_cleanup(self, text: str) -> str:
        cleaned = text.strip()

        # إزالة مسافات زائدة
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

        # إزالة بقايا markdown fences
        cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)

        return cleaned.strip()

    def _detect_suspicious_foreign_text(self, text: str) -> str:
        for pattern in self.suspicious_non_arabic_patterns:
            if re.search(pattern, text):
                return pattern
        return ""

    def _looks_overlong(self, user_input: str, text: str) -> bool:
        # إذا السؤال قصير جدًا والجواب طويل بشكل غير متوازن
        short_question = len(user_input.split()) <= 8
        long_answer = len(text.split()) > 220
        return short_question and long_answer

    def _trim_answer(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if len(lines) <= 12:
            return text

        trimmed = "\n".join(lines[:12]).strip()
        return trimmed

    def _has_broken_day_count(self, user_input: str, text: str) -> bool:
        match = re.search(r"(\d+)\s*يوم", user_input)
        if not match:
            return False

        requested_days = int(match.group(1))

        numbers = re.findall(r"اليوم\s+(\d+)", text)
        range_starts = [int(n) for n in numbers]

        range_ends = re.findall(r"اليوم\s+\d+[-\-–](\d+)", text)
        range_ends = [int(n) for n in range_ends]

        all_days = range_starts + range_ends
        if not all_days:
            return False

        return max(all_days) > requested_days