"""
domains/security/surface_mapper.py — بناء وتلخيص سطح الهجوم المحتمل

يستهلك TargetProfile الناتج من target_profiler ويحوّله إلى SurfaceSummary
منظم وقابل للاستخدام لاحقاً بواسطة vulnerability_hunter أو أي محلل لاحق.

الاستخدام:
    from domains.security.target_profiler import TargetProfiler
    from domains.security.surface_mapper import SurfaceMapper

    profiler = TargetProfiler()
    profile = profiler.profile("افحص https://example.com/login?next=/admin")

    mapper = SurfaceMapper()
    summary = mapper.map(profile, "افحص https://example.com/login?next=/admin")
    print(summary.surface_type)  # web أو api أو code أو ai-agent
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse

from domains.security.target_profiler import TargetProfile


@dataclass
class SurfaceInputPoint:
    """نقطة إدخال محتملة يمكن استهلاكها لاحقاً في فحص الثغرات."""
    name: str
    location: str  # endpoint, path, param, query_key, header, auth, form
    source: str = "explicit"  # explicit أو inferred
    notes: List[str] = field(default_factory=list)


@dataclass
class SurfaceForm:
    """تمثيل مبسط لنموذج إدخال في واجهة ويب."""
    name: str
    action: str = ""
    method: str = "unknown"
    fields: List[str] = field(default_factory=list)
    source: str = "inferred"
    notes: List[str] = field(default_factory=list)


@dataclass
class SurfaceSummary:
    """ملخص سطح الهجوم/التفاعل المحتمل للهدف."""
    raw_input: str
    normalized_target: str
    target_type: str
    surface_type: str  # web, api, code, ai-agent
    confidence: float = 0.0
    endpoints: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    params: List[str] = field(default_factory=list)
    query_keys: List[str] = field(default_factory=list)
    headers: List[str] = field(default_factory=list)
    auth_hints: List[str] = field(default_factory=list)
    forms: List[SurfaceForm] = field(default_factory=list)
    input_points: List[SurfaceInputPoint] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def is_web_like(self) -> bool:
        return self.surface_type in {"web", "api", "ai-agent"}

    @property
    def has_auth(self) -> bool:
        return len(self.auth_hints) > 0


class SurfaceMapper:
    """
    محلل سطح الهجوم — يحول TargetProfile إلى وصف منظم وقابل للمعالجة.

    الأنواع المدعومة:
    - web
    - api
    - code
    - ai-agent
    """

    _URL_PATTERN = re.compile(r"https?://[^\s)\]>\"']+", re.IGNORECASE)
    _PATH_PATTERN = re.compile(r"(?<!:)(/[a-zA-Z0-9_\-./{}:]+)")
    _QUERY_STRING_PATTERN = re.compile(r"\?([a-zA-Z0-9_\-=&%]+)")
    _PARAM_TOKEN_PATTERN = re.compile(
        r"(?:param|parameter|field|form field|query|body|json|arg|argument|بارام|معامل|حقل)\s*[:=]?\s*([a-zA-Z_][a-zA-Z0-9_\-]*)",
        re.IGNORECASE,
    )
    _PATH_PARAM_PATTERN = re.compile(r"[:{]([a-zA-Z_][a-zA-Z0-9_\-]*)[}]?")

    _KNOWN_HEADERS: List[str] = [
        "Authorization",
        "X-API-Key",
        "Api-Key",
        "X-Auth-Token",
        "X-CSRF-Token",
        "X-Forwarded-For",
        "Cookie",
        "Set-Cookie",
        "Content-Type",
        "Accept",
        "Origin",
        "Referer",
        "User-Agent",
    ]

    _API_KEYWORDS: Set[str] = {
        "api", "graphql", "swagger", "openapi", "rest", "json", "endpoint",
        "bearer", "authorization", "x-api-key", "webhook", "rpc",
    }
    _CODE_KEYWORDS: Set[str] = {
        "github", "gitlab", "repo", "repository", "source code", "codebase",
        "package.json", "requirements.txt", ".py", ".js", ".ts", ".java",
        "commit", "branch", "pull request", "merge request", "static analysis",
        "كود", "شفرة", "مستودع", "repository",
    }
    _AI_AGENT_KEYWORDS: Set[str] = {
        "agent", "ai agent", "assistant", "copilot", "llm", "gpt", "prompt",
        "system prompt", "tool call", "function call", "memory", "workflow",
        "assistant instructions", "model", "chatbot", "rag", "multi-agent",
        "وكيل", "مساعد ذكي", "برومبت", "سياق", "أداة",
    }
    _WEB_KEYWORDS: Set[str] = {
        "web", "website", "site", "portal", "login", "register", "form",
        "dashboard", "admin", "search", "html", "https", "http", "csrf",
        "xss", "browser", "صفح", "موقع", "نموذج", "تسجيل الدخول",
    }

    def map(self, profile: TargetProfile, context_text: Optional[str] = None) -> SurfaceSummary:
        """بناء SurfaceSummary من TargetProfile والنص الخام إن توفر."""
        text = (context_text or profile.raw_input or profile.normalized_target or "").strip()

        explicit_urls = self._extract_urls(text)
        parsed_paths, parsed_query_keys, parsed_params = self._extract_url_parts(explicit_urls)
        text_paths = self._extract_paths(text)
        paths = self._dedupe(parsed_paths + text_paths)
        if profile.target_type in {"ip", "cidr"} and not explicit_urls:
            paths = [path for path in paths if not re.fullmatch(r"/\d{1,2}", path)]
        query_keys = self._dedupe(parsed_query_keys + self._extract_query_keys_from_text(text))
        params = self._dedupe(parsed_params + self._extract_params(text, paths, query_keys))
        headers = self._extract_headers(text)
        auth_hints = self._extract_auth_hints(text, headers)

        surface_type, type_confidence, type_indicators, notes = self._detect_surface_type(
            profile=profile,
            text=text,
            paths=paths,
            headers=headers,
            auth_hints=auth_hints,
        )

        endpoints = self._build_endpoints(profile, explicit_urls, paths, surface_type)
        forms = self._extract_forms(
            text=text,
            surface_type=surface_type,
            paths=paths,
            auth_hints=auth_hints,
            params=params,
        )
        input_points = self._build_input_points(
            endpoints=endpoints,
            paths=paths,
            params=params,
            query_keys=query_keys,
            headers=headers,
            auth_hints=auth_hints,
            forms=forms,
        )

        confidence = self._compute_confidence(
            base=profile.confidence,
            type_confidence=type_confidence,
            evidence_count=len(endpoints) + len(paths) + len(params) + len(headers) + len(forms),
        )

        indicators = self._dedupe(list(profile.indicators) + type_indicators)
        notes = self._dedupe(notes + self._build_summary_notes(surface_type, endpoints, forms, auth_hints))

        return SurfaceSummary(
            raw_input=text,
            normalized_target=profile.normalized_target,
            target_type=profile.target_type,
            surface_type=surface_type,
            confidence=confidence,
            endpoints=endpoints,
            paths=paths,
            params=params,
            query_keys=query_keys,
            headers=headers,
            auth_hints=auth_hints,
            forms=forms,
            input_points=input_points,
            indicators=indicators,
            notes=notes,
        )

    def _extract_urls(self, text: str) -> List[str]:
        return self._dedupe([match.group(0).rstrip(".,)") for match in self._URL_PATTERN.finditer(text)])

    def _extract_url_parts(self, urls: List[str]) -> Tuple[List[str], List[str], List[str]]:
        paths: List[str] = []
        query_keys: List[str] = []
        params: List[str] = []

        for url in urls:
            parsed = urlparse(url)
            if parsed.path:
                paths.append(self._normalize_path(parsed.path))
                params.extend(self._PATH_PARAM_PATTERN.findall(parsed.path))
            if parsed.query:
                parsed_query = parse_qs(parsed.query, keep_blank_values=True)
                query_keys.extend(parsed_query.keys())
                params.extend(parsed_query.keys())

        return self._dedupe(paths), self._dedupe(query_keys), self._dedupe(params)

    def _extract_paths(self, text: str) -> List[str]:
        paths: List[str] = []
        for match in self._PATH_PATTERN.finditer(text):
            path = self._normalize_path(match.group(1))
            if path and path != "/":
                paths.append(path)

        if not paths and any(word in text.lower() for word in ["login", "تسجيل الدخول"]):
            paths.append("/login")
        if not paths and any(word in text.lower() for word in ["api", "graphql", "swagger"]):
            paths.append("/api")

        return self._dedupe(paths)

    def _extract_query_keys_from_text(self, text: str) -> List[str]:
        keys: List[str] = []
        for match in self._QUERY_STRING_PATTERN.finditer(text):
            query = match.group(1)
            parsed = parse_qs(query, keep_blank_values=True)
            keys.extend(parsed.keys())
        return self._dedupe(keys)

    def _extract_params(self, text: str, paths: List[str], query_keys: List[str]) -> List[str]:
        params: List[str] = list(query_keys)
        params.extend(self._PARAM_TOKEN_PATTERN.findall(text))
        for path in paths:
            params.extend(self._PATH_PARAM_PATTERN.findall(path))
        return self._dedupe([param for param in params if param])

    def _extract_headers(self, text: str) -> List[str]:
        found: List[str] = []
        text_lower = text.lower()
        for header in self._KNOWN_HEADERS:
            if header.lower() in text_lower:
                found.append(header)

        if "bearer" in text_lower and "Authorization" not in found:
            found.append("Authorization")
        if "cookie" in text_lower and "Cookie" not in found:
            found.append("Cookie")
        return self._dedupe(found)

    def _extract_auth_hints(self, text: str, headers: List[str]) -> List[str]:
        hints: List[str] = []
        lower = text.lower()

        auth_patterns = {
            "bearer-token": ["bearer", "jwt"],
            "api-key": ["x-api-key", "api key", "api-key"],
            "basic-auth": ["basic auth", "authorization basic"],
            "cookie-session": ["cookie", "session", "set-cookie"],
            "oauth": ["oauth", "openid", "oidc"],
            "csrf-token": ["csrf", "x-csrf-token"],
            "login-form": ["login", "signin", "تسجيل الدخول"],
        }

        for label, candidates in auth_patterns.items():
            if any(candidate in lower for candidate in candidates):
                hints.append(label)

        if "Authorization" in headers and not any(h in hints for h in ["bearer-token", "basic-auth"]):
            hints.append("authorization-header")

        return self._dedupe(hints)

    def _detect_surface_type(
        self,
        profile: TargetProfile,
        text: str,
        paths: List[str],
        headers: List[str],
        auth_hints: List[str],
    ) -> Tuple[str, float, List[str], List[str]]:
        lower = text.lower()
        indicators: List[str] = []
        notes: List[str] = []

        ai_score = self._keyword_score(lower, self._AI_AGENT_KEYWORDS)
        code_score = self._keyword_score(lower, self._CODE_KEYWORDS)
        api_score = self._keyword_score(lower, self._API_KEYWORDS)
        web_score = self._keyword_score(lower, self._WEB_KEYWORDS)

        if any(token in lower for token in ["api.", "/api", "graphql", "swagger", "openapi"]):
            api_score += 2
        if any(hint in auth_hints for hint in ["bearer-token", "api-key", "authorization-header"]):
            api_score += 1
        if any(p.startswith("/api") or "graphql" in p.lower() for p in paths):
            api_score += 2

        if profile.target_type in {"domain", "url"}:
            web_score += 2
        if "web_server" in profile.indicators:
            web_score += 1

        if ai_score > 0:
            notes.append("تم رصد مؤشرات مرتبطة بوكلاء الذكاء الاصطناعي أو الواجهات الحوارية.")
        if code_score > 0:
            notes.append("تم رصد مؤشرات مرتبطة بمستودع أو قاعدة شيفرة.")
        if api_score > 0:
            notes.append("تم رصد مؤشرات مرتبطة بواجهة API أو تكامل برمجي.")
        if web_score > 0:
            notes.append("تم رصد مؤشرات مرتبطة بواجهة ويب أو تطبيق HTTP.")

        scores = {
            "ai-agent": ai_score,
            "code": code_score,
            "api": api_score,
            "web": web_score,
        }
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]

        if best_score <= 0:
            if profile.target_type in {"domain", "url"}:
                best_type = "web"
                best_score = 1
                notes.append("لم تتوفر مؤشرات تخصصية كافية؛ تم اعتماد سطح ويب كافتراضي متوافق.")
            elif profile.target_type in {"ip", "cidr"}:
                if headers or auth_hints or paths:
                    best_type = "api"
                    best_score = 1
                    notes.append("الهدف شبكي بلا URL صريح؛ تم اعتماد surface من نوع api بشكل محافظ بدلاً من web الافتراضي.")
                else:
                    best_type = "code"
                    best_score = 1
                    notes.append("الهدف شبكي بلا مؤشرات HTTP صريحة؛ لم يتم افتراض surface:web تلقائياً.")
            else:
                best_type = "code"
                best_score = 1
                notes.append("تم اعتماد سطح code كافتراضي عند غياب مؤشرات الشبكة أو الويب.")

        indicators.append(f"surface:{best_type}")
        indicators.append(f"evidence_score:{best_score}")
        confidence = min(0.98, 0.45 + (best_score * 0.12))
        return best_type, round(confidence, 2), self._dedupe(indicators), self._dedupe(notes)

    def _build_endpoints(
        self,
        profile: TargetProfile,
        explicit_urls: List[str],
        paths: List[str],
        surface_type: str,
    ) -> List[str]:
        if explicit_urls:
            return self._dedupe(explicit_urls)

        if profile.target_type in {"ip", "cidr"}:
            return []

        host = profile.normalized_target.strip()
        if not host:
            return []

        endpoints: List[str] = []
        base_scheme = "https"
        if profile.target_type == "url" and profile.raw_input.lower().startswith("http://"):
            base_scheme = "http"

        if surface_type in {"web", "api", "ai-agent"}:
            if not paths:
                paths = ["/"]
            for path in paths:
                normalized_path = path if path.startswith("/") else f"/{path}"
                endpoints.append(f"{base_scheme}://{host}{normalized_path}")

        return self._dedupe(endpoints)

    def _extract_forms(
        self,
        text: str,
        surface_type: str,
        paths: List[str],
        auth_hints: List[str],
        params: List[str],
    ) -> List[SurfaceForm]:
        forms: List[SurfaceForm] = []
        lower = text.lower()

        if surface_type != "web":
            return forms

        if any(token in lower for token in ["login", "signin", "تسجيل الدخول"]) or "/login" in paths:
            forms.append(SurfaceForm(
                name="login",
                action="/login" if "/login" in paths else "",
                method="post",
                fields=self._dedupe([field for field in ["username", "email", "password"] + params if field]),
                source="inferred",
                notes=["نموذج مصادقة محتمل"],
            ))

        if any(token in lower for token in ["register", "signup", "تسجيل"]):
            forms.append(SurfaceForm(
                name="register",
                action="/register" if "/register" in paths else "",
                method="post",
                fields=self._dedupe([field for field in ["name", "email", "password"] + params if field]),
                source="inferred",
                notes=["نموذج تسجيل محتمل"],
            ))

        if any(token in lower for token in ["search", "بحث"]) or "/search" in paths:
            forms.append(SurfaceForm(
                name="search",
                action="/search" if "/search" in paths else "",
                method="get",
                fields=self._dedupe([field for field in ["q", "query"] + params if field]),
                source="inferred",
                notes=["نقطة إدخال بحث محتملة"],
            ))

        if not forms and auth_hints:
            forms.append(SurfaceForm(
                name="auth-entry",
                action="",
                method="post",
                fields=self._dedupe([field for field in ["token", "session", "password"] + params if field]),
                source="inferred",
                notes=["تم استنتاج نموذج إدخال مرتبط بالمصادقة من التلميحات المكتشفة"],
            ))

        return forms

    def _build_input_points(
        self,
        endpoints: List[str],
        paths: List[str],
        params: List[str],
        query_keys: List[str],
        headers: List[str],
        auth_hints: List[str],
        forms: List[SurfaceForm],
    ) -> List[SurfaceInputPoint]:
        points: List[SurfaceInputPoint] = []
        seen: Set[Tuple[str, str]] = set()

        def add(name: str, location: str, source: str = "explicit", notes: Optional[List[str]] = None) -> None:
            key = (location, name)
            if not name or key in seen:
                return
            seen.add(key)
            points.append(SurfaceInputPoint(name=name, location=location, source=source, notes=notes or []))

        for endpoint in endpoints:
            add(endpoint, "endpoint")
        for path in paths:
            add(path, "path")
        for param in params:
            add(param, "param")
        for query_key in query_keys:
            add(query_key, "query_key")
        for header in headers:
            add(header, "header")
        for auth_hint in auth_hints:
            add(auth_hint, "auth")
        for form in forms:
            add(form.name, "form", form.source, form.notes)
            for field in form.fields:
                add(field, "param", form.source, [f"مستنتج من النموذج {form.name}"])

        return points

    def _build_summary_notes(
        self,
        surface_type: str,
        endpoints: List[str],
        forms: List[SurfaceForm],
        auth_hints: List[str],
    ) -> List[str]:
        notes: List[str] = [f"تم تصنيف السطح الأساسي كـ {surface_type}."]
        if endpoints:
            notes.append(f"تم جمع {len(endpoints)} endpoint محتمل/صريح.")
        if forms:
            notes.append(f"تم استنتاج/استخراج {len(forms)} نموذج إدخال محتمل.")
        if auth_hints:
            notes.append("توجد مؤشرات على وجود آلية مصادقة أو جلسات أو مفاتيح وصول.")
        return notes

    def _compute_confidence(self, base: float, type_confidence: float, evidence_count: int) -> float:
        confidence = (base * 0.45) + (type_confidence * 0.45) + min(0.1, evidence_count * 0.01)
        return round(min(0.99, max(0.35, confidence)), 2)

    def _keyword_score(self, text: str, keywords: Set[str]) -> int:
        score = 0
        for keyword in keywords:
            if keyword.lower() in text:
                score += 1
        return score

    def _normalize_path(self, path: str) -> str:
        normalized = path.strip()
        if not normalized:
            return ""
        if not normalized.startswith("/"):
            normalized = f"/{normalized}"
        normalized = re.sub(r"//+", "/", normalized)
        return normalized

    def _dedupe(self, values: List[str]) -> List[str]:
        deduped: List[str] = []
        seen: Set[str] = set()
        for value in values:
            cleaned = value.strip() if isinstance(value, str) else value
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                deduped.append(cleaned)
        return deduped
