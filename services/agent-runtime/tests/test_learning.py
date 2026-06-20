from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fathiya_runtime.config import RuntimeConfig
from fathiya_runtime.learning import build_learning_session, make_learning_source
from fathiya_runtime.models import AgentModelRouter
from fathiya_runtime.planner import build_plan
from fathiya_runtime.tools import ToolExecutor


class LearningBootstrapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        os.environ["FATHIYA_STORE"] = "sqlite"
        os.environ["FATHIYA_LOCAL_SETTINGS_PATH"] = str(root / "operator-settings.json")
        os.environ["FATHIYA_SQLITE_PATH"] = str(root / "runtime.db")
        os.environ["FATHIYA_KNOWLEDGE_ROOT"] = str(root / "knowledge")
        os.environ["FATHIYA_TRADING_SQLITE_PATH"] = str(root / "trading.db")
        os.environ["FATHIYA_TRADING_MARKET_PROVIDER"] = "synthetic_second_market"
        os.environ["FATHIYA_ENABLE_HF_RETRIEVAL"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_GENERATION"] = "false"
        os.environ["FATHIYA_ENABLE_LOCAL_PLANNING"] = "false"
        os.environ["FATHIYA_ZAPIER_MCP_TOKEN_PATH"] = str(root / "zapier.json")
        os.environ.pop("OPENROUTER_API_KEY", None)
        self.config = RuntimeConfig.load()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_learning_session_turns_sources_into_cards_quiz_and_mastery_report(self) -> None:
        sources = [
            make_learning_source(
                "DataCamp AI Security and Risk Management",
                (
                    "AI security training covers agent tool risk management, "
                    "data security, defense in depth, least privilege, and evidence."
                ),
                url="https://www.datacamp.com/courses/ai-security-and-risk-management",
            ),
            make_learning_source(
                "Medium GraphQL BOLA writeup",
                (
                    "A GraphQL bug bounty writeup explains BOLA, IDOR, resolver "
                    "authorization, JavaScript recon, duplicate triage, Not Applicable "
                    "risk, and proof of concept evidence."
                ),
                url="https://medium.com/example/graphql-bola",
            ),
        ]

        result = build_learning_session(
            self.config.knowledge_root / "learning",
            sources,
            title="Fathiya test learning",
        )

        self.assertGreaterEqual(result["card_count"], 4)
        self.assertEqual(result["quiz_count"], result["card_count"] * 2)
        self.assertGreaterEqual(result["mastery_score"], 80)
        self.assertTrue(Path(result["report_path"]).exists())
        self.assertIn("graphql", result["coverage_topics"])
        report = Path(result["report_path"]).read_text(encoding="utf-8")
        self.assertIn("Fathiya learns each source through this loop", report)

    def test_tool_and_planner_route_learning_requests(self) -> None:
        executor = ToolExecutor(self.config)
        result = executor.execute(
            "learning_bootstrap",
            "تعلم الآلة لازم تتعلم وشلون تتعلم من داتاكامب وميديم",
            {
                "source_text": (
                    "DataCamp gives deep curriculum for data security and AI security. "
                    "Medium writeups teach API security, BOLA, GraphQL, JavaScript recon, "
                    "business logic, evidence, and duplicate triage."
                ),
                "title": "Arabic operator learning request",
            },
        )

        self.assertTrue(result["executed"])
        self.assertGreaterEqual(result["card_count"], 4)
        self.assertGreaterEqual(result["quiz_count"], 8)
        self.assertTrue(Path(result["report_path"]).exists())

        plan = build_plan(
            {
                "prompt": (
                    "تعلم الاله عشان تتعلم وشلون تتعلم من داتاكامب وميديم "
                    "وtraining posts"
                )
            },
            [],
            AgentModelRouter(
                "",
                "remote-model",
                enable_local_generation=False,
                local_model="local-model",
                local_max_new_tokens=64,
            ),
            executor.catalog(),
            max_tool_steps=6,
        )
        tools = [step["tool"] for step in plan if step.get("kind") == "tool"]

        self.assertIn("learning_bootstrap", tools)

    def test_post_training_material_creates_meta_learning_cards(self) -> None:
        source = make_learning_source(
            "Turing Post RL approaches",
            (
                "Modern LLM post-training uses reinforcement learning feedback "
                "signals including RLHF, RLAIF, RLVR, verifier signals, checklist "
                "feedback, process reward learning, CM2 step scoring, Critique-RL, "
                "self-play, tri-role attacker defender evaluator loops, "
                "co-rewarding, RESTRAIN, and self-feedback."
            ),
            url="https://www.turingpost.com/p/rlapproaches",
        )

        result = build_learning_session(
            self.config.knowledge_root / "learning",
            [source],
            title="Turing Post meta learning",
        )

        self.assertIn("post-training-rl", result["coverage_topics"])
        self.assertIn("verifiers-and-checklists", result["coverage_topics"])
        self.assertIn("multi-agent-critique", result["coverage_topics"])
        self.assertGreaterEqual(result["mastery_score"], 80)

    def test_medium_security_material_creates_realtime_and_tool_cards(self) -> None:
        source = make_learning_source(
            "Medium and InfoSec bug bounty learning",
            (
                "Medium writeups cover JavaScript recon, hidden API endpoints, "
                "IDOR access control, BOLA, WebSocket authorization bypass where "
                "the handshake is checked but channel messages are not, AI agent "
                "prompt injection risk, and HexStrike MCP orchestration with Kali, "
                "Ollama, SSH, tool-driven workflows, evidence receipts, and "
                "duplicate triage."
            ),
            url="https://medium.com/search?q=bug+bounty",
        )

        result = build_learning_session(
            self.config.knowledge_root / "learning",
            [source],
            title="Medium security learning",
        )

        self.assertIn("javascript-recon", result["coverage_topics"])
        self.assertIn("realtime-authorization", result["coverage_topics"])
        self.assertIn("tool-orchestration", result["coverage_topics"])
        self.assertGreaterEqual(result["mastery_score"], 80)

    def test_openrouter_fusion_material_creates_model_routing_cards(self) -> None:
        source = make_learning_source(
            "OpenRouter Fusion email",
            (
                "OpenRouter Fusion can be called as openrouter/fusion or as a "
                "server tool. A panel of up to eight models plus a judge maps "
                "agreement, conflict, unique catches, and shared blind spots. "
                "Advisor is for uncertainty escalation with named advisors, "
                "memory, and streaming. Subagent handles bounded routine work. "
                "Use cheap or free models first, then :floor, max_price, and "
                "Models API filters before paid routes. Do not use Fusion for "
                "the one-second trading loop."
            ),
        )

        result = build_learning_session(
            self.config.knowledge_root / "learning",
            [source],
            title="OpenRouter Fusion learning",
        )

        self.assertIn("model-routing", result["coverage_topics"])
        self.assertGreaterEqual(result["mastery_score"], 80)
        quiz = Path(result["session_dir"], "quiz.json").read_text(encoding="utf-8")
        self.assertIn("Fusion judge", quiz)
        self.assertIn(":floor or max_price", quiz)


if __name__ == "__main__":
    unittest.main()
