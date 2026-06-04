"""
config/models.py — إعدادات النماذج المتاحة وخيارات الاحتياط

يحدد النماذج الأساسية (primary) ونماذج الاحتياط (fallback)
لكل مزود خدمة (OpenRouter, OpenAI).

الاستخدام:
    from config.models import AVAILABLE_MODELS, get_model_config
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class ModelConfig:
    """إعدادات نموذج واحد"""
    model_id: str
    provider: str  # "openrouter" أو "openai"
    display_name: str
    is_free: bool = False
    max_tokens: int = 4096
    supports_json_mode: bool = True
    description: str = ""


@dataclass
class ModelGroup:
    """مجموعة نماذج لدور محدد (primary + fallbacks)"""
    role: str  # "framer", "solver", "evaluator"
    primary: ModelConfig = None
    fallbacks: List[ModelConfig] = field(default_factory=list)

    def get_ordered_models(self) -> List[ModelConfig]:
        """يرجع النموذج الأساسي ثم نماذج الاحتياط بالترتيب"""
        models = []
        if self.primary:
            models.append(self.primary)
        models.extend(self.fallbacks)
        return models


# --- النماذج المتاحة عبر OpenRouter ---

NEMOTRON_FREE = ModelConfig(
    model_id="nvidia/nemotron-3-super-120b-a12b:free",
    provider="openrouter",
    display_name="NVIDIA Nemotron 120B (Free)",
    is_free=True,
    max_tokens=4096,
    supports_json_mode=True,
    description="النموذج الأساسي المجاني — مستقر وسريع"
)

LLAMA3_70B = ModelConfig(
    model_id="meta-llama/llama-3-70b-instruct",
    provider="openrouter",
    display_name="Meta LLaMA 3 70B",
    is_free=False,
    max_tokens=4096,
    supports_json_mode=True,
    description="نموذج احتياطي قوي من Meta"
)

MISTRAL_LARGE = ModelConfig(
    model_id="mistralai/mistral-large-latest",
    provider="openrouter",
    display_name="Mistral Large",
    is_free=False,
    max_tokens=4096,
    supports_json_mode=True,
    description="نموذج احتياطي من Mistral"
)

# --- النماذج المتاحة عبر OpenAI (هيكل جاهز) ---

GPT4_MINI = ModelConfig(
    model_id="gpt-4o-mini",
    provider="openai",
    display_name="GPT-4o Mini",
    is_free=False,
    max_tokens=4096,
    supports_json_mode=True,
    description="نموذج OpenAI خفيف وسريع"
)

# --- مجموعات النماذج حسب الدور ---

FRAMER_MODELS = ModelGroup(
    role="framer",
    primary=NEMOTRON_FREE,
    fallbacks=[LLAMA3_70B, MISTRAL_LARGE]
)

SOLVER_MODELS = ModelGroup(
    role="solver",
    primary=NEMOTRON_FREE,
    fallbacks=[LLAMA3_70B, MISTRAL_LARGE]
)

EVALUATOR_MODELS = ModelGroup(
    role="evaluator",
    primary=NEMOTRON_FREE,
    fallbacks=[LLAMA3_70B]
)

# --- سجل مركزي للنماذج ---

AVAILABLE_MODELS: Dict[str, ModelConfig] = {
    model.model_id: model
    for model in [NEMOTRON_FREE, LLAMA3_70B, MISTRAL_LARGE, GPT4_MINI]
}

MODEL_GROUPS: Dict[str, ModelGroup] = {
    "framer": FRAMER_MODELS,
    "solver": SOLVER_MODELS,
    "evaluator": EVALUATOR_MODELS,
}


def get_model_config(model_id: str) -> Optional[ModelConfig]:
    """استرجاع إعدادات نموذج بمعرّفه"""
    return AVAILABLE_MODELS.get(model_id)


def get_model_group(role: str) -> Optional[ModelGroup]:
    """استرجاع مجموعة نماذج لدور محدد"""
    return MODEL_GROUPS.get(role)


# --- النموذج الافتراضي ---
DEFAULT_MODEL = NEMOTRON_FREE
