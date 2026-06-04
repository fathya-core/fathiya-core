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
    connector_dispatch_token_file: Path
    connector_dispatch_token: str
    operator_origins: tuple[str, ...]
    zapier_mcp_url: str
    zapier_mcp_token_path: Path
    zapier_mcp_access_token: str
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
    max_agent_rounds: int
    supabase_url: str
    supabase_service_role_key: str
    n8n_base_url: str
    n8n_api_key: str
    n8n_webhook_url: str
    kali_wsl_distro: str
    trading_sqlite_path: Path
    trading_mode: str
    trading_symbol: str
    trading_market_provider: str
    trading_market_timeout_seconds: float
    trading_tick_seconds: float
    trading_initial_cash: float
    trading_max_order_notional: float
    trading_max_position_notional: float
    trading_daily_loss_limit: float
    trading_min_order_notional: float
    trading_fee_bps: float
    trading_slippage_bps: float
    trading_signal_window: int
    trading_signal_threshold: float
    trading_evaluation_deadband: float
    trading_advisory_ttl_seconds: float
    trading_advisory_min_confidence: float
    trading_max_receipts: int
    trading_testnet_provider: str
    trading_testnet_base_url: str
    trading_testnet_symbol: str
    trading_testnet_api_key: str
    trading_testnet_api_secret: str
    trading_testnet_execution_enabled: bool
    trading_testnet_recv_window_ms: int

    @classmethod
    def load(cls) -> "RuntimeConfig":
        service_root = Path(__file__).resolve().parents[1]
        load_dotenv(service_root / ".env")

        def resolve_path(name: str, default: str) -> Path:
            value = Path(os.getenv(name, default))
            return value if value.is_absolute() else (service_root / value).resolve()

        connector_dispatch_token_file = resolve_path(
            "FATHIYA_CONNECTOR_DISPATCH_TOKEN_FILE",
            "runtime/connector_dispatch.token",
        )
        connector_dispatch_token = os.getenv(
            "FATHIYA_CONNECTOR_DISPATCH_TOKEN",
            "",
        ).strip()
        if not connector_dispatch_token and connector_dispatch_token_file.exists():
            connector_dispatch_token = connector_dispatch_token_file.read_text(
                encoding="utf-8",
            ).strip()

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
            connector_dispatch_token_file=connector_dispatch_token_file,
            connector_dispatch_token=connector_dispatch_token,
            operator_origins=tuple(
                origin.strip().rstrip("/")
                for origin in os.getenv(
                    "FATHIYA_OPERATOR_ORIGINS",
                    (
                        "https://fathya-core.com,"
                        "https://www.fathya-core.com,"
                        "https://fathya-project.github.io"
                    ),
                ).split(",")
                if origin.strip()
            ),
            zapier_mcp_url=os.getenv(
                "FATHIYA_ZAPIER_MCP_URL",
                "https://mcp.zapier.com/api/v1/connect",
            ).rstrip("/"),
            zapier_mcp_token_path=resolve_path(
                "FATHIYA_ZAPIER_MCP_TOKEN_PATH",
                "runtime/zapier_mcp_oauth.json",
            ),
            zapier_mcp_access_token=os.getenv(
                "FATHIYA_ZAPIER_MCP_ACCESS_TOKEN",
                "",
            ).strip(),
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
            max_agent_rounds=max(
                1,
                min(8, int(os.getenv("FATHIYA_MAX_AGENT_ROUNDS", "4"))),
            ),
            supabase_url=os.getenv("SUPABASE_URL", "").rstrip("/"),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            n8n_base_url=os.getenv("N8N_BASE_URL", "http://127.0.0.1:5678").rstrip("/"),
            n8n_api_key=os.getenv("N8N_API_KEY", ""),
            n8n_webhook_url=os.getenv("FATHIYA_N8N_WEBHOOK_URL", ""),
            kali_wsl_distro=os.getenv("KALI_WSL_DISTRO", "kali-linux"),
            trading_sqlite_path=resolve_path(
                "FATHIYA_TRADING_SQLITE_PATH",
                "runtime/fathiya_trading.db",
            ),
            trading_mode=os.getenv("FATHIYA_TRADING_MODE", "paper").strip().lower(),
            trading_symbol=os.getenv("FATHIYA_TRADING_SYMBOL", "BTC-USD").strip().upper(),
            trading_market_provider=os.getenv(
                "FATHIYA_TRADING_MARKET_PROVIDER",
                "coinbase_spot",
            )
            .strip()
            .lower(),
            trading_market_timeout_seconds=max(
                0.1,
                min(
                    10.0,
                    float(os.getenv("FATHIYA_TRADING_MARKET_TIMEOUT_SECONDS", "0.8")),
                ),
            ),
            trading_tick_seconds=max(
                0.05,
                min(60.0, float(os.getenv("FATHIYA_TRADING_TICK_SECONDS", "1"))),
            ),
            trading_initial_cash=max(
                100.0,
                float(os.getenv("FATHIYA_TRADING_INITIAL_CASH", "10000")),
            ),
            trading_max_order_notional=max(
                1.0,
                float(os.getenv("FATHIYA_TRADING_MAX_ORDER_NOTIONAL", "100")),
            ),
            trading_max_position_notional=max(
                1.0,
                float(os.getenv("FATHIYA_TRADING_MAX_POSITION_NOTIONAL", "500")),
            ),
            trading_daily_loss_limit=max(
                1.0,
                float(os.getenv("FATHIYA_TRADING_DAILY_LOSS_LIMIT", "100")),
            ),
            trading_min_order_notional=max(
                1.0,
                float(os.getenv("FATHIYA_TRADING_MIN_ORDER_NOTIONAL", "10")),
            ),
            trading_fee_bps=max(
                0.0,
                float(os.getenv("FATHIYA_TRADING_FEE_BPS", "1")),
            ),
            trading_slippage_bps=max(
                0.0,
                float(os.getenv("FATHIYA_TRADING_SLIPPAGE_BPS", "2")),
            ),
            trading_signal_window=max(
                2,
                min(120, int(os.getenv("FATHIYA_TRADING_SIGNAL_WINDOW", "4"))),
            ),
            trading_signal_threshold=max(
                0.000001,
                min(
                    1.0,
                    float(os.getenv("FATHIYA_TRADING_SIGNAL_THRESHOLD", "0.001")),
                ),
            ),
            trading_evaluation_deadband=max(
                0.0,
                min(
                    0.1,
                    float(os.getenv("FATHIYA_TRADING_EVALUATION_DEADBAND", "0.00005")),
                ),
            ),
            trading_advisory_ttl_seconds=max(
                10.0,
                min(
                    86_400.0,
                    float(os.getenv("FATHIYA_TRADING_ADVISORY_TTL_SECONDS", "300")),
                ),
            ),
            trading_advisory_min_confidence=max(
                0.0,
                min(
                    1.0,
                    float(os.getenv("FATHIYA_TRADING_ADVISORY_MIN_CONFIDENCE", "0.7")),
                ),
            ),
            trading_max_receipts=max(
                1_000,
                min(
                    5_000_000,
                    int(os.getenv("FATHIYA_TRADING_MAX_RECEIPTS", "100000")),
                ),
            ),
            trading_testnet_provider=os.getenv(
                "FATHIYA_TRADING_TESTNET_PROVIDER",
                "binance_spot_testnet",
            )
            .strip()
            .lower(),
            trading_testnet_base_url=os.getenv(
                "FATHIYA_TRADING_TESTNET_BASE_URL",
                "https://testnet.binance.vision",
            ).rstrip("/"),
            trading_testnet_symbol=os.getenv(
                "FATHIYA_TRADING_TESTNET_SYMBOL",
                "BTCUSDT",
            )
            .strip()
            .upper(),
            trading_testnet_api_key=os.getenv(
                "FATHIYA_TRADING_TESTNET_API_KEY",
                "",
            ).strip(),
            trading_testnet_api_secret=os.getenv(
                "FATHIYA_TRADING_TESTNET_API_SECRET",
                "",
            ).strip(),
            trading_testnet_execution_enabled=os.getenv(
                "FATHIYA_TRADING_TESTNET_EXECUTION_ENABLED",
                "false",
            ).lower()
            in {"1", "true", "yes"},
            trading_testnet_recv_window_ms=max(
                1_000,
                min(
                    5_000,
                    int(os.getenv("FATHIYA_TRADING_TESTNET_RECV_WINDOW_MS", "3000")),
                ),
            ),
        )
