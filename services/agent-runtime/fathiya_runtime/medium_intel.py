from __future__ import annotations

import hashlib
import html
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests

from .learning import TOPICS


DEFAULT_MEDIUM_FEEDS = (
    "https://medium.com/feed/tag/bug-bounty",
    "https://medium.com/feed/tag/hackerone",
    "https://medium.com/feed/tag/bugcrowd",
    "https://medium.com/feed/tag/web-security",
    "https://medium.com/feed/tag/api-security",
    "https://medium.com/feed/tag/oauth",
    "https://medium.com/feed/tag/graphql",
    "https://medium.com/feed/tag/ssrf",
    "https://medium.com/feed/tag/idor",
    "https://medium.com/feed/tag/csrf",
)

MAX_ITEMS_HARD_LIMIT = 500


@dataclass(frozen=True)
class MediumIntelItem:
    id: str
    title: str
    url: str
    source_name: str
    excerpt: str
    topics: list[str]
    root_cause_terms: list[str]
    duplicate_search_terms: list[str]
    evidence_score: int
    impact_score: int
    novelty_score: int
    readiness_score: int
    gate: str
    gate_reason: str
    required_next_evidence: list[str]
    dedupe_anchors: list[str]


def build_medium_intelligence_report(
    output_root: Path,
    *,
    source_urls: Iterable[str] = (),
    source_text: str = "",
    source_paths: Iterable[Path] = (),
    title: str = "FATHIYA Medium daily intelligence",
    max_items: int = 200,
    fetch_live: bool = True,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    max_items = max(1, min(int(max_items or 200), MAX_ITEMS_HARD_LIMIT))
    captured_at = datetime.now(UTC).isoformat()
    errors: list[str] = []
    raw_items: list[dict[str, str]] = []

    urls = [url.strip() for url in source_urls if str(url).strip()]
    if not urls and fetch_live:
        urls = list(DEFAULT_MEDIUM_FEEDS)
    if fetch_live:
        for url in urls:
            if len(raw_items) >= max_items:
                break
            try:
                raw_items.extend(_fetch_source_items(url, max_items - len(raw_items)))
            except requests.RequestException as exc:
                errors.append(f"{url}: {type(exc).__name__}: {str(exc)[:180]}")
            except ET.ParseError as exc:
                errors.append(f"{url}: XML parse failed: {str(exc)[:180]}")

    for source_path in source_paths:
        if len(raw_items) >= max_items:
            break
        try:
            text = source_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(f"{source_path}: {type(exc).__name__}")
            continue
        parsed_items = _items_from_source_blob(text, source_path.name)
        if parsed_items:
            raw_items.extend(parsed_items[: max_items - len(raw_items)])
        else:
            raw_items.append(
                {
                    "title": source_path.stem,
                    "url": str(source_path),
                    "source_name": source_path.name,
                    "text": text[:80_000],
                }
            )

    if source_text.strip() and len(raw_items) < max_items:
        parsed_items = _items_from_source_blob(source_text, "operator-source-text")
        if parsed_items:
            raw_items.extend(parsed_items[: max_items - len(raw_items)])
        else:
            raw_items.append(
                {
                    "title": "operator-supplied-medium-corpus",
                    "url": "",
                    "source_name": "operator-source-text",
                    "text": source_text[:80_000],
                }
            )

    deduped = _dedupe_raw_items(raw_items)[:max_items]
    items = [analyze_medium_item(item) for item in deduped]
    ready = [item for item in items if item.gate == "candidate"]
    needs_evidence = [item for item in items if item.gate == "needs_evidence"]
    dedupe_hold = [item for item in items if item.gate == "dedupe_hold"]
    learning_only = [item for item in items if item.gate == "learning_only"]
    topic_counts: dict[str, int] = {}
    for item in items:
        for topic in item.topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1

    ranked = sorted(
        ready,
        key=lambda item: (
            -item.readiness_score,
            -item.impact_score,
            -item.novelty_score,
            item.title.casefold(),
        ),
    )
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = _slug(title)[:80] or "medium-intelligence"
    report_dir = output_root / "reports" / "medium-intel"
    report_dir.mkdir(parents=True, exist_ok=True)
    json_path = report_dir / f"{timestamp}-{slug}.json"
    markdown_path = report_dir / f"{timestamp}-{slug}.md"
    payload = {
        "mode": "medium_intelligence_pipeline_v1",
        "title": title,
        "captured_at": captured_at,
        "source_url_count": len(urls),
        "processed_count": len(items),
        "ready_candidate_count": len(ready),
        "needs_evidence_count": len(needs_evidence),
        "dedupe_hold_count": len(dedupe_hold),
        "learning_only_count": len(learning_only),
        "topic_counts": dict(sorted(topic_counts.items())),
        "top_candidates": [asdict(item) for item in ranked[:25]],
        "needs_evidence": [asdict(item) for item in needs_evidence[:25]],
        "dedupe_hold": [asdict(item) for item in dedupe_hold[:25]],
        "learning_only": [asdict(item) for item in learning_only[:25]],
        "errors": errors[:25],
        "quality_gate": {
            "submission_blocked_by_default": True,
            "ready_requires": [
                "novel root cause or exploit primitive",
                "repeatable proof steps or PoC evidence",
                "clear customer/user/application impact",
                "dedupe search terms and anchors recorded",
            ],
            "previous_failure_lessons": [
                "text-only claims fail as Not Reproducible",
                "same root cause plus cleaner wording still closes as duplicate",
                "severity escalation needs demonstrated impact, not theory",
            ],
        },
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(_render_markdown(payload), encoding="utf-8")
    return {
        "available": True,
        "executed": True,
        "read_only": False,
        "external_submission": False,
        "network_call": bool(fetch_live and urls),
        "mode": payload["mode"],
        "captured_at": captured_at,
        "processed_count": len(items),
        "ready_candidate_count": len(ready),
        "needs_evidence_count": len(needs_evidence),
        "dedupe_hold_count": len(dedupe_hold),
        "learning_only_count": len(learning_only),
        "topic_counts": payload["topic_counts"],
        "top_candidates": payload["top_candidates"][:10],
        "report_path": str(markdown_path),
        "json_path": str(json_path),
        "errors": errors[:10],
        "quality_gate": payload["quality_gate"],
    }


def analyze_medium_item(raw: dict[str, str]) -> MediumIntelItem:
    title = _clean(raw.get("title") or "Untitled Medium report")[:220]
    url = _clean(raw.get("url") or "")
    text = _clean(raw.get("text") or "")
    full_text = f"{title}\n{text}".casefold()
    topics = _matched_topics(full_text)
    root_cause_terms = _root_cause_terms(full_text)
    dedupe_anchors = _dedupe_anchors(full_text)
    evidence_score = _score_terms(full_text, EVIDENCE_TERMS)
    impact_score = _score_terms(full_text, IMPACT_TERMS)
    novelty_score = _score_terms(full_text, NOVELTY_TERMS)
    tutorial_only = _looks_learning_only(full_text)
    duplicate_search_terms = _duplicate_search_terms(title, root_cause_terms, topics)
    readiness_score = min(
        100,
        evidence_score * 10 + impact_score * 12 + novelty_score * 8 + min(len(topics), 4) * 4,
    )
    if dedupe_anchors:
        gate = "dedupe_hold"
        gate_reason = "يطابق جذرًا أو اعتراضًا سبق أن أغلق كتكرار/غير قابل للتطبيق؛ يحتاج primitive جديد قبل أي تقرير."
    elif tutorial_only and evidence_score < 3:
        gate = "learning_only"
        gate_reason = "مادة تدريب أو قائمة أفكار؛ تصلح للتعلم وبناء فرضيات لا لتقرير مباشر."
    elif evidence_score < 3 or impact_score < 2:
        gate = "needs_evidence"
        gate_reason = "الفكرة لا تتجاوز بوابة الإثبات أو الأثر العملي بعد."
    else:
        gate = "candidate"
        gate_reason = "مرشح قابل للتحقيق: لديه إشارات إثبات وأثر، ويحتاج اختبار نطاق مصرح قبل Draft."
    required_next_evidence = _required_next_evidence(
        topics=topics,
        gate=gate,
        evidence_score=evidence_score,
        impact_score=impact_score,
    )
    return MediumIntelItem(
        id=_item_id(title, url, text),
        title=title,
        url=url,
        source_name=_clean(raw.get("source_name") or _source_name(url) or "medium"),
        excerpt=text[:700],
        topics=topics,
        root_cause_terms=root_cause_terms,
        duplicate_search_terms=duplicate_search_terms,
        evidence_score=evidence_score,
        impact_score=impact_score,
        novelty_score=novelty_score,
        readiness_score=readiness_score,
        gate=gate,
        gate_reason=gate_reason,
        required_next_evidence=required_next_evidence,
        dedupe_anchors=dedupe_anchors,
    )


EVIDENCE_TERMS = (
    "proof of concept",
    "poc",
    "steps to reproduce",
    "reproduce",
    "request",
    "response",
    "curl",
    "burp",
    "har",
    "screenshot",
    "video",
    "demo",
    "exploit",
    "payload",
    "before and after",
    "as an attacker",
    "impact",
    "working",
    "validated",
)

IMPACT_TERMS = (
    "account takeover",
    "ato",
    "cross tenant",
    "cross-tenant",
    "unauthorized",
    "privilege escalation",
    "admin",
    "sensitive data",
    "token theft",
    "credential",
    "ssrf",
    "rce",
    "remote code execution",
    "payment",
    "billing",
    "state change",
    "user impact",
    "customer impact",
    "bypass",
)

NOVELTY_TERMS = (
    "bypass",
    "patch bypass",
    "new technique",
    "novel",
    "zero day",
    "0day",
    "root cause",
    "different primitive",
    "production",
    "realistic",
    "post-fix",
)

ROOT_CAUSE_PATTERNS = (
    "oauth",
    "csrf",
    "cache-control",
    "cookie",
    "state",
    "nonce",
    "idor",
    "bola",
    "graphql",
    "websocket",
    "ssrf",
    "jwt",
    "oidc",
    "saml",
    "webhook",
    "race",
    "replay",
    "mass assignment",
    "access control",
    "authorization",
    "source map",
    "sourcemap",
    "cache poisoning",
    "request smuggling",
    "deserialization",
)


def _fetch_source_items(url: str, limit: int) -> list[dict[str, str]]:
    normalized_url = _normalize_medium_feed_url(url)
    response = requests.get(
        normalized_url,
        headers={
            "User-Agent": "FATHIYA-medium-intel/1.0 read-only",
            "Accept": "application/rss+xml,application/xml,text/xml,text/html;q=0.8,*/*;q=0.5",
        },
        timeout=12,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "")
    text = response.text
    if "xml" in content_type or "<rss" in text[:500].casefold() or "<feed" in text[:500].casefold():
        return _parse_feed(text, normalized_url, limit)
    return [
        {
            "title": _html_title(text) or normalized_url,
            "url": normalized_url,
            "source_name": _source_name(normalized_url) or normalized_url,
            "text": _strip_html(text)[:50_000],
        }
    ][:limit]


def _normalize_medium_feed_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.netloc.endswith("medium.com") and not parsed.path.startswith("/feed/"):
        parts = [part for part in parsed.path.split("/") if part]
        if parts[:1] == ["tag"] and len(parts) >= 2:
            return f"https://medium.com/feed/tag/{parts[1]}"
        if len(parts) == 1:
            return f"https://medium.com/feed/{'/'.join(parts)}"
    return url


def _items_from_source_blob(text: str, source_name: str) -> list[dict[str, str]]:
    raw = text.strip()
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        candidate_items = parsed.get("items") or parsed.get("articles") or parsed.get("stories")
    else:
        candidate_items = parsed
    if not isinstance(candidate_items, list):
        return []
    items: list[dict[str, str]] = []
    for index, item in enumerate(candidate_items):
        if not isinstance(item, dict):
            continue
        title = _clean(str(item.get("title") or item.get("name") or f"{source_name}-{index + 1}"))
        url = _clean(str(item.get("url") or item.get("href") or ""))
        body = _clean(
            str(
                item.get("text")
                or item.get("content")
                or item.get("excerpt")
                or item.get("summary")
                or ""
            )
        )
        if not title and not body:
            continue
        items.append(
            {
                "title": title[:220] or f"{source_name}-{index + 1}",
                "url": url,
                "source_name": _clean(str(item.get("source_name") or item.get("sourceList") or source_name)),
                "text": body[:80_000],
            }
        )
    return items


def _parse_feed(text: str, source_url: str, limit: int) -> list[dict[str, str]]:
    root = ET.fromstring(text.encode("utf-8"))
    items = root.findall(".//item")
    if not items:
        items = root.findall("{http://www.w3.org/2005/Atom}entry")
    parsed: list[dict[str, str]] = []
    for item in items[:limit]:
        title = _first_text(item, ("title", "{http://www.w3.org/2005/Atom}title"))
        link = _rss_link(item)
        body = " ".join(
            value
            for value in (
                _first_text(item, ("description", "summary", "{http://www.w3.org/2005/Atom}summary")),
                _first_text(item, ("{http://purl.org/rss/1.0/modules/content/}encoded", "{http://www.w3.org/2005/Atom}content")),
            )
            if value
        )
        parsed.append(
            {
                "title": _strip_html(title) or link or source_url,
                "url": link or source_url,
                "source_name": _source_name(source_url) or "medium-feed",
                "text": _strip_html(body)[:50_000],
            }
        )
    return parsed


def _first_text(item: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        node = item.find(name)
        if node is not None and node.text:
            return node.text
    return ""


def _rss_link(item: ET.Element) -> str:
    link = _first_text(item, ("link",))
    if link:
        return link.strip()
    atom = item.find("{http://www.w3.org/2005/Atom}link")
    if atom is not None:
        return str(atom.attrib.get("href") or "").strip()
    return ""


def _dedupe_raw_items(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        key = (item.get("url") or item.get("title") or item.get("text") or "").strip().casefold()
        if not key:
            continue
        digest = hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()
        if digest in seen:
            continue
        seen.add(digest)
        deduped.append(item)
    return deduped


def _matched_topics(text: str) -> list[str]:
    topics: list[str] = []
    for topic in TOPICS:
        if any(str(keyword).casefold() in text for keyword in topic.get("keywords", ())):
            topics.append(str(topic["id"]))
    return topics[:8] or ["evidence-and-reporting"]


def _root_cause_terms(text: str) -> list[str]:
    terms = [term for term in ROOT_CAUSE_PATTERNS if term in text]
    code_terms = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{6,}\(\)?", text)
    for term in code_terms[:12]:
        clean = term.rstrip("()")
        if clean.casefold() not in {item.casefold() for item in terms}:
            terms.append(clean)
    return terms[:16]


def _dedupe_anchors(text: str) -> list[str]:
    anchors: list[tuple[str, tuple[str, ...]]] = [
        ("stripe-smokescreen-upstream-proxy-header", ("upstreamproxyselector", "x-upstream-https-proxy", "setupstreamproxyheader")),
        ("vercel-flags-precompute-cross-group-replay", ("vercel", "precompute", "flag group", "cross-flag")),
        ("vercel-workflow-deterministic-webhook-token", ("vercel workflow", "deterministic", "webhook", "startedat")),
        ("querybook-google-sheets-oauth-csrf", ("querybook", "google sheets", "oauth", "csrf")),
    ]
    matched = []
    for name, terms in anchors:
        if all(term in text for term in terms):
            matched.append(name)
    return matched


def _score_terms(text: str, terms: tuple[str, ...]) -> int:
    return min(8, sum(1 for term in terms if term in text))


def _looks_learning_only(text: str) -> bool:
    learning_terms = ("tips", "checklist", "roadmap", "tools", "awesome", "how to", "tutorial", "course", "guide", "automation stack")
    report_terms = ("poc", "steps to reproduce", "request", "response", "as an attacker", "impact")
    return any(term in text for term in learning_terms) and not any(term in text for term in report_terms)


def _required_next_evidence(
    *,
    topics: list[str],
    gate: str,
    evidence_score: int,
    impact_score: int,
) -> list[str]:
    required = [
        "dedupe search across disclosed reports, report IDs, GitHub issues/PRs, changelog, CVEs, and exact root-cause terms",
        "one-sentence impact starting with: As an attacker, I could...",
    ]
    if evidence_score < 3:
        required.append("repeatable PoC: exact requests/responses, screenshots/video/HAR, or local test file")
    if impact_score < 2:
        required.append("customer/user/application impact proof, not only best-practice or missing-header prose")
    if "access-control" in topics or "graphql" in topics:
        required.append("two-account or two-tenant proof with victim-owned object and attacker-visible result")
    if "api-security" in topics:
        required.append("endpoint, method, payload, before/after state, and program scope confirmation")
    if "realtime-authorization" in topics:
        required.append("handshake plus per-channel/message authorization proof and negative control")
    if gate == "dedupe_hold":
        required.append("materially new primitive, root cause, or realistic production impact that defeats the prior duplicate")
    return required[:8]


def _duplicate_search_terms(title: str, root_causes: list[str], topics: list[str]) -> list[str]:
    words = [
        word
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", title)
        if word.casefold() not in {"medium", "security", "vulnerability", "writeup", "bug", "bounty"}
    ][:8]
    terms = [*root_causes[:8], *topics[:5], *words]
    deduped: list[str] = []
    seen: set[str] = set()
    for term in terms:
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(term)
    return deduped[:14]


def _item_id(title: str, url: str, text: str) -> str:
    digest = hashlib.sha256(f"{title}\n{url}\n{text[:1000]}".encode("utf-8", errors="ignore")).hexdigest()
    return f"mid-{digest[:12]}"


def _source_name(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.netloc:
        return ""
    path = parsed.path.strip("/").replace("/", "-")
    return f"{parsed.netloc}/{path}" if path else parsed.netloc


def _html_title(text: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", text, re.IGNORECASE | re.DOTALL)
    return _strip_html(match.group(1)) if match else ""


def _strip_html(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return _clean(html.unescape(without_tags))


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "-", value).strip("-").lower()


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# {payload['title']}",
        "",
        f"- Captured: `{payload['captured_at']}`",
        f"- Processed: **{payload['processed_count']}**",
        f"- Ready candidates: **{payload['ready_candidate_count']}**",
        f"- Needs evidence: **{payload['needs_evidence_count']}**",
        f"- Dedupe hold: **{payload['dedupe_hold_count']}**",
        f"- Learning only: **{payload['learning_only_count']}**",
        "",
        "## Gate",
        "",
        "No Medium item becomes a report-ready draft until it proves novelty, repeatability, and impact.",
        "",
        "## Top Candidates",
        "",
    ]
    if not payload["top_candidates"]:
        lines.append("No report-ready candidates passed the gate.")
    for item in payload["top_candidates"][:15]:
        lines.extend(
            [
                f"### {item['title']}",
                f"- Gate: `{item['gate']}` · readiness `{item['readiness_score']}`",
                f"- URL: {item['url'] or 'local/source text'}",
                f"- Topics: {', '.join(item['topics'])}",
                f"- Dedupe terms: {', '.join(item['duplicate_search_terms'])}",
                f"- Why: {item['gate_reason']}",
                f"- Next evidence: {'; '.join(item['required_next_evidence'])}",
                "",
            ]
        )
    if payload["needs_evidence"]:
        lines.extend(["## Needs Evidence", ""])
        for item in payload["needs_evidence"][:15]:
            lines.append(f"- `{item['readiness_score']}` {item['title']} - {item['gate_reason']}")
    if payload["dedupe_hold"]:
        lines.extend(["", "## Dedupe Holds", ""])
        for item in payload["dedupe_hold"][:15]:
            lines.append(f"- {item['title']} - anchors: {', '.join(item['dedupe_anchors'])}")
    if payload.get("errors"):
        lines.extend(["", "## Source Errors", ""])
        lines.extend(f"- {error}" for error in payload["errors"])
    lines.append("")
    return "\n".join(lines)
