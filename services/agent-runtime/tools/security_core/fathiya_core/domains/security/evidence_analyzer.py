"""
domains/security/evidence_analyzer.py — محلل الأدلة الأولي

يستهلك مخرجات:
- TargetProfile من target_profiler
- SurfaceSummary من surface_mapper
- TestPlan من test_planner
- VulnerabilityHuntResult من vulnerability_hunter

ويحوّل النتائج الأولية إلى حزم أدلة منظمة مع confidence وتدرج evidence strength،
مع تقليل false positives الواضحة دون تنفيذ exploit verification.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set

from domains.security.surface_mapper import SurfaceSummary
from domains.security.target_profiler import TargetProfile
from domains.security.test_planner import TestPlan
from domains.security.vulnerability_hunter import PreliminaryFinding, VulnerabilityHuntResult


@dataclass
class EvidenceAtom:
    """وحدة دليل فردية مرتبطة بنتيجة أولية."""
    kind: str  # finding_evidence, surface, profile, plan, note
    value: str
    source: str  # vulnerability_hunter, surface_mapper, target_profiler, test_planner
    weight: float = 0.0


@dataclass
class FindingEvidenceBundle:
    """حزمة أدلة منظمة خاصة بـ finding واحد."""
    finding_title: str
    finding_category: str
    original_classification: str
    evidence_level: str  # weak_evidence, medium_evidence, strong_evidence
    confidence: float
    kept: bool = True
    false_positive_reduced: bool = False
    reduction_reason: str = ""
    atoms: List[EvidenceAtom] = field(default_factory=list)
    supporting_points: List[str] = field(default_factory=list)
    contradictory_points: List[str] = field(default_factory=list)
    recommended_next_step: str = ""
    requires_verification: bool = True


@dataclass
class EvidenceAnalysisResult:
    """نتيجة تحليل الأدلة لكامل الجولة الأمنية."""
    target_type: str
    surface_type: str
    bundles: List[FindingEvidenceBundle] = field(default_factory=list)
    kept_bundles: List[FindingEvidenceBundle] = field(default_factory=list)
    filtered_bundles: List[FindingEvidenceBundle] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    safe_mode: bool = True

    @property
    def total_bundles(self) -> int:
        return len(self.bundles)

    @property
    def strong_evidence_count(self) -> int:
        return len([bundle for bundle in self.kept_bundles if bundle.evidence_level == "strong_evidence"])

    @property
    def medium_evidence_count(self) -> int:
        return len([bundle for bundle in self.kept_bundles if bundle.evidence_level == "medium_evidence"])

    @property
    def weak_evidence_count(self) -> int:
        return len([bundle for bundle in self.kept_bundles if bundle.evidence_level == "weak_evidence"])


class EvidenceAnalyzer:
    """محلل أدلة دفاعي فقط، لا ينفذ exploit verification ولا confirmation نهائي."""

    _SENSITIVE_INPUTS: Set[str] = {
        "token", "access_token", "api_key", "apikey", "password", "secret",
        "cmd", "command", "prompt", "system", "tool", "memory", "next",
        "redirect", "return", "return_url",
    }

    _AUTH_HEADERS: Set[str] = {
        "Authorization", "X-API-Key", "X-Auth-Token", "Cookie", "Set-Cookie",
    }

    def analyze(
        self,
        target_profile: TargetProfile,
        surface_summary: SurfaceSummary,
        test_plan: TestPlan,
        vulnerability_summary: VulnerabilityHuntResult,
    ) -> EvidenceAnalysisResult:
        bundles: List[FindingEvidenceBundle] = []

        for finding in vulnerability_summary.findings:
            bundle = self._build_bundle(
                finding=finding,
                target_profile=target_profile,
                surface_summary=surface_summary,
                test_plan=test_plan,
            )
            self._apply_false_positive_reduction(
                bundle=bundle,
                finding=finding,
                target_profile=target_profile,
                surface_summary=surface_summary,
            )
            bundles.append(bundle)

        kept_bundles = [bundle for bundle in bundles if bundle.kept]
        filtered_bundles = [bundle for bundle in bundles if not bundle.kept]

        notes = self._build_notes(
            vulnerability_summary=vulnerability_summary,
            kept_bundles=kept_bundles,
            filtered_bundles=filtered_bundles,
        )

        return EvidenceAnalysisResult(
            target_type=target_profile.target_type,
            surface_type=surface_summary.surface_type,
            bundles=bundles,
            kept_bundles=kept_bundles,
            filtered_bundles=filtered_bundles,
            notes=notes,
            safe_mode=True,
        )

    def _build_bundle(
        self,
        finding: PreliminaryFinding,
        target_profile: TargetProfile,
        surface_summary: SurfaceSummary,
        test_plan: TestPlan,
    ) -> FindingEvidenceBundle:
        atoms: List[EvidenceAtom] = []
        supporting_points: List[str] = []
        contradictory_points: List[str] = []

        finding_support = self._dedupe_strings(finding.evidence)
        surface_support = self._select_surface_support(finding, surface_summary)
        profile_support = self._select_profile_support(finding, target_profile)
        plan_support = self._select_plan_support(finding, test_plan)

        for item in finding_support:
            atoms.append(EvidenceAtom(
                kind="finding_evidence",
                value=item,
                source="vulnerability_hunter",
                weight=0.12,
            ))
            supporting_points.append(item)

        for item in surface_support:
            atoms.append(EvidenceAtom(
                kind="surface",
                value=item,
                source="surface_mapper",
                weight=0.14,
            ))
            supporting_points.append(item)

        for item in profile_support:
            atoms.append(EvidenceAtom(
                kind="profile",
                value=item,
                source="target_profiler",
                weight=0.1,
            ))
            supporting_points.append(item)

        for item in plan_support:
            atoms.append(EvidenceAtom(
                kind="plan",
                value=item,
                source="test_planner",
                weight=0.03,
            ))
            supporting_points.append(item)

        atoms = self._dedupe_atoms(atoms)
        contradictory_points.extend(self._derive_contradictions(finding, target_profile, surface_summary))

        base_confidence = self._base_confidence_for_classification(finding.classification)
        confidence = self._compute_confidence(base_confidence, atoms, contradictory_points)
        evidence_level = self._grade_evidence(
            confidence=confidence,
            atoms=atoms,
            contradiction_count=len(contradictory_points),
            has_surface_support=bool(surface_support),
            has_profile_support=bool(profile_support),
        )

        return FindingEvidenceBundle(
            finding_title=finding.title,
            finding_category=finding.category,
            original_classification=finding.classification,
            evidence_level=evidence_level,
            confidence=confidence,
            atoms=atoms,
            supporting_points=self._dedupe_strings(supporting_points),
            contradictory_points=self._dedupe_strings(contradictory_points),
            recommended_next_step=finding.recommended_next_step,
            requires_verification=True,
        )

    def _select_surface_support(self, finding: PreliminaryFinding, surface_summary: SurfaceSummary) -> List[str]:
        support: List[str] = []

        if finding.category == "transport":
            support.extend([endpoint for endpoint in surface_summary.endpoints if endpoint.startswith("http://")][:3])
            support.extend(surface_summary.auth_hints[:2])
            support.extend([form.name for form in surface_summary.forms][:2])

        elif finding.category == "exposure":
            support.extend([path for path in surface_summary.paths if any(token in path.lower() for token in ["admin", "debug", "api", "graphql", "login", "swagger"])][:5])

        elif finding.category == "input-handling":
            support.extend([key for key in surface_summary.query_keys if key.lower() in self._SENSITIVE_INPUTS][:5])
            support.extend([param for param in surface_summary.params if param.lower() in self._SENSITIVE_INPUTS][:5])

        elif finding.category == "authentication":
            support.extend(surface_summary.auth_hints[:4])
            support.extend([form.name for form in surface_summary.forms][:3])
            support.extend([header for header in surface_summary.headers if header in self._AUTH_HEADERS][:3])

        elif finding.category == "headers":
            support.extend([header for header in surface_summary.headers if header in self._AUTH_HEADERS or header == "X-Forwarded-For"][:5])

        elif finding.category == "ai-agent":
            support.extend([param for param in surface_summary.params if param.lower() in self._SENSITIVE_INPUTS][:6])
            support.extend([note for note in surface_summary.notes if "وكيل" in note or "الذكاء" in note or "ai" in note.lower()][:3])

        elif finding.category == "code":
            support.extend([note for note in surface_summary.notes if "شيفرة" in note or "code" in note.lower() or "مستودع" in note][:3])
            support.extend([indicator for indicator in surface_summary.indicators if "surface:code" in indicator][:2])

        elif finding.category == "scope":
            if target := surface_summary.normalized_target:
                support.append(target)

        return self._dedupe_strings(support)

    def _select_profile_support(self, finding: PreliminaryFinding, target_profile: TargetProfile) -> List[str]:
        support: List[str] = []

        if finding.category == "transport" and "http_only" in target_profile.indicators:
            support.append("http_only")
            support.extend(target_profile.risk_notes[:2])

        elif finding.category == "exposure":
            support.extend([item for item in target_profile.indicators if item in {"web_server", "domain", "subdomain"}][:3])

        elif finding.category == "input-handling":
            support.extend([item for item in target_profile.indicators if item in {"web_server", "https", "http_only", "domain"}][:3])

        elif finding.category == "authentication":
            support.extend([item for item in target_profile.indicators if item in {"web_server", "https", "http_only"}][:3])

        elif finding.category == "headers":
            support.extend([item for item in target_profile.indicators if item in {"web_server", "public_ip", "domain"}][:3])

        elif finding.category == "ai-agent":
            support.extend([item for item in target_profile.indicators if item in {"web_server", "domain"}][:2])
            support.extend([note for note in target_profile.risk_notes if "AI" in note or "ذكاء" in note][:2])

        elif finding.category == "code":
            support.extend([item for item in target_profile.indicators if item in {"domain", "subdomain"}][:2])

        elif finding.category == "scope":
            support.append(target_profile.normalized_target)
            support.extend([item for item in target_profile.indicators if item in {"network_range", "wide_range", "medium_range", "narrow_range"}][:3])
            support.extend(target_profile.risk_notes[:2])

        return self._dedupe_strings(support)

    def _select_plan_support(self, finding: PreliminaryFinding, test_plan: TestPlan) -> List[str]:
        support: List[str] = []
        explicit_map = {
            "transport": {"tls", "https", "transport", "ssl", "headers"},
            "exposure": {"exposure", "path", "content", "access", "vuln"},
            "input-handling": {"input", "param", "query", "validation", "vuln"},
            "authentication": {"auth", "login", "session", "csrf"},
            "headers": {"header", "headers", "proxy", "csrf"},
            "ai-agent": {"prompt", "agent", "tool", "memory", "workflow"},
            "code": {"repo", "code", "static", "source", "dependency"},
            "scope": {"scope", "range", "network", "cidr"},
        }
        allowed_tokens = explicit_map.get(finding.category, set())
        for step in test_plan.steps:
            haystack = f"{step.name} {step.description} {step.category}".lower()
            if any(token in haystack for token in allowed_tokens):
                support.append(step.name)
                if len(support) >= 2:
                    break

        if finding.category == "scope":
            support.extend(test_plan.warnings[:2])
            support.extend(test_plan.scope_notes[:2])
        elif finding.category in {"transport", "authentication"}:
            support.extend([warning for warning in test_plan.warnings if "HTTPS" in warning or "تصريح" in warning][:1])

        return self._dedupe_strings(support)

    def _derive_contradictions(
        self,
        finding: PreliminaryFinding,
        target_profile: TargetProfile,
        surface_summary: SurfaceSummary,
    ) -> List[str]:
        contradictions: List[str] = []

        if finding.category == "transport" and not any(endpoint.startswith("http://") for endpoint in surface_summary.endpoints):
            contradictions.append("لم تُرصد endpoints تعمل عبر HTTP غير المشفر.")

        if finding.category == "authentication" and not (surface_summary.auth_hints or surface_summary.forms or any(h in surface_summary.headers for h in self._AUTH_HEADERS)):
            contradictions.append("لا توجد مؤشرات مصادقة أو جلسات كافية في السطح الحالي.")

        if finding.category == "headers" and not any(header in surface_summary.headers for header in self._AUTH_HEADERS.union({"X-Forwarded-For"})):
            contradictions.append("لم تُرصد رؤوس حساسة مرتبطة بهذا finding.")

        if finding.category == "ai-agent" and surface_summary.surface_type != "ai-agent":
            contradictions.append("نوع السطح الحالي لا يدعم افتراض finding خاص بوكلاء الذكاء الاصطناعي.")

        if finding.category == "code" and surface_summary.surface_type != "code":
            contradictions.append("السطح الحالي ليس code، ما يضعف دلالة هذا finding.")

        if finding.category == "scope" and target_profile.target_type != "cidr":
            contradictions.append("الهدف ليس CIDR، لذا لا يوجد سند كافٍ لفئة scope network.")

        if finding.category == "input-handling":
            sensitive = [item for item in surface_summary.query_keys + surface_summary.params if item.lower() in self._SENSITIVE_INPUTS]
            if not sensitive:
                contradictions.append("لا توجد معاملات حساسة واضحة في المسار أو الاستعلامات الحالية.")

        return contradictions

    def _apply_false_positive_reduction(
        self,
        bundle: FindingEvidenceBundle,
        finding: PreliminaryFinding,
        target_profile: TargetProfile,
        surface_summary: SurfaceSummary,
    ) -> None:
        contradiction_count = len(bundle.contradictory_points)
        atom_count = len(bundle.atoms)

        if contradiction_count >= 2 and atom_count <= 3:
            bundle.kept = False
            bundle.false_positive_reduced = True
            bundle.reduction_reason = "تعارضات متعددة مع سند ضعيف؛ تم اعتباره false positive واضحاً."
            bundle.confidence = round(max(0.2, bundle.confidence - 0.25), 2)
            bundle.evidence_level = "weak_evidence"
            return

        if finding.category == "transport" and surface_summary.endpoints and all(endpoint.startswith("https://") for endpoint in surface_summary.endpoints):
            bundle.kept = False
            bundle.false_positive_reduced = True
            bundle.reduction_reason = "كل نقاط الدخول المرصودة تعمل عبر HTTPS؛ تم خفض finding النقل غير الآمن كإيجابية كاذبة واضحة."
            bundle.confidence = round(max(0.2, bundle.confidence - 0.3), 2)
            bundle.evidence_level = "weak_evidence"
            return

        if finding.category == "authentication" and not (surface_summary.auth_hints or surface_summary.forms):
            bundle.kept = False
            bundle.false_positive_reduced = True
            bundle.reduction_reason = "غياب مؤشرات المصادقة الصريحة يجعل finding المصادقة False positive واضحاً في هذه الجولة."
            bundle.confidence = round(max(0.2, bundle.confidence - 0.22), 2)
            bundle.evidence_level = "weak_evidence"
            return

        if finding.category == "ai-agent" and surface_summary.surface_type != "ai-agent":
            bundle.kept = False
            bundle.false_positive_reduced = True
            bundle.reduction_reason = "السطح ليس AI-agent؛ تم استبعاد finding غير المتسق مع نوع السطح."
            bundle.confidence = round(max(0.2, bundle.confidence - 0.28), 2)
            bundle.evidence_level = "weak_evidence"
            return

        if finding.category == "scope" and target_profile.target_type != "cidr":
            bundle.kept = False
            bundle.false_positive_reduced = True
            bundle.reduction_reason = "finding نطاق شبكي على هدف غير CIDR تم اعتباره false positive واضحاً."
            bundle.confidence = round(max(0.2, bundle.confidence - 0.3), 2)
            bundle.evidence_level = "weak_evidence"

    def _base_confidence_for_classification(self, classification: str) -> float:
        mapping = {
            "signal": 0.42,
            "possible_finding": 0.58,
            "likely_finding": 0.72,
        }
        return mapping.get(classification, 0.45)

    def _compute_confidence(self, base: float, atoms: List[EvidenceAtom], contradictions: List[str]) -> float:
        source_caps = {
            "vulnerability_hunter": 0.18,
            "surface_mapper": 0.18,
            "target_profiler": 0.12,
            "test_planner": 0.05,
        }
        source_totals = {key: 0.0 for key in source_caps}
        for atom in atoms[:10]:
            if atom.source not in source_caps:
                continue
            remaining = source_caps[atom.source] - source_totals[atom.source]
            if remaining <= 0:
                continue
            source_totals[atom.source] += min(atom.weight, remaining)

        score = base + sum(source_totals.values())
        score -= min(0.24, len(contradictions) * 0.08)
        return round(min(0.95, max(0.25, score)), 2)

    def _grade_evidence(
        self,
        confidence: float,
        atoms: List[EvidenceAtom],
        contradiction_count: int,
        has_surface_support: bool,
        has_profile_support: bool,
    ) -> str:
        atom_count = len(atoms)
        if not has_surface_support and not has_profile_support:
            return "weak_evidence"
        if confidence >= 0.78 and atom_count >= 4 and contradiction_count == 0 and has_surface_support and has_profile_support:
            return "strong_evidence"
        if confidence >= 0.6 and atom_count >= 3 and (has_surface_support or has_profile_support):
            return "medium_evidence"
        return "weak_evidence"

    def _build_notes(
        self,
        vulnerability_summary: VulnerabilityHuntResult,
        kept_bundles: List[FindingEvidenceBundle],
        filtered_bundles: List[FindingEvidenceBundle],
    ) -> List[str]:
        notes = [
            "تحليل الأدلة استدلالي فقط ولم يتضمن exploit verification.",
            f"إجمالي النتائج الأولية الواردة: {vulnerability_summary.total_findings}.",
            f"عدد الحزم المحتفظ بها بعد تقليل false positives: {len(kept_bundles)}.",
            f"عدد الحزم المستبعدة كإيجابيات كاذبة واضحة: {len(filtered_bundles)}.",
        ]
        if any(bundle.evidence_level == "strong_evidence" for bundle in kept_bundles):
            notes.append("تم رصد حزم أدلة قوية نسبيًا، لكنها ما تزال غير مؤكدة نهائيًا.")
        return notes

    def _dedupe_atoms(self, atoms: List[EvidenceAtom]) -> List[EvidenceAtom]:
        deduped: List[EvidenceAtom] = []
        seen = set()
        for atom in atoms:
            key = (atom.kind, atom.source, atom.value.strip())
            if key not in seen:
                seen.add(key)
                deduped.append(atom)
        return deduped

    def _dedupe_strings(self, values: List[str]) -> List[str]:
        deduped: List[str] = []
        seen: Set[str] = set()
        for value in values:
            cleaned = value.strip() if isinstance(value, str) else str(value).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                deduped.append(cleaned)
        return deduped
