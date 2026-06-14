"""
config/ — طبقة الإعدادات المركزية لمشروع FATHIYA CORE

تصدّر:
    settings  — إعدادات المتغيرات البيئية والاتصالات
    policies  — قواعد وسياسات النظام
    النماذج   — إعدادات النماذج المتاحة
"""

from config.settings import settings
from config.policies import policies
from config.models import (
    DEFAULT_MODEL,
    AVAILABLE_MODELS,
    MODEL_GROUPS,
    get_model_config,
    get_model_group,
)

__all__ = [
    "settings",
    "policies",
    "DEFAULT_MODEL",
    "AVAILABLE_MODELS",
    "MODEL_GROUPS",
    "get_model_config",
    "get_model_group",
]
