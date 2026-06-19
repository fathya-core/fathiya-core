import builtins
import importlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.logger import FathiyaLogger
from core.policy_engine import PolicyCheckResult
from core.router import RouteResult
from core.verifier import OutputVerifier, VerificationResult
from domains.security.evidence_analyzer import (
    EvidenceAnalysisResult,
    EvidenceAnalyzer,
    FindingEvidenceBundle,
)
from domains.security.exploit_verifier import (
    ExploitVerificationResult,
    ExploitVerifier,
    VerificationRecord,
)
from domains.security.security_reporter import SecurityReport, SecurityReporter
from domains.security.surface_mapper import SurfaceMapper, SurfaceSummary
from domains.security.target_profiler import TargetProfiler, TargetProfile
from domains.security.test_planner import (
    SecurityTestPlanner,
    TestPlan as SecurityTestPlan,
    TestStep as SecurityTestStep,
)
from domains.security.vulnerability_hunter import (
    PreliminaryFinding,
    VulnerabilityHunter,
    VulnerabilityHuntResult,
)


class DummyMemory:
    def __init__(self):
        self.sessions = []

    def save_session(
        self,
        user_input: str,
        framed_problem_json: str,
        solver_answer: str,
        evaluator_verdict: str,
        evaluator_reason: str,
        final_answer: str,
    ) -> int:
        session_id = len(self.sessions) + 1
        self.sessions.append(
            {
                "id": session_id,
                "user_input": user_input,
                "framed_problem_json": framed_problem_json,
                "solver_answer": solver_answer,
                "evaluator_verdict": evaluator_verdict,
                "evaluator_reason": evaluator_reason,
                "final_answer": final_answer,
            }
        )
        return session_id

    def get_recent_sessions(self, limit: int = 5):
        recent = self.sessions[-limit:]
        return [(item["id"], "", item["user_input"], item["evaluator_verdict"]) for item in recent]


def _sample_test_plan(target_type: str = "domain"):
    return SecurityTestPlan(
        target_summary="اختبار أمني أولي",
        target_type=target_type,
        steps=[
            SecurityTestStep(
                name="استطلاع أولي",
                description="جمع نقاط الإدخال",
                category="recon",
                priority=1,
                tools=["whois", "curl"],
            ),
            SecurityTestStep(
                name="مراجعة تعرض الويب",
                description="مراجعة المسارات والمعاملات",
                category="vuln",
                priority=2,
                tools=["browser", "curl"],
            ),
        ],
        total_estimated_time="10 دقائق",
        warnings=[],
        scope_notes=["يتطلب تصريحاً"],
    )


def _build_full_security_outputs(raw_text: str):
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()
    analyzer = EvidenceAnalyzer()
    exploit_verifier = ExploitVerifier()
    reporter = SecurityReporter()

    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    vulnerability_result = hunter.hunt(profile, surface_summary, test_plan)
    evidence_result = analyzer.analyze(profile, surface_summary, test_plan, vulnerability_result)
    exploit_result = exploit_verifier.verify(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface_summary,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_result,
        policy_check=PolicyCheckResult(passed=True, action="allow"),
    )
    report = reporter.build_report(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface_summary,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_result,
        exploit_summary=exploit_result,
    )
    return (
        profile,
        surface_summary,
        test_plan,
        vulnerability_result,
        evidence_result,
        exploit_result,
        report,
    )


def test_orchestrator_security_route_uses_phase3_chain(tmp_path):
    from core.orchestrator import FathiyaOrchestrator

    call_order = []

    class StubRouter:
        def route(self, user_input: str):
            call_order.append("router")
            return RouteResult(
                flow="security",
                domain="security",
                confidence=0.99,
                matched_keywords=["افحص"],
                reason="security request",
            )

    class StubPolicyEngine:
        def check_input(self, user_input: str):
            call_order.append("policy_engine.check_input")
            return PolicyCheckResult(passed=True, action="allow")

    class StubTargetProfiler:
        def profile(self, user_input: str):
            call_order.append("target_profiler")
            return TargetProfile(
                raw_input=user_input,
                target_type="domain",
                normalized_target="example.com",
                indicators=["web_server", "domain"],
                potential_services=["http", "https", "dns"],
                risk_notes=[],
                confidence=0.9,
            )

    class StubSurfaceMapper:
        def map(self, profile: TargetProfile, context_text: str = ""):
            call_order.append("surface_mapper")
            return SurfaceSummary(
                raw_input=context_text,
                normalized_target=profile.normalized_target,
                target_type=profile.target_type,
                surface_type="web",
                confidence=0.91,
                endpoints=["http://example.com/login"],
                paths=["/login", "/admin"],
                params=["next", "token"],
                query_keys=["next", "token"],
                headers=["Authorization"],
                auth_hints=["login-form"],
                forms=[],
                input_points=[],
                indicators=["surface:web"],
                notes=["surface mapped"],
            )

    class StubTestPlanner:
        def plan(self, profile: TargetProfile):
            call_order.append("test_planner")
            return _sample_test_plan(target_type=profile.target_type)

    class StubVulnerabilityHunter:
        def hunt(self, target_profile: TargetProfile, surface_summary: SurfaceSummary, test_plan: SecurityTestPlan):
            call_order.append("vulnerability_hunter")
            return VulnerabilityHuntResult(
                target_type=target_profile.target_type,
                surface_type=surface_summary.surface_type,
                checks_run=["transport_hygiene", "exposed_paths"],
                findings=[
                    PreliminaryFinding(
                        title="احتمال نقل غير آمن للبيانات",
                        classification="likely_finding",
                        category="transport",
                        rationale="مؤشر نقل غير مشفر",
                        evidence=["http://example.com/login", "login-form"],
                        related_elements=["/login"],
                        recommended_next_step="مراجعة النقل لاحقاً",
                        confidence=0.78,
                    )
                ],
                notes=["نتيجة أولية"],
                safe_mode=True,
            )

    class StubEvidenceAnalyzer:
        def analyze(
            self,
            target_profile: TargetProfile,
            surface_summary: SurfaceSummary,
            test_plan: SecurityTestPlan,
            vulnerability_summary: VulnerabilityHuntResult,
        ):
            call_order.append("evidence_analyzer")
            bundle = FindingEvidenceBundle(
                finding_title="احتمال نقل غير آمن للبيانات",
                finding_category="transport",
                original_classification="likely_finding",
                evidence_level="strong_evidence",
                confidence=0.84,
                atoms=[],
                supporting_points=["http://example.com/login", "login-form"],
                recommended_next_step="مراجعة لاحقة",
            )
            return EvidenceAnalysisResult(
                target_type=target_profile.target_type,
                surface_type=surface_summary.surface_type,
                bundles=[bundle],
                kept_bundles=[bundle],
                filtered_bundles=[],
                notes=["تحليل أدلة"],
                safe_mode=True,
            )

    class StubExploitVerifier:
        def verify(
            self,
            target_profile: TargetProfile,
            test_plan: SecurityTestPlan,
            surface_summary: SurfaceSummary,
            vulnerability_summary: VulnerabilityHuntResult,
            evidence_summary: EvidenceAnalysisResult,
            policy_check: PolicyCheckResult,
        ):
            call_order.append("exploit_verifier")
            record = VerificationRecord(
                finding_title="احتمال نقل غير آمن للبيانات",
                finding_category="transport",
                original_classification="likely_finding",
                evidence_level="strong_evidence",
                state="verified",
                eligible=True,
                policy_action=policy_check.action,
                rationale="تحقق محدود وآمن",
                confidence=0.84,
            )
            return ExploitVerificationResult(
                target_type=target_profile.target_type,
                surface_type=surface_summary.surface_type,
                policy_action=policy_check.action,
                records=[record],
                notes=["تحقق محدود"],
                safe_mode=True,
            )

    class StubSecurityReporter:
        def build_report(
            self,
            target_profile: TargetProfile,
            test_plan: SecurityTestPlan,
            surface_summary: SurfaceSummary,
            vulnerability_summary: VulnerabilityHuntResult,
            evidence_summary: EvidenceAnalysisResult,
            exploit_summary: ExploitVerificationResult,
        ):
            call_order.append("security_reporter")
            return SecurityReport(
                target_summary={"normalized_target": target_profile.normalized_target},
                attack_surface_summary={"surface_type": surface_summary.surface_type},
                findings_summary={"items": [{"title": "احتمال نقل غير آمن للبيانات"}]},
                evidence_summary={"strong_evidence_count": 1},
                confidence_levels={"average_confidence": 0.84},
                verification_status={"verified_count": 1},
                recommended_next_step="مراجعة لاحقة",
                human_readable="تقرير أمني منظم",
            )

    class StubVerifier:
        def verify(self, user_input: str, final_answer: str, flow: str = "general"):
            call_order.append("verifier")
            return VerificationResult(
                passed=True,
                issues=[],
                severity="none",
                cleaned_answer=final_answer,
            )

    logger = FathiyaLogger(str(tmp_path / "logs"))
    orchestrator = FathiyaOrchestrator(
        router=StubRouter(),
        policy_engine=StubPolicyEngine(),
        target_profiler=StubTargetProfiler(),
        surface_mapper=StubSurfaceMapper(),
        test_planner=StubTestPlanner(),
        vulnerability_hunter=StubVulnerabilityHunter(),
        evidence_analyzer=StubEvidenceAnalyzer(),
        exploit_verifier=StubExploitVerifier(),
        security_reporter=StubSecurityReporter(),
        verifier=StubVerifier(),
        memory=DummyMemory(),
        logger=logger,
    )

    result = orchestrator.run("أريد فحص example.com")

    assert call_order == [
        "router",
        "policy_engine.check_input",
        "target_profiler",
        "surface_mapper",
        "test_planner",
        "vulnerability_hunter",
        "evidence_analyzer",
        "exploit_verifier",
        "security_reporter",
        "verifier",
    ]
    assert result["route"].flow == "security"
    assert result["analysis"]["target_profile"].normalized_target == "example.com"
    assert result["analysis"]["surface_summary"].surface_type == "web"
    assert result["analysis"]["vulnerability_summary"].total_findings == 1
    assert result["analysis"]["evidence_summary"].strong_evidence_count == 1
    assert result["analysis"]["exploit_summary"].verified_count == 1
    assert result["analysis"]["security_report"].target_summary["normalized_target"] == "example.com"
    assert orchestrator.framer is None
    assert orchestrator.solver is None
    assert orchestrator.evaluator is None


def test_policy_engine_and_verifier_import_without_optional_api_deps(monkeypatch):
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "dotenv" or name.startswith("dotenv"):
            raise ModuleNotFoundError("No module named 'dotenv'")
        return real_import(name, globals, locals, fromlist, level)

    for module_name in [
        "core.policy_engine",
        "core.verifier",
        "config",
        "config.settings",
        "config.policies",
    ]:
        sys.modules.pop(module_name, None)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    policy_module = importlib.import_module("core.policy_engine")
    verifier_module = importlib.import_module("core.verifier")

    assert hasattr(policy_module, "PolicyEngine")
    assert hasattr(verifier_module, "OutputVerifier")
    assert policy_module.PolicyEngine().check_input("افحص example.com").passed is True
    assert verifier_module.OutputVerifier().quick_verify("هذا رد صالح وطويل بما يكفي") is True


def test_security_flow_extracts_apex_domain_from_free_text():
    profiler = TargetProfiler()
    profile = profiler.profile("افحص example.com")

    assert profile.target_type == "domain"
    assert profile.normalized_target == "example.com"
    assert profile.is_valid is True


def test_security_flow_rejects_invalid_ipv4_and_cidr_targets():
    profiler = TargetProfiler()

    invalid_ip = profiler.profile("افحص 999.999.999.999")
    invalid_cidr = profiler.profile("192.168.1.0/99")

    assert invalid_ip.target_type == "unknown"
    assert invalid_ip.is_valid is False
    assert any("IPv4 غير صالح" in note for note in invalid_ip.risk_notes)

    assert invalid_cidr.target_type == "unknown"
    assert invalid_cidr.is_valid is False
    assert any("CIDR غير صالح" in note for note in invalid_cidr.risk_notes)


def test_security_flow_does_not_duplicate_cidr_risk_warnings():
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()

    profile = profiler.profile("10.0.0.0/8")
    original_notes = list(profile.risk_notes)
    plan = planner.plan(profile)

    assert profile.risk_notes == original_notes
    assert len(plan.warnings) == len(set(plan.warnings))
    assert set(original_notes).issubset(set(plan.warnings))


def test_surface_mapper_builds_web_summary_with_forms_and_query_keys():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()

    raw_text = "افحص https://example.com/login?next=/admin&lang=ar مع header Authorization ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    summary = mapper.map(profile, raw_text)

    assert summary.surface_type == "web"
    assert any(endpoint.startswith("https://example.com") for endpoint in summary.endpoints)
    assert "/login" in summary.paths
    assert "next" in summary.query_keys
    assert "Authorization" in summary.headers
    assert summary.forms
    assert any(form.name == "login" for form in summary.forms)


def test_surface_mapper_detects_api_surface_and_auth_hints():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()

    raw_text = "راجع https://api.example.com/v1/users?id=7 مع Bearer token و X-API-Key"
    profile = profiler.profile(raw_text)
    summary = mapper.map(profile, raw_text)

    assert summary.surface_type == "api"
    assert any("api.example.com" in endpoint for endpoint in summary.endpoints)
    assert "id" in summary.query_keys
    assert "Authorization" in summary.headers
    assert "X-API-Key" in summary.headers
    assert any(hint in summary.auth_hints for hint in ["bearer-token", "api-key"])


def test_surface_mapper_detects_code_and_ai_agent_surfaces():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()

    code_text = "افحص مستودع GitHub source code فيه package.json و requirements.txt"
    code_profile = profiler.profile(code_text)
    code_summary = mapper.map(code_profile, code_text)

    ai_text = "افحص AI agent فيه system prompt و tool call و memory"
    ai_profile = profiler.profile(ai_text)
    ai_summary = mapper.map(ai_profile, ai_text)

    assert code_summary.surface_type == "code"
    assert ai_summary.surface_type == "ai-agent"


def test_vulnerability_hunter_classifies_preliminary_web_findings():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()

    raw_text = "افحص http://example.com/login?next=/admin&token=abc مع Authorization و Cookie ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    result = hunter.hunt(profile, surface_summary, test_plan)

    classifications = {finding.classification for finding in result.findings}
    assert result.safe_mode is True
    assert "signal" in classifications or "possible_finding" in classifications
    assert "possible_finding" in classifications or "likely_finding" in classifications
    assert result.total_findings >= 2
    assert all(finding.confirmed is False for finding in result.findings)
    assert all(finding.exploit_performed is False for finding in result.findings)


def test_vulnerability_hunter_detects_ai_agent_likely_findings_without_confirmation():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()

    raw_text = "افحص AI agent endpoint فيه params prompt و system و tool و memory"
    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    result = hunter.hunt(profile, surface_summary, test_plan)

    likely_findings = result.get_findings_by_classification("likely_finding")
    assert result.surface_type == "ai-agent"
    assert likely_findings
    assert all(finding.requires_confirmation is True for finding in likely_findings)
    assert all(finding.confirmed is False for finding in likely_findings)


def test_evidence_analyzer_builds_structured_bundles_and_confidence_levels():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()
    analyzer = EvidenceAnalyzer()

    raw_text = "افحص http://example.com/login?next=/admin&token=abc مع Authorization و Cookie ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    vulnerability_result = hunter.hunt(profile, surface_summary, test_plan)
    analysis = analyzer.analyze(profile, surface_summary, test_plan, vulnerability_result)

    assert analysis.safe_mode is True
    assert analysis.total_bundles >= 1
    assert analysis.kept_bundles
    assert any(bundle.evidence_level in {"medium_evidence", "strong_evidence", "weak_evidence"} for bundle in analysis.bundles)
    assert all(0.25 <= bundle.confidence <= 0.95 for bundle in analysis.bundles)
    assert all(bundle.requires_verification is True for bundle in analysis.bundles)


def test_evidence_analyzer_reduces_clear_transport_false_positive_on_https_surface():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    analyzer = EvidenceAnalyzer()

    raw_text = "افحص https://example.com/login مع Authorization ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    vulnerability_result = VulnerabilityHuntResult(
        target_type=profile.target_type,
        surface_type=surface_summary.surface_type,
        checks_run=["transport_hygiene"],
        findings=[
            PreliminaryFinding(
                title="احتمال نقل غير آمن للبيانات",
                classification="possible_finding",
                category="transport",
                rationale="فرضية أولية",
                evidence=["login-form"],
                related_elements=["https://example.com/login"],
                recommended_next_step="مراجعة النقل",
                confidence=0.6,
            )
        ],
        notes=["نتيجة أولية"],
        safe_mode=True,
    )

    analysis = analyzer.analyze(profile, surface_summary, test_plan, vulnerability_result)

    assert len(analysis.filtered_bundles) == 1
    assert analysis.filtered_bundles[0].false_positive_reduced is True
    assert analysis.filtered_bundles[0].evidence_level == "weak_evidence"


def test_exploit_verifier_marks_transport_finding_verified_when_safe_consistent_signals_exist():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()
    analyzer = EvidenceAnalyzer()
    verifier = ExploitVerifier()

    raw_text = "افحص http://example.com/login?next=/admin&token=abc مع Authorization ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    vulnerability_result = hunter.hunt(profile, surface_summary, test_plan)
    evidence_result = analyzer.analyze(profile, surface_summary, test_plan, vulnerability_result)
    exploit_result = verifier.verify(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface_summary,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_result,
        policy_check=PolicyCheckResult(passed=True, action="allow"),
    )

    assert exploit_result.safe_mode is True
    assert exploit_result.total_records >= 1
    assert any(record.state == "verified" for record in exploit_result.records)
    assert any(record.policy_action == "allow" for record in exploit_result.records)


def test_exploit_verifier_respects_policy_block_and_returns_manual_review():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()
    analyzer = EvidenceAnalyzer()
    verifier = ExploitVerifier()

    raw_text = "افحص http://example.com/login?token=abc"
    profile = profiler.profile(raw_text)
    surface_summary = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    vulnerability_result = hunter.hunt(profile, surface_summary, test_plan)
    evidence_result = analyzer.analyze(profile, surface_summary, test_plan, vulnerability_result)
    exploit_result = verifier.verify(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface_summary,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_result,
        policy_check=PolicyCheckResult(passed=False, action="block", violations=["policy blocked"]),
    )

    assert exploit_result.records
    assert all(record.state == "needs_manual_review" for record in exploit_result.records)
    assert all(record.eligible is False for record in exploit_result.records)
    assert exploit_result.policy_action == "block"


def test_security_reporter_builds_json_compatible_and_human_readable_report():
    raw_text = "افحص http://example.com/login?next=/admin&token=abc مع Authorization ونموذج تسجيل الدخول"
    (
        profile,
        surface_summary,
        test_plan,
        vulnerability_result,
        evidence_result,
        exploit_result,
        report,
    ) = _build_full_security_outputs(raw_text)

    assert isinstance(report, SecurityReport)
    report_dict = report.to_dict()
    assert report_dict["target_summary"]["normalized_target"] == profile.normalized_target
    assert report_dict["attack_surface_summary"]["surface_type"] == surface_summary.surface_type
    assert report_dict["findings_summary"]["total_findings"] == vulnerability_result.total_findings
    assert report_dict["evidence_summary"]["total_bundles"] == evidence_result.total_bundles
    assert report_dict["verification_status"]["verified_count"] == exploit_result.verified_count
    assert isinstance(report_dict["human_readable"], str)
    assert "تقرير أمني منظم" in report.human_readable


def test_security_reporter_selects_recommended_next_step_from_best_available_signal():
    raw_text = "افحص http://example.com/login?next=/admin&token=abc مع Authorization ونموذج تسجيل الدخول"
    *_, report = _build_full_security_outputs(raw_text)

    assert isinstance(report.recommended_next_step, str)
    assert report.recommended_next_step.strip()


def test_security_verifier_blocks_dangerous_command_output():
    verifier = OutputVerifier()
    result = verifier.verify(
        user_input="افحص الهدف",
        final_answer="يمكنك تنفيذ الأمر rm -rf / الآن دون تحقق.",
        flow="security",
    )

    assert result.passed is False
    assert result.severity != "none"
    assert result.severity == "critical"


def test_orchestrator_records_logger_and_benchmark_data_for_security_runs(tmp_path):
    from core.orchestrator import FathiyaOrchestrator

    logger = FathiyaLogger(str(tmp_path / "logs"))
    memory = DummyMemory()
    orchestrator = FathiyaOrchestrator(
        memory=memory,
        logger=logger,
    )

    result = orchestrator.run("أريد فحص http://example.com/login?next=/admin&token=abc")

    benchmark_report = result["benchmark_report"]
    stages = benchmark_report["stages"]
    expected_stages = {
        "router",
        "policy_engine.check_input",
        "target_profiler",
        "surface_mapper",
        "test_planner",
        "vulnerability_hunter",
        "evidence_analyzer",
        "exploit_verifier",
        "security_reporter",
        "verifier",
    }

    assert expected_stages.issubset(set(stages.keys()))
    assert benchmark_report["total_time_seconds"] >= 0.0
    assert result["analysis"]["surface_summary"].surface_type == "web"
    assert result["analysis"]["vulnerability_summary"].total_findings >= 1
    assert result["analysis"]["evidence_summary"].total_bundles >= 1
    assert result["analysis"]["exploit_summary"].total_records >= 1
    assert result["analysis"]["security_report"].human_readable

    run_logs = logger.read_log("runs", limit=20)
    session_logs = logger.read_log("sessions", limit=20)

    pipeline_entries = [entry for entry in run_logs if entry["component"] == "pipeline"]
    assert pipeline_entries
    assert pipeline_entries[-1]["metadata"]["flow"] == "security"
    assert pipeline_entries[-1]["metadata"]["session_id"] == result["session_id"]
    assert pipeline_entries[-1]["metadata"]["surface_type"] == "web"
    assert pipeline_entries[-1]["metadata"]["vulnerability_findings"] >= 1
    assert pipeline_entries[-1]["metadata"]["strong_evidence"] >= 0
    assert pipeline_entries[-1]["metadata"]["medium_evidence"] >= 0
    assert pipeline_entries[-1]["metadata"]["verified_findings"] >= 0
    assert pipeline_entries[-1]["metadata"]["manual_review_findings"] >= 0
    assert pipeline_entries[-1]["metadata"]["reported_findings"] >= 1

    assert session_logs
    assert session_logs[-1]["metadata"]["flow"] == "security"
    assert session_logs[-1]["metadata"]["surface_type"] == "web"
    assert session_logs[-1]["metadata"]["vulnerability_findings"] >= 1
    assert session_logs[-1]["metadata"]["strong_evidence"] >= 0
    assert session_logs[-1]["metadata"]["medium_evidence"] >= 0
    assert session_logs[-1]["metadata"]["verified_findings"] >= 0
    assert session_logs[-1]["metadata"]["manual_review_findings"] >= 0
    assert session_logs[-1]["metadata"]["reported_findings"] >= 1


def test_direct_ipv4_end_to_end(tmp_path):
    from core.orchestrator import FathiyaOrchestrator

    logger = FathiyaLogger(str(tmp_path / "logs"))
    orchestrator = FathiyaOrchestrator(memory=DummyMemory(), logger=logger)

    result = orchestrator.run("أريد فحص أمني للهدف 8.8.8.8")
    profile = result["analysis"]["target_profile"]
    surface = result["analysis"]["surface_summary"]
    plan = result["analysis"]["test_plan"]

    assert result["route"].flow == "security"
    assert profile.target_type == "ip"
    assert profile.normalized_target == "8.8.8.8"
    assert surface.endpoints == []
    assert all(path != "/32" for path in surface.paths)
    assert plan.target_type == "ip"



def test_true_cidr_end_to_end(tmp_path):
    from core.orchestrator import FathiyaOrchestrator

    logger = FathiyaLogger(str(tmp_path / "logs"))
    orchestrator = FathiyaOrchestrator(memory=DummyMemory(), logger=logger)

    result = orchestrator.run("أريد فحص أمني للنطاق 10.0.0.0/8")
    profile = result["analysis"]["target_profile"]
    surface = result["analysis"]["surface_summary"]
    plan = result["analysis"]["test_plan"]

    assert result["route"].flow == "security"
    assert profile.target_type == "cidr"
    assert profile.normalized_target == "10.0.0.0/8"
    assert surface.endpoints == []
    assert all(path not in {"/8", "/32"} for path in surface.paths)
    assert plan.target_type == "cidr"
    assert any("نطاق" in warning for warning in plan.warnings + profile.risk_notes)



def test_evidence_inflation_regression():
    analyzer = EvidenceAnalyzer()
    profile = TargetProfile(
        raw_input="افحص 8.8.8.8",
        target_type="ip",
        normalized_target="8.8.8.8",
        indicators=["public_ip"],
        potential_services=["http"],
        risk_notes=[],
        confidence=0.85,
    )
    surface = SurfaceSummary(
        raw_input="افحص 8.8.8.8",
        normalized_target="8.8.8.8",
        target_type="ip",
        surface_type="code",
        confidence=0.55,
        endpoints=[],
        paths=[],
        params=[],
        query_keys=[],
        headers=[],
        auth_hints=[],
        forms=[],
        input_points=[],
        indicators=["surface:code"],
        notes=["network target without web surface"],
    )
    test_plan = SecurityTestPlan(
        target_summary="اختبار تضخيم الأدلة",
        target_type="ip",
        steps=[
            SecurityTestStep(
                name="مراجعة input params الحساسة",
                description="فحص param token و cmd لاحقاً",
                category="input-review",
                priority=1,
                tools=["curl"],
            )
        ],
        total_estimated_time="5 دقائق",
        warnings=[],
        scope_notes=[],
    )
    vulnerability_result = VulnerabilityHuntResult(
        target_type="ip",
        surface_type="code",
        checks_run=["sensitive_inputs"],
        findings=[
            PreliminaryFinding(
                title="مدخلات حساسة أو مرتفعة الخطورة في المعاملات",
                classification="possible_finding",
                category="input-handling",
                rationale="إشارة أولية فقط",
                evidence=["token", "cmd"],
                related_elements=["token", "cmd"],
                recommended_next_step="مراجعة يدوية",
                confidence=0.6,
            )
        ],
        notes=["نتيجة أولية"],
        safe_mode=True,
    )

    analysis = analyzer.analyze(profile, surface, test_plan, vulnerability_result)

    assert analysis.total_bundles == 1
    assert analysis.bundles[0].evidence_level == "weak_evidence"
    assert analysis.bundles[0].confidence < 0.8



def test_duplicate_title_regression():
    reporter = SecurityReporter()
    verifier = ExploitVerifier()

    profile = TargetProfile(
        raw_input="افحص http://example.com/login?next=/admin&token=abc",
        target_type="url",
        normalized_target="example.com",
        indicators=["web_server", "http_only"],
        potential_services=["http"],
        risk_notes=["الموقع لا يستخدم HTTPS"],
        confidence=0.9,
    )
    surface = SurfaceSummary(
        raw_input=profile.raw_input,
        normalized_target=profile.normalized_target,
        target_type=profile.target_type,
        surface_type="web",
        confidence=0.9,
        endpoints=["http://example.com/login"],
        paths=["/login", "/admin"],
        params=["next", "token"],
        query_keys=["next", "token"],
        headers=["Authorization"],
        auth_hints=["login-form"],
        forms=[],
        input_points=["endpoint:http://example.com/login", "query:token"],
        indicators=["surface:web"],
        notes=[],
    )
    test_plan = _sample_test_plan(target_type="url")
    title = "عنوان مكرر"
    vulnerability_result = VulnerabilityHuntResult(
        target_type="url",
        surface_type="web",
        checks_run=["transport_hygiene", "sensitive_inputs"],
        findings=[
            PreliminaryFinding(
                title=title,
                classification="likely_finding",
                category="transport",
                rationale="نقل غير مشفر",
                evidence=["http://example.com/login", "login-form"],
                related_elements=["/login"],
                recommended_next_step="مراجعة النقل",
                confidence=0.8,
            ),
            PreliminaryFinding(
                title=title,
                classification="possible_finding",
                category="input-handling",
                rationale="مدخلات حساسة",
                evidence=["next", "token"],
                related_elements=["next", "token"],
                recommended_next_step="مراجعة المدخلات",
                confidence=0.66,
            ),
        ],
        notes=[],
        safe_mode=True,
    )
    evidence_summary = EvidenceAnalysisResult(
        target_type="url",
        surface_type="web",
        bundles=[
            FindingEvidenceBundle(
                finding_title=title,
                finding_category="transport",
                original_classification="likely_finding",
                evidence_level="strong_evidence",
                confidence=0.84,
                atoms=[],
                supporting_points=["http://example.com/login", "login-form"],
                recommended_next_step="مراجعة النقل",
            ),
            FindingEvidenceBundle(
                finding_title=title,
                finding_category="input-handling",
                original_classification="possible_finding",
                evidence_level="medium_evidence",
                confidence=0.63,
                atoms=[],
                supporting_points=["next", "token"],
                recommended_next_step="مراجعة المدخلات",
            ),
        ],
        kept_bundles=[],
        filtered_bundles=[],
        notes=[],
        safe_mode=True,
    )

    exploit_result = verifier.verify(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_summary,
        policy_check=PolicyCheckResult(passed=True, action="allow"),
    )
    report = reporter.build_report(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_summary,
        exploit_summary=exploit_result,
    )

    records = {(record.finding_category, record.finding_title): record for record in exploit_result.records}
    items = {
        (item["category"], item["title"]): item
        for item in report.findings_summary["items"]
    }

    assert records[("transport", title)].state == "verified"
    assert records[("input-handling", title)].state == "needs_manual_review"
    assert items[("transport", title)]["evidence_level"] == "strong_evidence"
    assert items[("input-handling", title)]["evidence_level"] == "medium_evidence"



def test_mixed_text_extraction():
    profiler = TargetProfiler()

    profile = profiler.profile("افحص 999.999.999.999 ثم example.com")

    assert profile.target_type == "domain"
    assert profile.normalized_target == "example.com"



def test_real_planner_integration():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    planner = SecurityTestPlanner()
    hunter = VulnerabilityHunter()
    analyzer = EvidenceAnalyzer()

    raw_text = "افحص http://example.com/login?next=/admin&token=abc مع Authorization ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    surface = mapper.map(profile, raw_text)
    test_plan = planner.plan(profile)
    vulnerability_result = hunter.hunt(profile, surface, test_plan)
    evidence_result = analyzer.analyze(profile, surface, test_plan, vulnerability_result)

    assert test_plan.steps
    assert any(atom.source == "test_planner" for bundle in evidence_result.bundles for atom in bundle.atoms)
    assert vulnerability_result.total_findings >= 1



def test_policy_warn_path():
    profiler = TargetProfiler()
    mapper = SurfaceMapper()
    hunter = VulnerabilityHunter()
    analyzer = EvidenceAnalyzer()
    verifier = ExploitVerifier()

    raw_text = "افحص http://example.com/login?next=/admin&token=abc&cmd=id مع Authorization ونموذج تسجيل الدخول"
    profile = profiler.profile(raw_text)
    surface = mapper.map(profile, raw_text)
    test_plan = _sample_test_plan(target_type=profile.target_type)
    vulnerability_result = hunter.hunt(profile, surface, test_plan)
    evidence_result = analyzer.analyze(profile, surface, test_plan, vulnerability_result)
    exploit_result = verifier.verify(
        target_profile=profile,
        test_plan=test_plan,
        surface_summary=surface,
        vulnerability_summary=vulnerability_result,
        evidence_summary=evidence_result,
        policy_check=PolicyCheckResult(passed=True, action="warn"),
    )

    input_records = [record for record in exploit_result.records if record.finding_category == "input-handling"]
    assert input_records
    assert any(record.policy_action == "warn" for record in input_records)
    assert any("policy-warn-limited-only" in record.constraints_applied for record in input_records)
    assert any(record.state == "needs_manual_review" for record in input_records)


def test_profile_handles_ip_with_path_suffix():
    profile = TargetProfiler().profile("8.8.8.8 /login")

    assert profile.target_type == "ip"
    assert profile.normalized_target == "8.8.8.8"
    assert profile.is_valid is True



def test_profile_handles_ip_with_query_suffix():
    profile = TargetProfiler().profile("8.8.8.8?next=/admin")

    assert profile.target_type == "ip"
    assert profile.normalized_target == "8.8.8.8"
    assert profile.is_valid is True



def test_profile_handles_true_cidr_with_trailing_path_text():
    profile = TargetProfiler().profile("10.0.0.0/8 then /admin")

    assert profile.target_type == "cidr"
    assert profile.normalized_target == "10.0.0.0/8"
    assert profile.is_valid is True



def test_run_tests_runner_is_phase3_isolated_in_lean_env(monkeypatch):
    import builtins
    import importlib

    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "dotenv" or name.startswith("dotenv"):
            raise ModuleNotFoundError("No module named 'dotenv'")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    module = importlib.import_module("tests.run_tests")
    results = module.run_tests()

    assert isinstance(results, list)
    assert results
    assert all(item["status"] in {"PASS", "SKIP", "FAIL", "ERROR"} for item in results)
    assert all(item["name"].isascii() for item in results)
    assert not any(item["status"] == "FAIL" and "dotenv" in item["error"] for item in results)



def test_observability_fields_are_persisted_in_session_snapshot(tmp_path):
    import json
    from core.orchestrator import FathiyaOrchestrator

    memory = DummyMemory()
    logger = FathiyaLogger(str(tmp_path / "logs"))
    orchestrator = FathiyaOrchestrator(memory=memory, logger=logger)

    result = orchestrator.run("أريد فحص أمني للهدف 8.8.8.8?next=/admin")

    assert memory.sessions
    snapshot = json.loads(memory.sessions[-1]["framed_problem_json"])
    assert "benchmark_report" in snapshot
    assert "logging_status" in snapshot
    assert snapshot["logging_status"]["run_log_written"] is True
    assert snapshot["logging_status"]["session_log_written"] is True
    assert snapshot["benchmark_report"]["stages"]
    assert result["analysis"]["logging_status"]["run_log_written"] is True


def test_invalid_mixed_text_cidr_must_fail_closed():
    profile = TargetProfiler().profile("scan 192.168.1.0/99 for vulnerabilities")

    assert profile.target_type == "unknown"
    assert profile.is_valid is False
    assert any("CIDR غير صالح" in note for note in profile.risk_notes)
    assert profile.normalized_target == "scan 192.168.1.0/99 for vulnerabilities"



def test_negative_control_invalid_cidr_case_remains_invalid():
    profile = TargetProfiler().profile("scan 192.168.1.0/99 for vulnerabilities")

    assert profile.target_type != "ip"
    assert profile.normalized_target != "192.168.1.0"



def test_orchestrator_invalid_target_hard_stop(tmp_path):
    from core.orchestrator import FathiyaOrchestrator

    logger = FathiyaLogger(str(tmp_path / "logs"))
    memory = DummyMemory()
    orchestrator = FathiyaOrchestrator(memory=memory, logger=logger)

    result = orchestrator.run("scan 192.168.1.0/99 for vulnerabilities")
    analysis = result["analysis"]
    benchmark_report = result["benchmark_report"]

    assert result["route"].flow == "security"
    assert analysis["target_profile"].is_valid is False
    assert analysis["surface_summary"] is None
    assert analysis["vulnerability_summary"] is None
    assert analysis["security_report"] is None
    assert "surface_mapper" not in benchmark_report["stages"]
    assert "vulnerability_hunter" not in benchmark_report["stages"]
    assert "security_reporter" not in benchmark_report["stages"]
    assert "تم إيقاف المسار الأمني" in result["solver_answer"]



def test_run_tests_exercises_security_flow_explicitly():
    import importlib

    module = importlib.import_module("tests.run_tests")
    results = module.run_tests()

    assert results
    assert all(case["expected_flow"] == "security" for case in module.TEST_CASES)
    assert all(item["name"].startswith("security_") or item["name"] == "phase3_runner_bootstrap" for item in results)
    if results[0]["name"] == "phase3_runner_bootstrap":
        assert results[0]["status"] == "ERROR"
        assert "dependency" in results[0]["error"] or "import error" in results[0]["error"]
    else:
        assert all(item["status"] == "PASS" for item in results)
        assert all(item["name"].startswith("security_") for item in results)


# ── Regression tests: VerificationResult backward-compatibility ──────────


def test_verification_result_exposes_legacy_verdict_property():
    """
    Regression: VerificationResult must expose .verdict so that
    main.py and any legacy output layer can access it without crash.
    """
    vr_pass = VerificationResult(passed=True, issues=[], severity="none")
    vr_fail = VerificationResult(
        passed=False, issues=["مشكلة أمنية"], severity="critical"
    )

    assert vr_pass.verdict == "approve"
    assert vr_fail.verdict == "revise"


def test_verification_result_exposes_legacy_reason_property():
    """
    Regression: VerificationResult must expose .reason so that
    main.py can print it without AttributeError.
    """
    vr_pass = VerificationResult(passed=True, issues=[], severity="none")
    vr_fail = VerificationResult(
        passed=False, issues=["تسريب محتمل", "خطر أمني"], severity="critical"
    )

    assert isinstance(vr_pass.reason, str)
    assert len(vr_pass.reason) > 0
    assert "تسريب محتمل" in vr_fail.reason
    assert "خطر أمني" in vr_fail.reason


def test_verification_result_exposes_legacy_revision_note_property():
    """
    Regression: VerificationResult must expose .revision_note so that
    main.py can print it without AttributeError.
    """
    vr_pass = VerificationResult(passed=True, issues=[], severity="none")
    vr_fail = VerificationResult(
        passed=False, issues=["مشكلة"], severity="warning"
    )
    vr_fail_empty = VerificationResult(passed=False, issues=[], severity="critical")

    assert vr_pass.revision_note == ""
    assert "مشكلة" in vr_fail.revision_note
    assert len(vr_fail_empty.revision_note) > 0


def test_orchestrator_security_result_evaluation_has_legacy_fields(tmp_path):
    """
    Regression: orchestrator.run() returns result["evaluation"] which is a
    VerificationResult in the security flow. main.py accesses .verdict,
    .reason, and .revision_note on it. This test ensures no AttributeError.
    """
    from core.orchestrator import FathiyaOrchestrator

    logger = FathiyaLogger(str(tmp_path / "logs"))
    memory = DummyMemory()
    orchestrator = FathiyaOrchestrator(memory=memory, logger=logger)

    result = orchestrator.run("أريد فحص أمني لموقع example.com")

    evaluation = result["evaluation"]
    # These three accesses are exactly what main.py does (lines 22-24):
    verdict = evaluation.verdict
    reason = evaluation.reason
    revision_note = evaluation.revision_note

    assert verdict in ("approve", "revise")
    assert isinstance(reason, str) and len(reason) > 0
    assert isinstance(revision_note, str)

    # If passed, revision_note should be empty
    if evaluation.passed:
        assert verdict == "approve"
        assert revision_note == ""
    else:
        assert verdict == "revise"
        assert len(revision_note) > 0


def test_orchestrator_security_result_evaluation_domain_ip_cidr(tmp_path):
    """
    Regression: ensure .verdict/.reason/.revision_note work for all
    target types without crash (domain, ip, cidr).
    """
    from core.orchestrator import FathiyaOrchestrator

    cases = [
        ("domain", "أريد فحص أمني لموقع example.com"),
        ("ip", "أريد فحص أمني للهدف 8.8.8.8 /login"),
        ("cidr", "scan 10.0.0.0/8 for vulnerabilities"),
    ]

    for label, user_input in cases:
        logger = FathiyaLogger(str(tmp_path / f"logs_{label}"))
        memory = DummyMemory()
        orchestrator = FathiyaOrchestrator(memory=memory, logger=logger)

        result = orchestrator.run(user_input)
        evaluation = result["evaluation"]

        # Must not raise AttributeError
        v = evaluation.verdict
        r = evaluation.reason
        n = evaluation.revision_note

        assert v in ("approve", "revise"), f"[{label}] unexpected verdict: {v}"
        assert isinstance(r, str), f"[{label}] reason is not str"
        assert isinstance(n, str), f"[{label}] revision_note is not str"


def test_orchestrator_invalid_target_evaluation_has_legacy_fields(tmp_path):
    """
    Regression: even when target is invalid and the security flow
    short-circuits, the returned evaluation must still have legacy fields.
    """
    from core.orchestrator import FathiyaOrchestrator

    logger = FathiyaLogger(str(tmp_path / "logs"))
    memory = DummyMemory()
    orchestrator = FathiyaOrchestrator(memory=memory, logger=logger)

    result = orchestrator.run("scan 192.168.1.0/99 for vulnerabilities")
    evaluation = result["evaluation"]

    # Must not raise AttributeError
    verdict = evaluation.verdict
    reason = evaluation.reason
    revision_note = evaluation.revision_note

    assert verdict in ("approve", "revise")
    assert isinstance(reason, str)
    assert isinstance(revision_note, str)


def test_verification_result_has_issues_still_works():
    """
    Regression: adding backward-compat properties must not break
    the existing has_issues property.
    """
    vr_clean = VerificationResult(passed=True, issues=[])
    vr_dirty = VerificationResult(passed=False, issues=["x"])

    assert vr_clean.has_issues is False
    assert vr_dirty.has_issues is True


def test_verification_result_original_fields_unchanged():
    """
    Regression: the original dataclass fields (passed, issues, severity,
    cleaned_answer) must remain intact after adding adapter properties.
    """
    vr = VerificationResult(
        passed=False,
        issues=["issue1", "issue2"],
        severity="critical",
        cleaned_answer="cleaned text",
    )

    assert vr.passed is False
    assert vr.issues == ["issue1", "issue2"]
    assert vr.severity == "critical"
    assert vr.cleaned_answer == "cleaned text"
    # Adapter properties must not interfere
    assert vr.verdict == "revise"
    assert "issue1" in vr.reason
