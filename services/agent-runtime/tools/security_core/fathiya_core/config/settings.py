"""
config/settings.py — إدارة مركزية للمتغيرات البيئية والإعدادات العامة

يجمع كل الإعدادات في مكان واحد بدلاً من تكرار load_dotenv() و os.getenv()
في كل ملف على حدة. يمكن استيراده من أي مكان في المشروع:

    from config.settings import settings
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# تحميل المتغيرات البيئية مرة واحدة عند الاستيراد
load_dotenv()


@dataclass
class RetrySettings:
    """إعدادات إعادة المحاولة للطلبات"""
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 30.0
    rate_limit_delay: float = 30.0
    jitter_min: float = 0.8
    jitter_max: float = 4.0


@dataclass
class TimeoutSettings:
    """إعدادات المهلة الزمنية"""
    api_request_timeout: int = 60
    evaluator_timeout: int = 40
    test_cooldown: int = 45


@dataclass
class FathiyaSettings:
    """
    الإعدادات المركزية لمشروع FATHIYA CORE.

    المتغيرات البيئية المطلوبة:
        OPENROUTER_API_KEY — مفتاح OpenRouter API

    المتغيرات البيئية الاختيارية:
        OPENAI_API_KEY     — مفتاح OpenAI API (للاستخدام المستقبلي)
        FATHIYA_DEBUG      — تفعيل وضع التشخيص (true/false)
        FATHIYA_DB_PATH    — مسار قاعدة بيانات الذاكرة
    """

    # --- مفاتيح API ---
    openrouter_api_key: str = ""
    openai_api_key: str = ""

    # --- إعدادات عامة ---
    debug: bool = False
    db_path: str = "memory/fathiya_memory.db"

    # --- إعدادات فرعية ---
    retry: RetrySettings = field(default_factory=RetrySettings)
    timeout: TimeoutSettings = field(default_factory=TimeoutSettings)

    def __post_init__(self):
        """تحميل القيم من المتغيرات البيئية"""
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.debug = os.getenv("FATHIYA_DEBUG", "false").lower() in ("true", "1", "yes")
        self.db_path = os.getenv("FATHIYA_DB_PATH", self.db_path)

    def validate(self) -> None:
        """التحقق من وجود المتغيرات المطلوبة"""
        if not self.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is missing. "
                "Set it in .env or as an environment variable."
            )

    @property
    def openrouter_headers(self) -> dict:
        """ترويسات HTTP الجاهزة لطلبات OpenRouter"""
        return {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "Content-Type": "application/json"
        }

    @property
    def openai_headers(self) -> dict:
        """ترويسات HTTP الجاهزة لطلبات OpenAI"""
        return {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }


# --- نسخة واحدة (Singleton) للاستخدام في كل المشروع ---
settings = FathiyaSettings()
