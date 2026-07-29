#!/usr/bin/env python3
"""Validate and atomically stage one extracted insurance document record."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from policy_common import (
    NOT_SPECIFIED,
    applicable_effective_date,
    append_review_flag,
    atomic_write_json,
    extract_year,
    load_json,
    normalize_policy_number,
    resolve_source_path,
    sha256_file,
    utc_now,
)

ALLOWED_DOCUMENT_TYPES = {
    "policy", "endorsement", "declaration", "quote", "binder", "proposal",
    "cancellation", "reinstatement", "audit", "notice", "other"
}
REQUIRED_KEYS = {
    "document_id", "source", "document_type", "document_name", "client", "named_insureds",
    "policy_number", "policy_type", "coverage_lines", "policy_effective_date",
    "policy_expiration_date", "endorsement_effective_date", "transaction_effective_date",
    "effective_year", "base_policy_reference", "broker_agency", "locations", "coverages",
    "premiums", "limits", "sublimits", "deductibles", "valuation_methods",
    "endorsements_exclusions", "exposures", "schedules", "source_notes", "review_flags", "extraction"
}
LIST_KEYS = {
    "named_insureds", "coverage_lines", "locations", "coverages", "premiums",
    "limits", "sublimits", "deductibles", "valuation_methods", "endorsements_exclusions",
    "exposures", "source_notes", "review_flags"
}
SCHEDULE_KEYS = {
    "locations", "properties", "vehicles", "equipment", "forms", "other"
}
COVERAGE_TERMS_DOCUMENT_TYPES = {
    "policy", "endorsement", "declaration", "quote", "binder", "proposal"
}
FORMS_REVIEW_FLAG = "MISSING_FORMS_ENDORSEMENTS_SCHEDULE"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--record", type=Path, required=True)
    return parser.parse_args()


def validate_shape(record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "endorsements_exclusions" not in record and "forms_endorsements_exclusions" in record:
        record["endorsements_exclusions"] = record.get("forms_endorsements_exclusions", [])
    missing = sorted(REQUIRED_KEYS - set(record))
    if missing:
        errors.append("Missing required keys: " + ", ".join(missing))
    if record.get("document_type") not in ALLOWED_DOCUMENT_TYPES:
        errors.append(f"Unsupported document_type: {record.get('document_type')!r}")
    if not isinstance(record.get("source"), dict):
        errors.append("source must be an object")
    if not isinstance(record.get("base_policy_reference"), dict):
        errors.append("base_policy_reference must be an object")
    if not isinstance(record.get("schedules"), dict):
        errors.append("schedules must be an object")
    else:
        missing_schedules = sorted(SCHEDULE_KEYS - set(record["schedules"]))
        if missing_schedules:
            errors.append("Missing schedule arrays: " + ", ".join(missing_schedules))
        for key in SCHEDULE_KEYS:
            if key in record["schedules"] and not isinstance(record["schedules"][key], list):
                errors.append(f"schedules.{key} must be an array")
    for key in LIST_KEYS:
        if key in record and not isinstance(record[key], list):
            errors.append(f"{key} must be an array")
    return errors




def populated_forms_rows(record: dict[str, Any]) -> list[Any]:
    rows: list[Any] = []
    endorsements = record.get("endorsements_exclusions")
    if isinstance(endorsements, list):
        rows.extend(endorsements)
    schedules = record.get("schedules")
    if isinstance(schedules, dict) and isinstance(schedules.get("forms"), list):
        rows.extend(schedules["forms"])
    return rows


def has_forms_review_explanation(record: dict[str, Any]) -> bool:
    flags = record.get("review_flags")
    if isinstance(flags, list) and any(isinstance(flag, dict) and flag.get("code") == FORMS_REVIEW_FLAG for flag in flags):
        return True
    notes = record.get("source_notes")
    if isinstance(notes, list):
        return any(isinstance(note, str) and "forms" in note.lower() and "endorsement" in note.lower() for note in notes)
    return False


def enforce_forms_schedule_gate(record: dict[str, Any]) -> None:
    if record.get("document_type") not in COVERAGE_TERMS_DOCUMENT_TYPES:
        return
    if populated_forms_rows(record):
        return
    if has_forms_review_explanation(record):
        append_review_flag(
            record,
            FORMS_REVIEW_FLAG,
            "The extraction did not capture a Schedule of Forms and Endorsements; source notes should identify the pages or sections checked.",
        )
        return
    append_review_flag(
        record,
        FORMS_REVIEW_FLAG,
        "No forms, endorsements, exclusions, notices, or advisory notices were captured. Recheck the source document's Schedule of Forms and Endorsements before treating the extraction as complete.",
    )


def find_entry(manifest: dict[str, Any], document_id: str) -> dict[str, Any] | None:
    for entry in manifest.get("files", []):
        if entry.get("document_id") == document_id:
            return entry
    return None


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    record_path = args.record.resolve()
    manifest = load_json(manifest_path)
    record = load_json(record_path)

    if not isinstance(record, dict):
        raise SystemExit("Record must contain one JSON object.")

    document_id = record.get("document_id")
    entry = find_entry(manifest, document_id)
    if entry is None:
        raise SystemExit(f"Document ID is not present in manifest: {document_id!r}")
    if entry.get("status") == "duplicate":
        raise SystemExit(f"Cannot stage duplicate manifest item: {document_id}")

    errors = validate_shape(record)
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    if source.get("relative_path") != entry.get("relative_path"):
        errors.append("source.relative_path does not match the manifest")

    source_path = resolve_source_path(entry.get("source_path"), entry.get("sha256"))
    if source_path is None:
        errors.append("manifest source_path is missing or no longer exists")
    elif sha256_file(source_path) != entry.get("sha256"):
        errors.append("source SHA-256 changed after inventory")

    if source_path is not None:
        resolved_name = source_path.name
        assigned_name = entry.get("exact_filename")
        if source.get("exact_filename") not in {assigned_name, resolved_name}:
            errors.append("source.exact_filename does not match the assigned or resolved source")
        source["exact_filename"] = resolved_name

    if errors:
        entry["status"] = "error"
        entry["last_error"] = "; ".join(errors)
        manifest["updated_at"] = utc_now()
        atomic_write_json(manifest_path, manifest)
        raise SystemExit("Record validation failed: " + "; ".join(errors))

    source["sha256"] = entry.get("sha256", NOT_SPECIFIED)
    record["source"] = source

    enforce_forms_schedule_gate(record)

    base_reference = record.get("base_policy_reference", {})
    grouping_date = applicable_effective_date(record)
    if record.get("document_type") == "endorsement":
        confidence = base_reference.get("match_confidence", "unmatched")
        matched_id = base_reference.get("matched_document_id", NOT_SPECIFIED)
        grouping_date = NOT_SPECIFIED
        if confidence in {"low", "unmatched"} or matched_id == NOT_SPECIFIED:
            append_review_flag(
                record,
                "UNMATCHED_ENDORSEMENT" if confidence == "unmatched" else "LOW_CONFIDENCE_POLICY_MATCH",
                "The endorsement does not have a high- or medium-confidence staged base-policy match.",
            )
        else:
            base_entry = find_entry(manifest, matched_id)
            staged_value = base_entry.get("staged_json") if base_entry else NOT_SPECIFIED
            staged_path = Path(staged_value) if isinstance(staged_value, str) and staged_value != NOT_SPECIFIED else None
            if staged_path is None or not staged_path.is_file():
                append_review_flag(
                    record,
                    "BASE_POLICY_NOT_STAGED",
                    "The matched base policy must be staged before the endorsement can be assigned to a calendar year.",
                )
            else:
                base_record = load_json(staged_path)
                grouping_date = base_record.get("policy_effective_date", NOT_SPECIFIED)
                base_reference["base_policy_effective_date"] = grouping_date

    year = extract_year(grouping_date)
    if year is None:
        record["effective_year"] = NOT_SPECIFIED
        append_review_flag(
            record,
            "MISSING_BASE_POLICY_EFFECTIVE_DATE" if record.get("document_type") == "endorsement" else "MISSING_EFFECTIVE_DATE",
            "The matched base policy effective date is missing or invalid." if record.get("document_type") == "endorsement" else "The applicable effective date is missing, incomplete, or not in YYYY-MM-DD format.",
        )
    else:
        record["effective_year"] = year
    extraction = record.setdefault("extraction", {})
    extraction["completed_at"] = extraction.get("completed_at") or utc_now()
    extraction["status"] = "needs_review" if record.get("review_flags") else "complete"

    work_dir = manifest_path.parent
    staged_path = work_dir / "documents" / f"{document_id}.json"
    atomic_write_json(staged_path, record)

    entry.update({
        "status": extraction["status"],
        "staged_json": str(staged_path),
        "document_type": record.get("document_type", NOT_SPECIFIED),
        "effective_year": record.get("effective_year", NOT_SPECIFIED),
        "policy_number": record.get("policy_number", NOT_SPECIFIED),
        "normalized_policy_number": normalize_policy_number(record.get("policy_number")),
        "parent_policy_id": base_reference.get("matched_document_id", NOT_SPECIFIED),
        "review_flags": record.get("review_flags", []),
        "last_error": NOT_SPECIFIED,
        "completed_at": utc_now(),
    })
    manifest["updated_at"] = utc_now()
    atomic_write_json(manifest_path, manifest)

    print(f"Staged: {staged_path}")
    print(f"Status: {entry['status']}")
    print(f"Effective year: {entry['effective_year']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
