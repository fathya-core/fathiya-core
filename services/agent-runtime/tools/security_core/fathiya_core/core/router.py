"""
core/router.py — Router قائم على القواعد (Rules-Based)

يوجّه الطلبات إلى المسار المناسب بناءً على كلمات مفتاحية:
- Web/Security → security flow
- Code/SAST → sast flow
- Crypto/Market → crypto flow
- Default → general flow

لا يستخدم LLM — فقط قواعد نصية بسيطة.

الاستخدام:
    from core.router import RequestRouter, RouteResult

    router = RequestRouter()
    route = router.route("افحص موقع example.com")
    print(route.flow)       # "security"
    print(route.domain)     # "security"
    print(route.confidence) # 0.9
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set


@dataclass
class RouteResult:
    """نتيجة التوجيه"""
    flow: str           # المسار: "security", "sast", "crypto", "general"
    domain: str         # النطاق: "security", "code", "crypto", "general"
    confidence: float   # مستوى الثقة: 0.0 - 1.0
    matched_keywords: List[str] = field(default_factory=list)
    reason: str = ""


class RequestRouter:
    """
    موجّه الطلبات — يحدد المسار المناسب بناءً على الكلمات المفتاحية.

    القواعد:
    1. إذا الهدف Web/Security → security flow
    2. إذا الهدف Code/SAST → sast flow
    3. إذا الطلب سوق/كريبتو → crypto flow
    4. غير ذلك → general flow
    """

    def __init__(self) -> None:
        # --- كلمات مفتاحية لكل مسار ---
        self._security_keywords: Set[str] = {
            # عربي
            "اختراق", "ثغرة", "ثغرات", "فحص", "أمن", "أمان", "حماية",
            "هجوم", "هجمات", "تشفير", "جدار", "ناري", "بورت", "منفذ",
            "سكان", "مسح", "نطاق", "موقع", "سيرفر", "خادم",
            "شبكة", "شبكات", "بروكسي", "فايروول",
            "اختبار اختراق", "تحليل أمني", "فحص أمني",
            # إنجليزي
            "hack", "exploit", "vulnerability", "pentest", "penetration",
            "scan", "nmap", "burp", "sqlmap", "xss", "csrf", "sqli",
            "injection", "firewall", "proxy", "port", "target",
            "web", "website", "domain", "subdomain", "dns",
            "ssl", "tls", "https", "http", "owasp",
            "reconnaissance", "recon", "footprint",
            "brute", "bruteforce", "payload", "shell", "reverse",
            "metasploit", "kali", "wireshark", "sniff",
        }

        self._sast_keywords: Set[str] = {
            # عربي
            "كود", "شفرة", "مراجعة كود", "تحليل كود", "تحليل ثابت",
            "باق", "خطأ برمجي", "أخطاء برمجية", "ديبق",
            # إنجليزي
            "code", "sast", "static analysis", "code review",
            "source code", "bug", "debug", "lint", "linter",
            "sonarqube", "semgrep", "bandit", "pylint", "flake8",
            "codeql", "snyk", "dependency", "cve",
        }

        self._crypto_keywords: Set[str] = {
            # عربي
            "كريبتو", "عملة", "عملات", "بيتكوين", "إيثريوم",
            "سوق", "تداول", "بورصة", "محفظة", "بلوكتشين",
            "توكن", "رمز", "عقد ذكي",
            # إنجليزي
            "crypto", "bitcoin", "btc", "ethereum", "eth",
            "blockchain", "token", "defi", "nft", "wallet",
            "exchange", "trading", "binance", "coinbase",
            "smart contract", "solidity", "web3",
            "market", "altcoin", "staking", "mining",
        }

        # --- أولوية المسارات (الأعلى أولاً) ---
        self._routes: List[Dict] = [
            {
                "flow": "security",
                "domain": "security",
                "keywords": self._security_keywords,
                "weight": 1.0,
            },
            {
                "flow": "sast",
                "domain": "code",
                "keywords": self._sast_keywords,
                "weight": 0.9,
            },
            {
                "flow": "crypto",
                "domain": "crypto",
                "keywords": self._crypto_keywords,
                "weight": 0.85,
            },
        ]

    def route(self, user_input: str) -> RouteResult:
        """
        توجيه الطلب إلى المسار المناسب.

        المعاملات:
            user_input — نص الطلب من المستخدم

        يرجع:
            RouteResult مع المسار والنطاق ومستوى الثقة
        """
        if not user_input or not user_input.strip():
            return RouteResult(
                flow="general",
                domain="general",
                confidence=0.0,
                reason="المدخل فارغ"
            )

        input_lower = user_input.lower().strip()
        best_route: Optional[RouteResult] = None
        best_score: float = 0.0

        for route_def in self._routes:
            matched = self._match_keywords(input_lower, route_def["keywords"])

            if matched:
                # حساب الثقة بناءً على عدد الكلمات المطابقة والوزن
                score = min(1.0, len(matched) * 0.3) * route_def["weight"]

                if score > best_score:
                    best_score = score
                    best_route = RouteResult(
                        flow=route_def["flow"],
                        domain=route_def["domain"],
                        confidence=round(score, 2),
                        matched_keywords=matched,
                        reason=f"تطابق {len(matched)} كلمة مفتاحية مع مسار {route_def['flow']}"
                    )

        if best_route:
            return best_route

        # المسار الافتراضي
        return RouteResult(
            flow="general",
            domain="general",
            confidence=0.5,
            reason="لم يتطابق الطلب مع أي مسار متخصص — توجيه عام"
        )

    def _match_keywords(self, text: str, keywords: Set[str]) -> List[str]:
        """البحث عن الكلمات المفتاحية المطابقة في النص"""
        matched: List[str] = []

        for keyword in keywords:
            kw_lower = keyword.lower()
            # بحث كامل عن الكلمة أو العبارة
            if " " in kw_lower:
                # عبارة متعددة الكلمات
                if kw_lower in text:
                    matched.append(keyword)
            else:
                # كلمة واحدة — بحث بحدود الكلمة
                pattern = r"(?:^|\s|[^\w])" + re.escape(kw_lower) + r"(?:\s|[^\w]|$)"
                if re.search(pattern, text):
                    matched.append(keyword)

        return matched

    def get_supported_flows(self) -> List[str]:
        """استرجاع قائمة المسارات المدعومة"""
        flows = [r["flow"] for r in self._routes]
        flows.append("general")
        return flows

    def get_supported_domains(self) -> List[str]:
        """استرجاع قائمة النطاقات المدعومة"""
        domains = list({r["domain"] for r in self._routes})
        domains.append("general")
        return domains
