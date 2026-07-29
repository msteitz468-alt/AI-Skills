#!/usr/bin/env python3
"""Validate isolated subagent records without modifying the shared manifest."""
from __future__ import annotations

import argparse
from pathlib import Path

from policy_common import load_json, resolve_source_path, sha256_file
from stage_document import validate_shape


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--shards-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = load_json(args.manifest.resolve())
    entries = {entry["document_id"]: entry for entry in manifest.get("files", [])}
    pending = {document_id for document_id, entry in entries.items() if entry.get("status") == "pending"}
    assigned: dict[str, dict] = {}
    errors: list[str] = []

    for assignment_path in sorted(args.shards_dir.resolve().glob("*/assignment.json")):
        assignment = load_json(assignment_path)
        for item in assignment.get("documents", []):
            document_id = item.get("document_id")
            if document_id in assigned:
                errors.append(f"{document_id}: assigned more than once")
                continue
            assigned[document_id] = item
            entry = entries.get(document_id)
            if entry is None:
                errors.append(f"{document_id}: not present in manifest")
                continue
            for key in ("exact_filename", "relative_path", "source_path", "sha256"):
                if item.get(key) != entry.get(key):
                    errors.append(f"{document_id}: assignment {key} does not match manifest")
            record_path = Path(str(item.get("output_record", "")))
            if not record_path.is_file():
                errors.append(f"{document_id}: output record is missing")
                continue
            record = load_json(record_path)
            if record.get("document_id") != document_id:
                errors.append(f"{document_id}: record ID mismatch")
            source_path = resolve_source_path(entry.get("source_path"), entry.get("sha256"))
            resolved_name = source_path.name if source_path is not None else entry.get("exact_filename")
            source = record.get("source", {})
            accepted_names = {entry.get("exact_filename"), resolved_name}
            if not isinstance(source, dict) or source.get("exact_filename") not in accepted_names or source.get("relative_path") != entry.get("relative_path"):
                errors.append(f"{document_id}: record source identity mismatch")
            errors.extend(f"{document_id}: {error}" for error in validate_shape(record))
            if source_path is None or sha256_file(source_path) != entry.get("sha256"):
                errors.append(f"{document_id}: source is missing or its hash changed")

    missing_assignments = sorted(pending - set(assigned))
    unexpected_assignments = sorted(set(assigned) - pending)
    if missing_assignments:
        errors.append("Pending IDs missing assignments: " + ", ".join(missing_assignments))
    if unexpected_assignments:
        errors.append("Assignments include non-pending IDs: " + ", ".join(unexpected_assignments))
    if errors:
        print("SHARD VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("SHARD VALIDATION PASSED")
    print(f"Validated records: {len(assigned)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
