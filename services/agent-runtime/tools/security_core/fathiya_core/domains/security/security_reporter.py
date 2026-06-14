"""
domains/security/security_reporter.py — مولد التقرير الأمني المنظم

يستهلك مخرجات:
- TargetProfile من target_profiler
- TestPlan من test_planner
- SurfaceSummary من surface_mapper
- VulnerabilityHuntResult من vulnerability_hunter
- EvidenceAnalysisResult من evidence_analyzer
- ExploitVerificationResult من exploit_verifier

ويحوّلها إلى تقرير منظم:
- JSON-compatible
- human-readable

مع الحفاظ على التوافق الخلفي وعدم إدخال أي توسعة معمارية إضافية.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from domains.security.evidence_analyzer import EvidenceAnalysisResult, FindingEvidenceBundle
from domains.security.exploit_verifier import ExploitVerificationResult, VerificationRecord
from domains.security.surface_mapper import SurfaceForm, SurfaceSummary
from domains.security.target_profiler import TargetProfile
from domains.security.test_planner import TestPlan
from domains.security.vulnerability_hunter import PreliminaryFinding, VulnerabilityHuntResult


@dataclass
class ReportFindingEntry:
    title: str
    category: str
    initial_classification: str
    evidence_level: str
    confidence: float
    verification_status: str
    rationale: str
    evidence_points: List[str] = field(default_factory=list)
    verified_signals: List[str] = field(default_factory=list)
    recommended_next_step: str = ""


@dataclass
class SecurityReport:
    target_summary: Dict[str, Any]
    attack_surface_summary: Dict[str, Any]
    findings_summary: Dict[str, Any]
    evidence_summary: Dict[str, Any]
    confidence_levels: Dict[str, Any]
    verification_status: Dict[str, Any]
    recommended_next_step: str
    human_readable: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SecurityReporter:
    """يبني تقريراً أمنياً منظمًا ومقروءًا دون تغيير معنى المخرجات الأساسية."""

    def build_report(
        self,
        target_profile: TargetProfile,
        test_plan: TestPlan,
        surface_summary: SurfaceSummary,
        vulnerability_summary: VulnerabilityHuntResult,
        evidence_summary: EvidenceAnalysisResult,
        exploit_summary: ExploitVerificationResult,
    ) -> SecurityReport:
        bundle_map = {
            (bundle.finding_category, bundle.finding_title): bundle
            for bundle in evidence_summary.bundles
        }
        verification_map = {
            (record.finding_category, record.finding_title): record
            for record in exploit_summary.records
        }

        finding_entries = self._build_finding_entries(
            vulnerability_summary=vulnerability_summary,
            bundle_map=bundle_map,
            verification_map=verification_map,
        )

        target_section = self._build_target_summary(target_profile, test_plan)
        attack_surface_section = self._build_attack_surface_summary(surface_summary)
        findings_section = self._build_findings_summary(vulnerability_summary, finding_entries)
        evidence_section = self._build_evidence_summary(evidence_summary)
        confidence_section = self._build_confidence_summary(finding_entries, evidence_summary)
        verification_section = self._build_verification_summary(exploit_summary)
        next_step = self._select_recommended_next_step(finding_entries, exploit_summary, evidence_summary, test_plan)
        human_readable = self._build_human_readable_report(
            target_summary=target_section,
            attack_surface_summary=attack_surface_section,
            findings_summary=findings_section,
            evidence_summary=evidence_section,
            confidence_levels=confidence_section,
            verification_status=verification_section,
            recommended_next_step=next_step,
            finding_entries=finding_entries,
        )

        return SecurityReport(
            target_summary=target_section,
            attack_surface_summary=attack_surface_section,
            findings_summary=findings_section,
            evidence_summary=evidence_section,
            confidence_levels=confidence_section,
            verification_status=verification_section,
            recommended_next_step=next_step,
            human_readable=human_readable,
        )

    def _build_finding_entries(
        self,
        vulnerability_summary: VulnerabilityHuntResult,
        bundle_map: Dict[str, FindingEvidenceBundle],
        verification_map: Dict[str, VerificationRecord],
    ) -> List[ReportFindingEntry]:
        entries: List[ReportFindingEntry] = []
        for finding in vulnerability_summary.findings:
            bundle = bundle_map.get((finding.category, finding.title))
            verification = verification_map.get((finding.category, finding.title))
            entries.append(
                ReportFindingEntry(
                    title=finding.title,
                    category=finding.category,
                    initial_classification=finding.classification,
                    evidence_level=bundle.evidence_level if bundle else "weak_evidence",
                    confidence=round((bundle.confidence if bundle else finding.confidence), 2),
                    verification_status=verification.state if verification else "not_verified",
                    rationale=(verification.rationale if verification else finding.rationale),
                    evidence_points=self._dedupe(
                        (bundle.supporting_points if bundle else []) + list(finding.evidence)
                    )[:8],
                    verified_signals=(verification.verified_signals if verification else [])[:8],
                    recommended_next_step=(
                        bundle.recommended_next_step if bundle and bundle.recommended_next_step
                        else finding.recommended_next_step
                    ),
                )
            )
        return entries

    def _build_target_summary(self, target_profile: TargetProfile, test_plan: TestPlan) -> Dict[str, Any]:
        return {
            "normalized_target": target_profile.normalized_target,
            "target_type": target_profile.target_type,
            "is_valid": target_profile.is_valid,
            "confidence": round(target_profile.confidence, 2),
            "potential_services": list(target_profile.potential_services[:8]),
            "indicators": list(target_profile.indicators[:8]),
            "risk_notes": list(target_profile.risk_notes[:8]),
            "scope_notes": list(test_plan.scope_notes[:8]),
            "plan_summary": test_plan.target_summary,
            "estimated_time": test_plan.total_estimated_time,
        }

    def _build_attack_surface_summary(self, surface_summary: SurfaceSummary) -> Dict[str, Any]:
        return {
            "surface_type": surface_summary.surface_type,
            "confidence": round(surface_summary.confidence, 2),
            "endpoints": list(surface_summary.endpoints[:8]),
            "paths": list(surface_summary.paths[:10]),
            "params": list(surface_summary.params[:10]),
            "query_keys": list(surface_summary.query_keys[:10]),
            "headers": list(surface_summary.headers[:10]),
            "auth_hints": list(surface_summary.auth_hints[:8]),
            "forms": [self._serialize_form(form) for form in surface_summary.forms[:5]],
            "input_points_count": len(surface_summary.input_points),
            "notes": list(surface_summary.notes[:8]),
        }

    def _build_findings_summary(
        self,
        vulnerability_summary: VulnerabilityHuntResult,
        finding_entries: List[ReportFindingEntry],
    ) -> Dict[str, Any]:
        return {
            "total_findings": vulnerability_summary.total_findings,
            "signal_count": len([item for item in finding_entries if item.initial_classification == "signal"]),
            "possible_finding_count": len([item for item in finding_entries if item.initial_classification == "possible_finding"]),
            "likely_finding_count": len([item for item in finding_entries if item.initial_classification == "likely_finding"]),
            "items": [asdict(entry) for entry in finding_entries],
            "notes": list(vulnerability_summary.notes[:8]),
        }

    def _build_evidence_summary(self, evidence_summary: EvidenceAnalysisResult) -> Dict[str, Any]:
        return {
            "total_bundles": evidence_summary.total_bundles,
            "kept_bundles": len(evidence_summary.kept_bundles),
            "filtered_bundles": len(evidence_summary.filtered_bundles),
            "weak_evidence_count": evidence_summary.weak_evidence_count,
            "medium_evidence_count": evidence_summary.medium_evidence_count,
            "strong_evidence_count": evidence_summary.strong_evidence_count,
            "filtered_titles": [bundle.finding_title for bundle in evidence_summary.filtered_bundles[:8]],
            "filtered_keys": [
                {
                    "category": bundle.finding_category,
                    "title": bundle.finding_title,
                }
                for bundle in evidence_summary.filtered_bundles[:8]
            ],
            "notes": list(evidence_summary.notes[:8]),
        }

    def _build_confidence_summary(
        self,
        finding_entries: List[ReportFindingEntry],
        evidence_summary: EvidenceAnalysisResult,
    ) -> Dict[str, Any]:
        confidences = [item.confidence for item in finding_entries]
        avg_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
        return {
            "average_confidence": avg_confidence,
            "high_confidence_titles": [item.title for item in finding_entries if item.confidence >= 0.8][:8],
            "medium_confidence_titles": [item.title for item in finding_entries if 0.55 <= item.confidence < 0.8][:8],
            "lower_confidence_titles": [item.title for item in finding_entries if item.confidence < 0.55][:8],
            "high_confidence_keys": [
                {"category": item.category, "title": item.title}
                for item in finding_entries if item.confidence >= 0.8
            ][:8],
            "medium_confidence_keys": [
                {"category": item.category, "title": item.title}
                for item in finding_entries if 0.55 <= item.confidence < 0.8
            ][:8],
            "lower_confidence_keys": [
                {"category": item.category, "title": item.title}
                for item in finding_entries if item.confidence < 0.55
            ][:8],
            "evidence_distribution": {
                "weak_evidence": evidence_summary.weak_evidence_count,
                "medium_evidence": evidence_summary.medium_evidence_count,
                "strong_evidence": evidence_summary.strong_evidence_count,
            },
        }

    def _build_verification_summary(self, exploit_summary: ExploitVerificationResult) -> Dict[str, Any]:
        return {
            "policy_action": exploit_summary.policy_action,
            "verified_count": exploit_summary.verified_count,
            "not_verified_count": exploit_summary.not_verified_count,
            "needs_manual_review_count": exploit_summary.needs_manual_review_count,
            "records": [
                {
                    "finding_title": record.finding_title,
                    "finding_category": record.finding_category,
                    "state": record.state,
                    "eligible": record.eligible,
                    "policy_action": record.policy_action,
                    "constraints_applied": list(record.constraints_applied[:8]),
                }
                for record in exploit_summary.records[:12]
            ],
            "notes": list(exploit_summary.notes[:8]),
        }

    def _select_recommended_next_step(
        self,
        finding_entries: List[ReportFindingEntry],
        exploit_summary: ExploitVerificationResult,
        evidence_summary: EvidenceAnalysisResult,
        test_plan: TestPlan,
    ) -> str:
        verified_entry = next((item for item in finding_entries if item.verification_status == "verified"), None)
        if verified_entry and verified_entry.recommended_next_step:
            return verified_entry.recommended_next_step

        manual_entry = next((item for item in finding_entries if item.verification_status == "needs_manual_review"), None)
        if manual_entry and manual_entry.recommended_next_step:
            return manual_entry.recommended_next_step

        if evidence_summary.filtered_bundles:
            return "مراجعة النتائج المصفاة أولاً واستبعاد الإيجابيات الكاذبة قبل أي خطوة تحقق إضافية."

        if test_plan.steps:
            first_step = test_plan.steps[0]
            return f"الاستمرار بخطوة الخطة الأعلى أولوية: {first_step.name}."

        return "إجراء مراجعة بشرية منظمة للنتائج الحالية قبل أي تصعيد لاحق."

    def _build_human_readable_report(
        self,
        target_summary: Dict[str, Any],
        attack_surface_summary: Dict[str, Any],
        findings_summary: Dict[str, Any],
        evidence_summary: Dict[str, Any],
        confidence_levels: Dict[str, Any],
        verification_status: Dict[str, Any],
        recommended_next_step: str,
        finding_entries: List[ReportFindingEntry],
    ) -> str:
        lines: List[str] = [
            "تقرير أمني منظم",
            "",
            "[target summary]",
            f"- الهدف: {target_summary.get('normalized_target')}",
            f"- نوع الهدف: {target_summary.get('target_type')}",
            f"- صلاحية الهدف: {target_summary.get('is_valid')}",
            f"- ثقة التوصيف: {target_summary.get('confidence')}",
            "",
            "[attack surface summary]",
            f"- نوع السطح: {attack_surface_summary.get('surface_type')}",
            f"- endpoints: {', '.join(attack_surface_summary.get('endpoints', [])[:5]) or 'none'}",
            f"- paths: {', '.join(attack_surface_summary.get('paths', [])[:6]) or 'none'}",
            f"- params: {', '.join(attack_surface_summary.get('params', [])[:6]) or 'none'}",
            f"- auth hints: {', '.join(attack_surface_summary.get('auth_hints', [])[:6]) or 'none'}",
            "",
            "[findings summary]",
            f"- total findings: {findings_summary.get('total_findings')}",
            f"- signal: {findings_summary.get('signal_count')}",
            f"- possible: {findings_summary.get('possible_finding_count')}",
            f"- likely: {findings_summary.get('likely_finding_count')}",
            "",
            "[evidence summary]",
            f"- weak: {evidence_summary.get('weak_evidence_count')}",
            f"- medium: {evidence_summary.get('medium_evidence_count')}",
            f"- strong: {evidence_summary.get('strong_evidence_count')}",
            "",
            "[verification status]",
            f"- verified: {verification_status.get('verified_count')}",
            f"- not verified: {verification_status.get('not_verified_count')}",
            f"- needs manual review: {verification_status.get('needs_manual_review_count')}",
            f"- policy action: {verification_status.get('policy_action')}",
            "",
            "[confidence levels]",
            f"- average confidence: {confidence_levels.get('average_confidence')}",
        ]

        if finding_entries:
            lines.append("")
            lines.append("[top findings]")
            for entry in finding_entries[:5]:
                lines.append(
                    f"- {entry.title} | classification={entry.initial_classification} | evidence={entry.evidence_level} | verification={entry.verification_status} | confidence={entry.confidence}"
                )

        lines.extend([
            "",
            "[recommended next step]",
            f"- {recommended_next_step}",
        ])
        return "\n".join(lines).strip()

    def _serialize_form(self, form: SurfaceForm) -> Dict[str, Any]:
        return {
            "name": form.name,
            "action": form.action,
            "method": form.method,
            "fields": list(form.fields[:8]),
            "source": form.source,
            "notes": list(form.notes[:6]),
        }

    def _dedupe(self, values: List[str]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            cleaned = value.strip() if isinstance(value, str) else str(value).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
        return result
