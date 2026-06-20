from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Sequence


MAX_SOURCE_CHARACTERS = 24_000


@dataclass(frozen=True)
class LearningSource:
    name: str
    source_type: str
    text: str
    url: str = ""


@dataclass(frozen=True)
class LearningCard:
    id: str
    source_name: str
    source_type: str
    topic: str
    learning_goal: str
    security_principle: str
    bug_bounty_relevance: str
    decision_prompts: list[str]
    evidence_requirements: list[str]
    false_positive_risks: list[str]
    severity_upgrade_conditions: list[str]
    practice_task: str
    duplicate_search_terms: list[str]


@dataclass(frozen=True)
class QuizQuestion:
    id: str
    card_id: str
    question: str
    expected_signals: list[str]
    fail_if_answer_only_says: list[str]


TOPICS: tuple[dict[str, Any], ...] = (
    {
        "id": "access-control",
        "keywords": (
            "idor",
            "bola",
            "bfla",
            "access control",
            "authorization",
            "tenant",
            "organization",
            "role",
            "membership",
            "invite",
            "دعوة",
            "صلاحية",
        ),
        "principle": "Authorization must be enforced on the server for every object and function boundary.",
        "relevance": "Most high-signal bounty reports prove a cross-user, cross-tenant, or role-boundary violation.",
        "evidence": (
            "Two authorized roles or tenants, when available.",
            "Request and response showing the attacker-controlled object identifier.",
            "Victim resource ownership and the attacker-visible result.",
            "A minimal impact statement beginning with 'As an attacker, I could...'.",
        ),
        "false_positive": (
            "The resource is intentionally public or shared.",
            "The proof uses only one account and cannot show a boundary crossing.",
            "The role model is not established from docs, UI, or source.",
        ),
        "upgrade": (
            "Cross-tenant sensitive data access.",
            "Unauthorized state change against another user or organization.",
            "Privilege escalation from low-trust role to admin-like action.",
        ),
    },
    {
        "id": "api-security",
        "keywords": (
            "api",
            "rest",
            "endpoint",
            "hidden endpoint",
            "mass assignment",
            "swagger",
            "openapi",
            "rate limit",
            "webhook",
        ),
        "principle": "API contracts must reject attacker-supplied fields and enforce intent server-side.",
        "relevance": "API bugs become reportable when hidden or weakly documented behavior produces unauthorized data access or state change.",
        "evidence": (
            "Endpoint, method, auth context, and exact payload.",
            "Unexpected field or object accepted by the server.",
            "Before and after state, or response proving impact.",
            "Program scope confirmation for the API surface.",
        ),
        "false_positive": (
            "Endpoint is intentionally unauthenticated or public.",
            "Extra fields are ignored and do not change state.",
            "Only documentation drift is shown without user impact.",
        ),
        "upgrade": (
            "Mass assignment changes role, billing, ownership, or security settings.",
            "Hidden endpoint exposes sensitive user or tenant data.",
            "Webhook behavior enables replay, spoofing, or cross-account action.",
        ),
    },
    {
        "id": "graphql",
        "keywords": (
            "graphql",
            "resolver",
            "introspection",
            "mutation",
            "alias",
            "batch",
            "global id",
            "schema",
        ),
        "principle": "GraphQL resolvers need object-level authorization independent of schema shape.",
        "relevance": "GraphQL findings often emerge from resolver-level object lookup, batching, aliasing, and authorization mismatches.",
        "evidence": (
            "Operation name, variables, and resolver/object involved.",
            "Attacker and victim object identifiers.",
            "Observed unauthorized field access or mutation result.",
            "Why the schema shape is realistic in production.",
        ),
        "false_positive": (
            "Only introspection exposure is shown.",
            "The proof requires artificial schema alignment.",
            "The field is public by product design.",
        ),
        "upgrade": (
            "Cross-user data access through object IDs.",
            "Mutation against another tenant's object.",
            "Batching or aliasing bypasses per-request checks at scale.",
        ),
    },
    {
        "id": "realtime-authorization",
        "keywords": (
            "websocket",
            "web socket",
            "socket.io",
            "realtime",
            "real-time",
            "channel",
            "subscription",
            "handshake",
            "message",
            "ws",
            "wss",
        ),
        "principle": "Realtime systems must authorize every message, channel, and subscription, not only the initial connection.",
        "relevance": "WebSocket and realtime bugs become high impact when they prove unauthorized cross-user data access or state change.",
        "evidence": (
            "Handshake request, auth context, and channel or message name.",
            "Victim-owned channel, room, resource, or event identifier.",
            "Attacker-sent or attacker-received message proving a boundary crossing.",
            "Negative control showing authorized users behave differently from unauthorized users.",
        ),
        "false_positive": (
            "The realtime stream is intentionally public.",
            "Only authentication is tested, not per-message authorization.",
            "A client-side subscription appears possible but the server drops sensitive events.",
        ),
        "upgrade": (
            "Cross-tenant realtime data exposure.",
            "Unauthorized message causes state change or notification to another user.",
            "Subscription bypass persists after token expiry, role change, or resource removal.",
        ),
    },
    {
        "id": "javascript-recon",
        "keywords": (
            "javascript",
            "js",
            "bundle",
            "source map",
            "route",
            "frontend",
            "html comment",
            "hidden routes",
        ),
        "principle": "Client-side artifacts are discovery material, not proof of vulnerability by themselves.",
        "relevance": "JavaScript and comments help form hypotheses about routes, APIs, feature flags, and auth logic.",
        "evidence": (
            "Discovered route or API path.",
            "Why the route is sensitive or undocumented.",
            "Safe validation showing impact, not only existence.",
            "Dedupe search terms from file names, route names, and function names.",
        ),
        "false_positive": (
            "A hidden route exists but is correctly protected.",
            "Source maps expose no secrets or sensitive logic.",
            "Comments reveal stale or non-production endpoints.",
        ),
        "upgrade": (
            "Hidden route enables unauthorized access or state change.",
            "Bundle leak contains live secrets or exploitable trust assumptions.",
            "Client auth logic reveals a bypass validated server-side.",
        ),
    },
    {
        "id": "source-review",
        "keywords": (
            "source code",
            "code review",
            "sink",
            "taint",
            "data flow",
            "middleware",
            "token",
            "crypto",
            "ssrf",
        ),
        "principle": "A reportable source finding needs a trace from attacker-controlled input to an impact-bearing sink.",
        "relevance": "Source review finds issues dynamic testing misses, but bounty reports still need exploitability and realistic deployment context.",
        "evidence": (
            "Source location and affected version.",
            "Attacker input source, sanitizer or missing guard, and sink.",
            "Local reproduction or unit test proving behavior.",
            "Realistic production preconditions.",
        ),
        "false_positive": (
            "The code path is dead, test-only, or not shipped.",
            "The sink is unreachable from attacker input.",
            "The scenario depends on artificial alignment or non-security boundary assumptions.",
        ),
        "upgrade": (
            "Reliable auth bypass, SSRF, credential disclosure, or token forgery.",
            "Patch bypass of a known fixed vulnerability.",
            "Real product configuration makes the vulnerable path reachable.",
        ),
    },
    {
        "id": "business-logic",
        "keywords": (
            "business logic",
            "price",
            "billing",
            "parser",
            "workflow",
            "state machine",
            "race",
            "replay",
        ),
        "principle": "Business logic must preserve the intended state transition, not merely validate individual fields.",
        "relevance": "High-value bounty findings often show an attacker changing workflow state, price, ownership, or approval assumptions.",
        "evidence": (
            "State transition before and after each action.",
            "Attacker action sequence and exact preconditions.",
            "Impact on customer, user, billing, or workflow integrity.",
            "Non-destructive proof or local reproduction.",
        ),
        "false_positive": (
            "Only a UI inconsistency is shown.",
            "The server rejects or corrects the invalid state.",
            "The proof requires destructive production behavior.",
        ),
        "upgrade": (
            "Unauthorized purchase, plan change, refund, or approval state.",
            "Race or replay causes reliable cross-user impact.",
            "Parser differential bypasses a security or billing control.",
        ),
    },
    {
        "id": "evidence-and-reporting",
        "keywords": (
            "evidence",
            "proof of concept",
            "poc",
            "not applicable",
            "duplicate",
            "triage",
            "report",
            "as an attacker",
        ),
        "principle": "A bounty report is an evidence package, not a claim.",
        "relevance": "Triage accepts demonstrated customer or user impact; text-only claims and duplicates fail.",
        "evidence": (
            "Steps to reproduce.",
            "Screenshots, videos, request/response pairs, or working PoC file.",
            "Impact statement and severity rationale.",
            "Dedupe record with searched terms and why this root cause is new.",
        ),
        "false_positive": (
            "No customer, application, or user impact is demonstrated.",
            "Evidence is only prose.",
            "The same root cause and attack vector were previously reported.",
        ),
        "upgrade": (
            "Evidence proves direct user or tenant harm.",
            "New exploit primitive bypasses a prior fix.",
            "Impact is realistic in the vendor's production model.",
        ),
    },
    {
        "id": "model-routing",
        "keywords": (
            "openrouter",
            "fusion",
            "advisor",
            "subagent",
            "server tool",
            "panel",
            "judge",
            "web search",
            "models api",
            "cost per correct answer",
            "cost per token",
            ":floor",
            "max_price",
            "qwen3.7",
            "kimi k2.7",
            "nemotron",
            "nex-n2-pro",
        ),
        "principle": "Model routing should spend reasoning only when the task needs it, using cheap defaults, bounded escalation, and receipt-safe cost controls.",
        "relevance": "Fathiya needs separate routes for routine planning, deep research, safety checks, bug-bounty dedupe, and trading advice so stronger models improve judgment without becoming uncontrolled defaults.",
        "evidence": (
            "A route decision explaining why the cheap/default model is enough or not enough.",
            "Uncertainty, conflicting evidence, freshness, or depth requirement that justifies Fusion or Advisor.",
            "Cost controls such as free-first routing, `:floor`, `max_price`, and Models API filters before paid use.",
            "A receipt showing no token-spending network call happened during readiness checks.",
        ),
        "false_positive": (
            "Fusion is used for routine chat, normal coding, or simple status checks.",
            "Advisor becomes the default planner instead of an uncertainty escalation path.",
            "A paid model is selected only because it is newer or higher ranked, without a task-fit reason.",
        ),
        "upgrade": (
            "Fusion maps disagreements across fresh sources and changes the final decision.",
            "Advisor catches a material blind spot in a cheap/free plan.",
            "Subagent removes routine work from an expensive model while preserving evidence quality.",
        ),
    },
    {
        "id": "ai-security",
        "keywords": (
            "ai security",
            "model",
            "prompt injection",
            "agent",
            "tool",
            "risk management",
            "openai",
            "llm",
        ),
        "principle": "Agents must separate untrusted source content from operator intent and tool authority.",
        "relevance": "Fathiya must learn from public sources without letting those sources issue hidden instructions.",
        "evidence": (
            "Source trust boundary label.",
            "Operator objective separated from source content.",
            "Tool approval gate evidence for external, financial, destructive, or live-security actions.",
            "Receipt showing what was learned versus what was executed.",
        ),
        "false_positive": (
            "The source text is treated as an instruction.",
            "A model summary is accepted without tests.",
            "The agent claims learning without a quiz or verification loop.",
        ),
        "upgrade": (
            "Untrusted content can cause external action.",
            "Tool output can override policy.",
            "The agent can be induced to submit or execute without evidence gates.",
        ),
    },
    {
        "id": "post-training-rl",
        "keywords": (
            "post-training",
            "reinforcement learning",
            "rlhf",
            "rlaif",
            "rlvr",
            "reward model",
            "preference",
            "policy",
            "feedback",
            "fine-tuning",
        ),
        "principle": "Agent learning improves when feedback is structured, measured, and tied to objective behavior.",
        "relevance": "Fathiya can turn operator feedback, triage results, and reproducible tests into better decisions without treating praise or wording as proof.",
        "evidence": (
            "A named feedback source and why it is trusted.",
            "A reward or scoring rule tied to observable behavior.",
            "Before and after examples showing the decision improved.",
            "A holdout task or negative control that reduces reward-hacking risk.",
        ),
        "false_positive": (
            "The agent learns to optimize report wording instead of evidence quality.",
            "The same evaluator both creates and grades the answer with no check.",
            "The reward is vague, biased, or disconnected from real outcomes.",
        ),
        "upgrade": (
            "A verifier proves the answer is correct on objective tasks.",
            "Human or community feedback is converted into stable criteria.",
            "The learned behavior improves on unseen realistic investigations.",
        ),
    },
    {
        "id": "tool-orchestration",
        "keywords": (
            "hexstrike",
            "kali",
            "mcp",
            "ollama",
            "ssh",
            "orchestration",
            "tool-driven",
            "tool usage",
            "terminal mcp",
            "agent-style workflow",
        ),
        "principle": "Security tools should be orchestrated with scope, receipts, repeatability, and human-readable evidence gates.",
        "relevance": "Fathiya can use Kali and HexStrike-style workflows as evidence collectors, but tool output is not a report by itself.",
        "evidence": (
            "Exact tool, version, target scope, and command intent.",
            "Raw output saved with timestamp and artifact path.",
            "Manual or scripted validation that converts a tool signal into proof.",
            "Safety limits for rate, scope, destructive actions, and credentials.",
        ),
        "false_positive": (
            "A scanner finding is submitted without reproduction.",
            "The agent trusts tool output from an out-of-scope or noisy target.",
            "Latency or partial output is mistaken for failure or success.",
        ),
        "upgrade": (
            "Tool output leads to a reproducible boundary-crossing proof.",
            "Multiple independent tools confirm the same root cause.",
            "Receipts make the finding auditable and easy to retest.",
        ),
    },
    {
        "id": "verifiers-and-checklists",
        "keywords": (
            "verifiable reward",
            "verifier",
            "checklist",
            "checklists",
            "process reward",
            "process reward learning",
            "prl",
            "cm2",
            "rlcf",
            "unit test",
            "binary judgment",
        ),
        "principle": "Complex agent work should be scored through explicit criteria, process checks, and objective verifiers.",
        "relevance": "Bug bounty agents need step-level gates for scope, evidence, impact, duplicate search, and report quality before submission.",
        "evidence": (
            "A checklist with pass/fail criteria for each important step.",
            "Verifier outputs such as tests, screenshots, request/response pairs, or reproducible scripts.",
            "Process evidence showing the agent did not skip prerequisites.",
            "A final score that separates leads from report-ready findings.",
        ),
        "false_positive": (
            "The checklist is too generic to catch missing impact.",
            "Only the final answer is graded, so bad reasoning is hidden.",
            "The verifier checks formatting but not the security boundary.",
        ),
        "upgrade": (
            "Every report-ready claim passes a concrete evidence gate.",
            "Failed checklist items trigger more investigation instead of submission.",
            "The verifier catches duplicate, theoretical, or no-impact findings early.",
        ),
    },
    {
        "id": "multi-agent-critique",
        "keywords": (
            "critique-rl",
            "critique reinforcement learning",
            "critic",
            "self-play",
            "tri-role",
            "attacker",
            "defender",
            "evaluator",
            "community feedback",
            "self-feedback",
            "co-rewarding",
            "restrain",
            "spiral",
        ),
        "principle": "Separate proposing, attacking, defending, and judging roles to reduce blind spots in agent reasoning.",
        "relevance": "Fathiya should stress-test every candidate finding with a critic role before calling it strong or reportable.",
        "evidence": (
            "A proposer hypothesis and a critic objection list.",
            "An evaluator decision grounded in evidence, not confidence.",
            "Adversarial questions that try to downgrade the finding.",
            "A revised proof that addresses the strongest objection.",
        ),
        "false_positive": (
            "The critic only paraphrases the proposer.",
            "Self-feedback increases confidence without new evidence.",
            "The attacker role proposes unsafe or out-of-scope actions.",
        ),
        "upgrade": (
            "Independent critic review finds a new exploit path or removes weak claims.",
            "Evaluator scoring is tied to real impact and program rules.",
            "The final report includes objections already tested and resolved.",
        ),
    },
    {
        "id": "defense-in-depth",
        "keywords": (
            "defense in depth",
            "cia triad",
            "least privilege",
            "zero trust",
            "detect",
            "respond",
            "data security",
        ),
        "principle": "Security decisions should combine prevention, detection, containment, and recovery.",
        "relevance": "This turns course knowledge into practical severity and remediation reasoning.",
        "evidence": (
            "Asset and data classification.",
            "Control that failed and compensating controls that did or did not help.",
            "Confidentiality, integrity, and availability impact.",
            "Remediation tied to the failed layer.",
        ),
        "false_positive": (
            "A best-practice gap has no exploit path.",
            "The missing control is compensated elsewhere.",
            "The report cannot show affected data or operation.",
        ),
        "upgrade": (
            "Multiple layers fail together.",
            "Sensitive data exposure or integrity loss is demonstrated.",
            "Detection or recovery gaps materially increase impact.",
        ),
    },
)


def make_learning_source(
    name: str,
    text: str,
    *,
    url: str = "",
    source_type: str = "",
) -> LearningSource:
    clean_name = re.sub(r"\s+", " ", name).strip()[:160] or "learning-source"
    clean_text = text.strip()[:MAX_SOURCE_CHARACTERS]
    inferred_type = source_type.strip() or classify_source(clean_name, url, clean_text)
    return LearningSource(
        name=clean_name,
        source_type=inferred_type,
        text=clean_text,
        url=url.strip(),
    )


def classify_source(name: str, url: str, text: str) -> str:
    haystack = f"{name}\n{url}\n{text[:2000]}".casefold()
    if "datacamp" in haystack:
        return "deep_curriculum"
    if "portswigger" in haystack or "owasp" in haystack or "apisec" in haystack:
        return "structured_lab"
    if "medium.com" in haystack or "infosecwriteups" in haystack:
        return "vulnerability_writeup"
    if "training" in haystack or "roadmap" in haystack or "course" in haystack:
        return "training_post"
    return "knowledge_source"


def build_learning_session(
    output_root: Path,
    sources: Sequence[LearningSource],
    *,
    title: str = "Fathiya learning session",
    objective: str = "Teach Fathiya how to learn from security material.",
    created_at: datetime | None = None,
) -> dict[str, Any]:
    if not sources:
        raise ValueError("At least one learning source is required")

    timestamp = (created_at or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    session_slug = _slug(title) or "learning-session"
    session_dir = output_root / f"{timestamp}-{session_slug}"
    session_dir.mkdir(parents=True, exist_ok=True)

    cards = _dedupe_cards(
        card
        for source in sources
        for card in _cards_for_source(source)
    )
    quizzes = [
        question
        for card in cards
        for question in _quiz_for_card(card)
    ]
    assessment = _assess_mastery(sources, cards, quizzes)

    manifest = {
        "schema": "fathiya_learning_session_v1",
        "title": title,
        "objective": objective,
        "created_at": (created_at or datetime.now(UTC)).isoformat(),
        "source_count": len(sources),
        "sources": [
            {
                "name": source.name,
                "source_type": source.source_type,
                "url": source.url,
                "sha256": hashlib.sha256(source.text.encode("utf-8")).hexdigest(),
                "characters": len(source.text),
            }
            for source in sources
        ],
    }
    review_queue = _review_queue(cards, quizzes)
    report = _render_mastery_report(
        title=title,
        objective=objective,
        sources=sources,
        cards=cards,
        quizzes=quizzes,
        assessment=assessment,
    )

    (session_dir / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "learning_cards.json").write_text(
        json.dumps([asdict(card) for card in cards], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "quiz.json").write_text(
        json.dumps([asdict(question) for question in quizzes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (session_dir / "review_queue.json").write_text(
        json.dumps(review_queue, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    report_path = session_dir / "mastery_report.md"
    report_path.write_text(report, encoding="utf-8")

    return {
        "schema": "fathiya_learning_session_v1",
        "session_dir": str(session_dir),
        "report_path": str(report_path),
        "source_count": len(sources),
        "card_count": len(cards),
        "quiz_count": len(quizzes),
        "mastery_score": assessment["mastery_score"],
        "status": assessment["status"],
        "coverage_topics": assessment["coverage_topics"],
        "gaps": assessment["gaps"],
        "cards_preview": [asdict(card) for card in cards[:5]],
    }


def _cards_for_source(source: LearningSource) -> list[LearningCard]:
    text = f"{source.name}\n{source.url}\n{source.text}"
    topic_defs = _matched_topics(text)
    if not topic_defs:
        topic_defs = [TOPICS[-1]]
    cards: list[LearningCard] = []
    for topic in topic_defs:
        card_id = _card_id(source, str(topic["id"]))
        cards.append(
            LearningCard(
                id=card_id,
                source_name=source.name,
                source_type=source.source_type,
                topic=str(topic["id"]),
                learning_goal=(
                    f"Use {source.source_type} material to explain {topic['id']} "
                    "as a decision process with proof requirements."
                ),
                security_principle=str(topic["principle"]),
                bug_bounty_relevance=str(topic["relevance"]),
                decision_prompts=[
                    "What observation starts the investigation?",
                    "What trust boundary is being tested?",
                    "What attacker preconditions are required?",
                    "What evidence would make this reportable?",
                    "What would make it Not Applicable, Informative, or Duplicate?",
                ],
                evidence_requirements=list(topic["evidence"]),
                false_positive_risks=list(topic["false_positive"]),
                severity_upgrade_conditions=list(topic["upgrade"]),
                practice_task=_practice_task(str(topic["id"])),
                duplicate_search_terms=_duplicate_terms(source, str(topic["id"]), text),
            )
        )
    return cards


def _matched_topics(text: str) -> list[dict[str, Any]]:
    lowered = text.casefold()
    matched: list[tuple[int, dict[str, Any]]] = []
    for topic in TOPICS:
        score = sum(1 for keyword in topic["keywords"] if keyword.casefold() in lowered)
        if score:
            matched.append((score, topic))
    return [topic for _score, topic in sorted(matched, key=lambda item: (-item[0], item[1]["id"]))]


def _dedupe_cards(cards: Sequence[LearningCard]) -> list[LearningCard]:
    seen: set[str] = set()
    unique: list[LearningCard] = []
    for card in cards:
        key = f"{card.source_name.casefold()}:{card.topic}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(card)
    return unique


def _quiz_for_card(card: LearningCard) -> list[QuizQuestion]:
    if card.topic == "model-routing":
        return [
            QuizQuestion(
                id=f"{card.id}-q1",
                card_id=card.id,
                question=(
                    f"For {card.source_name}, when should FATHIYA stay on a cheap/free "
                    "planner, when should it use Advisor, and when is Fusion justified?"
                ),
                expected_signals=[
                    "cheap/free default",
                    "uncertainty escalation",
                    "research-heavy or conflicting evidence",
                    "not for one-second trading",
                ],
                fail_if_answer_only_says=[
                    "use the strongest model",
                    "Fusion is always better",
                    "newer model means better route",
                ],
            ),
            QuizQuestion(
                id=f"{card.id}-q2",
                card_id=card.id,
                question=(
                    "Explain how the Fusion judge, Advisor, Subagent, and cost controls "
                    "should work together before FATHIYA spends on a paid route."
                ),
                expected_signals=[
                    "judge maps agreement and conflict",
                    "Advisor only when stuck",
                    "Subagent for bounded routine work",
                    ":floor or max_price before paid use",
                ],
                fail_if_answer_only_says=[
                    "majority vote",
                    "Advisor is the default planner",
                    "ignore price controls",
                ],
            ),
        ]
    return [
        QuizQuestion(
            id=f"{card.id}-q1",
            card_id=card.id,
            question=(
                f"Explain {card.topic} from {card.source_name} without naming tools first. "
                "State the trust boundary, attacker preconditions, and the evidence needed."
            ),
            expected_signals=[
                "trust boundary",
                "attacker preconditions",
                "evidence requirement",
                "impact statement",
            ],
            fail_if_answer_only_says=[
                "interesting endpoint",
                "best practice",
                "probably vulnerable",
            ],
        ),
        QuizQuestion(
            id=f"{card.id}-q2",
            card_id=card.id,
            question=(
                f"Before reporting a {card.topic} candidate, what would make it Not Applicable, "
                "Informative, or Duplicate?"
            ),
            expected_signals=[
                "customer or user impact",
                "working proof",
                "duplicate root cause search",
                "scope check",
            ],
            fail_if_answer_only_says=[
                "the code looks wrong",
                "the article says it is critical",
                "severity can be upgraded by wording",
            ],
        ),
    ]


def _assess_mastery(
    sources: Sequence[LearningSource],
    cards: Sequence[LearningCard],
    quizzes: Sequence[QuizQuestion],
) -> dict[str, Any]:
    topics = sorted({card.topic for card in cards})
    source_types = sorted({source.source_type for source in sources})
    checks = {
        "has_multiple_source_types": len(source_types) >= 2 or len(sources) == 1,
        "has_learning_cards": len(cards) >= max(1, len(sources)),
        "has_quiz_loop": len(quizzes) >= len(cards) * 2,
        "covers_evidence": all(card.evidence_requirements for card in cards),
        "covers_false_positive": all(card.false_positive_risks for card in cards),
        "covers_severity": all(card.severity_upgrade_conditions for card in cards),
        "covers_dedupe": any(
            "duplicate" in " ".join(card.duplicate_search_terms).casefold()
            or card.topic == "evidence-and-reporting"
            for card in cards
        ),
        "covers_impact_sentence": any(
            "As an attacker" in " ".join(card.evidence_requirements + card.decision_prompts)
            or (
                card.topic == "model-routing"
                and "route decision" in " ".join(card.evidence_requirements).casefold()
            )
            for card in cards
        ),
        "covers_enough_topics": len(topics) >= min(4, len(TOPICS)),
    }
    passed = sum(1 for ok in checks.values() if ok)
    score = int(round((passed / len(checks)) * 100))
    gaps = [name for name, ok in checks.items() if not ok]
    status = (
        "ready_for_guided_practice"
        if score >= 80
        else "needs_more_sources_or_questions"
        if score >= 55
        else "needs_curriculum_bootstrap"
    )
    return {
        "mastery_score": score,
        "status": status,
        "coverage_topics": topics,
        "source_types": source_types,
        "checks": checks,
        "gaps": gaps,
    }


def _review_queue(
    cards: Sequence[LearningCard],
    quizzes: Sequence[QuizQuestion],
) -> list[dict[str, Any]]:
    by_card = {card.id: card for card in cards}
    queue: list[dict[str, Any]] = []
    for index, question in enumerate(quizzes, start=1):
        card = by_card.get(question.card_id)
        queue.append(
            {
                "question_id": question.id,
                "card_id": question.card_id,
                "topic": card.topic if card else "",
                "review_stage": "first_pass" if index <= len(cards) else "second_pass",
                "due_after_minutes": 0 if index <= len(cards) else 30,
                "expected_signals": question.expected_signals,
            }
        )
    return queue


def _render_mastery_report(
    *,
    title: str,
    objective: str,
    sources: Sequence[LearningSource],
    cards: Sequence[LearningCard],
    quizzes: Sequence[QuizQuestion],
    assessment: dict[str, Any],
) -> str:
    lines = [
        f"# {title}",
        "",
        f"Objective: {objective}",
        "",
        "## Mastery",
        "",
        f"- Status: {assessment['status']}",
        f"- Mastery score: {assessment['mastery_score']}/100",
        f"- Sources: {len(sources)}",
        f"- Learning cards: {len(cards)}",
        f"- Quiz questions: {len(quizzes)}",
        f"- Coverage topics: {', '.join(assessment['coverage_topics']) or 'none'}",
        "",
        "## Learning Method",
        "",
        "Fathiya learns each source through this loop:",
        "",
        "1. Extract the security principle.",
        "2. Convert it into a decision card.",
        "3. Ask what evidence proves impact.",
        "4. Ask what would make the claim Not Applicable, Informative, or Duplicate.",
        "5. Create a safe practice task.",
        "6. Review again until the answer explains reasoning instead of repeating article wording.",
        "",
        "## Source Types",
        "",
    ]
    for source in sources:
        label = f"{source.name} ({source.source_type})"
        if source.url:
            label += f" - {source.url}"
        lines.append(f"- {label}")
    if assessment["gaps"]:
        lines.extend(["", "## Gaps", ""])
        lines.extend(f"- {gap}" for gap in assessment["gaps"])
    lines.extend(["", "## Card Preview", ""])
    for card in cards[:12]:
        lines.extend(
            [
                f"### {card.topic} - {card.source_name}",
                "",
                f"- Principle: {card.security_principle}",
                f"- Relevance: {card.bug_bounty_relevance}",
                f"- Practice: {card.practice_task}",
                "- Evidence: " + "; ".join(card.evidence_requirements),
                "- False positive risks: " + "; ".join(card.false_positive_risks),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _practice_task(topic: str) -> str:
    tasks = {
        "access-control": "Build a two-role object-boundary table and mark the exact request that should fail.",
        "api-security": "Map endpoints, attacker-controlled fields, and server-side state changes before any live test.",
        "graphql": "Write a resolver/object authorization checklist and a minimal non-destructive query proof.",
        "realtime-authorization": "Build a user/channel/message authorization matrix and prove one forbidden message path safely.",
        "javascript-recon": "Extract routes from a bundle, rank them by sensitivity, then require impact evidence.",
        "source-review": "Trace source-to-sink and write a local unit-style reproduction before drafting a report.",
        "business-logic": "Draw the intended state machine and compare it to the attacker action sequence.",
        "evidence-and-reporting": "Create an evidence pack with scope, steps, PoC, impact, severity, and dedupe notes.",
        "ai-security": "Label untrusted source content and verify it cannot trigger external tools.",
        "post-training-rl": "Define a reward loop for one agent behavior and test it against a holdout task.",
        "tool-orchestration": "Run one authorized tool workflow and save scope, command intent, raw output, and validation notes.",
        "verifiers-and-checklists": "Create a pass/fail checklist that blocks report submission when evidence is missing.",
        "multi-agent-critique": "Run proposer, critic, and evaluator roles on one candidate finding before drafting.",
        "defense-in-depth": "Map failed controls and compensating controls to CIA impact and remediation.",
    }
    return tasks.get(topic, "Turn the source into a decision card, quiz, and safe evidence checklist.")


def _duplicate_terms(source: LearningSource, topic: str, text: str) -> list[str]:
    terms = {
        topic,
        source.name,
        "duplicate",
        "Not Applicable",
        "Informative",
    }
    for token in re.findall(r"[A-Za-z][A-Za-z0-9_.:/-]{4,}", text[:4000]):
        if any(marker in token for marker in ("/", ".", "_", "-")):
            terms.add(token[:120])
        if len(terms) >= 12:
            break
    return sorted(terms)


def _card_id(source: LearningSource, topic: str) -> str:
    digest = hashlib.sha256(f"{source.name}:{source.url}:{topic}".encode("utf-8")).hexdigest()
    return f"{_slug(topic)}-{digest[:10]}"


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-").lower()[:80]
