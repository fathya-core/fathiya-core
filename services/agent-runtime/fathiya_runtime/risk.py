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
    r"شراء|بيع|صفقة|فحص حي|اختبار اختراق|استغلال|نشر|إرسال|بريد|رفع خارجي)",
    re.IGNORECASE,
)

READ_ONLY_AGENT_MESH_AUDIT = re.compile(
    r"^\s*(?:agent\s+mesh\s+audit|مسح\s+شبكة\s+الوكلاء)\s*:",
    re.IGNORECASE,
)

SAFE_AGENT_MESH_EXECUTE = re.compile(
    r"^\s*(?:FATHIYA_EXECUTION_OS_MISSION_V1\s*)?"
    r"(?:agent\s+mesh\s+execute|safe\s+mesh\s+execute|تشغيل\s+شبكة\s+الوكلاء)\s*:",
    re.IGNORECASE,
)

SAFE_KNOWLEDGE_EXECUTION = re.compile(
    r"(?:knowledge\s+execution\s+mission|FATHIYA_KNOWLEDGE_EXECUTION_V1|"
    r"learn\s+and\s+execute|report\s+to\s+execution|تقرير\s+إلى\s+تنفيذ|"
    r"تقرير\s+الى\s+تنفيذ|استيعاب\s+وتشغيل|معرفة\s+ثم\s+تنفيذ|"
    r"المعرفة\s+ثم\s+التنفيذ)",
    re.IGNORECASE,
)

SAFE_PRODUCTION_SITE_AUDIT = re.compile(
    r"(?:production\s+site\s+audit|fathiya\s+production\s+audit|"
    r"فحص\s+الدومين|إثبات\s+الدومين|اثبات\s+الدومين|"
    r"فحص\s+الإنتاج|فحص\s+الانتاج)",
    re.IGNORECASE,
)

SAFE_TRADING_SIMULATION = re.compile(
    r"(?:paper|simulate|simulation|simulated|backtest|sandbox|testnet|test\s+net|"
    r"status|probe|readiness|strategy|advisor|forecast|prediction|quality|"
    r"ورقي|محاكاة|محاكي|تجريبي|اختبار|حالة|جاهزية|افحص|تحقق|استراتيجية|"
    r"استراتيجيه|مستشار|تنبؤ|توقع|جودة)",
    re.IGNORECASE,
)

REAL_TRADING_INTENT = re.compile(
    r"(?:real|live|actual|submit|market\s+order|حقيقي|فعلي|مباشر|إرسال\s+أمر|"
    r"ارسل\s+أمر|نفذ\s+أمر|نفّذ\s+أمر|أمر\s+سوق)",
    re.IGNORECASE,
)

STATIC_SECURITY_REVIEW = re.compile(
    r"(?:bug\s+bounty\s+static\s+review|static-only\s+bug\s+bounty|"
    r"bugcrowd\s+static|static\s+review|مسودة\s+bugcrowd|تقرير\s+bugcrowd|"
    r"صيد\s+bugcrowd|الرابع\s+من\s+داخل\s+فتحي[هة]|تحليل\s+ساكن|مراجعة\s+ساكنة)",
    re.IGNORECASE,
)

BUG_BOUNTY_INTERNAL_DRAFT_GATE = re.compile(
    r"(?:bug\s+bounty\s+draft\s+gate|verified\s+draft\s+gate|"
    r"draft\s+داخل\s+فتحي[هة]|مسودة\s+قرار|بوابة\s+مسودة|ارفع\s+draft\s+داخل)",
    re.IGNORECASE,
)

EXTERNAL_DRAFT_SUBMISSION_INTENT = re.compile(
    r"(?:submit|send\s+to\s+bugcrowd|external\s+upload|upload\s+to\s+bugcrowd|"
    r"ارفع(?:ه|ها)?\s+على\s+bugcrowd|إرسال\s+خارجي\s+الآن|رفع\s+خارجي\s+الآن|"
    r"قدّم(?:ه|ها)?\s+على\s+bugcrowd)",
    re.IGNORECASE,
)

LIVE_OR_EXTERNAL_SECURITY_ACTION = re.compile(
    r"(?:\bscan\b|\bexploit\b|\bpentest\b|\bnmap\b|\bnuclei\b|"
    r"\bsend\b|\bpublish\b|\bdeploy\b|\bemail\b|\bwebhook\b|"
    r"فحص\s+حي|اختبار\s+اختراق|استغلال|نشر|إرسال|بريد|رفع\s+خارجي)",
    re.IGNORECASE,
)


def classify_risk(prompt: str) -> RiskDecision:
    prompt = operator_request(prompt)
    if (
        READ_ONLY_AGENT_MESH_AUDIT.search(prompt)
        or SAFE_AGENT_MESH_EXECUTE.search(prompt)
        or SAFE_KNOWLEDGE_EXECUTION.search(prompt)
        or SAFE_PRODUCTION_SITE_AUDIT.search(prompt)
    ):
        return RiskDecision(risk_class="internal_owned", requires_approval=False)
    prompt = NEGATED_RISK_ACTION.sub("", prompt)
    if BUG_BOUNTY_INTERNAL_DRAFT_GATE.search(prompt) and not EXTERNAL_DRAFT_SUBMISSION_INTENT.search(prompt):
        return RiskDecision(risk_class="internal_owned", requires_approval=False)
    if STATIC_SECURITY_REVIEW.search(prompt) and not LIVE_OR_EXTERNAL_SECURITY_ACTION.search(prompt):
        return RiskDecision(risk_class="internal_owned", requires_approval=False)
    if SAFE_TRADING_SIMULATION.search(prompt) and not REAL_TRADING_INTENT.search(prompt):
        prompt = RISK_PATTERNS[1][1].sub("", prompt)
    for risk_class, pattern in RISK_PATTERNS:
        if pattern.search(prompt):
            return RiskDecision(risk_class=risk_class, requires_approval=True)
    return RiskDecision(risk_class="internal_owned", requires_approval=False)
