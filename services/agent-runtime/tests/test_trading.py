from __future__ import annotations

import tempfile
import time
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

from fathiya_runtime.trading import (
    BinanceSpotTestnetGateway,
    CoinbaseSpotMarket,
    FallbackMarketDataProvider,
    MomentumSignalModel,
    PaperBroker,
    PaperTradingAgent,
    SyntheticSecondMarket,
    TradingLedger,
    TradingRiskEngine,
)


class BinanceSpotTestnetGatewayTests(unittest.TestCase):
    def build_gateway(self, *, execution_enabled: bool = False) -> BinanceSpotTestnetGateway:
        return BinanceSpotTestnetGateway(
            base_url="https://testnet.binance.vision",
            symbol="BTCUSDT",
            api_key="test-api-key",
            api_secret="test-api-secret",
            execution_enabled=execution_enabled,
        )

    def test_probe_reports_account_readiness_without_exposing_credentials(self) -> None:
        public = Mock(ok=True, status_code=200)
        public.json.return_value = {"serverTime": 123}
        account = Mock(ok=True, status_code=200)
        account.json.return_value = {
            "canTrade": True,
            "accountType": "SPOT",
            "permissions": ["SPOT"],
            "balances": [{"asset": "BTC", "free": "100"}],
        }
        with patch(
            "fathiya_runtime.trading.requests.request",
            side_effect=[public, account],
        ) as request:
            result = self.build_gateway().probe()

        self.assertTrue(result["reachable"])
        self.assertTrue(result["authenticated"])
        self.assertTrue(result["can_trade"])
        self.assertNotIn("test-api-key", str(result))
        self.assertNotIn("test-api-secret", str(result))
        self.assertIn("signature=", request.call_args_list[1].args[1])

    def test_market_order_validation_never_submits_to_matching_engine(self) -> None:
        response = Mock(ok=True, status_code=200)
        response.json.return_value = {}
        with patch("fathiya_runtime.trading.requests.request", return_value=response) as request:
            result = self.build_gateway().market_order(
                side="buy",
                quote_order_qty="25",
                validate_only=True,
            )

        self.assertTrue(result["validated"])
        self.assertFalse(result["submitted"])
        self.assertIn("/api/v3/order/test?", request.call_args.args[1])

    def test_market_order_submission_requires_local_testnet_execution_flag(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "execution remains disabled"):
            self.build_gateway().market_order(
                side="buy",
                quote_order_qty="25",
                validate_only=False,
            )

    def test_gateway_rejects_non_testnet_host(self) -> None:
        with self.assertRaisesRegex(ValueError, "approved Binance Testnet host"):
            BinanceSpotTestnetGateway(
                base_url="https://api.binance.com",
                symbol="BTCUSDT",
                api_key="test-api-key",
                api_secret="test-api-secret",
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
        quality = agent.status()["prediction_quality"]
        self.assertGreaterEqual(quality["evaluated_count"], 2)
        self.assertIsNotNone(quality["directional_accuracy"])
        self.assertEqual(quality["latest_evaluation"]["symbol"], "TEST-USD")
        cadence = agent.status()["execution_cadence"]
        self.assertEqual(cadence["target_seconds"], 0.05)
        self.assertGreaterEqual(cadence["sample_count"], 4)
        self.assertIsNotNone(cadence["latest_interval_seconds"])
        self.assertTrue(cadence["within_target"])

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

    def test_coinbase_market_parses_public_spot_price(self) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": {"amount": "62989.58", "base": "BTC", "currency": "USD"}
        }
        with patch("fathiya_runtime.trading.requests.get", return_value=response) as get:
            market = CoinbaseSpotMarket("BTC-USD", timeout_seconds=0.4)
            tick = market.next_tick()

        self.assertEqual(tick.symbol, "BTC-USD")
        self.assertEqual(tick.price, Decimal("62989.58000000"))
        self.assertEqual(tick.source, "coinbase_spot")
        self.assertEqual(market.health()["success_count"], 1)
        get.assert_called_once()

    def test_fallback_market_tick_is_observed_but_never_filled(self) -> None:
        primary = CoinbaseSpotMarket("BTC-USD")
        market = FallbackMarketDataProvider(
            primary,
            SyntheticSecondMarket("BTC-USD", changes=["0.01"]),
        )
        agent = PaperTradingAgent(
            symbol="BTC-USD",
            ledger=self.ledger,
            market=market,
            signal_model=MomentumSignalModel(window=2, threshold=0.001),
            broker=PaperBroker(initial_cash="1000"),
            risk=TradingRiskEngine(
                max_order_notional="100",
                max_position_notional="200",
                daily_loss_limit="100",
                min_order_notional="10",
            ),
        )

        with patch.object(primary, "next_tick", side_effect=RuntimeError("offline")):
            agent.run_cycle()
            blocked = agent.run_cycle()

        self.assertEqual(blocked["prediction"]["action"], "buy")
        self.assertFalse(blocked["risk"]["allowed"])
        self.assertEqual(blocked["risk"]["reason"], "fallback_market_tick")
        self.assertIsNone(blocked["fill"])
        self.assertTrue(agent.status()["market_health"]["fallback_active"])
        self.assertEqual(agent.status()["prediction_quality"]["evaluated_count"], 0)

    def test_symbol_state_and_history_are_isolated(self) -> None:
        first = self.build_agent(changes=["0.01"])
        second = PaperTradingAgent(
            symbol="OTHER-USD",
            ledger=self.ledger,
            market=SyntheticSecondMarket("OTHER-USD", changes=["0.01"]),
            signal_model=MomentumSignalModel(window=2, threshold=0.001),
            broker=PaperBroker(initial_cash="2000"),
            risk=TradingRiskEngine(
                max_order_notional="100",
                max_position_notional="200",
                daily_loss_limit="100",
                min_order_notional="10",
            ),
        )

        first.run_cycle()
        second.run_cycle()

        self.assertEqual(first.status()["cycle_count"], 1)
        self.assertEqual(second.status()["cycle_count"], 1)
        self.assertEqual(first.recent(1)[0]["tick"]["symbol"], "TEST-USD")
        self.assertEqual(second.recent(1)[0]["tick"]["symbol"], "OTHER-USD")
        self.assertEqual(self.ledger.count(), 2)

    def test_model_advisory_can_veto_but_not_originate_paper_orders(self) -> None:
        agent = self.build_agent(changes=["0.01"])
        agent.run_cycle()
        agent.run_cycle()
        advisory = agent.update_advisory(
            action="sell",
            confidence=0.9,
            rationale="short-lived disagreement",
            provider="openrouter",
            ttl_seconds=60,
        )

        vetoed = agent.run_cycle()

        self.assertTrue(advisory["active"])
        self.assertEqual(vetoed["prediction"]["action"], "hold")
        self.assertIn("advisor_veto", vetoed["prediction"]["model"])
        self.assertIsNone(vetoed["fill"])
        self.assertEqual(agent.status()["strategy_advisory_policy"]["mode"], "veto_only")
        self.assertFalse(
            agent.status()["strategy_advisory_policy"]["can_originate_orders"]
        )

        hold_agent = PaperTradingAgent(
            symbol="HOLD-USD",
            ledger=self.ledger,
            market=SyntheticSecondMarket("HOLD-USD", changes=["0"]),
            signal_model=MomentumSignalModel(window=2, threshold=0.001),
            broker=PaperBroker(initial_cash="1000"),
            risk=TradingRiskEngine(
                max_order_notional="100",
                max_position_notional="200",
                daily_loss_limit="100",
                min_order_notional="10",
            ),
        )
        hold_agent.run_cycle()
        hold_agent.update_advisory(
            action="buy",
            confidence=1.0,
            rationale="advisor wants buy",
            provider="huggingface_local",
            ttl_seconds=60,
        )
        still_hold = hold_agent.run_cycle()

        self.assertEqual(still_hold["prediction"]["action"], "hold")
        self.assertIsNone(still_hold["fill"])

    def test_model_advisory_can_confirm_existing_paper_signal(self) -> None:
        agent = self.build_agent(changes=["0.01"])
        agent.run_cycle()
        agent.run_cycle()
        agent.update_advisory(
            action="buy",
            confidence=0.9,
            rationale="momentum agrees",
            provider="openrouter",
            ttl_seconds=60,
        )

        confirmed = agent.run_cycle()

        self.assertEqual(confirmed["prediction"]["action"], "buy")
        self.assertIn("advisor_confirmed", confirmed["prediction"]["model"])
        self.assertIsNotNone(confirmed["fill"])


if __name__ == "__main__":
    unittest.main()
