"""
domains/security/target_profiler.py — تحليل وتوصيف الهدف الأمني

يجمع معلومات أولية عن الهدف (موقع، IP، نطاق) ويبني ملفاً تعريفياً
يُستخدم لاحقاً من قبل test_planner وبقية المسار الأمني.
"""

import ipaddress
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
from urllib.parse import urlparse


@dataclass
class TargetProfile:
    """الملف التعريفي للهدف"""
    raw_input: str
    target_type: str  # "domain", "ip", "url", "cidr", "unknown"
    normalized_target: str
    indicators: List[str] = field(default_factory=list)
    potential_services: List[str] = field(default_factory=list)
    risk_notes: List[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def is_valid(self) -> bool:
        return self.target_type != "unknown" and self.confidence > 0.3


class TargetProfiler:
    """محلل الأهداف الأمنية — يحدد نوع الهدف ويجمع مؤشرات أولية."""

    _IP_LIKE_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    _CIDR_LIKE_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}/\d{1,2}\b")
    _DOMAIN_PATTERN = re.compile(
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+"
        r"[a-zA-Z]{2,}$"
    )
    _DOMAIN_IN_TEXT_PATTERN = re.compile(
        r"\b((?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,})\b"
    )
    _URL_PATTERN = re.compile(r"^https?://", re.IGNORECASE)
    _URL_IN_TEXT_PATTERN = re.compile(r"https?://[^\s]+", re.IGNORECASE)
    _CIDR_TOKEN_PATTERN = re.compile(r"(?:^|[^\d])((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})(?=$|[^\d])")
    _INVALID_CIDR_TOKEN_PATTERN = re.compile(r"(?:^|[^\d])((?:\d{1,3}\.){3}\d{1,3}/[^\s]*)")

    def profile(self, raw_input: str) -> TargetProfile:
        if not raw_input or not raw_input.strip():
            return TargetProfile(
                raw_input=raw_input or "",
                target_type="unknown",
                normalized_target="",
                confidence=0.0,
                risk_notes=["المدخل فارغ"],
            )

        cleaned = raw_input.strip()

        if self._URL_PATTERN.match(cleaned):
            return self._profile_url(cleaned)

        exact_ip = self._parse_ip(cleaned)
        if exact_ip is not None:
            return self._profile_ip(str(exact_ip), raw_input=cleaned)

        has_cidr_token = self._has_real_cidr_token(cleaned)
        if has_cidr_token:
            exact_network = self._parse_network(cleaned)
            if exact_network is not None:
                return self._profile_cidr(exact_network.with_prefixlen, raw_input=cleaned)

            invalid_cidr = self._detect_invalid_cidr(cleaned)
            if invalid_cidr:
                return self._invalid_target_profile(cleaned, f"نطاق CIDR غير صالح: {invalid_cidr}")

        invalid_ip = self._detect_invalid_ip(cleaned)
        if invalid_ip:
            text_profile = self._profile_from_text(cleaned)
            if text_profile.is_valid:
                return text_profile
            return self._invalid_target_profile(cleaned, f"عنوان IPv4 غير صالح: {invalid_ip}")

        if self._DOMAIN_PATTERN.match(cleaned):
            return self._profile_domain(cleaned)

        return self._profile_from_text(cleaned)

    def _profile_url(self, url: str) -> TargetProfile:
        parsed = urlparse(url)
        indicators: List[str] = ["web_server"]
        services: List[str] = ["http"]
        risk_notes: List[str] = []

        if parsed.scheme.lower() == "https":
            indicators.append("https")
            services.append("https")
        else:
            indicators.append("http_only")
            risk_notes.append("الموقع لا يستخدم HTTPS")

        if parsed.port:
            indicators.append(f"custom_port:{parsed.port}")

        hostname = (parsed.hostname or "").lower()
        return TargetProfile(
            raw_input=url,
            target_type="url",
            normalized_target=hostname,
            indicators=indicators,
            potential_services=self._dedupe(services),
            risk_notes=self._dedupe(risk_notes),
            confidence=0.9,
        )

    def _profile_ip(self, ip: str, raw_input: Optional[str] = None) -> TargetProfile:
        ip_obj = ipaddress.ip_address(ip)
        indicators: List[str] = ["ip_address"]
        services: List[str] = []
        risk_notes: List[str] = []

        if ip_obj.is_private or ip_obj.is_loopback:
            indicators.append("private_network")
            risk_notes.append("عنوان IP داخلي — غير قابل للوصول من الخارج")
        else:
            indicators.append("public_ip")
            services.extend(["http", "https", "ssh", "ftp"])

        if ip_obj.is_loopback:
            indicators.append("loopback")
            risk_notes.append("عنوان loopback — يشير إلى الجهاز المحلي")

        return TargetProfile(
            raw_input=raw_input or ip,
            target_type="ip",
            normalized_target=str(ip_obj),
            indicators=self._dedupe(indicators),
            potential_services=self._dedupe(services),
            risk_notes=self._dedupe(risk_notes),
            confidence=0.85,
        )

    def _profile_cidr(self, cidr: str, raw_input: Optional[str] = None) -> TargetProfile:
        network = ipaddress.ip_network(cidr, strict=False)
        prefix = network.prefixlen

        indicators: List[str] = ["network_range"]
        risk_notes: List[str] = []

        if prefix < 16:
            risk_notes.append(f"نطاق واسع جداً (/{prefix}) — قد يشمل آلاف الأجهزة")
            indicators.append("wide_range")
        elif prefix < 24:
            indicators.append("medium_range")
        else:
            indicators.append("narrow_range")

        if network.is_private:
            risk_notes.append("نطاق داخلي — قد يتطلب وصولاً من داخل الشبكة")

        return TargetProfile(
            raw_input=raw_input or cidr,
            target_type="cidr",
            normalized_target=network.with_prefixlen,
            indicators=self._dedupe(indicators),
            potential_services=["multiple"],
            risk_notes=self._dedupe(risk_notes),
            confidence=0.8,
        )

    def _profile_domain(self, domain: str) -> TargetProfile:
        normalized = domain.lower().rstrip(".")
        indicators: List[str] = ["web_server", "domain"]
        services: List[str] = ["http", "https", "dns"]
        risk_notes: List[str] = []

        parts = normalized.split(".")
        if len(parts) > 2:
            indicators.append("subdomain")

        tld = parts[-1].lower()
        if tld in ("gov", "mil", "edu"):
            risk_notes.append(f"نطاق حكومي/عسكري/تعليمي (.{tld}) — يتطلب تصريح")
            indicators.append("sensitive_tld")

        return TargetProfile(
            raw_input=domain,
            target_type="domain",
            normalized_target=normalized,
            indicators=self._dedupe(indicators),
            potential_services=self._dedupe(services),
            risk_notes=self._dedupe(risk_notes),
            confidence=0.9,
        )

    def _profile_from_text(self, text: str) -> TargetProfile:
        invalid_cidr = self._detect_invalid_cidr(text)
        if invalid_cidr is not None:
            return self._invalid_target_profile(text, f"نطاق CIDR غير صالح: {invalid_cidr}")

        candidates = self._collect_text_candidates(text)
        if candidates:
            _, _, profile = min(candidates, key=lambda item: (item[1], item[0]))
            return profile

        invalid_token = self._find_first_invalid_token(text)
        if invalid_token is not None:
            token_type, token = invalid_token
            if token_type == "cidr":
                return self._invalid_target_profile(text, f"نطاق CIDR غير صالح: {token}")
            return self._invalid_target_profile(text, f"عنوان IPv4 غير صالح: {token}")

        return TargetProfile(
            raw_input=text,
            target_type="unknown",
            normalized_target=text,
            indicators=["unstructured_input"],
            confidence=0.3,
            risk_notes=["لم يتم التعرف على هدف محدد في النص"],
        )

    def _collect_text_candidates(self, text: str) -> List[Tuple[int, int, TargetProfile]]:
        candidates: List[Tuple[int, int, TargetProfile]] = []
        seen: Set[Tuple[str, str]] = set()

        for match in self._URL_IN_TEXT_PATTERN.finditer(text):
            candidate = match.group().rstrip(".,)]}'\"")
            profile = self._profile_url(candidate)
            key = (profile.target_type, profile.normalized_target)
            if key not in seen:
                seen.add(key)
                candidates.append((match.start(), 0, profile))

        for match in self._CIDR_LIKE_PATTERN.finditer(text):
            candidate = match.group()
            network = self._parse_network(candidate)
            if network is None:
                continue
            profile = self._profile_cidr(network.with_prefixlen, raw_input=text)
            key = (profile.target_type, profile.normalized_target)
            if key not in seen:
                seen.add(key)
                candidates.append((match.start(), 1, profile))

        for match in self._IP_LIKE_PATTERN.finditer(text):
            candidate = match.group()
            ip_obj = self._parse_ip(candidate)
            if ip_obj is None:
                continue
            profile = self._profile_ip(str(ip_obj), raw_input=text)
            key = (profile.target_type, profile.normalized_target)
            if key not in seen:
                seen.add(key)
                candidates.append((match.start(), 2, profile))

        for match in self._DOMAIN_IN_TEXT_PATTERN.finditer(text):
            candidate = match.group(1).lower().rstrip(".")
            profile = self._profile_domain(candidate)
            key = (profile.target_type, profile.normalized_target)
            if key not in seen:
                seen.add(key)
                candidates.append((match.start(), 3, profile))

        return candidates

    def _parse_ip(self, ip: str) -> Optional[ipaddress.IPv4Address]:
        try:
            parsed = ipaddress.ip_address(ip)
            if isinstance(parsed, ipaddress.IPv4Address):
                return parsed
        except ValueError:
            return None
        return None

    def _parse_network(self, cidr: str) -> Optional[ipaddress.IPv4Network]:
        if "/" not in cidr:
            return None
        try:
            parsed = ipaddress.ip_network(cidr, strict=False)
            if isinstance(parsed, ipaddress.IPv4Network):
                return parsed
        except ValueError:
            return None
        return None

    def _has_real_cidr_token(self, text: str) -> bool:
        return self._CIDR_TOKEN_PATTERN.search(text) is not None

    def _detect_invalid_ip(self, text: str) -> Optional[str]:
        if "/" in text:
            return None
        if self._IP_LIKE_PATTERN.fullmatch(text) and self._parse_ip(text) is None:
            return text
        return None

    def _detect_invalid_cidr(self, text: str) -> Optional[str]:
        match = self._INVALID_CIDR_TOKEN_PATTERN.search(text)
        if not match:
            return None
        candidate = match.group(1).rstrip(".,)]}'\"")
        if self._parse_network(candidate) is None:
            return candidate
        return None

    def _find_first_invalid_token(self, text: str) -> Optional[Tuple[str, str]]:
        invalids: List[Tuple[int, str, str]] = []

        for match in self._INVALID_CIDR_TOKEN_PATTERN.finditer(text):
            candidate = match.group(1).rstrip(".,)]}'\"")
            if not candidate or "/" not in candidate:
                continue
            if self._parse_network(candidate) is None:
                invalids.append((match.start(1), "cidr", candidate))

        for match in self._IP_LIKE_PATTERN.finditer(text):
            candidate = match.group()
            if self._parse_ip(candidate) is None:
                invalids.append((match.start(), "ip", candidate))

        if not invalids:
            return None

        invalids.sort(key=lambda item: item[0])
        _, token_type, token = invalids[0]
        return token_type, token

    def _invalid_target_profile(self, raw_input: str, reason: str) -> TargetProfile:
        return TargetProfile(
            raw_input=raw_input,
            target_type="unknown",
            normalized_target=raw_input.strip(),
            indicators=["invalid_target"],
            confidence=0.0,
            risk_notes=[reason],
        )

    def _dedupe(self, values: List[str]) -> List[str]:
        seen: Set[str] = set()
        deduped: List[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                deduped.append(value)
        return deduped

    def extract_targets(self, text: str) -> List[TargetProfile]:
        targets: List[TargetProfile] = []
        seen: Set[Tuple[str, str]] = set()

        for _, _, profile in sorted(self._collect_text_candidates(text), key=lambda item: (item[1], item[0])):
            key = (profile.target_type, profile.normalized_target)
            if key not in seen:
                seen.add(key)
                targets.append(profile)

        return targets
