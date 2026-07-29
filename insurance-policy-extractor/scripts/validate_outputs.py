#!/usr/bin/env python3
"""Validate calendar-year insurance JSON outputs against the extraction manifest."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

from policy_common import load_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def all_annual_records(data: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(data.get("documents"), list):
        return data["documents"]

    # Transition tolerance for annual files built by older versions of this
    # script. New outputs must use top-level documents[].
    records: list[dict[str, Any]] = []
    for key in ("policies", "endorsements", "other_documents"):
        value = data.get(key)
        if not isinstance(value, list):
            raise ValueError("Annual output must include a documents array")
        records.extend(value)
    return records


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    errors: list[str] = []

    manifest = load_json(manifest_path)
    entries = manifest.get("files", [])
    if not isinstance(entries, list):
        errors.append("Manifest files field must be an array.")
        entries = []

    disallowed = [path.name for path in output_dir.iterdir() if path.is_file() and not re.fullmatch(r"\d{4}_Policies\.json", path.name)] if output_dir.exists() else []
    if disallowed:
        errors.append("Output directory may contain only calendar-year *_Policies.json files: " + ", ".join(sorted(disallowed)))

    expected: dict[str, int] = {}
    for entry in entries:
        document_id = entry.get("document_id")
        status = entry.get("status")
        year = entry.get("effective_year")
        if status in {"complete", "needs_review"}:
            if isinstance(year, int):
                expected[document_id] = year
            else:
                errors.append(f"{document_id}: terminal staged record has no integer effective_year for calendar-year output")

    found: dict[str, int] = {}
    records_by_id: dict[str, dict[str, Any]] = {}
    for path in sorted(output_dir.glob("*_Policies.json")):
        if not re.fullmatch(r"\d{4}_Policies\.json", path.name):
            continue
        try:
            year_from_name = int(path.name[:4])
            data = load_json(path)
            metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
            calendar_year = data.get("calendar_year", metadata.get("calendar_year"))
            if calendar_year != year_from_name:
                errors.append(f"{path.name}: calendar_year does not match filename")
            records = all_annual_records(data)
            document_count = data.get("document_count", metadata.get("document_count"))
            if document_count != len(records):
                errors.append(f"{path.name}: document_count does not equal the number of records")
            if "documents" not in data:
                errors.append(f"{path.name}: annual output must use top-level documents[] for handbook-compatible extraction")
            for record in records:
                document_id = record.get("document_id")
                if not document_id:
                    errors.append(f"{path.name}: record missing document_id")
                    continue
                if document_id in found:
                    errors.append(f"{document_id} appears in more than one annual output")
                found[document_id] = year_from_name
                records_by_id[document_id] = record
                if record.get("effective_year") != year_from_name:
                    errors.append(f"{document_id}: effective_year does not match {path.name}")
        except Exception as exc:
            errors.append(f"Unable to validate {path.name}: {exc}")

    for document_id, record in records_by_id.items():
        if record.get("document_type") != "endorsement":
            continue
        reference = record.get("base_policy_reference", {})
        matched_id = reference.get("matched_document_id", "Not specified") if isinstance(reference, dict) else "Not specified"
        base_record = records_by_id.get(matched_id)
        if base_record is None:
            errors.append(f"{document_id}: matched base policy {matched_id!r} is missing from calendar-year outputs")
            continue
        if record.get("effective_year") != base_record.get("effective_year"):
            errors.append(f"{document_id}: endorsement effective_year must equal matched base policy effective_year")
        if isinstance(reference, dict) and reference.get("base_policy_effective_date") != base_record.get("policy_effective_date"):
            errors.append(f"{document_id}: base_policy_effective_date does not match the staged base policy")

    for document_id, year in expected.items():
        if document_id not in found:
            errors.append(f"Expected staged document {document_id} is missing from {year}_Policies.json")
        elif found[document_id] != year:
            errors.append(f"{document_id} was assigned to {found[document_id]}, expected {year}")
    for document_id in found:
        if document_id not in expected:
            errors.append(f"Unexpected document {document_id} appears in annual outputs")

    nonterminal = [
        entry.get("document_id") for entry in entries
        if entry.get("status") in {"pending", "in_progress", "error"}
    ]
    if nonterminal:
        errors.append("Manifest still has nonterminal items: " + ", ".join(str(item) for item in nonterminal))

    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VALIDATION PASSED")
    print(f"Annual records validated: {len(found)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
