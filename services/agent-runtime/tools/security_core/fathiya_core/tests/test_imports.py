"""
tests/test_imports.py — اختبار شامل لجميع الاستيرادات والوظائف

يتحقق من أن كل الوحدات والملفات تعمل بشكل صحيح.
يشمل: المرحلة 1 + 2 + 3 + 4 (جزئي) + الإضافات.
"""

import sys
import os

# إضافة مسار المشروع
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASSED = 0
FAILED = 0


def test(name, func):
    global PASSED, FAILED
    try:
        func()
        print(f"  [PASS] {name}")
        PASSED += 1
    except Exception as e:
        print(f"  [FAIL] {name} — {e}")
        FAILED += 1


print("=" * 70)
print("FATHIYA CORE — Comprehensive Test Suite (Phase 1-4)")
print("=" * 70)

# ============================================================
# المرحلة 1: اختبار الملفات المُصلحة
# ============================================================
print("\n--- المرحلة 1: Mandatory Fix ---")

test("schemas.target_schema → FramedProblem",
     lambda: __import__("schemas.target_schema", fromlist=["FramedProblem"]))

test("schemas.framer_schema → FramedProblem (re-export)",
     lambda: __import__("schemas.framer_schema", fromlist=["FramedProblem"]))

test("agents.framer → ProblemFramer",
     lambda: __import__("agents.framer", fromlist=["ProblemFramer"]))

test("agents.solver → ProblemSolver",
     lambda: __import__("agents.solver", fromlist=["ProblemSolver"]))

test("agents.evaluator → ResponseEvaluator, EvaluationResult",
     lambda: __import__("agents.evaluator", fromlist=["ResponseEvaluator", "EvaluationResult"]))

test("memory.session_memory → SessionMemory",
     lambda: __import__("memory.session_memory", fromlist=["SessionMemory"]))

test("core.hooks → FathiyaHooks, HookResult",
     lambda: __import__("core.hooks", fromlist=["FathiyaHooks", "HookResult"]))

test("core.orchestrator → FathiyaOrchestrator",
     lambda: __import__("core.orchestrator", fromlist=["FathiyaOrchestrator"]))

test("core.memory → SessionMemory",
     lambda: __import__("core.memory", fromlist=["SessionMemory"]))

test("domains.security.framer → ProblemFramer",
     lambda: __import__("domains.security.framer", fromlist=["ProblemFramer"]))

test("domains.security.solver → ProblemSolver",
     lambda: __import__("domains.security.solver", fromlist=["ProblemSolver"]))

test("domains.security.evaluator → ResponseEvaluator",
     lambda: __import__("domains.security.evaluator", fromlist=["ResponseEvaluator"]))

# ============================================================
# المرحلة 2: اختبار طبقات الاستقرار
# ============================================================
print("\n--- المرحلة 2: Stabilization Layer ---")

test("config.settings → settings",
     lambda: __import__("config.settings", fromlist=["settings"]))

test("config.models → AVAILABLE_MODELS, DEFAULT_MODEL",
     lambda: __import__("config.models", fromlist=["AVAILABLE_MODELS", "DEFAULT_MODEL"]))

test("config.policies → policies",
     lambda: __import__("config.policies", fromlist=["policies"]))

test("config → settings, policies",
     lambda: __import__("config", fromlist=["settings", "policies"]))

test("models.model_registry → ModelRegistry",
     lambda: __import__("models.model_registry", fromlist=["ModelRegistry"]))

test("models.provider_openrouter → OpenRouterProvider",
     lambda: __import__("models.provider_openrouter", fromlist=["OpenRouterProvider"]))

test("models.provider_openai → OpenAIProvider",
     lambda: __import__("models.provider_openai", fromlist=["OpenAIProvider"]))

test("models → ModelRegistry, OpenRouterProvider, OpenAIProvider",
     lambda: __import__("models", fromlist=["ModelRegistry", "OpenRouterProvider", "OpenAIProvider"]))

# ============================================================
# المرحلة 3: Core Upgrade
# ============================================================
print("\n--- المرحلة 3: Core Upgrade ---")

test("core.router → RequestRouter, RouteResult",
     lambda: __import__("core.router", fromlist=["RequestRouter", "RouteResult"]))

test("core.verifier → OutputVerifier, VerificationResult",
     lambda: __import__("core.verifier", fromlist=["OutputVerifier", "VerificationResult"]))

test("core.policy_engine → PolicyEngine, PolicyCheckResult",
     lambda: __import__("core.policy_engine", fromlist=["PolicyEngine", "PolicyCheckResult"]))

test("core.logger → fathiya_logger, FathiyaLogger",
     lambda: __import__("core.logger", fromlist=["fathiya_logger", "FathiyaLogger"]))

test("core.benchmark → PipelineBenchmark",
     lambda: __import__("core.benchmark", fromlist=["PipelineBenchmark"]))

# ============================================================
# المرحلة 4 (جزئي): domains/security
# ============================================================
print("\n--- المرحلة 4: Security Domain ---")

test("domains.security.target_profiler → TargetProfiler, TargetProfile",
     lambda: __import__("domains.security.target_profiler", fromlist=["TargetProfiler", "TargetProfile"]))

test("domains.security.test_planner → SecurityTestPlanner, TestPlan",
     lambda: __import__("domains.security.test_planner", fromlist=["SecurityTestPlanner", "TestPlan"]))

# ============================================================
# اختبارات وظيفية — Router
# ============================================================
print("\n--- اختبارات وظيفية: Router ---")


def test_router_security():
    from core.router import RequestRouter
    router = RequestRouter()
    result = router.route("افحص موقع example.com بحثاً عن ثغرات XSS")
    assert result.flow == "security", f"Expected 'security', got '{result.flow}'"
    assert result.confidence > 0, "Confidence should be > 0"
    assert len(result.matched_keywords) > 0, "Should have matched keywords"


test("Router: security flow detection", test_router_security)


def test_router_sast():
    from core.router import RequestRouter
    router = RequestRouter()
    result = router.route("حلل الكود المصدري بحثاً عن أخطاء باستخدام static analysis")
    assert result.flow == "sast", f"Expected 'sast', got '{result.flow}'"


test("Router: SAST flow detection", test_router_sast)


def test_router_crypto():
    from core.router import RequestRouter
    router = RequestRouter()
    result = router.route("ما هو سعر بيتكوين اليوم في بورصة binance")
    assert result.flow == "crypto", f"Expected 'crypto', got '{result.flow}'"


test("Router: crypto flow detection", test_router_crypto)


def test_router_general():
    from core.router import RequestRouter
    router = RequestRouter()
    result = router.route("أبي أسوي مشروع")
    assert result.flow == "general", f"Expected 'general', got '{result.flow}'"


test("Router: general flow fallback", test_router_general)


def test_router_empty():
    from core.router import RequestRouter
    router = RequestRouter()
    result = router.route("")
    assert result.flow == "general"
    assert result.confidence == 0.0


test("Router: empty input handling", test_router_empty)


def test_router_supported_flows():
    from core.router import RequestRouter
    router = RequestRouter()
    flows = router.get_supported_flows()
    assert "security" in flows
    assert "sast" in flows
    assert "crypto" in flows
    assert "general" in flows


test("Router: supported flows list", test_router_supported_flows)


def test_router_mixed_keywords():
    from core.router import RequestRouter
    router = RequestRouter()
    # نص يحتوي كلمات أمنية متعددة
    result = router.route("أريد فحص الموقع واختبار اختراق مع nmap و burp")
    assert result.flow == "security"
    assert result.confidence > 0.5, f"Expected confidence > 0.5, got {result.confidence}"


test("Router: multiple security keywords boost confidence", test_router_mixed_keywords)

# ============================================================
# اختبارات وظيفية — Verifier
# ============================================================
print("\n--- اختبارات وظيفية: Verifier ---")


def test_verifier_pass():
    from core.verifier import OutputVerifier
    v = OutputVerifier()
    result = v.verify(
        user_input="كيف أتعلم البرمجة",
        final_answer="يمكنك البدء بتعلم لغة بايثون من خلال دورات مجانية على الإنترنت. ابدأ بالأساسيات مثل المتغيرات والحلقات والدوال.",
        flow="general"
    )
    assert result.passed, f"Should pass, issues: {result.issues}"


test("Verifier: clean answer passes", test_verifier_pass)


def test_verifier_empty():
    from core.verifier import OutputVerifier
    v = OutputVerifier()
    result = v.verify("سؤال", "", "general")
    assert not result.passed
    assert result.severity == "critical"


test("Verifier: empty answer fails", test_verifier_empty)


def test_verifier_internal_leak():
    from core.verifier import OutputVerifier
    v = OutputVerifier()
    result = v.verify(
        "سؤال",
        "الـ Framer حلل السؤال وأرسله للـ Solver عبر الـ pipeline",
        "general"
    )
    assert result.has_issues, "Should detect internal leak"


test("Verifier: internal leak detection", test_verifier_internal_leak)


def test_verifier_quick():
    from core.verifier import OutputVerifier
    v = OutputVerifier()
    assert v.quick_verify("هذا رد صالح وكافي") == True
    assert v.quick_verify("") == False
    assert v.quick_verify("قصير") == False


test("Verifier: quick_verify", test_verifier_quick)


def test_verifier_security_dangerous():
    from core.verifier import OutputVerifier
    v = OutputVerifier()
    result = v.verify(
        "كيف أحذف ملفات",
        "استخدم الأمر rm -rf / لحذف كل شيء",
        "security"
    )
    assert result.has_issues, "Should detect dangerous command"


test("Verifier: dangerous command detection in security flow", test_verifier_security_dangerous)

# ============================================================
# اختبارات وظيفية — PolicyEngine
# ============================================================
print("\n--- اختبارات وظيفية: PolicyEngine ---")


def test_policy_input_valid():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_input("أريد تعلم البرمجة بلغة بايثون")
    assert result.passed, f"Should pass, violations: {result.violations}"
    assert result.action == "allow"


test("PolicyEngine: valid input passes", test_policy_input_valid)


def test_policy_input_empty():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_input("")
    assert not result.passed
    assert result.action == "block"


test("PolicyEngine: empty input blocked", test_policy_input_empty)


def test_policy_input_short():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_input("ا")
    assert not result.passed
    assert len(result.violations) > 0


test("PolicyEngine: too short input blocked", test_policy_input_short)


def test_policy_output_valid():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_output(
        "كيف أتعلم",
        "ابدأ بتعلم الأساسيات ثم تدرج في المواضيع المتقدمة",
        "direct_execution"
    )
    assert result.passed


test("PolicyEngine: valid output passes", test_policy_output_valid)


def test_policy_output_empty():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_output("سؤال", "", "direct_execution")
    assert not result.passed
    assert result.action == "block"


test("PolicyEngine: empty output blocked", test_policy_output_empty)


def test_policy_strategy_check():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    assert engine.check_strategy("direct_execution").passed
    assert engine.check_strategy("clarify_first").passed
    assert engine.check_strategy("research_first").passed
    assert engine.check_strategy("analysis_then_execution").passed
    assert not engine.check_strategy("unknown_strategy").passed


test("PolicyEngine: strategy validation", test_policy_strategy_check)


def test_policy_revision_check():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_revision(
        revised_answer="هذا الرد المعدل الجديد والمحسن",
        original_answer="هذا الرد الأصلي"
    )
    assert result.passed


test("PolicyEngine: revision check passes", test_policy_revision_check)


def test_policy_revision_empty():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    result = engine.check_revision("", "الرد الأصلي")
    assert not result.passed


test("PolicyEngine: empty revision blocked", test_policy_revision_empty)


def test_policy_max_revision():
    from core.policy_engine import PolicyEngine
    engine = PolicyEngine()
    assert engine.max_revision_rounds > 0


test("PolicyEngine: max_revision_rounds accessible", test_policy_max_revision)

# ============================================================
# اختبارات وظيفية — TargetProfiler
# ============================================================
print("\n--- اختبارات وظيفية: TargetProfiler ---")


def test_profiler_domain():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("example.com")
    assert profile.target_type == "domain"
    assert profile.is_valid
    assert "domain" in profile.indicators
    assert profile.confidence > 0.5


test("TargetProfiler: domain detection", test_profiler_domain)


def test_profiler_ip():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("192.168.1.1")
    assert profile.target_type == "ip"
    assert "private_network" in profile.indicators


test("TargetProfiler: private IP detection", test_profiler_ip)


def test_profiler_public_ip():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("8.8.8.8")
    assert profile.target_type == "ip"
    assert "public_ip" in profile.indicators


test("TargetProfiler: public IP detection", test_profiler_public_ip)


def test_profiler_url():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("https://example.com/admin")
    assert profile.target_type == "url"
    assert "https" in profile.indicators


test("TargetProfiler: URL detection", test_profiler_url)


def test_profiler_cidr():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("10.0.0.0/8")
    assert profile.target_type == "cidr"
    assert "wide_range" in profile.indicators


test("TargetProfiler: CIDR detection", test_profiler_cidr)


def test_profiler_empty():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("")
    assert profile.target_type == "unknown"
    assert not profile.is_valid


test("TargetProfiler: empty input handling", test_profiler_empty)


def test_profiler_text_extraction():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("أريد فحص الموقع https://test.example.com")
    assert profile.target_type == "url"
    assert profile.normalized_target == "test.example.com"


test("TargetProfiler: URL extraction from text", test_profiler_text_extraction)


def test_profiler_prioritizes_url_over_program_domain():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile(
        "Authorized Bugcrowd Web.com target https://www.hostgator.com/my-account/login"
    )
    assert profile.target_type == "url"
    assert profile.normalized_target == "www.hostgator.com"


test("TargetProfiler: URL priority over program domain", test_profiler_prioritizes_url_over_program_domain)


def test_profiler_extract_multiple():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    targets = profiler.extract_targets(
        "افحص https://a.com و 192.168.1.1 و test.example.org"
    )
    assert len(targets) >= 2, f"Expected >= 2 targets, got {len(targets)}"


test("TargetProfiler: multiple target extraction", test_profiler_extract_multiple)


def test_profiler_sensitive_tld():
    from domains.security.target_profiler import TargetProfiler
    profiler = TargetProfiler()
    profile = profiler.profile("secret.gov")
    assert "sensitive_tld" in profile.indicators
    assert len(profile.risk_notes) > 0


test("TargetProfiler: sensitive TLD warning", test_profiler_sensitive_tld)

# ============================================================
# اختبارات وظيفية — TestPlanner
# ============================================================
print("\n--- اختبارات وظيفية: TestPlanner ---")


def test_planner_web():
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()
    profile = profiler.profile("example.com")
    plan = planner.plan(profile)
    assert plan.step_count > 0, "Should have steps"
    assert plan.target_type == "domain"
    categories = {s.category for s in plan.steps}
    assert "recon" in categories
    assert "scan" in categories
    assert "vuln" in categories
    assert "report" in categories


test("TestPlanner: web test plan", test_planner_web)


def test_planner_ip():
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()
    profile = profiler.profile("8.8.8.8")
    plan = planner.plan(profile)
    assert plan.step_count > 0
    assert plan.target_type == "ip"


test("TestPlanner: IP test plan", test_planner_ip)


def test_planner_cidr():
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()
    profile = profiler.profile("192.168.0.0/24")
    plan = planner.plan(profile)
    assert plan.step_count > 0
    assert plan.target_type == "cidr"


test("TestPlanner: CIDR test plan", test_planner_cidr)


def test_planner_unknown():
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()
    profile = profiler.profile("")
    plan = planner.plan(profile)
    assert plan.target_type == "unknown"
    assert len(plan.warnings) > 0


test("TestPlanner: unknown target plan", test_planner_unknown)


def test_planner_filter_by_priority():
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()
    profile = profiler.profile("example.com")
    plan = planner.plan(profile)
    high_priority = plan.get_steps_by_priority(1)
    assert len(high_priority) > 0, "Should have high priority steps"
    for step in high_priority:
        assert step.priority <= 1


test("TestPlanner: filter by priority", test_planner_filter_by_priority)


def test_planner_filter_by_category():
    from domains.security.target_profiler import TargetProfiler
    from domains.security.test_planner import SecurityTestPlanner
    profiler = TargetProfiler()
    planner = SecurityTestPlanner()
    profile = profiler.profile("example.com")
    plan = planner.plan(profile)
    recon_steps = plan.get_steps_by_category("recon")
    assert len(recon_steps) > 0


test("TestPlanner: filter by category", test_planner_filter_by_category)

# ============================================================
# اختبارات وظيفية — Logger
# ============================================================
print("\n--- اختبارات وظيفية: Logger ---")


def test_logger_basic():
    import tempfile
    from core.logger import FathiyaLogger
    tmp = tempfile.mkdtemp()
    logger = FathiyaLogger(log_dir=tmp)
    logger.info("test", "رسالة اختبار", {"key": "value"})
    logger.error("test", "خطأ اختبار")
    logger.warning("test", "تحذير")
    logger.debug("test", "تشخيص")
    logger.critical("test", "حرج")

    runs = logger.read_log("runs")
    assert len(runs) >= 3, f"Expected >= 3 run entries, got {len(runs)}"

    errors = logger.read_log("errors")
    assert len(errors) >= 2, f"Expected >= 2 error entries, got {len(errors)}"

    # التحقق من بنية السجل
    entry = runs[0]
    assert "timestamp" in entry
    assert "level" in entry
    assert "component" in entry
    assert "message" in entry
    assert "metadata" in entry

    logger.clear_logs()


test("Logger: basic logging and reading", test_logger_basic)


def test_logger_session():
    import tempfile
    from core.logger import FathiyaLogger
    tmp = tempfile.mkdtemp()
    logger = FathiyaLogger(log_dir=tmp)
    logger.log_session(
        session_id=1,
        user_input="سؤال اختبار",
        verdict="approve",
        flow="security"
    )
    sessions = logger.read_log("sessions")
    assert len(sessions) == 1
    assert sessions[0]["metadata"]["session_id"] == 1
    logger.clear_logs()


test("Logger: session logging", test_logger_session)


def test_logger_api_call():
    import tempfile
    from core.logger import FathiyaLogger
    tmp = tempfile.mkdtemp()
    logger = FathiyaLogger(log_dir=tmp)
    logger.log_api_call("framer", "nemotron", 2.5, True, attempt=1)
    logger.log_api_call("solver", "nemotron", 0.0, False, attempt=2, error="timeout")
    runs = logger.read_log("runs")
    assert len(runs) == 2
    assert runs[0]["metadata"]["model"] == "nemotron"
    assert runs[1]["metadata"]["success"] == False
    logger.clear_logs()


test("Logger: API call logging", test_logger_api_call)


def test_logger_run():
    import tempfile
    from core.logger import FathiyaLogger
    tmp = tempfile.mkdtemp()
    logger = FathiyaLogger(log_dir=tmp)
    logger.log_run(
        run_id="test-001",
        stages={"framer": 1.2, "solver": 3.5, "evaluator": 0.8},
        total_time=5.5,
        retries=1,
        success=True
    )
    runs = logger.read_log("runs")
    assert len(runs) == 1
    assert runs[0]["metadata"]["run_id"] == "test-001"
    logger.clear_logs()


test("Logger: pipeline run logging", test_logger_run)

# ============================================================
# اختبارات وظيفية — Benchmark
# ============================================================
print("\n--- اختبارات وظيفية: Benchmark ---")


def test_benchmark_stages():
    import time as t
    from core.benchmark import PipelineBenchmark
    bench = PipelineBenchmark()
    bench.start_pipeline()
    bench.start_stage("test_stage")
    t.sleep(0.02)
    duration = bench.end_stage("test_stage")
    bench.end_pipeline()
    assert duration > 0
    assert bench.total_time > 0
    report = bench.get_report()
    assert "test_stage" in report["stages"]


test("Benchmark: stage timing", test_benchmark_stages)


def test_benchmark_api_tracking():
    from core.benchmark import PipelineBenchmark
    bench = PipelineBenchmark()
    bench.record_api_call("framer", 1.5, True)
    bench.record_api_call("solver", 2.0, False)
    bench.record_retry("solver")
    assert bench.total_api_calls == 2
    assert bench.total_retries == 1
    assert bench.avg_api_latency > 0


test("Benchmark: API call tracking", test_benchmark_api_tracking)


def test_benchmark_summary():
    from core.benchmark import PipelineBenchmark
    bench = PipelineBenchmark()
    bench.start_pipeline()
    bench.start_stage("s1")
    bench.end_stage("s1")
    bench.end_pipeline()
    summary = bench.get_summary()
    assert "s1" in summary
    assert "FATHIYA" in summary


test("Benchmark: summary generation", test_benchmark_summary)


def test_benchmark_reset():
    from core.benchmark import PipelineBenchmark
    bench = PipelineBenchmark()
    bench.start_pipeline()
    bench.record_api_call("x", 1.0, True)
    bench.record_retry("x")
    bench.reset()
    assert bench.total_api_calls == 0
    assert bench.total_retries == 0


test("Benchmark: reset", test_benchmark_reset)

# ============================================================
# اختبارات وظيفية أصلية (المرحلة 1 + 2)
# ============================================================
print("\n--- اختبارات وظيفية أصلية ---")


def test_framed_problem_creation():
    from schemas.target_schema import FramedProblem
    fp = FramedProblem(
        problem_type="exploratory",
        clarity_score=5,
        needs_research=False,
        needs_clarification=False,
        missing_information=[],
        handling_strategy="direct_execution",
        sub_tasks=["فهم الطلب"]
    )
    assert fp.problem_type == "exploratory"
    assert fp.clarity_score == 5


test("FramedProblem instantiation", test_framed_problem_creation)


def test_framer_schema_reexport():
    from schemas.framer_schema import FramedProblem as FP1
    from schemas.target_schema import FramedProblem as FP2
    assert FP1 is FP2


test("framer_schema re-export identity", test_framer_schema_reexport)


def test_settings_object():
    from config.settings import settings
    assert hasattr(settings, "openrouter_api_key")
    assert hasattr(settings, "retry")
    assert hasattr(settings, "timeout")
    assert settings.retry.max_retries == 5


test("settings object attributes", test_settings_object)


def test_policies_object():
    from config.policies import policies
    assert policies.is_valid_strategy("direct_execution")
    assert not policies.is_valid_strategy("unknown_strategy")
    assert policies.is_overlong_answer(5, 300)
    assert not policies.is_overlong_answer(20, 100)


test("policies object methods", test_policies_object)


def test_model_registry():
    from models.model_registry import ModelRegistry
    registry = ModelRegistry()
    model_id = registry.get_model_id("framer")
    assert "nemotron" in model_id.lower()
    status = registry.get_status()
    assert "framer" in status
    assert "solver" in status
    assert "evaluator" in status


test("ModelRegistry basic operations", test_model_registry)


def test_session_memory():
    from memory.session_memory import SessionMemory
    import tempfile
    db_path = os.path.join(tempfile.mkdtemp(), "test.db")
    mem = SessionMemory(db_path=db_path)
    sid = mem.save_session(
        user_input="test",
        framed_problem_json="{}",
        solver_answer="answer",
        evaluator_verdict="approve",
        evaluator_reason="ok",
        final_answer="final"
    )
    assert sid == 1
    session = mem.get_session_by_id(sid)
    assert session is not None
    recent = mem.get_recent_sessions(limit=5)
    assert len(recent) == 1
    os.unlink(db_path)


test("SessionMemory CRUD operations", test_session_memory)

# ============================================================
# الملخص
# ============================================================
print("\n" + "=" * 70)
TOTAL = PASSED + FAILED
print(f"TOTAL: {TOTAL}  |  PASSED: {PASSED}  |  FAILED: {FAILED}")
if FAILED == 0:
    print("ALL TESTS PASSED")
else:
    print(f"WARNING: {FAILED} test(s) failed!")
print("=" * 70)
