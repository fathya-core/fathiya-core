#!/usr/bin/env python3
"""Import and validate FATHIYA retrieval index JSON under knowledge/."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
README_PATH = KNOWLEDGE_DIR / "retrieval" / "README_RETRIEVAL_INDEXES_v0.md"

INDEX_FILES = (
    "search_index.json",
    "domain_index.json",
    "sensitivity_index.json",
    "type_index.json",
    "graph_neighbors.json",
    "retrieval_index_summary.json",
)

ZIP_CANDIDATES = (
    REPO_ROOT / "FATHIYA_RETRIEVAL_INDEXES_v0.zip",
    KNOWLEDGE_DIR / "retrieval" / "FATHIYA_RETRIEVAL_INDEXES_v0.zip",
)


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    errors: list[str] = field(default_factory=list)


@dataclass
class ValidationReport:
    status: str
    validated_at: str
    branch: str
    import_source: str | None
    checks: list[CheckResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "PASS" and all(c.passed for c in self.checks)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _collect_paths(obj: Any, paths: set[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key == "path" and isinstance(value, str) and value.strip():
                paths.add(value.strip().replace("\\", "/"))
            else:
                _collect_paths(value, paths)
    elif isinstance(obj, list):
        for item in obj:
            _collect_paths(item, paths)


def _neighbor_ids(obj: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(obj, dict):
        if "neighbors" in obj and isinstance(obj["neighbors"], list):
            for n in obj["neighbors"]:
                if isinstance(n, str):
                    ids.add(n)
                elif isinstance(n, dict) and "id" in n:
                    ids.add(str(n["id"]))
        if "related_nodes" in obj and isinstance(obj["related_nodes"], list):
            for n in obj["related_nodes"]:
                if isinstance(n, str):
                    ids.add(n)
        for value in obj.values():
            ids |= _neighbor_ids(value)
    elif isinstance(obj, list):
        for item in obj:
            ids |= _neighbor_ids(item)
    return ids


def _graph_node_ids(graph_neighbors: dict[str, Any], graph_json: dict[str, Any] | None) -> set[str]:
    node_ids: set[str] = set()
    nodes = graph_neighbors.get("nodes")
    if isinstance(nodes, dict):
        node_ids |= {str(k) for k in nodes}
    elif isinstance(nodes, list):
        for node in nodes:
            if isinstance(node, dict) and "id" in node:
                node_ids.add(str(node["id"]))
            elif isinstance(node, str):
                node_ids.add(node)
    for key in ("node_ids", "ids"):
        if isinstance(graph_neighbors.get(key), list):
            node_ids |= {str(x) for x in graph_neighbors[key]}
    if graph_json:
        g_nodes = graph_json.get("nodes")
        if isinstance(g_nodes, dict):
            node_ids |= {str(k) for k in g_nodes}
        elif isinstance(g_nodes, list):
            for node in g_nodes:
                if isinstance(node, dict) and "id" in node:
                    node_ids.add(str(node["id"]))
    return node_ids


def check_json_parse() -> CheckResult:
    errors: list[str] = []
    loaded: list[str] = []
    for name in INDEX_FILES:
        path = KNOWLEDGE_DIR / name
        if not path.is_file():
            errors.append(f"missing file: knowledge/{name}")
            continue
        try:
            _load_json(path)
            loaded.append(name)
        except json.JSONDecodeError as exc:
            errors.append(f"knowledge/{name}: JSON parse error at line {exc.lineno}: {exc.msg}")
    passed = not errors
    detail = f"parsed {len(loaded)}/{len(INDEX_FILES)} index files"
    return CheckResult("json_parse", passed, detail, errors)


def check_indexed_paths_exist() -> CheckResult:
    errors: list[str] = []
    paths: set[str] = set()
    for name in INDEX_FILES:
        path = KNOWLEDGE_DIR / name
        if not path.is_file():
            continue
        try:
            data = _load_json(path)
        except json.JSONDecodeError:
            continue
        _collect_paths(data, paths)
    missing = sorted(p for p in paths if not (REPO_ROOT / p).is_file())
    for p in missing[:50]:
        errors.append(f"missing path: {p}")
    if len(missing) > 50:
        errors.append(f"... and {len(missing) - 50} more missing paths")
    passed = not missing
    detail = f"checked {len(paths)} indexed paths; missing {len(missing)}"
    return CheckResult("indexed_paths_exist", passed, detail, errors)


def check_graph_neighbors_resolve() -> CheckResult:
    errors: list[str] = []
    graph_neighbors_path = KNOWLEDGE_DIR / "graph_neighbors.json"
    graph_path = KNOWLEDGE_DIR / "graph.json"
    if not graph_neighbors_path.is_file():
        return CheckResult(
            "graph_neighbors_resolve",
            False,
            "graph_neighbors.json not present",
            ["missing knowledge/graph_neighbors.json"],
        )
    try:
        graph_neighbors = _load_json(graph_neighbors_path)
    except json.JSONDecodeError as exc:
        return CheckResult(
            "graph_neighbors_resolve",
            False,
            "graph_neighbors.json invalid",
            [str(exc)],
        )
    graph_json = None
    if graph_path.is_file():
        try:
            graph_json = _load_json(graph_path)
        except json.JSONDecodeError:
            pass
    node_ids = _graph_node_ids(graph_neighbors, graph_json)
    referenced = _neighbor_ids(graph_neighbors)
    search_path = KNOWLEDGE_DIR / "search_index.json"
    if search_path.is_file():
        try:
            referenced |= _neighbor_ids(_load_json(search_path))
        except json.JSONDecodeError:
            pass
    unresolved = sorted(r for r in referenced if r not in node_ids)
    for node_id in unresolved[:50]:
        errors.append(f"unresolved neighbor id: {node_id}")
    if len(unresolved) > 50:
        errors.append(f"... and {len(unresolved) - 50} more unresolved ids")
    passed = not unresolved
    detail = f"nodes={len(node_ids)} referenced_neighbors={len(referenced)} unresolved={len(unresolved)}"
    return CheckResult("graph_neighbors_resolve", passed, detail, errors)


def _parse_readme_counts(text: str) -> dict[str, int]:
    mapping = {
        "search_records": r"Search records:\s*(\d+)",
        "domains": r"Domains:\s*(\d+)",
        "sensitivities": r"Sensitivities:\s*(\d+)",
        "types": r"Types:\s*(\d+)",
        "graph_neighbor_nodes": r"Graph neighbor nodes:\s*(\d+)",
        "graph_edges": r"Graph edges:\s*(\d+)",
    }
    counts: dict[str, int] = {}
    for key, pattern in mapping.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            counts[key] = int(match.group(1))
    return counts


def _summary_counts(summary: dict[str, Any]) -> dict[str, int]:
    aliases = {
        "search_records": (
            "search_records",
            "search_record_count",
            "search_records_count",
            "records",
        ),
        "domains": ("domains", "domain_count", "domains_count"),
        "sensitivities": ("sensitivities", "sensitivity_count", "sensitivities_count"),
        "types": ("types", "type_count", "types_count"),
        "graph_neighbor_nodes": (
            "graph_neighbor_nodes",
            "graph_neighbor_node_count",
            "neighbor_nodes",
            "nodes",
        ),
        "graph_edges": ("graph_edges", "graph_edge_count", "edges"),
    }
    counts: dict[str, int] = {}
    for canonical, keys in aliases.items():
        for key in keys:
            if key in summary and isinstance(summary[key], int):
                counts[canonical] = summary[key]
                break
    counts_obj = summary.get("counts")
    if isinstance(counts_obj, dict):
        for canonical, keys in aliases.items():
            if canonical in counts:
                continue
            for key in keys:
                if key in counts_obj and isinstance(counts_obj[key], int):
                    counts[canonical] = counts_obj[key]
                    break
    return counts


def check_readme_index_consistency() -> CheckResult:
    errors: list[str] = []
    if not README_PATH.is_file():
        return CheckResult(
            "readme_index_consistency",
            False,
            "README missing",
            [f"missing {README_PATH.relative_to(REPO_ROOT)}"],
        )
    readme_counts = _parse_readme_counts(README_PATH.read_text(encoding="utf-8"))
    summary_path = KNOWLEDGE_DIR / "retrieval_index_summary.json"
    if not summary_path.is_file():
        return CheckResult(
            "readme_index_consistency",
            False,
            "summary file missing",
            ["missing knowledge/retrieval_index_summary.json"],
        )
    try:
        summary = _load_json(summary_path)
    except json.JSONDecodeError as exc:
        return CheckResult(
            "readme_index_consistency",
            False,
            "summary JSON invalid",
            [str(exc)],
        )
    if not isinstance(summary, dict):
        return CheckResult(
            "readme_index_consistency",
            False,
            "summary must be a JSON object",
            ["retrieval_index_summary.json root must be object"],
        )
    summary_counts = _summary_counts(summary)
    for key, readme_value in readme_counts.items():
        summary_value = summary_counts.get(key)
        if summary_value is None:
            errors.append(f"summary missing count for {key} (README={readme_value})")
        elif summary_value != readme_value:
            errors.append(f"count mismatch for {key}: README={readme_value} summary={summary_value}")
    for key in readme_counts:
        if key not in summary_counts:
            continue
    passed = not errors
    detail = f"compared {len(readme_counts)} README metrics to summary"
    return CheckResult("readme_index_consistency", passed, detail, errors)


def validate(import_source: str | None = None) -> ValidationReport:
    checks = [
        check_json_parse(),
        check_indexed_paths_exist(),
        check_graph_neighbors_resolve(),
        check_readme_index_consistency(),
    ]
    all_pass = all(c.passed for c in checks)
    status = "PASS" if all_pass else "FAIL"
    summary: dict[str, Any] = {"checks_passed": sum(1 for c in checks if c.passed), "checks_total": len(checks)}
    summary_path = KNOWLEDGE_DIR / "retrieval_index_summary.json"
    if summary_path.is_file():
        try:
            summary["index_summary"] = _load_json(summary_path)
        except json.JSONDecodeError:
            pass
    return ValidationReport(
        status=status,
        validated_at=datetime.now(timezone.utc).isoformat(),
        branch="vault/hub-ready-v0",
        import_source=import_source,
        checks=checks,
        summary=summary,
    )


def write_report(report: ValidationReport) -> Path:
    out = KNOWLEDGE_DIR / "retrieval_validation_report.json"
    payload = {
        "status": report.status,
        "validated_at": report.validated_at,
        "branch": report.branch,
        "import_source": report.import_source,
        "summary": report.summary,
        "checks": [asdict(c) for c in report.checks],
    }
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return out


def import_zip(zip_path: Path, dry_run: bool = False) -> list[str]:
    if not zip_path.is_file():
        raise FileNotFoundError(f"zip not found: {zip_path}")
    imported: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        members = [m for m in zf.namelist() if m.endswith(".json") and not m.endswith("/")]
        if not members:
            raise ValueError(f"no JSON files in zip: {zip_path}")
        for member in members:
            name = Path(member).name
            if name not in INDEX_FILES and name != "retrieval_validation_report.json":
                continue
            dest = KNOWLEDGE_DIR / name
            if dry_run:
                imported.append(f"would write knowledge/{name} <= {member}")
                continue
            KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, dest.open("wb") as dst:
                shutil.copyfileobj(src, dst)
            imported.append(f"knowledge/{name}")
    return imported


def _write_blocked_import_report(searched: list[str]) -> Path:
    report = ValidationReport(
        status="IMPORT_BLOCKED",
        validated_at=datetime.now(timezone.utc).isoformat(),
        branch="vault/hub-ready-v0",
        import_source=None,
        checks=[
            CheckResult(
                "import_zip_present",
                False,
                "FATHIYA_RETRIEVAL_INDEXES_v0.zip not found in workspace",
                [f"searched: {p}" for p in searched],
            )
        ],
        summary={
            "reason": "Archive not available in cloud agent workspace; upload zip to repo root and re-run import.",
            "expected_archive": "FATHIYA_RETRIEVAL_INDEXES_v0.zip",
            "expected_outputs": [f"knowledge/{name}" for name in INDEX_FILES],
        },
    )
    return write_report(report)


def cmd_import(args: argparse.Namespace) -> int:
    zip_path = Path(args.zip).resolve() if args.zip else None
    if zip_path is None:
        zip_path = next((p for p in ZIP_CANDIDATES if p.is_file()), None)
    if zip_path is None:
        searched = [str(p.relative_to(REPO_ROOT)) for p in ZIP_CANDIDATES]
        out = _write_blocked_import_report(searched)
        print("Error: FATHIYA_RETRIEVAL_INDEXES_v0.zip not found.", file=sys.stderr)
        print("  Place the archive at repo root or pass --zip <path>", file=sys.stderr)
        print("  Example: python knowledge/retrieval/fathiya_retrieval.py import --zip ./FATHIYA_RETRIEVAL_INDEXES_v0.zip", file=sys.stderr)
        print(f"blocked report: {out.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 2
    try:
        imported = import_zip(zip_path, dry_run=args.dry_run)
    except (OSError, zipfile.BadZipFile, ValueError) as exc:
        print(f"Error: import failed: {exc}", file=sys.stderr)
        return 1
    if args.dry_run:
        for line in imported:
            print(line)
        return 0
    report = validate(import_source=str(zip_path))
    out = write_report(report)
    print(f"imported {len(imported)} files from {zip_path}")
    for line in imported:
        print(f"  {line}")
    print(f"validation: {report.status}")
    print(f"report: {out.relative_to(REPO_ROOT)}")
    return 0 if report.passed else 1


def cmd_validate(args: argparse.Namespace) -> int:
    report = validate(import_source=args.import_source)
    out = write_report(report)
    print(f"validation: {report.status}")
    for check in report.checks:
        mark = "ok" if check.passed else "FAIL"
        print(f"  [{mark}] {check.name}: {check.detail}")
        for err in check.errors[:5]:
            print(f"        - {err}")
        if len(check.errors) > 5:
            print(f"        - ... {len(check.errors) - 5} more")
    print(f"report: {out.relative_to(REPO_ROOT)}")
    return 0 if report.passed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import and validate FATHIYA retrieval indexes under knowledge/.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Extract index JSON from FATHIYA_RETRIEVAL_INDEXES_v0.zip")
    p_import.add_argument("--zip", help="Path to FATHIYA_RETRIEVAL_INDEXES_v0.zip")
    p_import.add_argument("--dry-run", action="store_true", help="List files without writing")
    p_import.set_defaults(func=cmd_import)

    p_validate = sub.add_parser("validate", help="Run JSON/path/graph/README validation checks")
    p_validate.add_argument("--import-source", help="Record zip path in validation report")
    p_validate.set_defaults(func=cmd_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
