from __future__ import annotations

import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path

from fathiya_runtime.trading import (
    MomentumSignalModel,
    PaperBroker,
    PaperTradingAgent,
    SyntheticSecondMarket,
    TradingLedger,
    TradingRiskEngine,
)


class PaperTradingAgentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.ledger = TradingLedger(Path(self.temp.name) / "trading.db")
        self.ledger.initialize()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def build_agent(
        self,
        *,
        changes: list[str] | None = None,
        requested_mode: str = "paper",
        interval_seconds: float = 0.05,
        daily_loss_limit: str = "100",
    ) -> PaperTradingAgent:
        return PaperTradingAgent(
            symbol="TEST-USD",
            ledger=self.ledger,
            market=SyntheticSecondMarket(
                "TEST-USD",
                start_price="100",
                changes=changes or ["0.01", "0.01", "0.01", "-0.02", "-0.02"],
            ),
            signal_model=MomentumSignalModel(window=3, threshold=0.005),
            broker=PaperBroker(initial_cash="1000", fee_bps="1", slippage_bps="1"),
            risk=TradingRiskEngine(
                max_order_notional="100",
                max_position_notional="200",
                daily_loss_limit=daily_loss_limit,
                min_order_notional="10",
                max_tick_age_seconds=2,
            ),
            interval_seconds=interval_seconds,
            requested_mode=requested_mode,
        )

    def test_second_cycle_predicts_executes_and_records_receipts(self) -> None:
        agent = self.build_agent()
        cycles = [agent.run_cycle() for _ in range(5)]

        self.assertEqual(cycles[0]["prediction"]["action"], "hold")
        self.assertEqual(cycles[2]["prediction"]["action"], "buy")
        self.assertEqual(cycles[2]["status"], "executed")
        self.assertLess(cycles[2]["latency_ms"], 1000)
        self.assertTrue(cycles[2]["receipt_id"].startswith("TR-"))
        self.assertGreater(cycles[2]["portfolio"]["quantity"], 0)
        self.assertLessEqual(cycles[2]["portfolio"]["position_notional"], 200.01)
        self.assertIn("daily_pnl", cycles[2]["portfolio"])
        self.assertEqual(len(agent.recent(10)), 5)

    def test_background_loop_runs_at_configured_cadence_and_stops(self) -> None:
        agent = self.build_agent(interval_seconds=0.05)
        agent.start()
        time.sleep(0.18)
        with self.assertRaisesRegex(RuntimeError, "Manual paper tick is blocked"):
            agent.tick_once()
        status = agent.stop()

        self.assertFalse(status["running"])
        self.assertGreaterEqual(status["cycle_count"], 3)
        self.assertEqual(status["mode"], "paper")
        self.assertFalse(status["live_execution_enabled"])

    def test_live_mode_is_blocked_without_broker_policy(self) -> None:
        agent = self.build_agent(requested_mode="live")

        with self.assertRaisesRegex(RuntimeError, "Live trading remains blocked"):
            agent.run_cycle()
        with self.assertRaisesRegex(RuntimeError, "Live trading remains blocked"):
            agent.start()

    def test_ledger_prunes_old_cycles_to_configured_limit(self) -> None:
        ledger = TradingLedger(Path(self.temp.name) / "bounded.db", max_cycles=10)
        ledger.initialize()
        agent = PaperTradingAgent(
            symbol="TEST-USD",
            ledger=ledger,
            market=SyntheticSecondMarket("TEST-USD", changes=["0.001"]),
            signal_model=MomentumSignalModel(window=2, threshold=0.001),
            broker=PaperBroker(initial_cash="1000"),
            risk=TradingRiskEngine(
                max_order_notional="10",
                max_position_notional="20",
                daily_loss_limit="100",
                min_order_notional="1",
            ),
        )
        for _ in range(20):
            agent.run_cycle()

        self.assertEqual(ledger.count(), 10)
        for _ in range(5):
            agent.run_cycle()
        self.assertEqual(ledger.count(), 15)
        self.assertEqual(ledger.prune(), 5)
        self.assertEqual(ledger.count(), 10)

    def test_daily_loss_limit_blocks_new_orders(self) -> None:
        broker = PaperBroker(initial_cash="1000")
        broker.cash = Decimal("800")
        risk = TradingRiskEngine(
            max_order_notional="100",
            max_position_notional="200",
            daily_loss_limit="100",
            min_order_notional="10",
        )
        agent = PaperTradingAgent(
            symbol="TEST-USD",
            ledger=self.ledger,
            market=SyntheticSecondMarket(
                "TEST-USD",
                start_price="100",
                changes=["0.01", "0.01", "0.01"],
            ),
            signal_model=MomentumSignalModel(window=2, threshold=0.001),
            broker=broker,
            risk=risk,
        )

        agent.run_cycle()
        blocked = agent.run_cycle()

        self.assertFalse(blocked["risk"]["allowed"])
        self.assertEqual(blocked["risk"]["reason"], "daily_loss_limit_reached")
        self.assertIsNone(blocked["fill"])


if __name__ == "__main__":
    unittest.main()
