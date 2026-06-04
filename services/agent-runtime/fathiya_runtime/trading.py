from __future__ import annotations

import json
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

from .store import now_iso


MONEY_QUANTUM = Decimal("0.00000001")
ZERO = Decimal("0")


def _decimal(value: Decimal | float | int | str) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def _as_float(value: Decimal) -> float:
    return float(_money(value))


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
                CREATE INDEX IF NOT EXISTS idx_trading_cycles_created_at
                  ON trading_cycles(created_at DESC);
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
        return deleted.rowcount

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trading_cycles ORDER BY created_at DESC LIMIT ?",
                (max(1, min(200, int(limit))),),
            ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["mode"] = "paper"
            for key in ("tick", "prediction", "risk", "fill", "portfolio"):
                item[key] = json.loads(item[key]) if item[key] else None
            result.append(item)
        return result

    def count(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM trading_cycles").fetchone()
        return int(row["count"])


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
    ):
        self.symbol = symbol
        self.ledger = ledger
        self.market = market
        self.signal_model = signal_model
        self.broker = broker
        self.risk = risk
        self.interval_seconds = max(0.05, interval_seconds)
        self.requested_mode = requested_mode
        self.mode = "paper"
        self._running = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()
        self._last_error: str | None = None
        self._last_cycle: dict[str, Any] | None = None
        state = self.ledger.load_state("engine") or {}
        self._last_price = _decimal(state.get("last_price", "0"))
        self._cycle_count = self.ledger.count()

    @classmethod
    def from_config(cls, config: Any) -> "PaperTradingAgent":
        ledger = TradingLedger(
            config.trading_sqlite_path,
            max_cycles=config.trading_max_receipts,
        )
        ledger.initialize()
        state = ledger.load_state("broker")
        return cls(
            symbol=config.trading_symbol,
            ledger=ledger,
            market=SyntheticSecondMarket(config.trading_symbol),
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
        )

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
            prediction = self.signal_model.predict(tick)
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
            self.ledger.save_state("broker", self.broker.export_state())
            self.ledger.save_state(
                "engine",
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
        return self.ledger.recent(limit)

    def status(self) -> dict[str, Any]:
        with self._lock:
            mark_price = self._last_price
            recent = self.ledger.recent(1)
            latest = self._last_cycle or (recent[0] if recent else None)
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
                "signal_model": self.signal_model.name,
                "cycle_count": self._cycle_count,
                "last_error": self._last_error,
                "latest_receipt_id": latest.get("receipt_id") if latest else None,
                "latest_cycle": latest,
                "portfolio": self.broker.portfolio(mark_price),
                "risk_limits": self.risk.as_dict(),
            }

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
