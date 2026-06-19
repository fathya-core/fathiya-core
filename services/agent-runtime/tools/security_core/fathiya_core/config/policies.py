"""
config/policies.py — قواعد وسياسات النظام

يحدد الحدود والقيود التشغيلية لمشروع FATHIYA CORE:
- حدود الطول (مدخلات ومخرجات)
- اللغات المسموحة
- حدود حلقة المراجعة
- المصطلحات التقنية المسموحة

الاستخدام:
    from config.policies import policies
"""

from dataclasses import dataclass, field
from typing import Set, List


@dataclass
class InputPolicies:
    """سياسات المدخلات"""
    min_input_length: int = 2  # الحد الأدنى لطول المدخل (أحرف)
    max_input_length: int = 5000  # الحد الأقصى لطول المدخل (أحرف)
    min_input_words: int = 1  # الحد الأدنى لعدد الكلمات


@dataclass
class OutputPolicies:
    """سياسات المخرجات"""
    max_answer_words: int = 220  # الحد الأقصى لعدد الكلمات قبل اعتبار الرد طويلاً
    short_question_threshold: int = 8  # عتبة السؤال القصير (كلمات)
    min_revision_ratio: float = 0.25  # الحد الأدنى لنسبة الرد المعدل من الأصلي
    min_revision_length: int = 20  # الحد الأدنى لطول الرد المعدل (أحرف)
    answer_preview_length: int = 700  # طول المعاينة في الاختبارات


@dataclass
class RevisionPolicies:
    """سياسات حلقة المراجعة"""
    max_revision_rounds: int = 2  # الحد الأقصى لعدد جولات المراجعة
    evaluator_max_retries: int = 3  # الحد الأقصى لإعادة محاولة الـ Evaluator
    evaluator_retry_delay: float = 2.0  # تأخير بين محاولات الـ Evaluator (ثوانٍ)


@dataclass
class LanguagePolicies:
    """سياسات اللغة"""
    primary_language: str = "ar"  # اللغة الأساسية
    allowed_technical_languages: Set[str] = field(default_factory=lambda: {"en"})

    # المصطلحات التقنية المسموح بها بالإنجليزية
    allowed_technical_terms: Set[str] = field(default_factory=lambda: {
        "Python", "JSON", "API", "CSV", "HTML", "CSS", "JavaScript",
        "pandas", "NumPy", "matplotlib", "VS Code", "Jupyter",
        "GitHub", "SQL", "Flask", "Django", "FastAPI",
        "React", "Node.js", "MongoDB", "TypeScript",
        "Docker", "Kubernetes", "AWS", "Azure", "GCP",
        "Git", "Linux", "Ubuntu", "Windows", "macOS",
        "HTTP", "HTTPS", "REST", "GraphQL", "WebSocket",
        "TCP", "UDP", "DNS", "SSL", "TLS",
        "OpenRouter", "OpenAI", "GPT", "LLM",
    })

    # أنماط اللغات المشبوهة (غير العربية وغير الإنجليزية)
    suspicious_patterns: List[str] = field(default_factory=lambda: [
        r"[ぁ-んァ-ン一-龯]",   # ياباني
        r"[가-힣]",           # كوري
        r"[א-ת]",             # عبري
        r"[А-Яа-я]",          # سيريلي (روسي)
    ])


@dataclass
class HandlingStrategies:
    """استراتيجيات التعامل المعتمدة"""
    valid_strategies: Set[str] = field(default_factory=lambda: {
        "clarify_first",
        "research_first",
        "direct_execution",
        "analysis_then_execution",
    })


@dataclass
class FathiyaPolicies:
    """
    السياسات المركزية لمشروع FATHIYA CORE.
    تجمع كل القواعد والحدود في مكان واحد.
    """
    input: InputPolicies = field(default_factory=InputPolicies)
    output: OutputPolicies = field(default_factory=OutputPolicies)
    revision: RevisionPolicies = field(default_factory=RevisionPolicies)
    language: LanguagePolicies = field(default_factory=LanguagePolicies)
    strategies: HandlingStrategies = field(default_factory=HandlingStrategies)

    def is_valid_strategy(self, strategy: str) -> bool:
        """التحقق من صلاحية استراتيجية التعامل"""
        return strategy in self.strategies.valid_strategies

    def is_overlong_answer(self, question_words: int, answer_words: int) -> bool:
        """التحقق مما إذا كان الرد أطول من اللازم"""
        short_question = question_words <= self.output.short_question_threshold
        long_answer = answer_words > self.output.max_answer_words
        return short_question and long_answer

    def is_revision_too_short(self, revised_length: int, original_length: int) -> bool:
        """التحقق مما إذا كان الرد المعدل انكمش أكثر من اللازم"""
        min_length = max(
            self.output.min_revision_length,
            int(original_length * self.output.min_revision_ratio)
        )
        return revised_length < min_length


# --- نسخة واحدة (Singleton) للاستخدام في كل المشروع ---
policies = FathiyaPolicies()
