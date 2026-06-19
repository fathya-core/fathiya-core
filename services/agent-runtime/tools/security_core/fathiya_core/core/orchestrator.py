import json
import time
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from core.benchmark import PipelineBenchmark
from core.hooks import FathiyaHooks
from core.logger import fathiya_logger
from core.policy_engine import PolicyEngine
from core.router import RequestRouter, RouteResult
from core.verifier import OutputVerifier, VerificationResult
from domains.security.surface_mapper import SurfaceMapper, SurfaceSummary
from domains.security.target_profiler import TargetProfiler, TargetProfile
from domains.security.test_planner import SecurityTestPlanner, TestPlan
from domains.security.vulnerability_hunter import VulnerabilityHunter, VulnerabilityHuntResult
from domains.security.evidence_analyzer import EvidenceAnalyzer, EvidenceAnalysisResult
from domains.security.exploit_verifier import ExploitVerifier, ExploitVerificationResult
from domains.security.security_reporter import SecurityReporter, SecurityReport
from memory.session_memory import SessionMemory

DEBUG = False  # غيّرها إلى True وقت الحاجة للتشخيص


class FathiyaOrchestrator:
    def __init__(
        self,
        router: Optional[RequestRouter] = None,
        policy_engine: Optional[PolicyEngine] = None,
        target_profiler: Optional[TargetProfiler] = None,
        surface_mapper: Optional[SurfaceMapper] = None,
        test_planner: Optional[SecurityTestPlanner] = None,
        vulnerability_hunter: Optional[VulnerabilityHunter] = None,
        evidence_analyzer: Optional[EvidenceAnalyzer] = None,
        exploit_verifier: Optional[ExploitVerifier] = None,
        security_reporter: Optional[SecurityReporter] = None,
        verifier: Optional[OutputVerifier] = None,
        memory: Optional[SessionMemory] = None,
        hooks: Optional[FathiyaHooks] = None,
        logger=None,
        benchmark_factory=PipelineBenchmark,
    ):
        self.router = router or RequestRouter()
        self.policy_engine = policy_engine or PolicyEngine()
        self.target_profiler = target_profiler or TargetProfiler()
        self.surface_mapper = surface_mapper or SurfaceMapper()
        self.test_planner = test_planner or SecurityTestPlanner()
        self.vulnerability_hunter = vulnerability_hunter or VulnerabilityHunter()
        self.evidence_analyzer = evidence_analyzer or EvidenceAnalyzer()
        self.exploit_verifier = exploit_verifier or ExploitVerifier()
        self.security_reporter = security_reporter or SecurityReporter()
        self.verifier = verifier or OutputVerifier()
        self.memory = memory or SessionMemory()
        self.hooks = hooks or FathiyaHooks()
        self.logger = logger or fathiya_logger
        self.benchmark_factory = benchmark_factory

        # يتم تحميل المكوّنات القديمة عند الحاجة فقط للحفاظ على import-safety
        self.framer = None
        self.solver = None
        self.evaluator = None

    def _ensure_legacy_stack(self) -> None:
        if self.framer is not None and self.solver is not None and self.evaluator is not None:
            return

        from agents.framer import ProblemFramer
        from agents.solver import ProblemSolver
        from agents.evaluator import ResponseEvaluator

        self.framer = ProblemFramer()
        self.solver = ProblemSolver()
        self.evaluator = ResponseEvaluator()

    def run(self, user_input: str) -> dict:
        benchmark = self.benchmark_factory()
        benchmark.start_pipeline()

        benchmark.start_stage("router")
        route = self.router.route(user_input)
        benchmark.end_stage("router")

        if route.flow == "security":
            return self._run_security_flow(user_input, route, benchmark)

        benchmark.end_pipeline()
        return self._run_legacy_flow(user_input)

    def _run_security_flow(
        self,
        user_input: str,
        route: RouteResult,
        benchmark: PipelineBenchmark,
    ) -> dict:
        run_id = str(uuid.uuid4())
        self.logger.info(
            "orchestrator",
            "بدء تشغيل المسار الأمني",
            {
                "run_id": run_id,
                "flow": route.flow,
                "matched_keywords": list(route.matched_keywords),
            },
        )

        benchmark.start_stage("policy_engine.check_input")
        policy_check = self.policy_engine.check_input(user_input)
        benchmark.end_stage("policy_engine.check_input")

        if not policy_check.passed:
            blocked_answer = self._build_policy_block_message(policy_check)
            benchmark.start_stage("verifier")
            verification = self.verifier.verify(user_input, blocked_answer, flow="security")
            benchmark.end_stage("verifier")
            return self._finalize_security_result(
                user_input=user_input,
                route=route,
                policy_check=policy_check,
                target_profile=None,
                surface_summary=None,
                vulnerability_summary=None,
                evidence_summary=None,
                exploit_summary=None,
                security_report=None,
                test_plan=None,
                generated_answer=blocked_answer,
                verification=verification,
                benchmark=benchmark,
                run_id=run_id,
            )

        benchmark.start_stage("target_profiler")
        target_profile = self.target_profiler.profile(user_input)
        benchmark.end_stage("target_profiler")

        if not target_profile.is_valid:
            rejected_answer = self._build_invalid_target_message(target_profile)
            benchmark.start_stage("verifier")
            verification = self.verifier.verify(user_input, rejected_answer, flow="security")
            benchmark.end_stage("verifier")
            return self._finalize_security_result(
                user_input=user_input,
                route=route,
                policy_check=policy_check,
                target_profile=target_profile,
                surface_summary=None,
                vulnerability_summary=None,
                evidence_summary=None,
                exploit_summary=None,
                security_report=None,
                test_plan=None,
                generated_answer=rejected_answer,
                verification=verification,
                benchmark=benchmark,
                run_id=run_id,
            )

        benchmark.start_stage("surface_mapper")
        surface_summary = self.surface_mapper.map(target_profile, user_input)
        benchmark.end_stage("surface_mapper")

        benchmark.start_stage("test_planner")
        test_plan = self.test_planner.plan(target_profile)
        benchmark.end_stage("test_planner")

        benchmark.start_stage("vulnerability_hunter")
        vulnerability_summary = self.vulnerability_hunter.hunt(
            target_profile=target_profile,
            surface_summary=surface_summary,
            test_plan=test_plan,
        )
        benchmark.end_stage("vulnerability_hunter")

        benchmark.start_stage("evidence_analyzer")
        evidence_summary = self.evidence_analyzer.analyze(
            target_profile=target_profile,
            surface_summary=surface_summary,
            test_plan=test_plan,
            vulnerability_summary=vulnerability_summary,
        )
        benchmark.end_stage("evidence_analyzer")

        benchmark.start_stage("exploit_verifier")
        exploit_summary = self.exploit_verifier.verify(
            target_profile=target_profile,
            test_plan=test_plan,
            surface_summary=surface_summary,
            vulnerability_summary=vulnerability_summary,
            evidence_summary=evidence_summary,
            policy_check=policy_check,
        )
        benchmark.end_stage("exploit_verifier")

        benchmark.start_stage("security_reporter")
        security_report = self.security_reporter.build_report(
            target_profile=target_profile,
            test_plan=test_plan,
            surface_summary=surface_summary,
            vulnerability_summary=vulnerability_summary,
            evidence_summary=evidence_summary,
            exploit_summary=exploit_summary,
        )
        benchmark.end_stage("security_reporter")

        generated_answer = self._build_security_answer(
            route=route,
            policy_check=policy_check,
            target_profile=target_profile,
            surface_summary=surface_summary,
            test_plan=test_plan,
            vulnerability_summary=vulnerability_summary,
            evidence_summary=evidence_summary,
            exploit_summary=exploit_summary,
            security_report=security_report,
        )

        benchmark.start_stage("verifier")
        verification = self.verifier.verify(user_input, generated_answer, flow="security")
        benchmark.end_stage("verifier")

        return self._finalize_security_result(
            user_input=user_input,
            route=route,
            policy_check=policy_check,
            target_profile=target_profile,
            surface_summary=surface_summary,
            vulnerability_summary=vulnerability_summary,
            evidence_summary=evidence_summary,
            exploit_summary=exploit_summary,
            security_report=security_report,
            test_plan=test_plan,
            generated_answer=generated_answer,
            verification=verification,
            benchmark=benchmark,
            run_id=run_id,
        )

    def _finalize_security_result(
        self,
        user_input: str,
        route: RouteResult,
        policy_check,
        target_profile: Optional[TargetProfile],
        surface_summary: Optional[SurfaceSummary],
        vulnerability_summary: Optional[VulnerabilityHuntResult],
        evidence_summary: Optional[EvidenceAnalysisResult],
        exploit_summary: Optional[ExploitVerificationResult],
        security_report: Optional[SecurityReport],
        test_plan: Optional[TestPlan],
        generated_answer: str,
        verification: VerificationResult,
        benchmark: PipelineBenchmark,
        run_id: str,
    ) -> dict:
        delivered_answer = generated_answer
        if not verification.passed:
            delivered_answer = (
                "تعذر تسليم المخرج كما هو لأن التحقق الأمني فشل. "
                "راجع المشكلات المسجلة قبل متابعة أي تنفيذ."
            )

        analysis: Dict[str, Any] = {
            "route": route,
            "policy_check": policy_check,
            "target_profile": target_profile,
            "surface_summary": surface_summary,
            "vulnerability_summary": vulnerability_summary,
            "evidence_summary": evidence_summary,
            "exploit_summary": exploit_summary,
            "security_report": security_report,
            "test_plan": test_plan,
        }

        evaluator_verdict = "approve" if verification.passed else "blocked"
        evaluator_reason = "؛ ".join(verification.issues) or "نجح التحقق النهائي"

        session_id = self.memory.save_session(
            user_input=user_input,
            framed_problem_json="{}",
            solver_answer=generated_answer,
            evaluator_verdict=evaluator_verdict,
            evaluator_reason=evaluator_reason,
            final_answer=delivered_answer,
        )

        benchmark.end_pipeline()
        benchmark_report = benchmark.get_report()

        run_metadata = {
            "flow": route.flow,
            "target_type": target_profile.target_type if target_profile else "unknown",
            "verifier_severity": verification.severity,
            "policy_action": policy_check.action,
            "surface_type": surface_summary.surface_type if surface_summary else "unknown",
            "vulnerability_findings": vulnerability_summary.total_findings if vulnerability_summary else 0,
            "likely_findings": vulnerability_summary.likely_finding_count if vulnerability_summary else 0,
            "strong_evidence": evidence_summary.strong_evidence_count if evidence_summary else 0,
            "medium_evidence": evidence_summary.medium_evidence_count if evidence_summary else 0,
            "verified_findings": exploit_summary.verified_count if exploit_summary else 0,
            "manual_review_findings": exploit_summary.needs_manual_review_count if exploit_summary else 0,
            "reported_findings": len(security_report.findings_summary.get("items", [])) if security_report else 0,
            "session_id": session_id,
        }
        if benchmark_report.get("api_calls_count", 0) > 0:
            run_metadata["api_calls_count"] = benchmark_report.get("api_calls_count")
            run_metadata["avg_api_latency_seconds"] = benchmark_report.get("avg_api_latency_seconds")
        if benchmark_report.get("total_retries", 0) > 0:
            run_metadata["total_retries"] = benchmark_report.get("total_retries")
            run_metadata["retries_by_component"] = benchmark_report.get("retries_by_component", {})

        run_log_written = self.logger.log_run(
            run_id=run_id,
            stages=benchmark_report.get("stages", {}),
            total_time=benchmark.total_time,
            retries=benchmark.total_retries,
            success=verification.passed,
            metadata=run_metadata,
        )
        session_log_written = self.logger.log_session(
            session_id=session_id,
            user_input=user_input,
            verdict=evaluator_verdict,
            flow=route.flow,
            revised=False,
            metadata={
                "run_id": run_id,
                "target_type": target_profile.target_type if target_profile else "unknown",
                "surface_type": surface_summary.surface_type if surface_summary else "unknown",
                "vulnerability_findings": vulnerability_summary.total_findings if vulnerability_summary else 0,
                "likely_findings": vulnerability_summary.likely_finding_count if vulnerability_summary else 0,
                "strong_evidence": evidence_summary.strong_evidence_count if evidence_summary else 0,
                "medium_evidence": evidence_summary.medium_evidence_count if evidence_summary else 0,
                "verified_findings": exploit_summary.verified_count if exploit_summary else 0,
                "manual_review_findings": exploit_summary.needs_manual_review_count if exploit_summary else 0,
                "reported_findings": len(security_report.findings_summary.get("items", [])) if security_report else 0,
                "verifier_severity": verification.severity,
            },
        )
        logging_status = {
            "run_log_written": run_log_written,
            "session_log_written": session_log_written,
            "last_write_error": self.logger.last_write_error,
        }
        if not run_log_written or not session_log_written:
            self.logger.error("logger", "تم رصد فشل في تسجيل مخرجات الجولة", logging_status)

        analysis["benchmark_report"] = benchmark_report
        analysis["logging_status"] = logging_status
        analysis_json = json.dumps(
            self._serialize_for_json(analysis),
            ensure_ascii=False,
            indent=4,
        )
        if hasattr(self.memory, "sessions") and getattr(self.memory, "sessions", None):
            try:
                self.memory.sessions[-1]["framed_problem_json"] = analysis_json
            except Exception:
                pass

        return {
            "route": route,
            "analysis": analysis,
            "analysis_json": analysis_json,
            "solver_answer": generated_answer,
            "evaluation": verification,
            "final_answer": delivered_answer,
            "revised_by_loop": False,
            "session_id": session_id,
            "recent_sessions": self.memory.get_recent_sessions(limit=5),
            "benchmark_report": benchmark_report,
            "logging_status": logging_status,
        }

    def _build_policy_block_message(self, policy_check) -> str:
        issues = policy_check.violations or ["المدخل لم يجتز فحص السياسات"]
        return (
            "تعذر إنشاء خطة أمنية لأن المدخل لم يجتز فحص السياسات الأولي.\n"
            f"الإجراء: {policy_check.action}\n"
            f"المشكلات: {'؛ '.join(issues)}"
        )

    def _build_invalid_target_message(self, target_profile: TargetProfile) -> str:
        issues = target_profile.risk_notes or ["تعذر تفسير الهدف الأمني بشكل صالح"]
        return (
            "تم إيقاف المسار الأمني لأن الهدف المستخرج غير صالح.\n"
            f"نوع الهدف: {target_profile.target_type}\n"
            f"القيمة المستخرجة: {target_profile.normalized_target or target_profile.raw_input}\n"
            f"المشكلات: {'؛ '.join(issues)}"
        )

    def _build_security_answer(
        self,
        route: RouteResult,
        policy_check,
        target_profile: TargetProfile,
        surface_summary: SurfaceSummary,
        test_plan: TestPlan,
        vulnerability_summary: VulnerabilityHuntResult,
        evidence_summary: EvidenceAnalysisResult,
        exploit_summary: ExploitVerificationResult,
        security_report: SecurityReport,
    ) -> str:
        lines = [
            "تم تفعيل المسار الأمني الحي (phase-3).",
            f"التوجيه: {route.flow} — الثقة {route.confidence}",
            f"الهدف المستخرج: {target_profile.normalized_target or target_profile.raw_input}",
            f"نوع الهدف: {target_profile.target_type}",
            f"نوع السطح: {surface_summary.surface_type}",
            f"حالة فحص السياسات: {policy_check.action}",
            f"عدد النتائج الأولية: {vulnerability_summary.total_findings}",
            f"عدد حزم الأدلة المحتفظ بها: {len(evidence_summary.kept_bundles)}",
            f"عدد النتائج المتحقق منها بشكل محدود: {exploit_summary.verified_count}",
            "",
            f"ملخص الخطة: {test_plan.target_summary}",
            f"إجمالي الوقت التقديري: {test_plan.total_estimated_time}",
            "الخطوات ذات الأولوية الأعلى:",
        ]

        high_priority_steps = test_plan.get_steps_by_priority(max_priority=2) or test_plan.steps[:3]
        for idx, step in enumerate(high_priority_steps[:4], start=1):
            tools_text = ", ".join(step.tools[:4]) if step.tools else "بدون أدوات محددة"
            lines.append(
                f"{idx}. {step.name} — {step.description} "
                f"(الفئة: {step.category}, الأولوية: {step.priority}, أدوات مقترحة: {tools_text})"
            )

        if surface_summary.endpoints:
            lines.append("")
            lines.append("نقاط الدخول المحتملة:")
            for endpoint in surface_summary.endpoints[:5]:
                lines.append(f"- {endpoint}")

        if surface_summary.query_keys or surface_summary.headers or surface_summary.auth_hints:
            lines.append("")
            lines.append("مؤشرات السطح:")
            if surface_summary.query_keys:
                lines.append(f"- query keys: {', '.join(surface_summary.query_keys[:8])}")
            if surface_summary.headers:
                lines.append(f"- headers: {', '.join(surface_summary.headers[:8])}")
            if surface_summary.auth_hints:
                lines.append(f"- auth hints: {', '.join(surface_summary.auth_hints[:8])}")

        if surface_summary.forms:
            lines.append("")
            lines.append("نماذج إدخال محتملة:")
            for form in surface_summary.forms[:3]:
                fields_text = ", ".join(form.fields[:6]) if form.fields else "بدون حقول محددة"
                lines.append(f"- {form.name} ({form.method}) — الحقول: {fields_text}")

        if vulnerability_summary.findings:
            lines.append("")
            lines.append("النتائج الأولية:")
            for finding in vulnerability_summary.findings[:5]:
                lines.append(
                    f"- [{finding.classification}] {finding.title}: {finding.rationale}"
                )

        if evidence_summary.kept_bundles:
            lines.append("")
            lines.append("ملخص الأدلة:")
            for bundle in evidence_summary.kept_bundles[:5]:
                lines.append(
                    f"- [{bundle.evidence_level}] {bundle.finding_title} — الثقة {bundle.confidence}"
                )

        if exploit_summary.records:
            lines.append("")
            lines.append("حالات التحقق المحدود:")
            for record in exploit_summary.records[:5]:
                lines.append(
                    f"- [{record.state}] {record.finding_title} — مستوى الدليل {record.evidence_level}"
                )

        if test_plan.warnings:
            lines.append("")
            lines.append("تحذيرات النطاق:")
            for warning in test_plan.warnings:
                lines.append(f"- {warning}")

        if test_plan.scope_notes:
            lines.append("")
            lines.append("ملاحظات النطاق:")
            for note in test_plan.scope_notes:
                lines.append(f"- {note}")

        lines.extend([
            "",
            "هذه الخلاصة تخطيطية ودفاعية، ولا تتضمن أوامر تشغيلية خطيرة أو خطوات استغلال مباشرة.",
            "النتائج المذكورة هنا أولية وغير مؤكدة، وتستلزم مرحلة تحقق منفصلة إذا لزم الأمر.",
            "تحليل الأدلة هنا استدلالي فقط، ولم يتضمن exploit verification أو confirmation نهائي.",
            "التحقق المحدود هنا غير عدواني، ويراعي السياسات صراحةً، ولا يرقى إلى استغلال عميق أو إثبات اختراق حاسم.",
            "التقرير النهائي أدناه منظم ومتوافق مع JSON في طبقة التحليل الداخلية.",
            "",
            security_report.human_readable,
        ])
        return "\n".join(lines).strip()

    def _serialize_for_json(self, value: Any) -> Any:
        if value is None:
            return None
        if is_dataclass(value):
            return {k: self._serialize_for_json(v) for k, v in asdict(value).items()}
        if isinstance(value, dict):
            return {k: self._serialize_for_json(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._serialize_for_json(v) for v in value]
        if hasattr(value, "model_dump"):
            return self._serialize_for_json(value.model_dump())
        return value

    def _run_legacy_flow(self, user_input: str) -> dict:
        self._ensure_legacy_stack()

        session_check = self.hooks.on_session_start(user_input)
        if not session_check.passed:
            raise ValueError(f"SessionStart hook failed: {session_check.reason}")

        analysis = self.framer.frame(user_input)
        analysis_json = analysis.model_dump_json(indent=4)

        pre_solver_check = self.hooks.pre_solver(
            user_input=user_input,
            handling_strategy=analysis.handling_strategy
        )
        if not pre_solver_check.passed:
            raise ValueError(f"PreSolver hook failed: {pre_solver_check.reason}")

        solver_answer = self.solver.solve(user_input, analysis)

        post_solver_check = self.hooks.post_solver(user_input, solver_answer)
        if not post_solver_check.passed:
            raise ValueError(f"PostSolver hook failed: {post_solver_check.reason}")

        if post_solver_check.cleaned_text:
            solver_answer = post_solver_check.cleaned_text

        final_answer = solver_answer
        revised_by_loop = False

        if post_solver_check.needs_revision:
            if DEBUG:
                print("\n[DEBUG] Hook requested revision")
                print(f"[DEBUG] hook reason: {post_solver_check.reason}")

            revised_answer = self.solver.revise(
                user_input=user_input,
                original_answer=solver_answer,
                revision_note=post_solver_check.reason
            )

            if DEBUG:
                print("\n[DEBUG] Revised answer from Solver (hook revision):")
                print(revised_answer)

            post_revision_check = self.hooks.post_revision(
                revised_answer=revised_answer,
                original_answer=solver_answer
            )

            if DEBUG:
                print(f"\n[DEBUG] post_revision_check.passed (hook): {post_revision_check.passed}")
                print(f"[DEBUG] post_revision_check.reason (hook): {post_revision_check.reason}")

            if post_revision_check.passed:
                final_answer = post_revision_check.cleaned_text or revised_answer
                revised_by_loop = True
            else:
                final_answer = solver_answer

        evaluation = self.evaluator.evaluate(user_input, final_answer)

        if evaluation.verdict == "revise":
            note = evaluation.revision_note.strip() or evaluation.reason.strip()

            if DEBUG:
                print("\n[DEBUG] Evaluator requested revision")
                print(f"[DEBUG] verdict: {evaluation.verdict}")
                print(f"[DEBUG] reason: {evaluation.reason}")
                print(f"[DEBUG] revision_note: {note}")

            revised_answer = self.solver.revise(
                user_input=user_input,
                original_answer=final_answer,
                revision_note=note
            )

            if DEBUG:
                print("\n[DEBUG] Revised answer from Solver (evaluator revision):")
                print(revised_answer)

            post_revision_check = self.hooks.post_revision(
                revised_answer=revised_answer,
                original_answer=final_answer
            )

            if DEBUG:
                print(f"\n[DEBUG] post_revision_check.passed (evaluator): {post_revision_check.passed}")
                print(f"[DEBUG] post_revision_check.reason (evaluator): {post_revision_check.reason}")

            if post_revision_check.passed:
                final_answer = post_revision_check.cleaned_text or revised_answer
                revised_by_loop = True

        session_id = self.memory.save_session(
            user_input=user_input,
            framed_problem_json=analysis_json,
            solver_answer=solver_answer,
            evaluator_verdict=evaluation.verdict,
            evaluator_reason=evaluation.reason,
            final_answer=final_answer
        )

        return {
            "analysis": analysis,
            "analysis_json": analysis_json,
            "solver_answer": solver_answer,
            "evaluation": evaluation,
            "final_answer": final_answer,
            "revised_by_loop": revised_by_loop,
            "session_id": session_id,
            "recent_sessions": self.memory.get_recent_sessions(limit=5)
        }
