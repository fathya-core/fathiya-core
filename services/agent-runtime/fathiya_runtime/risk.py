from __future__ import annotations

import re
from dataclasses import dataclass

from .knowledge_mission import operator_request


@dataclass(frozen=True)
class RiskDecision:
    risk_class: str
    requires_approval: bool


RISK_PATTERNS = (
    (
        "destructive",
        re.compile(r"delete|remove|drop|wipe|format|حذف|مسح|تهيئة", re.IGNORECASE),
    ),
    (
        "financial",
        re.compile(
            r"trade|buy|sell|order|portfolio|wallet|تحويل|شراء|بيع|صفقة|محفظة",
            re.IGNORECASE,
        ),
    ),
    (
        "live_security",
        re.compile(
            r"scan|exploit|pentest|nmap|nuclei|فحص حي|اختبار اختراق|استغلال",
            re.IGNORECASE,
        ),
    ),
    (
        "external",
        re.compile(r"send|publish|deploy|email|webhook|نشر|إرسال|بريد", re.IGNORECASE),
    ),
)

NEGATED_RISK_ACTION = re.compile(
    r"(?:\bwithout\b|\bnever\b|\bdo\s+not\b|\bdon't\b|دون|بدون|لا|لن)"
    r"\s+(?:أن\s+)?(?:أي\s+)?"
    r"(?:delete|remove|drop|wipe|format|trade|buy|sell|order|transfer|scan|"
    r"exploit|pentest|send|publish|deploy|email|webhook|حذف|مسح|تهيئة|تحويل|"
    r"شراء|بيع|صفقة|فحص حي|اختبار اختراق|استغلال|نشر|إرسال|بريد)",
    re.IGNORECASE,
)


def classify_risk(prompt: str) -> RiskDecision:
    prompt = operator_request(prompt)
    prompt = NEGATED_RISK_ACTION.sub("", prompt)
    for risk_class, pattern in RISK_PATTERNS:
        if pattern.search(prompt):
            return RiskDecision(risk_class=risk_class, requires_approval=True)
    return RiskDecision(risk_class="internal_owned", requires_approval=False)
