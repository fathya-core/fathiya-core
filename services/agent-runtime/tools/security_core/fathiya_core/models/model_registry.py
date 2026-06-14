"""
models/model_registry.py — سجل مركزي للنماذج مع primary/fallback

يدير اختيار النموذج المناسب لكل وكيل، مع دعم التبديل التلقائي
إلى نماذج الاحتياط عند فشل النموذج الأساسي.

الاستخدام:
    from models.model_registry import ModelRegistry

    registry = ModelRegistry()
    provider = registry.get_provider("framer")
    result = provider.chat(messages)
"""

from typing import Optional, Dict, List, Any
from config.models import (
    ModelConfig,
    ModelGroup,
    MODEL_GROUPS,
    DEFAULT_MODEL,
    get_model_config,
    get_model_group,
)


class ModelRegistry:
    """
    سجل مركزي للنماذج — يدير اختيار النموذج والتبديل بين الأساسي والاحتياطي.

    يعمل كطبقة وسيطة بين الوكلاء ومزودي الخدمة:
    - يحدد النموذج المناسب لكل دور (framer, solver, evaluator)
    - يدعم التبديل التلقائي عند الفشل (fallback)
    - يحتفظ بسجل الحالة لكل نموذج
    """

    def __init__(self) -> None:
        self._active_models: Dict[str, ModelConfig] = {}
        self._failure_counts: Dict[str, int] = {}
        self._initialize()

    def _initialize(self) -> None:
        """تهيئة النماذج النشطة من الإعدادات"""
        for role, group in MODEL_GROUPS.items():
            if group.primary:
                self._active_models[role] = group.primary
                self._failure_counts[role] = 0

    def get_active_model(self, role: str) -> ModelConfig:
        """
        استرجاع النموذج النشط لدور محدد.
        يرجع النموذج الأساسي ما لم يكن قد فشل وتم التبديل.
        """
        if role in self._active_models:
            return self._active_models[role]
        return DEFAULT_MODEL

    def get_model_id(self, role: str) -> str:
        """استرجاع معرّف النموذج النشط لدور محدد"""
        return self.get_active_model(role).model_id

    def report_failure(self, role: str) -> Optional[ModelConfig]:
        """
        الإبلاغ عن فشل النموذج الحالي لدور محدد.
        يحاول التبديل إلى نموذج احتياطي.
        يرجع النموذج الجديد أو None إذا لم يتوفر احتياطي.
        """
        self._failure_counts[role] = self._failure_counts.get(role, 0) + 1

        group: Optional[ModelGroup] = get_model_group(role)
        if not group:
            return None

        ordered: List[ModelConfig] = group.get_ordered_models()
        failure_count: int = self._failure_counts[role]

        # التبديل إلى النموذج التالي في القائمة
        if failure_count < len(ordered):
            new_model: ModelConfig = ordered[failure_count]
            self._active_models[role] = new_model
            return new_model

        return None

    def report_success(self, role: str) -> None:
        """الإبلاغ عن نجاح النموذج الحالي — يعيد عداد الفشل إلى صفر"""
        self._failure_counts[role] = 0

    def reset(self, role: Optional[str] = None) -> None:
        """
        إعادة تعيين النماذج النشطة.
        إذا حُدد role يعيد تعيين دور واحد، وإلا يعيد تعيين الكل.
        """
        if role:
            group: Optional[ModelGroup] = get_model_group(role)
            if group and group.primary:
                self._active_models[role] = group.primary
                self._failure_counts[role] = 0
        else:
            self._initialize()

    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """استرجاع حالة جميع النماذج النشطة"""
        status: Dict[str, Dict[str, Any]] = {}
        for role in MODEL_GROUPS:
            model: Optional[ModelConfig] = self._active_models.get(role)
            status[role] = {
                "model_id": model.model_id if model else "none",
                "provider": model.provider if model else "none",
                "failures": self._failure_counts.get(role, 0),
                "is_primary": (
                    model == MODEL_GROUPS[role].primary
                    if model and role in MODEL_GROUPS
                    else False
                ),
            }
        return status

    def list_available_models(self, role: str) -> List[Dict[str, Any]]:
        """استرجاع قائمة النماذج المتاحة لدور محدد"""
        group: Optional[ModelGroup] = get_model_group(role)
        if not group:
            return []
        return [
            {"model_id": m.model_id, "display_name": m.display_name, "is_free": m.is_free}
            for m in group.get_ordered_models()
        ]
