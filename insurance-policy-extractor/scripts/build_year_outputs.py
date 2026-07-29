#!/usr/bin/env python3
"""Build legacy-compatible calendar-year JSON outputs from staged document records."""

from __future__ import annotations

import argparse
import copy
import re
from pathlib import Path
from typing import Any

from policy_common import NOT_SPECIFIED, atomic_write_json, load_json, utc_now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def record_sort_key(record: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(record.get("policy_number", NOT_SPECIFIED)),
        str(record.get("policy_effective_date", NOT_SPECIFIED)),
        str(record.get("source", {}).get("exact_filename", record.get("document_name", NOT_SPECIFIED))),
    )


def review_reasons(entry: dict[str, Any], record: dict[str, Any] | None) -> list[Any]:
    reasons = []
    if record and isinstance(record.get("review_flags"), list):
        reasons.extend(record["review_flags"])
    elif isinstance(entry.get("review_flags"), list):
        reasons.extend(entry["review_flags"])
    if entry.get("status") in {"pending", "in_progress", "error"}:
        reasons.append({
            "code": f"MANIFEST_{str(entry.get('status')).upper()}",
            "message": entry.get("last_error", "The file has not reached a completed extraction state."),
            "source_pages": [],
        })
    return reasons


def term_folder(record: dict[str, Any]) -> str:
    existing = record.get("term_folder")
    if isinstance(existing, str) and existing:
        return existing
    effective = str(record.get("policy_effective_date", NOT_SPECIFIED))
    expiration = str(record.get("policy_expiration_date", NOT_SPECIFIED))
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", effective) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", expiration):
        return f"{effective[2:4]}-{expiration[2:4]}"
    return NOT_SPECIFIED


def source_path_alias(record: dict[str, Any]) -> str:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    for key in ("relative_path", "exact_filename"):
        value = source.get(key)
        if isinstance(value, str) and value:
            return value
    value = record.get("source_path")
    return value if isinstance(value, str) and value else NOT_SPECIFIED


def page_count_alias(record: dict[str, Any]) -> Any:
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    if source.get("page_count") not in (None, ""):
        return source.get("page_count")
    return record.get("source_page_count", NOT_SPECIFIED)


def notes_alias(record: dict[str, Any]) -> Any:
    if "extraction_notes" in record:
        return record.get("extraction_notes")
    notes = record.get("source_notes", [])
    if isinstance(notes, list):
        return notes
    if isinstance(notes, str):
        return [notes]
    return []


def legacy_compatible_document(record: dict[str, Any]) -> dict[str, Any]:
    """Return a flat documents[] record that preserves the full staged extraction."""

    annual = copy.deepcopy(record)
    source = annual.get("source") if isinstance(annual.get("source"), dict) else {}

    annual.setdefault("document_name", source.get("exact_filename", NOT_SPECIFIED))
    annual.setdefault("source_path", source_path_alias(record))
    annual.setdefault("source_sha256", source.get("sha256", NOT_SPECIFIED))
    annual.setdefault("source_page_count", page_count_alias(record))
    annual.setdefault("searchable_pages_reviewed", page_count_alias(record))
    annual.setdefault("source_text_excerpt", NOT_SPECIFIED)
    annual.setdefault("extraction_notes", notes_alias(record))
    annual.setdefault("term_folder", term_folder(record))

    if "coverages" not in annual and isinstance(annual.get("coverage_lines"), list):
        annual["coverages"] = annual["coverage_lines"]
    if "locations" not in annual:
        schedules = annual.get("schedules") if isinstance(annual.get("schedules"), dict) else {}
        annual["locations"] = schedules.get("locations", []) if isinstance(schedules.get("locations"), list) else []

    return annual


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_json(manifest_path)

    for path in output_dir.iterdir():
        if path.is_file() and (re.fullmatch(r"\d{4}_Policies\.json", path.name) or path.name in {"needs_review.json", "All_Policies.json"}):
            path.unlink()

    years: dict[int, list[dict[str, Any]]] = {}
    review_items: list[dict[str, Any]] = []

    for entry in sorted(manifest.get("files", []), key=lambda item: item.get("document_id", "")):
        status = entry.get("status")
        if status == "duplicate":
            continue

        record = None
        staged_value = entry.get("staged_json")
        if isinstance(staged_value, str) and staged_value != NOT_SPECIFIED:
            staged_path = Path(staged_value)
            if staged_path.exists():
                record = load_json(staged_path)

        if record is not None and isinstance(record.get("effective_year"), int):
            years.setdefault(record["effective_year"], []).append(legacy_compatible_document(record))

        effective_year = record.get("effective_year", NOT_SPECIFIED) if record else entry.get("effective_year", NOT_SPECIFIED)
        reasons = review_reasons(entry, record)
        if status in {"pending", "in_progress", "error"} or not isinstance(effective_year, int):
            review_items.append({
                "document_id": entry.get("document_id"),
                "relative_path": entry.get("relative_path"),
                "status": status,
                "effective_year": effective_year,
                "document_type": record.get("document_type", NOT_SPECIFIED) if record else entry.get("document_type", NOT_SPECIFIED),
                "policy_number": record.get("policy_number", NOT_SPECIFIED) if record else entry.get("policy_number", NOT_SPECIFIED),
                "staged_json": staged_value,
                "review_flags": reasons,
            })

    generated_at = utc_now()
    for year, documents in sorted(years.items()):
        documents.sort(key=record_sort_key)
        annual = {
            "documents": documents,
            "metadata": {
                "calendar_year": year,
                "generated_at": generated_at,
                "source_manifest": manifest_path.name,
                "document_count": len(documents),
                "output_shape": "legacy_documents_v1",
            },
        }
        atomic_write_json(output_dir / f"{year}_Policies.json", annual)

    if review_items:
        review_ids = ", ".join(str(item.get("document_id")) for item in review_items)
        raise SystemExit("Calendar-year output cannot be finalized while review-only or unassigned items remain: " + review_ids)

    print(f"Annual files created: {len(years)}")
    print(f"Output directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
