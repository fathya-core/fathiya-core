#!/usr/bin/env python3
"""Import and validate FATHIYA retrieval index artifacts."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ARCHIVE_NAME = "FATHIYA_RETRIEVAL_INDEXES_v0.zip"
REQUIRED_INDEX_FILES = (
    "search_index.json",
    "domain_index.json",
    "sensitivity_index.json",
    "type_index.json",
    "graph_neighbors.json",
)
DERIVED_FILES = (
    "retrieval_index_summary.json",
    "retrieval_validation_report.json",
)
TRACKED_JSON_FILES = REQUIRED_INDEX_FILES + DERIVED_FILES


@dataclass(frozen=True)
class ValidationResult:
    status: str
    json_files_parsed: int
    records_created: int
    missing_paths: list[str]
    duplicate_ids: list[str]
    empty_titles: list[str]
    graph_missing_refs: list[str]
    readme_mismatches: list[str]
    summary_mismatches: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root_from(script_path: Path) -> Path:
    return script_path.resolve().parents[2]


def default_paths(repo_root: Path) -> dict[str, Path]:
    knowledge_dir = repo_root / "knowledge"
    retrieval_dir = knowledge_dir / "retrieval"
    artifact_dir = retrieval_dir / "artifacts" / "FATHIYA_RETRIEVAL_INDEXES_v0"
    return {
        "repo_root": repo_root,
        "knowledge_dir": knowledge_dir,
        "retrieval_dir": retrieval_dir,
        "canonical_zip": retrieval_dir / ARCHIVE_NAME,
        "manifest": artifact_dir / "manifest.json",
        "readme": retrieval_dir / "README_RETRIEVAL_INDEXES_v0.md",
        "summary": knowledge_dir / "retrieval_index_summary.json",
        "report": knowledge_dir / "retrieval_validation_report.json",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import or validate FATHIYA retrieval indexes."
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="import",
        choices=("import", "validate"),
        help="import artifacts or validate existing indexes",
    )
    parser.add_argument(
        "--source",
        choices=("auto", "zip", "chunks"),
        default="auto",
        help="prefer a direct zip or chunked manifest when importing",
    )
    parser.add_argument(
        "--zip",
        dest="zip_path",
        help="path to a direct retrieval archive zip",
    )
    parser.add_argument(
        "--manifest",
        dest="manifest_path",
        help="path to a chunk manifest json file",
    )
    parser.add_argument(
        "--repo-root",
        dest="repo_root",
        help="override the repository root used for validation",
    )
    return parser.parse_args()


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=True)
        handle.write("\n")


def normalize_repo_path(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().replace("\\", "/")
    return normalized.lstrip("./")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manifest_value(manifest: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    for path in paths:
        current: Any = manifest
        for key in path:
            if not isinstance(current, dict) or key not in current:
                current = None
                break
            current = current[key]
        if current is not None:
            return current
    return None


def blocked_steps(paths: dict[str, Path]) -> list[str]:
    return [
        (
            "Place a direct archive at "
            f"{paths['canonical_zip'].relative_to(paths['repo_root'])} "
            "and rerun `python3 knowledge/retrieval/fathiya_retrieval.py import`."
        ),
        (
            "Or place manifest.json plus chunk_*.b64 files under "
            "knowledge/retrieval/artifacts/FATHIYA_RETRIEVAL_INDEXES_v0/ "
            "and rerun `python3 knowledge/retrieval/fathiya_retrieval.py import --source chunks`."
        ),
    ]


def write_blocked_report(
    report_path: Path,
    paths: dict[str, Path],
    zip_candidate: Path,
    manifest_candidate: Path,
) -> None:
    write_json(
        report_path,
        {
            "schema_version": "FATHIYA_RETRIEVAL_VALIDATION_v0",
            "validated_at": utc_now(),
            "status": "IMPORT_BLOCKED",
            "json_files_parsed": 0,
            "records_created": 0,
            "missing_paths": [],
            "duplicate_ids": [],
            "empty_titles": [],
            "graph_missing_refs": [],
            "readme_mismatches": [],
            "summary_mismatches": [],
            "checked_sources": {
                "zip": str(zip_candidate),
                "manifest": str(manifest_candidate),
            },
            "next_steps": blocked_steps(paths),
        },
    )


def normalize_chunk_entries(manifest: dict[str, Any], manifest_path: Path) -> list[dict[str, Any]]:
    chunks = manifest.get("chunks")
    if isinstance(chunks, list) and chunks:
        normalized: list[dict[str, Any]] = []
        for index, entry in enumerate(chunks):
            if isinstance(entry, str):
                normalized.append({"path": entry, "index": index})
                continue
            if isinstance(entry, dict):
                chunk_path = (
                    entry.get("path")
                    or entry.get("file")
                    or entry.get("filename")
                    or entry.get("name")
                )
                if not chunk_path:
                    raise ValueError("Manifest chunk entry is missing a filename.")
                normalized.append(
                    {
                        "path": chunk_path,
                        "index": entry.get("index", index),
                        "sha256": entry.get("sha256"),
                    }
                )
                continue
            raise ValueError("Manifest chunks must be strings or objects.")
        return sorted(normalized, key=lambda item: int(item.get("index", 0)))

    chunk_paths = sorted(manifest_path.parent.glob("chunk_*.b64"))
    if not chunk_paths:
        raise ValueError("No chunk files were found next to manifest.json.")
    return [{"path": chunk.name, "index": idx} for idx, chunk in enumerate(chunk_paths)]


def reconstruct_zip_from_chunks(manifest_path: Path, output_zip: Path) -> tuple[Path, dict[str, Any]]:
    manifest = read_json(manifest_path)
    expected_sha = manifest_value(
        manifest,
        ("sha256",),
        ("archive", "sha256"),
        ("output", "sha256"),
    )
    expected_size = manifest_value(
        manifest,
        ("size_bytes",),
        ("archive", "size_bytes"),
        ("output", "size_bytes"),
    )
    chunks = normalize_chunk_entries(manifest, manifest_path)

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with output_zip.open("wb") as destination:
        for entry in chunks:
            chunk_path = manifest_path.parent / str(entry["path"])
            if not chunk_path.exists():
                raise FileNotFoundError(f"Missing chunk file: {chunk_path}")
            encoded = chunk_path.read_text(encoding="utf-8")
            decoded = base64.b64decode("".join(encoded.split()), validate=True)
            chunk_sha = entry.get("sha256")
            if chunk_sha:
                actual_chunk_sha = hashlib.sha256(decoded).hexdigest()
                if actual_chunk_sha != chunk_sha:
                    raise ValueError(
                        f"Chunk sha256 mismatch for {chunk_path.name}: "
                        f"expected {chunk_sha}, got {actual_chunk_sha}"
                    )
            destination.write(decoded)

    actual_sha = sha256_file(output_zip)
    if expected_sha and actual_sha != expected_sha:
        raise ValueError(
            f"Archive sha256 mismatch: expected {expected_sha}, got {actual_sha}"
        )

    if expected_size is not None and output_zip.stat().st_size != int(expected_size):
        raise ValueError(
            f"Archive size mismatch: expected {expected_size}, got {output_zip.stat().st_size}"
        )

    return output_zip, {
        "manifest": str(manifest_path),
        "chunk_count": len(chunks),
        "sha256": actual_sha,
        "size_bytes": output_zip.stat().st_size,
    }


def stage_direct_zip(source_zip: Path, canonical_zip: Path) -> tuple[Path, dict[str, Any]]:
    canonical_zip.parent.mkdir(parents=True, exist_ok=True)
    if source_zip.resolve() != canonical_zip.resolve():
        shutil.copyfile(source_zip, canonical_zip)
    return canonical_zip, {
        "source_zip": str(source_zip),
        "sha256": sha256_file(canonical_zip),
        "size_bytes": canonical_zip.stat().st_size,
    }


def import_index_zip(zip_path: Path, knowledge_dir: Path) -> list[str]:
    extracted: list[str] = []
    supported = set(TRACKED_JSON_FILES)
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            member_name = Path(member.filename).name
            if member_name not in supported:
                continue
            target_path = knowledge_dir / member_name
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target_path.open("wb") as destination:
                shutil.copyfileobj(source, destination)
            extracted.append(str(target_path))

    if not extracted:
        raise ValueError("No retrieval index JSON files were found in the archive.")
    return sorted(extracted)


def extract_records(search_index: Any) -> list[dict[str, Any]]:
    if isinstance(search_index, list):
        return [item for item in search_index if isinstance(item, dict)]
    if isinstance(search_index, dict):
        for key in ("records", "items", "entries", "documents", "search_records"):
            value = search_index.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        if all(isinstance(value, dict) for value in search_index.values()):
            return [value for value in search_index.values() if isinstance(value, dict)]
    raise ValueError("search_index.json must be a list or an object with record lists.")


def extract_group_values(group_index: Any) -> dict[str, Any]:
    if isinstance(group_index, dict):
        return group_index
    raise ValueError("Grouped indexes must be JSON objects.")


def count_group_members(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("records", "items", "entries", "paths", "ids"):
            nested = value.get(key)
            if isinstance(nested, list):
                return len(nested)
        return len(value)
    return 0


def top_group_counts(group_index: dict[str, Any]) -> list[list[Any]]:
    counts = sorted(
        ((key, count_group_members(value)) for key, value in group_index.items()),
        key=lambda item: (-item[1], item[0]),
    )
    return [[key, value] for key, value in counts[:20]]


def iter_reference_values(payload: Any) -> Iterable[str]:
    if isinstance(payload, str):
        yield payload
        return
    if isinstance(payload, list):
        for item in payload:
            yield from iter_reference_values(item)
        return
    if isinstance(payload, dict):
        for key in ("neighbors", "related_nodes", "items", "entries", "records", "paths", "ids"):
            if key in payload:
                yield from iter_reference_values(payload[key])
        for key in ("id", "path", "node", "target", "neighbor"):
            value = payload.get(key)
            if isinstance(value, str):
                yield value


def parse_readme(readme_path: Path) -> dict[str, Any]:
    lines = readme_path.read_text(encoding="utf-8").splitlines()
    current_section = ""
    counts: dict[str, int] = {}
    generated_files: list[str] = []
    validation_value: str | None = None

    for line in lines:
        if line.startswith("## "):
            current_section = line[3:].strip().lower()
            continue
        if current_section == "validation" and line.strip():
            validation_value = line.strip()
        elif current_section == "counts" and line.startswith("- "):
            body = line[2:]
            if ":" not in body:
                continue
            label, raw_value = body.split(":", 1)
            slug = label.strip().lower().replace(" ", "_")
            try:
                counts[slug] = int(raw_value.strip())
            except ValueError:
                continue
        elif current_section == "generated index files" and line.startswith("- "):
            generated_files.append(line[2:].strip().strip("`"))

    return {
        "counts": counts,
        "generated_files": generated_files,
        "validation": validation_value,
    }


def build_summary_payload(
    source_archive: str,
    knowledge_dir: Path,
    search_records: list[dict[str, Any]],
    domain_index: dict[str, Any],
    sensitivity_index: dict[str, Any],
    type_index: dict[str, Any],
    graph_neighbors: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "FATHIYA_RETRIEVAL_INDEX_SUMMARY_v0",
        "created_at": utc_now(),
        "source_archive": source_archive,
        "counts": {
            "search_records": len(search_records),
            "domains": len(domain_index),
            "sensitivities": len(sensitivity_index),
            "types": len(type_index),
            "graph_neighbor_nodes": len(graph_neighbors),
            "graph_edges": sum(
                len(list(iter_reference_values(value))) for value in graph_neighbors.values()
            ),
        },
        "top_domains": top_group_counts(domain_index),
        "top_sensitivities": top_group_counts(sensitivity_index),
        "top_types": top_group_counts(type_index),
        "files": [f"knowledge/{name}" for name in REQUIRED_INDEX_FILES],
    }


def validate_indexes(paths: dict[str, Path], source_archive: str) -> tuple[ValidationResult, dict[str, Any]]:
    search_index = read_json(paths["knowledge_dir"] / "search_index.json")
    domain_index = extract_group_values(read_json(paths["knowledge_dir"] / "domain_index.json"))
    sensitivity_index = extract_group_values(
        read_json(paths["knowledge_dir"] / "sensitivity_index.json")
    )
    type_index = extract_group_values(read_json(paths["knowledge_dir"] / "type_index.json"))
    graph_neighbors = extract_group_values(
        read_json(paths["knowledge_dir"] / "graph_neighbors.json")
    )

    search_records = extract_records(search_index)
    ids_seen: set[str] = set()
    duplicate_ids: list[str] = []
    empty_titles: list[str] = []
    missing_paths: list[str] = []
    known_refs: set[str] = set()

    for record in search_records:
        record_id = str(record.get("id", "")).strip()
        if record_id:
            if record_id in ids_seen and record_id not in duplicate_ids:
                duplicate_ids.append(record_id)
            ids_seen.add(record_id)
            known_refs.add(record_id)

        title = str(record.get("title", "")).strip()
        if not title:
            empty_titles.append(record_id or normalize_repo_path(str(record.get("path", ""))) or "<unknown>")

        record_path = normalize_repo_path(str(record.get("path", "")))
        if record_path:
            known_refs.add(record_path)
            if not (paths["repo_root"] / record_path).exists():
                missing_paths.append(record_path)

    for node, neighbors in graph_neighbors.items():
        node_ref = normalize_repo_path(str(node))
        if node_ref:
            known_refs.add(node_ref)

    graph_missing_refs: list[str] = []
    for neighbors in graph_neighbors.values():
        for neighbor in iter_reference_values(neighbors):
            normalized = normalize_repo_path(neighbor)
            if normalized and normalized not in known_refs and normalized not in graph_missing_refs:
                graph_missing_refs.append(normalized)

    summary_payload = build_summary_payload(
        source_archive=source_archive,
        knowledge_dir=paths["knowledge_dir"],
        search_records=search_records,
        domain_index=domain_index,
        sensitivity_index=sensitivity_index,
        type_index=type_index,
        graph_neighbors=graph_neighbors,
    )

    readme_data = parse_readme(paths["readme"])
    actual_files = set(summary_payload["files"])
    readme_mismatches: list[str] = []
    if set(readme_data["generated_files"]) != actual_files | {
        "knowledge/retrieval_index_summary.json",
        "knowledge/retrieval_validation_report.json",
    }:
        readme_mismatches.append("README generated file list does not match imported index files.")

    expected_readme_counts = {
        "search_records": summary_payload["counts"]["search_records"],
        "domains": summary_payload["counts"]["domains"],
        "sensitivities": summary_payload["counts"]["sensitivities"],
        "types": summary_payload["counts"]["types"],
        "graph_neighbor_nodes": summary_payload["counts"]["graph_neighbor_nodes"],
        "graph_edges": summary_payload["counts"]["graph_edges"],
    }
    for key, actual_value in expected_readme_counts.items():
        readme_value = readme_data["counts"].get(key)
        if readme_value != actual_value:
            readme_mismatches.append(
                f"README count mismatch for {key}: expected {actual_value}, found {readme_value}."
            )
    if readme_data["validation"] and readme_data["validation"] != "PASS":
        readme_mismatches.append(
            f"README validation section must be PASS after a clean import, found {readme_data['validation']}."
        )

    summary_path = paths["summary"]
    summary_mismatches: list[str] = []
    if summary_path.exists():
        existing_summary = read_json(summary_path)
        if existing_summary.get("files") not in (None, summary_payload["files"]):
            summary_mismatches.append("Existing retrieval_index_summary.json file list is inconsistent.")
        if existing_summary.get("counts") not in (None, summary_payload["counts"]):
            summary_mismatches.append("Existing retrieval_index_summary.json counts are inconsistent.")

    status = "PASS"
    if any(
        (
            missing_paths,
            duplicate_ids,
            empty_titles,
            graph_missing_refs,
            readme_mismatches,
            summary_mismatches,
        )
    ):
        status = "FAIL"

    result = ValidationResult(
        status=status,
        json_files_parsed=len(search_records) + 1,
        records_created=len(search_records),
        missing_paths=sorted(missing_paths),
        duplicate_ids=sorted(duplicate_ids),
        empty_titles=sorted(empty_titles),
        graph_missing_refs=sorted(graph_missing_refs),
        readme_mismatches=readme_mismatches,
        summary_mismatches=summary_mismatches,
    )
    return result, summary_payload


def write_validation_report(
    report_path: Path,
    source_mode: str,
    source_archive: str,
    source_details: dict[str, Any],
    validation: ValidationResult,
) -> None:
    payload = {
        "schema_version": "FATHIYA_RETRIEVAL_VALIDATION_v0",
        "validated_at": utc_now(),
        "status": validation.status,
        "source_mode": source_mode,
        "source_archive": source_archive,
        "source_details": source_details,
        "json_files_parsed": validation.json_files_parsed,
        "records_created": validation.records_created,
        "missing_paths": validation.missing_paths,
        "duplicate_ids": validation.duplicate_ids,
        "empty_titles": validation.empty_titles,
        "graph_missing_refs": validation.graph_missing_refs,
        "readme_mismatches": validation.readme_mismatches,
        "summary_mismatches": validation.summary_mismatches,
    }
    if validation.status != "PASS":
        payload["next_steps"] = [
            "Fix the validation mismatches listed above and rerun `python3 knowledge/retrieval/fathiya_retrieval.py validate`.",
        ]
    write_json(report_path, payload)


def resolve_import_source(
    args: argparse.Namespace, paths: dict[str, Path]
) -> tuple[str | None, Path | None, Path | None]:
    requested_zip = Path(args.zip_path).expanduser().resolve() if args.zip_path else paths["canonical_zip"]
    requested_manifest = (
        Path(args.manifest_path).expanduser().resolve() if args.manifest_path else paths["manifest"]
    )

    if args.source == "zip":
        return "zip", requested_zip, requested_manifest
    if args.source == "chunks":
        return "chunks", requested_zip, requested_manifest

    if requested_zip.exists():
        return "zip", requested_zip, requested_manifest
    if requested_manifest.exists():
        return "chunks", requested_zip, requested_manifest
    return None, requested_zip, requested_manifest


def ensure_required_indexes(paths: dict[str, Path]) -> None:
    missing = [
        str(paths["knowledge_dir"] / filename)
        for filename in REQUIRED_INDEX_FILES
        if not (paths["knowledge_dir"] / filename).exists()
    ]
    if missing:
        raise FileNotFoundError(f"Missing required index files: {', '.join(missing)}")


def run_import(args: argparse.Namespace, paths: dict[str, Path]) -> int:
    source_mode, zip_candidate, manifest_candidate = resolve_import_source(args, paths)
    if source_mode is None or zip_candidate is None or manifest_candidate is None:
        write_blocked_report(paths["report"], paths, paths["canonical_zip"], paths["manifest"])
        print("IMPORT_BLOCKED: retrieval archive zip or chunk manifest is missing.")
        return 2

    if source_mode == "zip":
        if not zip_candidate.exists():
            write_blocked_report(paths["report"], paths, zip_candidate, manifest_candidate)
            print(f"IMPORT_BLOCKED: direct zip not found at {zip_candidate}.")
            return 2
        canonical_zip, source_details = stage_direct_zip(zip_candidate, paths["canonical_zip"])
        source_archive = canonical_zip.name
    else:
        if not manifest_candidate.exists():
            write_blocked_report(paths["report"], paths, zip_candidate, manifest_candidate)
            print(f"IMPORT_BLOCKED: chunk manifest not found at {manifest_candidate}.")
            return 2
        canonical_zip, source_details = reconstruct_zip_from_chunks(
            manifest_candidate, paths["canonical_zip"]
        )
        source_archive = canonical_zip.name

    extracted = import_index_zip(canonical_zip, paths["knowledge_dir"])
    validation, summary_payload = validate_indexes(paths, source_archive=source_archive)
    summary_payload["files"] = sorted(
        {f"knowledge/{Path(path).name}" for path in extracted if Path(path).suffix == ".json"}
        & {f"knowledge/{name}" for name in REQUIRED_INDEX_FILES}
    )
    write_json(paths["summary"], summary_payload)
    write_validation_report(
        report_path=paths["report"],
        source_mode=source_mode,
        source_archive=source_archive,
        source_details=source_details,
        validation=validation,
    )
    print(validation.status)
    return 0 if validation.status == "PASS" else 1


def run_validate(paths: dict[str, Path]) -> int:
    ensure_required_indexes(paths)
    validation, summary_payload = validate_indexes(paths, source_archive=ARCHIVE_NAME)
    write_json(paths["summary"], summary_payload)
    write_validation_report(
        report_path=paths["report"],
        source_mode="validate",
        source_archive=ARCHIVE_NAME,
        source_details={},
        validation=validation,
    )
    print(validation.status)
    return 0 if validation.status == "PASS" else 1


def main() -> int:
    args = parse_args()
    repo_root = (
        Path(args.repo_root).expanduser().resolve()
        if args.repo_root
        else repo_root_from(Path(__file__))
    )
    paths = default_paths(repo_root)

    try:
        if args.command == "validate":
            return run_validate(paths)
        return run_import(args, paths)
    except Exception as exc:  # noqa: BLE001 - CLI should emit the root cause.
        write_json(
            paths["report"],
            {
                "schema_version": "FATHIYA_RETRIEVAL_VALIDATION_v0",
                "validated_at": utc_now(),
                "status": "FAIL",
                "json_files_parsed": 0,
                "records_created": 0,
                "missing_paths": [],
                "duplicate_ids": [],
                "empty_titles": [],
                "graph_missing_refs": [],
                "readme_mismatches": [],
                "summary_mismatches": [],
                "error": str(exc),
                "next_steps": [
                    "Fix the import artifact or JSON validation error above and rerun the retrieval importer.",
                ],
            },
        )
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
