from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .quiet_io import quiet_huggingface_output


@dataclass
class RetrievedSource:
    path: str
    score: float
    excerpt: str


class KnowledgeRetriever:
    def __init__(self, root: Path, *, enable_hf: bool = False, hf_model: str = ""):
        self.root = root
        self.enable_hf = enable_hf
        self.hf_model = hf_model
        self._encoder: Any = None
        self.last_mode = "not_run"
        self.last_error: str | None = None

    def search(self, query: str, limit: int = 5) -> list[RetrievedSource]:
        self.last_error = None
        documents = self._documents()
        explicit = self._explicit_sources(query, documents, limit)
        explicit_paths = {source.path for source in explicit}
        documents = [
            (path, text)
            for path, text in documents
            if str(path.relative_to(self.root)) not in explicit_paths
        ]
        remaining_limit = max(limit - len(explicit), 0)
        if remaining_limit == 0:
            self.last_mode = "explicit_paths"
            return explicit
        if self.enable_hf:
            results = self._hf_search(query, documents, remaining_limit)
            if results is not None:
                self.last_mode = (
                    "explicit_paths+huggingface" if explicit else "huggingface"
                )
                return [*explicit, *results]
            self.last_mode = (
                "explicit_paths+keyword_fallback" if explicit else "keyword_fallback"
            )
        else:
            self.last_mode = "explicit_paths+keyword" if explicit else "keyword"
        return [
            *explicit,
            *self._keyword_search(query, documents, remaining_limit),
        ][:limit]

    def _documents(self) -> list[tuple[Path, str]]:
        if not self.root.exists():
            return []
        files = sorted(
            path
            for path in self.root.rglob("*")
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".json"}
        )
        documents: list[tuple[Path, str]] = []
        for path in files[:750]:
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                continue
            if path.suffix.lower() == ".json":
                try:
                    text = json.dumps(json.loads(text), ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            documents.append((path, text[:12_000]))
        return documents

    def _keyword_search(
        self,
        query: str,
        documents: list[tuple[Path, str]],
        limit: int,
    ) -> list[RetrievedSource]:
        query_terms = set(self._terms(query))
        scored: list[RetrievedSource] = []
        for path, text in documents:
            terms = self._terms(f"{path.name} {text}")
            if not terms:
                continue
            overlap = sum(1 for term in terms if term in query_terms)
            if overlap == 0:
                continue
            score = overlap / math.sqrt(max(len(set(terms)), 1))
            scored.append(
                RetrievedSource(
                    path=str(path.relative_to(self.root)),
                    score=round(score, 4),
                    excerpt=self._excerpt(text, query_terms),
                )
            )
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _hf_search(
        self,
        query: str,
        documents: list[tuple[Path, str]],
        limit: int,
    ) -> list[RetrievedSource] | None:
        try:
            with quiet_huggingface_output():
                from sentence_transformers import SentenceTransformer, util

                if not documents:
                    return []
                if self._encoder is None:
                    self._encoder = SentenceTransformer(self.hf_model, device="cpu")
                snippets = [f"{path.name}\n{text[:1600]}" for path, text in documents]
                embeddings = self._encoder.encode(
                    snippets,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                )
                query_embedding = self._encoder.encode(query, convert_to_tensor=True)
                scores = util.cos_sim(query_embedding, embeddings)[0]
                top = scores.topk(k=min(limit, len(documents)))
            return [
                RetrievedSource(
                    path=str(documents[int(index)][0].relative_to(self.root)),
                    score=round(float(score), 4),
                    excerpt=documents[int(index)][1][:500].replace("\n", " "),
                )
                for score, index in zip(top.values, top.indices)
            ]
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {str(exc)[:500]}"
            return None

    def _explicit_sources(
        self,
        query: str,
        documents: list[tuple[Path, str]],
        limit: int,
    ) -> list[RetrievedSource]:
        if limit <= 0:
            return []
        by_relative = {
            str(path.relative_to(self.root)).replace("\\", "/").lower(): (path, text)
            for path, text in documents
        }
        requested: list[str] = []
        for match in re.findall(
            r"(?:\.?[\\/])?(?:knowledge[\\/])?[\w./\\-]+\.(?:md|txt|json)",
            query,
            flags=re.IGNORECASE,
        ):
            candidate = match.strip().strip("`'\".,);:")
            candidate = candidate.replace("\\", "/").lstrip("./")
            if candidate.lower().startswith("knowledge/"):
                candidate = candidate[len("knowledge/") :]
            candidate = candidate.lower()
            if candidate and candidate not in requested:
                requested.append(candidate)

        results: list[RetrievedSource] = []
        for candidate in requested:
            if len(results) >= limit:
                break
            item = by_relative.get(candidate)
            if item is None:
                item = next(
                    (
                        (path, text)
                        for relative, (path, text) in by_relative.items()
                        if relative.endswith("/" + candidate) or relative.endswith(candidate)
                    ),
                    None,
                )
            if item is None:
                continue
            path, text = item
            results.append(
                RetrievedSource(
                    path=str(path.relative_to(self.root)),
                    score=1.0,
                    excerpt=self._source_excerpt(text),
                )
            )
        return results

    @staticmethod
    def _terms(text: str) -> list[str]:
        return [term.lower() for term in re.findall(r"[\w\u0600-\u06ff-]{3,}", text)]

    @staticmethod
    def _excerpt(text: str, query_terms: set[str]) -> str:
        flattened = re.sub(r"\s+", " ", text).strip()
        lower = flattened.lower()
        indexes = [lower.find(term) for term in query_terms if lower.find(term) >= 0]
        start = max(min(indexes, default=0) - 120, 0)
        return flattened[start : start + 500]

    @staticmethod
    def _source_excerpt(text: str) -> str:
        return "\n".join(line.strip() for line in text.strip().splitlines())[:4_000]
