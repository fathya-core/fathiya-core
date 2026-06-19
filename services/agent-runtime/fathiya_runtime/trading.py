from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import threading
import time
import uuid
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from typing import Any, Iterator, Protocol
from urllib.parse import urlencode, urlparse

import requests

from .store import now_iso


MONEY_QUANTUM = Decimal("0.00000001")
ZERO = Decimal("0")
COINBASE_SYMBOL = re.compile(r"^[A-Z0-9]{2,12}-[A-Z0-9]{2,12}$")


def _decimal(value: Decimal | float | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def _as_float(value: Decimal) -> float:
    return float(_money(value))


def _safe_error_name(exc: Exception) -> str:
    return type(exc).__name__


def _is_fallback_source(source: str) -> bool:
    return ":fallback_for:" in source


@dataclass(frozen=True)
class MarketTick:
    symbol: str
    price: Decimal
    observed_at: str
    source: str
    sequence: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": _as_float(self.price),
            "observed_at": self.observed_at,
            "source": self.source,
            "sequence": self.sequence,
        }


@dataclass(frozen=True)
class Prediction:
    action: str
    score: float
    confidence: float
    horizon_seconds: int
    model: str
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "score": self.score,
            "confidence": self.confidence,
            "horizon_seconds": self.horizon_seconds,
            "model": self.model,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class StrategyAdvisory:
    action: str
    confidence: float
    rationale: str
    provider: str
    generated_at: str
    expires_at: str

    def active(self) -> bool:
        try:
            return datetime.fromisoformat(self.expires_at) > datetime.now(UTC)
        except ValueError:
            return False

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "provider": self.provider,
            "generated_at": self.generated_at,
            "expires_at": self.expires_at,
            "active": self.active(),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any] | None) -> "StrategyAdvisory | None":
        if not state:
            return None
        action = str(state.get("action") or "")
        if action not in {"buy", "sell", "hold"}:
            return None
        try:
            confidence = max(0.0, min(1.0, float(state.get("confidence", 0))))
        except (TypeError, ValueError):
            return None
        return cls(
            action=action,
            confidence=confidence,
            rationale=str(state.get("rationale") or "")[:400],
            provider=str(state.get("provider") or "unknown")[:120],
            generated_at=str(state.get("generated_at") or ""),
            expires_at=str(state.get("expires_at") or ""),
        )


@dataclass(frozen=True)
class RiskCheck:
    allowed: bool
    action: str
    order_notional: Decimal
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "order_notional": _as_float(self.order_notional),
            "reason": self.reason,
        }


class MarketDataProvider(Protocol):
    name: str
    symbol: str

    def next_tick(self) -> MarketTick: ...


class SignalModel(Protocol):
    name: str

    def predict(self, tick: MarketTick) -> Prediction: ...


class BinanceSpotTestnetGateway:
    """Secret-safe Binance Spot Testnet account and order gateway."""

    provider = "binance_spot_testnet"
    allowed_hosts = {"testnet.binance.vision"}

    def __init__(
        self,
        *,
        base_url: str,
        symbol: str,
        api_key: str,
        api_secret: str,
        execution_enabled: bool = False,
        recv_window_ms: int = 3000,
        timeout_seconds: float = 5.0,
    ):
        parsed = urlparse(base_url)
        if parsed.scheme != "https" or parsed.hostname not in self.allowed_hosts:
            raise ValueError("Trading Testnet base URL must use the approved Binance Testnet host")
        clean_symbol = symbol.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{5,24}", clean_symbol):
            raise ValueError("Trading Testnet symbol must be a Binance spot symbol")
        self.base_url = base_url.rstrip("/")
        self.symbol = clean_symbol
        self.api_key = api_key.strip()
        self.api_secret = api_secret.strip()
        self.execution_requested = bool(execution_enabled)
        self.recv_window_ms = max(1000, min(5000, int(recv_window_ms)))
        self.timeout_seconds = max(0.5, min(15.0, float(timeout_seconds)))

    @classmethod
    def from_config(cls, config: Any) -> "BinanceSpotTestnetGateway":
        if config.trading_testnet_provider != cls.provider:
            raise ValueError(
                f"Unsupported trading Testnet provider: {config.trading_testnet_provider}"
            )
        return cls(
            base_url=config.trading_testnet_base_url,
            symbol=config.trading_testnet_symbol,
            api_key=config.trading_testnet_api_key,
            api_secret=config.trading_testnet_api_secret,
            execution_enabled=config.trading_testnet_execution_enabled,
            recv_window_ms=config.trading_testnet_recv_window_ms,
            timeout_seconds=config.trading_market_timeout_seconds,
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    @property
    def execution_enabled(self) -> bool:
        return self.configured and self.execution_requested

    def status(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "environment": "testnet",
            "configured": self.configured,
            "execution_enabled": self.execution_enabled,
            "symbol": self.symbol,
            "base_host": urlparse(self.base_url).hostname,
            "withdrawal_permission_allowed": False,
            "real_funds_possible": False,
        }

    def probe(self) -> dict[str, Any]:
        public = self._request("GET", "/api/v3/time")
        result = {
            **self.status(),
            "reachable": public["ok"],
            "authenticated": False,
            "can_trade": False,
            "permissions": [],
            "error": public["error"],
        }
        if not self.configured or not public["ok"]:
            return result
        account = self._signed_request(
            "GET",
            "/api/v3/account",
            {"omitZeroBalances": "true"},
        )
        payload = account["payload"] if isinstance(account["payload"], dict) else {}
        return {
            **result,
            "authenticated": account["ok"],
            "can_trade": bool(payload.get("canTrade")) if account["ok"] else False,
            "permissions": [
                str(permission)
                for permission in payload.get("permissions", [])
                if isinstance(permission, str)
            ][:20],
            "account_type": payload.get("accountType") if account["ok"] else None,
            "error": account["error"],
        }

    def market_order(
        self,
        *,
        side: str,
        quote_order_qty: Decimal | float | str | None = None,
        quantity: Decimal | float | str | None = None,
        validate_only: bool = True,
    ) -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Trading Testnet credentials are not configured")
        clean_side = side.strip().upper()
        if clean_side not in {"BUY", "SELL"}:
            raise ValueError("Trading Testnet side must be buy or sell")
        if not validate_only and not self.execution_enabled:
            raise RuntimeError(
                "Trading Testnet execution remains disabled until the local execution flag is enabled"
            )
        params: dict[str, Any] = {
            "symbol": self.symbol,
            "side": clean_side,
            "type": "MARKET",
            "newClientOrderId": f"fathiya-{uuid.uuid4().hex[:24]}",
        }
        if quote_order_qty is not None:
            value = _decimal(quote_order_qty)
            if value <= ZERO:
                raise ValueError("quote_order_qty must be greater than zero")
            params["quoteOrderQty"] = format(value, "f")
        elif quantity is not None:
            value = _decimal(quantity)
            if value <= ZERO:
                raise ValueError("quantity must be greater than zero")
            params["quantity"] = format(value, "f")
        else:
            raise ValueError("Trading Testnet market order requires quote_order_qty or quantity")
        response = self._signed_request(
            "POST",
            "/api/v3/order/test" if validate_only else "/api/v3/order",
            params,
        )
        if not response["ok"]:
            raise RuntimeError(response["error"] or "Trading Testnet rejected the order")
        payload = response["payload"] if isinstance(response["payload"], dict) else {}
        return {
            **self.status(),
            "validated": validate_only,
            "submitted": not validate_only,
            "side": clean_side.lower(),
            "quote_order_qty": params.get("quoteOrderQty"),
            "quantity": params.get("quantity"),
            "order": {
                key: payload.get(key)
                for key in (
                    "symbol",
                    "orderId",
                    "clientOrderId",
                    "transactTime",
                    "status",
                    "executedQty",
                    "cummulativeQuoteQty",
                )
                if key in payload
            },
        }

    def _signed_request(
        self,
        method: str,
        path: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        signed = {
            **params,
            "recvWindow": self.recv_window_ms,
            "timestamp": int(time.time() * 1000),
        }
        query = urlencode(signed)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return self._request(
            method,
            path,
            query=f"{query}&signature={signature}",
            headers={"X-MBX-APIKEY": self.api_key},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        query: str = "",
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{query}"
        try:
            response = requests.request(
                method,
                url,
                headers=headers or {},
                timeout=self.timeout_seconds,
            )
            try:
                payload: Any = response.json()
            except ValueError:
                payload = {}
            message = (
                str(payload.get("msg") or "")
                if isinstance(payload, dict)
                else ""
            )
            return {
                "ok": response.ok,
                "status_code": response.status_code,
                "payload": payload,
                "error": None
                if response.ok
                else f"Binance Testnet HTTP {response.status_code}: {message[:300]}",
            }
        except requests.RequestException as exc:
            return {
                "ok": False,
                "status_code": None,
                "payload": {},
                "error": f"Binance Testnet request failed: {_safe_error_name(exc)}",
            }


class SyntheticSecondMarket:
    """Deterministic paper-only market feed used until a broker feed is configured."""

    name = "synthetic_second_market"

    def __init__(
        self,
        symbol: str,
        *,
        start_price: Decimal | float | str = Decimal("100"),
        changes: list[Decimal | float | str] | None = None,
    ):
        self.symbol = symbol
        self._price = _decimal(start_price)
        self._changes = [
            _decimal(value)
            for value in (
                changes
                or [
                    "0.0004",
                    "0.0007",
                    "0.0010",
                    "0.0005",
                    "-0.0002",
                    "-0.0008",
                    "-0.0011",
                    "-0.0004",
                    "0.0003",
                ]
            )
        ]
        self._sequence = 0
        self._lock = threading.Lock()

    def next_tick(self) -> MarketTick:
        with self._lock:
            change = self._changes[self._sequence % len(self._changes)]
            self._sequence += 1
            self._price = _money(self._price * (Decimal("1") + change))
            return MarketTick(
                symbol=self.symbol,
                price=self._price,
                observed_at=now_iso(),
                source=self.name,
                sequence=self._sequence,
            )


class CoinbaseSpotMarket:
    name = "coinbase_spot"

    def __init__(self, symbol: str, *, timeout_seconds: float = 0.8):
        if not COINBASE_SYMBOL.fullmatch(symbol):
            raise ValueError("Coinbase spot symbol must look like BTC-USD")
        self.symbol = symbol
        self.timeout_seconds = max(0.1, min(10.0, timeout_seconds))
        self._sequence = 0
        self._success_count = 0
        self._failure_count = 0
        self._last_error: str | None = None
        self._lock = threading.Lock()

    def next_tick(self) -> MarketTick:
        with self._lock:
            try:
                response = requests.get(
                    f"https://api.coinbase.com/v2/prices/{self.symbol}/spot",
                    headers={"User-Agent": "FATHIYA-Agent-Runtime/0.1"},
                    timeout=self.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                price = _decimal(payload["data"]["amount"])
                if price <= ZERO:
                    raise ValueError("Coinbase returned a non-positive spot price")
                self._sequence += 1
                self._success_count += 1
                self._last_error = None
                return MarketTick(
                    symbol=self.symbol,
                    price=_money(price),
                    observed_at=now_iso(),
                    source=self.name,
                    sequence=self._sequence,
                )
            except Exception as exc:
                self._failure_count += 1
                self._last_error = _safe_error_name(exc)
                raise

    def health(self) -> dict[str, Any]:
        return {
            "provider": self.name,
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "last_error": self._last_error,
        }


class FallbackMarketDataProvider:
    def __init__(self, primary: MarketDataProvider, fallback: MarketDataProvider):
        if primary.symbol != fallback.symbol:
            raise ValueError("Primary and fallback market symbols must match")
        self.primary = primary
        self.fallback = fallback
        self.symbol = primary.symbol
        self.name = f"{primary.name}+{fallback.name}_fallback"
        self._fallback_count = 0
        self._last_error: str | None = None
        self._last_primary_tick: MarketTick | None = None
        self._active_source: str | None = None

    def next_tick(self) -> MarketTick:
        try:
            tick = self.primary.next_tick()
            self._last_error = None
            self._last_primary_tick = tick
            self._active_source = tick.source
            return tick
        except Exception as exc:
            self._fallback_count += 1
            self._last_error = _safe_error_name(exc)
            fallback_tick = self.fallback.next_tick()
            tick = MarketTick(
                symbol=fallback_tick.symbol,
                price=(
                    self._last_primary_tick.price
                    if self._last_primary_tick
                    else fallback_tick.price
                ),
                observed_at=fallback_tick.observed_at,
                source=f"{fallback_tick.source}:fallback_for:{self.primary.name}",
                sequence=fallback_tick.sequence,
            )
            self._active_source = tick.source
            return tick

    def health(self) -> dict[str, Any]:
        primary_health = getattr(self.primary, "health", None)
        return {
            "provider": self.name,
            "active_source": self._active_source,
            "fallback_active": bool(
                self._active_source and _is_fallback_source(self._active_source)
            ),
            "fallback_count": self._fallback_count,
            "last_error": self._last_error,
            "primary": primary_health() if callable(primary_health) else None,
        }


class MomentumSignalModel:
    name = "momentum_v1"

    def __init__(self, *, window: int = 4, threshold: float = 0.001):
        self.window = max(2, window)
        self.threshold = max(0.000001, threshold)
        self._prices: deque[Decimal] = deque(maxlen=self.window)

    def predict(self, tick: MarketTick) -> Prediction:
        self._prices.append(tick.price)
        if len(self._prices) < self.window:
            return Prediction(
                action="hold",
                score=0.0,
                confidence=0.0,
                horizon_seconds=1,
                model=self.name,
                reason=f"warming_up:{len(self._prices)}/{self.window}",
            )
        baseline = self._prices[0]
        momentum = float((tick.price / baseline) - Decimal("1"))
        if momentum >= self.threshold:
            action = "buy"
        elif momentum <= -self.threshold:
            action = "sell"
        else:
            action = "hold"
        return Prediction(
            action=action,
            score=momentum,
            confidence=min(1.0, abs(momentum) / self.threshold),
            horizon_seconds=1,
            model=self.name,
            reason=f"{self.window}-tick momentum {momentum:.6f}",
        )


class PaperBroker:
    def __init__(
        self,
        *,
        initial_cash: Decimal | float | str,
        fee_bps: Decimal | float | str = "1",
        slippage_bps: Decimal | float | str = "2",
        state: dict[str, Any] | None = None,
    ):
        self.initial_cash = _decimal(initial_cash)
        self.fee_rate = _decimal(fee_bps) / Decimal("10000")
        self.slippage_rate = _decimal(slippage_bps) / Decimal("10000")
        state = state or {}
        self.cash = _decimal(state.get("cash", self.initial_cash))
        self.quantity = _decimal(state.get("quantity", "0"))
        self.average_price = _decimal(state.get("average_price", "0"))
        self.realized_pnl = _decimal(state.get("realized_pnl", "0"))
        self.fees_paid = _decimal(state.get("fees_paid", "0"))
        self.session_date = str(
            state.get("session_date", datetime.now(UTC).date().isoformat())
        )
        self.day_start_equity = _decimal(
            state.get("day_start_equity", self.initial_cash)
        )

    def execute(
        self,
        action: str,
        order_notional: Decimal,
        tick: MarketTick,
    ) -> dict[str, Any]:
        if action == "buy":
            gross = min(order_notional, self.cash / (Decimal("1") + self.fee_rate))
            fill_price = _money(tick.price * (Decimal("1") + self.slippage_rate))
            quantity = (gross / fill_price).quantize(MONEY_QUANTUM, rounding=ROUND_DOWN)
            gross = _money(quantity * fill_price)
            fee = _money(gross * self.fee_rate)
            previous_cost = self.quantity * self.average_price
            self.cash = _money(self.cash - gross - fee)
            self.quantity = _money(self.quantity + quantity)
            self.average_price = (
                _money((previous_cost + gross) / self.quantity)
                if self.quantity > ZERO
                else ZERO
            )
            realized = ZERO
        elif action == "sell":
            fill_price = _money(tick.price * (Decimal("1") - self.slippage_rate))
            quantity = min(
                self.quantity,
                (order_notional / fill_price).quantize(MONEY_QUANTUM, rounding=ROUND_DOWN),
            )
            gross = _money(quantity * fill_price)
            fee = _money(gross * self.fee_rate)
            realized = _money((fill_price - self.average_price) * quantity - fee)
            self.cash = _money(self.cash + gross - fee)
            self.quantity = _money(self.quantity - quantity)
            self.realized_pnl = _money(self.realized_pnl + realized)
            if self.quantity <= ZERO:
                self.quantity = ZERO
                self.average_price = ZERO
        else:
            raise ValueError(f"Unsupported paper action: {action}")
        self.fees_paid = _money(self.fees_paid + fee)
        return {
            "fill_id": str(uuid.uuid4()),
            "mode": "paper",
            "symbol": tick.symbol,
            "action": action,
            "quantity": _as_float(quantity),
            "fill_price": _as_float(fill_price),
            "gross_notional": _as_float(gross),
            "fee": _as_float(fee),
            "realized_pnl": _as_float(realized),
            "filled_at": now_iso(),
        }

    def portfolio(self, mark_price: Decimal) -> dict[str, Any]:
        position_notional = _money(self.quantity * mark_price)
        unrealized_pnl = _money((mark_price - self.average_price) * self.quantity)
        equity = _money(self.cash + position_notional)
        today = datetime.now(UTC).date().isoformat()
        if self.session_date != today:
            self.session_date = today
            self.day_start_equity = equity
        return {
            "initial_cash": _as_float(self.initial_cash),
            "cash": _as_float(self.cash),
            "quantity": _as_float(self.quantity),
            "average_price": _as_float(self.average_price),
            "mark_price": _as_float(mark_price),
            "position_notional": _as_float(position_notional),
            "unrealized_pnl": _as_float(unrealized_pnl),
            "realized_pnl": _as_float(self.realized_pnl),
            "fees_paid": _as_float(self.fees_paid),
            "equity": _as_float(equity),
            "net_pnl": _as_float(equity - self.initial_cash),
            "daily_pnl": _as_float(equity - self.day_start_equity),
        }

    def export_state(self) -> dict[str, str]:
        return {
            "cash": str(self.cash),
            "quantity": str(self.quantity),
            "average_price": str(self.average_price),
            "realized_pnl": str(self.realized_pnl),
            "fees_paid": str(self.fees_paid),
            "session_date": self.session_date,
            "day_start_equity": str(self.day_start_equity),
        }


class TradingRiskEngine:
    def __init__(
        self,
        *,
        max_order_notional: Decimal | float | str,
        max_position_notional: Decimal | float | str,
        daily_loss_limit: Decimal | float | str,
        min_order_notional: Decimal | float | str = "10",
        max_tick_age_seconds: float = 3.0,
    ):
        self.max_order_notional = _decimal(max_order_notional)
        self.max_position_notional = _decimal(max_position_notional)
        self.daily_loss_limit = _decimal(daily_loss_limit)
        self.min_order_notional = _decimal(min_order_notional)
        self.max_tick_age_seconds = max(0.1, max_tick_age_seconds)

    def evaluate(
        self,
        prediction: Prediction,
        tick: MarketTick,
        portfolio: dict[str, Any],
    ) -> RiskCheck:
        tick_time = datetime.fromisoformat(tick.observed_at)
        age_seconds = (datetime.now(UTC) - tick_time).total_seconds()
        if age_seconds > self.max_tick_age_seconds:
            return RiskCheck(False, "hold", ZERO, "stale_market_tick")
        if _is_fallback_source(tick.source):
            return RiskCheck(False, "hold", ZERO, "fallback_market_tick")
        daily_pnl = _decimal(portfolio["daily_pnl"])
        if daily_pnl <= -self.daily_loss_limit:
            return RiskCheck(False, "hold", ZERO, "daily_loss_limit_reached")
        if prediction.action == "hold":
            return RiskCheck(False, "hold", ZERO, "signal_hold")
        if prediction.action == "buy":
            capacity = max(
                ZERO,
                self.max_position_notional - _decimal(portfolio["position_notional"]),
            )
            notional = min(
                self.max_order_notional,
                capacity,
                _decimal(portfolio["cash"]),
            )
            if notional < self.min_order_notional:
                return RiskCheck(False, "hold", ZERO, "buy_capacity_below_minimum")
            return RiskCheck(True, "buy", _money(notional), "paper_limits_passed")
        if prediction.action == "sell":
            notional = min(
                self.max_order_notional,
                _decimal(portfolio["position_notional"]),
            )
            if notional < self.min_order_notional:
                return RiskCheck(False, "hold", ZERO, "no_long_position_to_sell")
            return RiskCheck(True, "sell", _money(notional), "paper_limits_passed")
        return RiskCheck(False, "hold", ZERO, "unknown_signal_action")

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_order_notional": _as_float(self.max_order_notional),
            "max_position_notional": _as_float(self.max_position_notional),
            "daily_loss_limit": _as_float(self.daily_loss_limit),
            "min_order_notional": _as_float(self.min_order_notional),
            "max_tick_age_seconds": self.max_tick_age_seconds,
            "long_only": True,
        }


class TradingLedger:
    def __init__(self, path: Path, *, max_cycles: int = 100_000):
        self.path = path
        self.max_cycles = max(10, max_cycles)
        self._prune_interval = min(1_000, self.max_cycles)
        self._writes_since_prune = 0
        self._lock = threading.Lock()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS trading_cycles (
                  receipt_id TEXT PRIMARY KEY,
                  status TEXT NOT NULL,
                  symbol TEXT NOT NULL,
                  observed_at TEXT NOT NULL,
                  tick TEXT NOT NULL,
                  prediction TEXT NOT NULL,
                  risk TEXT NOT NULL,
                  fill TEXT,
                  portfolio TEXT NOT NULL,
                  latency_ms REAL NOT NULL,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trading_state (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS trading_evaluations (
                  receipt_id TEXT PRIMARY KEY,
                  symbol TEXT NOT NULL,
                  model TEXT NOT NULL,
                  action TEXT NOT NULL,
                  entry_price REAL NOT NULL,
                  exit_price REAL NOT NULL,
                  realized_return REAL NOT NULL,
                  strategy_return_bps REAL NOT NULL,
                  correct INTEGER NOT NULL,
                  horizon_seconds INTEGER NOT NULL,
                  evaluated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_trading_cycles_created_at
                  ON trading_cycles(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_trading_cycles_symbol_created_at
                  ON trading_cycles(symbol, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_trading_evaluations_symbol_evaluated_at
                  ON trading_evaluations(symbol, evaluated_at DESC);
                """
            )

    def load_state(self, key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM trading_state WHERE key=?",
                (key,),
            ).fetchone()
        return json.loads(row["value"]) if row else None

    def save_state(self, key: str, value: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trading_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                  value=excluded.value,
                  updated_at=excluded.updated_at
                """,
                (key, json.dumps(value, ensure_ascii=False), now_iso()),
            )

    def add_cycle(self, cycle: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO trading_cycles (
                  receipt_id, status, symbol, observed_at, tick, prediction,
                  risk, fill, portfolio, latency_ms, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cycle["receipt_id"],
                    cycle["status"],
                    cycle["tick"]["symbol"],
                    cycle["tick"]["observed_at"],
                    json.dumps(cycle["tick"], ensure_ascii=False),
                    json.dumps(cycle["prediction"], ensure_ascii=False),
                    json.dumps(cycle["risk"], ensure_ascii=False),
                    json.dumps(cycle["fill"], ensure_ascii=False)
                    if cycle["fill"]
                    else None,
                    json.dumps(cycle["portfolio"], ensure_ascii=False),
                    cycle["latency_ms"],
                    cycle["created_at"],
                ),
            )
        with self._lock:
            self._writes_since_prune += 1
            should_prune = self._writes_since_prune >= self._prune_interval
            if should_prune:
                self._writes_since_prune = 0
        if should_prune:
            self.prune()

    def add_evaluation(self, evaluation: dict[str, Any]) -> bool:
        with self._connect() as conn:
            inserted = conn.execute(
                """
                INSERT OR IGNORE INTO trading_evaluations (
                  receipt_id, symbol, model, action, entry_price, exit_price,
                  realized_return, strategy_return_bps, correct,
                  horizon_seconds, evaluated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation["receipt_id"],
                    evaluation["symbol"],
                    evaluation["model"],
                    evaluation["action"],
                    evaluation["entry_price"],
                    evaluation["exit_price"],
                    evaluation["realized_return"],
                    evaluation["strategy_return_bps"],
                    int(evaluation["correct"]),
                    evaluation["horizon_seconds"],
                    evaluation["evaluated_at"],
                ),
            )
        return inserted.rowcount == 1

    def prune(self) -> int:
        with self._connect() as conn:
            deleted = conn.execute(
                """
                DELETE FROM trading_cycles
                WHERE receipt_id IN (
                  SELECT receipt_id FROM trading_cycles
                  ORDER BY created_at DESC
                  LIMIT -1 OFFSET ?
                )
                """,
                (self.max_cycles,),
            )
            conn.execute(
                """
                DELETE FROM trading_evaluations
                WHERE receipt_id NOT IN (SELECT receipt_id FROM trading_cycles)
                """
            )
        return deleted.rowcount

    def recent(
        self,
        limit: int = 20,
        *,
        symbol: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._connect() as conn:
            bounded_limit = max(1, min(200, int(limit)))
            if symbol:
                rows = conn.execute(
                    """
                    SELECT * FROM trading_cycles
                    WHERE symbol=?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (symbol, bounded_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM trading_cycles ORDER BY created_at DESC LIMIT ?",
                    (bounded_limit,),
                ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["mode"] = "paper"
            for key in ("tick", "prediction", "risk", "fill", "portfolio"):
                item[key] = json.loads(item[key]) if item[key] else None
            result.append(item)
        return result

    def count(self, *, symbol: str | None = None) -> int:
        with self._connect() as conn:
            if symbol:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM trading_cycles WHERE symbol=?",
                    (symbol,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) AS count FROM trading_cycles"
                ).fetchone()
        return int(row["count"])

    def quality(self, symbol: str) -> dict[str, Any]:
        with self._connect() as conn:
            totals = conn.execute(
                """
                SELECT
                  COUNT(*) AS evaluated_count,
                  COALESCE(SUM(correct), 0) AS correct_count,
                  COALESCE(SUM(strategy_return_bps), 0) AS cumulative_return_bps,
                  COALESCE(AVG(strategy_return_bps), 0) AS average_return_bps
                FROM trading_evaluations
                WHERE symbol=?
                """,
                (symbol,),
            ).fetchone()
            latest = conn.execute(
                """
                SELECT * FROM trading_evaluations
                WHERE symbol=?
                ORDER BY evaluated_at DESC
                LIMIT 1
                """,
                (symbol,),
            ).fetchone()
        evaluated_count = int(totals["evaluated_count"])
        correct_count = int(totals["correct_count"])
        latest_evaluation = dict(latest) if latest else None
        if latest_evaluation:
            latest_evaluation["correct"] = bool(latest_evaluation["correct"])
        return {
            "evaluated_count": evaluated_count,
            "correct_count": correct_count,
            "directional_accuracy": (
                correct_count / evaluated_count if evaluated_count else None
            ),
            "cumulative_strategy_return_bps": round(
                float(totals["cumulative_return_bps"]),
                6,
            ),
            "average_strategy_return_bps": round(
                float(totals["average_return_bps"]),
                6,
            ),
            "latest_evaluation": latest_evaluation,
        }


def _cycle_cadence(
    cycles: list[dict[str, Any]],
    target_seconds: float,
) -> dict[str, Any]:
    timestamps: list[datetime] = []
    for cycle in cycles:
        created_at = str(cycle.get("created_at") or "")
        try:
            timestamps.append(datetime.fromisoformat(created_at))
        except ValueError:
            continue
    timestamps.sort()
    intervals = [
        (timestamps[index] - timestamps[index - 1]).total_seconds()
        for index in range(1, len(timestamps))
    ]
    latest = intervals[-1] if intervals else None
    average = sum(intervals) / len(intervals) if intervals else None
    maximum = max(intervals) if intervals else None
    tolerance = max(target_seconds * 1.5, target_seconds + 0.25)
    return {
        "target_seconds": round(float(target_seconds), 3),
        "target_tolerance_seconds": round(float(tolerance), 3),
        "sample_count": len(intervals),
        "latest_interval_seconds": round(float(latest), 3)
        if latest is not None
        else None,
        "average_interval_seconds": round(float(average), 3)
        if average is not None
        else None,
        "max_interval_seconds": round(float(maximum), 3)
        if maximum is not None
        else None,
        "within_target": latest <= tolerance if latest is not None else None,
    }


class PaperTradingAgent:
    def __init__(
        self,
        *,
        symbol: str,
        ledger: TradingLedger,
        market: MarketDataProvider,
        signal_model: SignalModel,
        broker: PaperBroker,
        risk: TradingRiskEngine,
        interval_seconds: float = 1.0,
        requested_mode: str = "paper",
        evaluation_deadband: float = 0.00005,
        advisory_min_confidence: float = 0.7,
    ):
        if market.symbol != symbol:
            raise ValueError("Trading agent and market provider symbols must match")
        self.symbol = symbol
        self.ledger = ledger
        self.market = market
        self.signal_model = signal_model
        self.broker = broker
        self.risk = risk
        self.interval_seconds = max(0.05, interval_seconds)
        self.requested_mode = requested_mode
        self.evaluation_deadband = max(0.0, min(1.0, evaluation_deadband))
        self.advisory_min_confidence = max(
            0.0,
            min(1.0, advisory_min_confidence),
        )
        self.mode = "paper"
        self._running = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._last_error: str | None = None
        recent = self.ledger.recent(1, symbol=self.symbol)
        self._last_cycle: dict[str, Any] | None = recent[0] if recent else None
        state = self.ledger.load_state(f"engine:{self.symbol}") or {}
        last_price = state.get("last_price")
        if last_price is None and self._last_cycle:
            last_price = self._last_cycle["tick"]["price"]
        self._last_price = _decimal(last_price or "0")
        self._cycle_count = self.ledger.count(symbol=self.symbol)
        self._advisory = StrategyAdvisory.from_state(
            self.ledger.load_state(f"advisory:{self.symbol}")
        )

    @classmethod
    def from_config(cls, config: Any) -> "PaperTradingAgent":
        ledger = TradingLedger(
            config.trading_sqlite_path,
            max_cycles=config.trading_max_receipts,
        )
        ledger.initialize()
        symbol = config.trading_symbol
        state = ledger.load_state(f"broker:{symbol}")
        engine_state = ledger.load_state(f"engine:{symbol}") or {}
        if config.trading_market_provider in {
            "synthetic",
            "synthetic_second_market",
        }:
            market: MarketDataProvider = SyntheticSecondMarket(symbol)
        elif config.trading_market_provider == "coinbase_spot":
            market = FallbackMarketDataProvider(
                CoinbaseSpotMarket(
                    symbol,
                    timeout_seconds=config.trading_market_timeout_seconds,
                ),
                SyntheticSecondMarket(
                    symbol,
                    start_price=engine_state.get("last_price", "100"),
                ),
            )
        else:
            raise ValueError(
                f"Unsupported trading market provider: {config.trading_market_provider}"
            )
        return cls(
            symbol=symbol,
            ledger=ledger,
            market=market,
            signal_model=MomentumSignalModel(
                window=config.trading_signal_window,
                threshold=config.trading_signal_threshold,
            ),
            broker=PaperBroker(
                initial_cash=config.trading_initial_cash,
                fee_bps=config.trading_fee_bps,
                slippage_bps=config.trading_slippage_bps,
                state=state,
            ),
            risk=TradingRiskEngine(
                max_order_notional=config.trading_max_order_notional,
                max_position_notional=config.trading_max_position_notional,
                daily_loss_limit=config.trading_daily_loss_limit,
                min_order_notional=config.trading_min_order_notional,
                max_tick_age_seconds=max(3.0, config.trading_tick_seconds * 3),
            ),
            interval_seconds=config.trading_tick_seconds,
            requested_mode=config.trading_mode,
            evaluation_deadband=config.trading_evaluation_deadband,
            advisory_min_confidence=config.trading_advisory_min_confidence,
        )

    def update_advisory(
        self,
        *,
        action: str,
        confidence: float,
        rationale: str,
        provider: str,
        ttl_seconds: float,
    ) -> dict[str, Any]:
        clean_action = action.strip().lower()
        if clean_action not in {"buy", "sell", "hold"}:
            raise ValueError("Strategy advisory action must be buy, sell, or hold")
        clean_confidence = max(0.0, min(1.0, float(confidence)))
        generated = datetime.now(UTC)
        expires = generated.timestamp() + max(1.0, min(86_400.0, ttl_seconds))
        advisory = StrategyAdvisory(
            action=clean_action,
            confidence=clean_confidence,
            rationale=" ".join(rationale.split())[:400],
            provider=provider.strip()[:120] or "unknown",
            generated_at=generated.isoformat(),
            expires_at=datetime.fromtimestamp(expires, UTC).isoformat(),
        )
        with self._lock:
            self._advisory = advisory
            self.ledger.save_state(f"advisory:{self.symbol}", advisory.as_dict())
            return advisory.as_dict()

    def start(self) -> dict[str, Any]:
        with self._lock:
            self._require_paper_mode()
            if self._running:
                return self.status()
            self._stop.clear()
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                name="fathiya-paper-trading-agent",
                daemon=True,
            )
            self._thread.start()
            return self.status()

    def stop(self) -> dict[str, Any]:
        with self._lock:
            thread = self._thread
            self._stop.set()
        if thread and thread is not threading.current_thread():
            thread.join(timeout=max(2.0, self.interval_seconds * 3))
        with self._lock:
            self._running = False
            return self.status()

    def run_cycle(self) -> dict[str, Any]:
        with self._lock:
            self._require_paper_mode()
            started = time.perf_counter()
            tick = self.market.next_tick()
            self._evaluate_previous_prediction(tick)
            prediction = self._apply_advisory(self.signal_model.predict(tick))
            portfolio_before = self.broker.portfolio(tick.price)
            risk = self.risk.evaluate(prediction, tick, portfolio_before)
            fill = (
                self.broker.execute(risk.action, risk.order_notional, tick)
                if risk.allowed
                else None
            )
            portfolio = self.broker.portfolio(tick.price)
            latency_ms = round((time.perf_counter() - started) * 1000, 3)
            receipt_id = (
                f"TR-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}-"
                f"{uuid.uuid4().hex[:8]}"
            )
            cycle = {
                "receipt_id": receipt_id,
                "status": "executed" if fill else "observed",
                "mode": self.mode,
                "tick": tick.as_dict(),
                "prediction": prediction.as_dict(),
                "risk": risk.as_dict(),
                "fill": fill,
                "portfolio": portfolio,
                "latency_ms": latency_ms,
                "created_at": now_iso(),
            }
            self.ledger.add_cycle(cycle)
            self.ledger.save_state(f"broker:{self.symbol}", self.broker.export_state())
            self.ledger.save_state(
                f"engine:{self.symbol}",
                {"last_price": str(tick.price), "last_receipt_id": receipt_id},
            )
            self._last_price = tick.price
            self._last_cycle = cycle
            self._cycle_count += 1
            self._last_error = None
            return cycle

    def tick_once(self) -> dict[str, Any]:
        with self._lock:
            if self._running:
                raise RuntimeError(
                    "Manual paper tick is blocked while the automatic loop is running."
                )
            return self.run_cycle()

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.ledger.recent(limit, symbol=self.symbol)

    def status(self) -> dict[str, Any]:
        with self._lock:
            mark_price = self._last_price
            recent = self.ledger.recent(20, symbol=self.symbol)
            latest = self._last_cycle or (recent[0] if recent else None)
            market_health = getattr(self.market, "health", None)
            return {
                "agent": "trading-primary",
                "running": self._running,
                "mode": self.mode,
                "requested_mode": self.requested_mode,
                "live_execution_enabled": False,
                "live_execution_block_reason": (
                    "No broker account is configured and live execution is not implemented."
                ),
                "symbol": self.symbol,
                "cycle_target_seconds": self.interval_seconds,
                "market_provider": self.market.name,
                "current_market_source": (
                    latest["tick"]["source"] if latest else None
                ),
                "market_health": market_health() if callable(market_health) else None,
                "signal_model": self.signal_model.name,
                "strategy_advisory": (
                    self._advisory.as_dict() if self._advisory else None
                ),
                "strategy_advisory_policy": {
                    "mode": "veto_only",
                    "min_confidence": self.advisory_min_confidence,
                    "can_originate_orders": False,
                },
                "cycle_count": self._cycle_count,
                "last_error": self._last_error,
                "latest_receipt_id": latest.get("receipt_id") if latest else None,
                "latest_cycle": latest,
                "execution_cadence": _cycle_cadence(recent, self.interval_seconds),
                "portfolio": self.broker.portfolio(mark_price),
                "prediction_quality": self.ledger.quality(self.symbol),
                "risk_limits": self.risk.as_dict(),
            }

    def _apply_advisory(self, base: Prediction) -> Prediction:
        advisory = self._advisory
        if (
            not advisory
            or not advisory.active()
            or advisory.confidence < self.advisory_min_confidence
            or base.action == "hold"
        ):
            return base
        if advisory.action != base.action:
            return Prediction(
                action="hold",
                score=0.0,
                confidence=advisory.confidence,
                horizon_seconds=base.horizon_seconds,
                model=f"{base.model}+advisor_veto",
                reason=(
                    f"advisor_veto:{advisory.provider}:{advisory.action}:"
                    f"{advisory.rationale[:160]}"
                ),
            )
        return Prediction(
            action=base.action,
            score=base.score,
            confidence=max(base.confidence, advisory.confidence),
            horizon_seconds=base.horizon_seconds,
            model=f"{base.model}+advisor_confirmed",
            reason=(
                f"{base.reason}; advisor_confirmed:{advisory.provider}:"
                f"{advisory.rationale[:160]}"
            ),
        )

    def _evaluate_previous_prediction(self, exit_tick: MarketTick) -> dict[str, Any] | None:
        if _is_fallback_source(exit_tick.source):
            return None
        recent = self.ledger.recent(1, symbol=self.symbol)
        if not recent:
            return None
        previous = recent[0]
        entry_tick = previous["tick"]
        prediction = previous["prediction"]
        if _is_fallback_source(entry_tick["source"]) or str(
            prediction["reason"]
        ).startswith("warming_up:"):
            return None
        entry_price = _decimal(entry_tick["price"])
        if entry_price <= ZERO:
            return None
        elapsed_seconds = (
            datetime.fromisoformat(exit_tick.observed_at)
            - datetime.fromisoformat(entry_tick["observed_at"])
        ).total_seconds()
        horizon_seconds = int(prediction["horizon_seconds"])
        if elapsed_seconds < 0 or elapsed_seconds > max(3.0, horizon_seconds * 3.0):
            return None
        realized_return = (exit_tick.price / entry_price) - Decimal("1")
        action = prediction["action"]
        if action == "buy":
            correct = realized_return > _decimal(self.evaluation_deadband)
            strategy_return = realized_return
        elif action == "sell":
            correct = realized_return < -_decimal(self.evaluation_deadband)
            strategy_return = -realized_return
        else:
            correct = abs(realized_return) <= _decimal(self.evaluation_deadband)
            strategy_return = ZERO
        evaluation = {
            "receipt_id": previous["receipt_id"],
            "symbol": self.symbol,
            "model": prediction["model"],
            "action": action,
            "entry_price": _as_float(entry_price),
            "exit_price": _as_float(exit_tick.price),
            "realized_return": round(float(realized_return), 10),
            "strategy_return_bps": round(float(strategy_return * Decimal("10000")), 6),
            "correct": bool(correct),
            "horizon_seconds": horizon_seconds,
            "evaluated_at": now_iso(),
        }
        return evaluation if self.ledger.add_evaluation(evaluation) else None

    def _run_loop(self) -> None:
        next_run = time.monotonic()
        try:
            while not self._stop.is_set():
                try:
                    self.run_cycle()
                except Exception as exc:
                    with self._lock:
                        self._last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
                next_run += self.interval_seconds
                wait_seconds = max(0.0, next_run - time.monotonic())
                self._stop.wait(wait_seconds)
        finally:
            with self._lock:
                self._running = False

    def _require_paper_mode(self) -> None:
        if self.requested_mode != "paper":
            raise RuntimeError(
                "Live trading remains blocked until a broker connector and explicit "
                "financial approval policy are configured."
            )
