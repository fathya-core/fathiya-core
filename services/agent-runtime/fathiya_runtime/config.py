from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class RuntimeConfig:
    service_root: Path
    store: str
    sqlite_path: Path
    worker_id: str
    worker_name: str
    repo_root: Path
    knowledge_root: Path
    tool_inventory_path: Path
    command_profiles_path: Path
    connector_profiles_path: Path
    enable_hf_retrieval: bool
    hf_model: str
    enable_local_generation: bool
    enable_local_planning: bool
    local_model: str
    local_max_new_tokens: int
    local_max_generation_seconds: float
    openrouter_api_key: str
    openrouter_model: str
    max_tool_steps: int
    supabase_url: str
    supabase_service_role_key: str
    n8n_base_url: str
    n8n_api_key: str
    n8n_webhook_url: str
    kali_wsl_distro: str

    @classmethod
    def load(cls) -> "RuntimeConfig":
        service_root = Path(__file__).resolve().parents[1]
        load_dotenv(service_root / ".env")

        def resolve_path(name: str, default: str) -> Path:
            value = Path(os.getenv(name, default))
            return value if value.is_absolute() else (service_root / value).resolve()

        return cls(
            service_root=service_root,
            store=os.getenv("FATHIYA_STORE", "sqlite").lower(),
            sqlite_path=resolve_path("FATHIYA_SQLITE_PATH", "runtime/fathiya_runtime.db"),
            worker_id=os.getenv("FATHIYA_WORKER_ID", "local-primary"),
            worker_name=os.getenv("FATHIYA_WORKER_NAME", "FATHIYA Local Primary"),
            repo_root=resolve_path("FATHIYA_REPO_ROOT", "../.."),
            knowledge_root=resolve_path("FATHIYA_KNOWLEDGE_ROOT", "../../knowledge"),
            tool_inventory_path=resolve_path(
                "FATHIYA_TOOL_INVENTORY_PATH",
                "../../knowledge/runtime/connected_tool_inventory_v1.json",
            ),
            command_profiles_path=resolve_path(
                "FATHIYA_COMMAND_PROFILES_PATH",
                "config/command_profiles.json",
            ),
            connector_profiles_path=resolve_path(
                "FATHIYA_CONNECTOR_PROFILES_PATH",
                "config/connector_profiles.json",
            ),
            enable_hf_retrieval=os.getenv("FATHIYA_ENABLE_HF_RETRIEVAL", "false").lower()
            in {"1", "true", "yes"},
            hf_model=os.getenv(
                "FATHIYA_HF_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            ),
            enable_local_generation=os.getenv(
                "FATHIYA_ENABLE_LOCAL_GENERATION",
                "false",
            ).lower()
            in {"1", "true", "yes"},
            enable_local_planning=os.getenv(
                "FATHIYA_ENABLE_LOCAL_PLANNING",
                "false",
            ).lower()
            in {"1", "true", "yes"},
            local_model=os.getenv(
                "FATHIYA_LOCAL_MODEL",
                "Qwen/Qwen2.5-0.5B-Instruct",
            ),
            local_max_new_tokens=max(
                64,
                min(1024, int(os.getenv("FATHIYA_LOCAL_MAX_NEW_TOKENS", "128"))),
            ),
            local_max_generation_seconds=max(
                5.0,
                min(
                    60.0,
                    float(os.getenv("FATHIYA_LOCAL_MAX_GENERATION_SECONDS", "20")),
                ),
            ),
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
            openrouter_model=os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
            max_tool_steps=max(1, min(12, int(os.getenv("FATHIYA_MAX_TOOL_STEPS", "6")))),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            n8n_base_url=os.getenv("N8N_BASE_URL", "http://127.0.0.1:5678").rstrip("/"),
            n8n_api_key=os.getenv("N8N_API_KEY", ""),
            n8n_webhook_url=os.getenv("FATHIYA_N8N_WEBHOOK_URL", ""),
            kali_wsl_distro=os.getenv("KALI_WSL_DISTRO", "kali-linux"),
        )
