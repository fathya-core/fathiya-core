from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


KNOWLEDGE_MISSION_PREFIX = "FATHIYA_KNOWLEDGE_MISSION_V1:"
MAX_OBJECTIVE_CHARACTERS = 2_000
MAX_REPORT_CHARACTERS = 12_000
MAX_SOURCE_NAME_CHARACTERS = 120


@dataclass(frozen=True)
class KnowledgeMission:
    source_name: str
    objective: str
    content: str


def build_knowledge_mission_prompt(
    source_name: str,
    objective: str,
    content: str,
) -> str:
    payload = {
        "source_name": source_name,
        "objective": objective,
        "content": content,
    }
    prompt = f"{KNOWLEDGE_MISSION_PREFIX}{json.dumps(payload, ensure_ascii=False)}"
    parse_knowledge_mission(prompt)
    if len(prompt) > 20_000:
        raise ValueError("Knowledge mission prompt exceeds 20,000 characters")
    return prompt


def parse_knowledge_mission(prompt: str) -> KnowledgeMission | None:
    if not prompt.startswith(KNOWLEDGE_MISSION_PREFIX):
        return None
    try:
        payload = json.loads(prompt[len(KNOWLEDGE_MISSION_PREFIX) :])
    except json.JSONDecodeError as exc:
        raise ValueError("Knowledge mission payload is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("Knowledge mission payload must be an object")

    source_name = _bounded_text(
        payload.get("source_name"),
        "source_name",
        MAX_SOURCE_NAME_CHARACTERS,
    )
    objective = _bounded_text(
        payload.get("objective"),
        "objective",
        MAX_OBJECTIVE_CHARACTERS,
    )
    content = _bounded_text(
        payload.get("content"),
        "content",
        MAX_REPORT_CHARACTERS,
    )
    return KnowledgeMission(
        source_name=source_name,
        objective=objective,
        content=content,
    )


def operator_request(prompt: str) -> str:
    mission = parse_knowledge_mission(prompt)
    return mission.objective if mission else prompt


def persist_knowledge_mission(root: Path, mission: KnowledgeMission) -> dict[str, Any]:
    digest = hashlib.sha256(mission.content.encode("utf-8")).hexdigest()
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", mission.source_name).strip("-")[:72]
    filename = f"{slug or 'report'}-{digest[:12]}.md"
    intake = root / "intake" / "runtime"
    intake.mkdir(parents=True, exist_ok=True)
    path = intake / filename
    existed = path.exists()
    if not existed:
        captured_at = datetime.now(UTC).isoformat()
        path.write_text(
            "\n".join(
                (
                    "---",
                    "schema: fathiya_knowledge_intake_v1",
                    f"source_name: {json.dumps(mission.source_name, ensure_ascii=False)}",
                    f"captured_at: {captured_at}",
                    f"sha256: {digest}",
                    "trust_boundary: untrusted_evidence",
                    "---",
                    "",
                    f"# {mission.source_name}",
                    "",
                    mission.content,
                    "",
                )
            ),
            encoding="utf-8",
        )
    return {
        "source_name": mission.source_name,
        "path": str(path.relative_to(root)),
        "sha256": digest,
        "characters": len(mission.content),
        "existed": existed,
        "trust_boundary": "untrusted_evidence",
    }


def _bounded_text(value: Any, field: str, limit: int) -> str:
    if not isinstance(value, str) or len(value.strip()) < 3:
        raise ValueError(f"Knowledge mission {field} must contain at least 3 characters")
    clean = value.strip()
    if len(clean) > limit:
        raise ValueError(f"Knowledge mission {field} exceeds {limit} characters")
    return clean
