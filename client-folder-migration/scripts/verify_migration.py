#!/usr/bin/env python3
"""Verify a client-folder migration plan against the move log and filesystem."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from migration_common import (
    MOVE_LOG_HEADERS,
    PERMANENT_ROOT_FAMILIES,
    PLAN_HEADERS,
    QUOTE_PROPOSAL_FOLDER,
    QUOTE_ROOT,
    ROOT_YEAR_CATEGORIES,
    is_folder_context_path,
    is_protected_path,
    is_standard_path,
    load_register,
    parse_relative_path,
    row_effective_year,
    sha256_file,
)


def read_csv(path: Path, headers: list[str]) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != headers:
            raise ValueError(f"unexpected headers in {path}: {reader.fieldnames!r}")
        return list(reader)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a client-folder migration")
    parser.add_argument("client_root")
    parser.add_argument("plan")
    parser.add_argument("--allow-folder-context", action="store_true", help="Treat folder-context LOB/term/category paths as valid even when not register-supported")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    plan_path = Path(args.plan).expanduser().resolve()
    log_path = root / "_Workflow" / "migration" / "cleanup-move-log.csv"
    report_path = root / "_Workflow" / "migration" / "verification-report.json"

    try:
        rows, supported, years = load_register(root / "Policy_Register.csv")
        plan_rows = read_csv(plan_path, PLAN_HEADERS)
        log_rows = read_csv(log_path, MOVE_LOG_HEADERS)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    latest: dict[str, dict[str, str]] = {}
    plan_text = str(plan_path)
    prior_failed_attempts = [
        row for row in log_rows
        if row["plan_file"] != plan_text and row["result"] == "failed"
    ]
    for row in log_rows:
        if row["plan_file"] == plan_text:
            latest[row["source_path"].casefold()] = row

    failures: list[dict[str, str]] = []
    verified_moves: list[dict[str, str]] = []
    verified_copies: list[dict[str, str]] = []
    left_or_skipped: list[dict[str, str]] = []
    duplicate_destinations: list[dict[str, str]] = []

    for row in plan_rows:
        action = row["action"].strip().lower()
        source_key = row["source_path"].replace("\\", "/").casefold()
        log = latest.get(source_key)
        if log is None:
            failures.append({"source_path": row["source_path"], "issue": "No move-log record for this plan"})
            continue
        result = log["result"]
        if action in {"move", "copy"}:
            expected_result = "moved" if action == "move" else "copied"
            if result == expected_result:
                destination = root.joinpath(*PurePosixPath(log["actual_destination"]).parts)
                if not destination.is_file():
                    failures.append({"source_path": row["source_path"], "issue": f"{action.capitalize()} destination is missing"})
                elif sha256_file(destination) != row["source_sha256"].strip().lower():
                    failures.append({"source_path": row["source_path"], "issue": f"{action.capitalize()} destination hash mismatch"})
                elif action == "copy":
                    source = root.joinpath(*PurePosixPath(row["source_path"].replace("\\", "/")).parts)
                    if not source.is_file():
                        failures.append({"source_path": row["source_path"], "issue": "Copied source is missing"})
                    elif sha256_file(source) != row["source_sha256"].strip().lower():
                        failures.append({"source_path": row["source_path"], "issue": "Copied source hash mismatch"})
                    else:
                        verified_copies.append({"source_path": row["source_path"], "destination": log["actual_destination"]})
                else:
                    verified_moves.append({"source_path": row["source_path"], "destination": log["actual_destination"]})
            elif result == "duplicate_destination":
                duplicate_destinations.append({"source_path": row["source_path"], "destination": log["actual_destination"]})
            else:
                failures.append({"source_path": row["source_path"], "issue": f"{action.capitalize()} result is {result!r}"})
        else:
            left_or_skipped.append({"source_path": row["source_path"], "action": action, "result": result})

    missing_structure: list[str] = []
    for relative in [
        "raw",
        "Epic_Attach",
        "Markdown",
        "_Workflow/migration",
        "Account/Permanent",
        *PERMANENT_ROOT_FAMILIES,
        QUOTE_ROOT,
    ]:
        if not (root / relative).is_dir():
            missing_structure.append(relative)
    for lob_key, year in sorted(supported):
        display_lob = next(
            (
                row["lob"].strip()
                for row in rows
                if row["lob"].strip().casefold() == lob_key and row_effective_year(row) == year
            ),
            lob_key,
        )
        for family in ("Policies", "Applications"):
            relative = f"{family}/{year}/{display_lob}"
            if not (root / relative).is_dir():
                missing_structure.append(relative)
    for year in sorted(years):
        for family in ROOT_YEAR_CATEGORIES:
            relative = f"{family}/{year}"
            if not (root / relative).is_dir():
                missing_structure.append(relative)
        relative = f"Account/{year}"
        if not (root / relative).is_dir():
            missing_structure.append(relative)
        relative = f"Quotes/{year}/{QUOTE_PROPOSAL_FOLDER}"
        if not (root / relative).is_dir():
            missing_structure.append(relative)

    epic_files = [
        str(path.relative_to(root)).replace("\\", "/")
        for path in (root / "Epic_Attach").rglob("*")
        if path.is_file()
    ] if (root / "Epic_Attach").is_dir() else []

    remaining_nonstandard: list[str] = []
    for path in sorted(root.rglob("*"), key=lambda p: str(p).casefold()):
        if not path.is_file():
            continue
        relative = PurePosixPath(*path.relative_to(root).parts)
        if is_protected_path(relative):
            continue
        if not is_standard_path(relative, supported, years) and not (
            args.allow_folder_context and is_folder_context_path(relative)
        ):
            remaining_nonstandard.append(relative.as_posix())

    manifest_path = root / "_Workflow" / "migration" / "target-structure.json"
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            original_register_hash = manifest.get("policy_register_sha256")
            current_register_hash = sha256_file(root / "Policy_Register.csv")
            if original_register_hash and original_register_hash != current_register_hash:
                failures.append({"source_path": "Policy_Register.csv", "issue": "Policy register changed after target structure creation"})
        except (OSError, ValueError, TypeError) as exc:
            failures.append({"source_path": "", "issue": f"Could not validate target structure manifest: {exc}"})
    else:
        failures.append({"source_path": "", "issue": "Target structure manifest is missing"})

    if missing_structure:
        failures.append({"source_path": "", "issue": f"Missing target directories: {missing_structure}"})
    if epic_files:
        failures.append({"source_path": "", "issue": f"Historical files found in Epic_Attach: {epic_files}"})

    report = {
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "client_root": str(root),
        "plan_file": str(plan_path),
        "verified_move_count": len(verified_moves),
        "verified_copy_count": len(verified_copies),
        "left_or_skipped_count": len(left_or_skipped),
        "duplicate_destination_count": len(duplicate_destinations),
        "failure_count": len(failures),
        "prior_failed_attempt_count": len(prior_failed_attempts),
        "verified_moves": verified_moves,
        "verified_copies": verified_copies,
        "left_or_skipped": left_or_skipped,
        "duplicate_destinations": duplicate_destinations,
        "remaining_nonstandard_files": remaining_nonstandard,
        "failures": failures,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"Verification report: {report_path}")
    print(
        f"Verified {len(verified_moves)} move(s), {len(verified_copies)} copy/copies; {len(left_or_skipped)} left/skipped; "
        f"{len(duplicate_destinations)} duplicate destination(s); {len(failures)} failure(s); "
        f"{len(remaining_nonstandard)} nonstandard file(s) remain"
    )
    if prior_failed_attempts:
        print(f"Prior failed log entries from earlier plans: {len(prior_failed_attempts)}; final verification only evaluates {plan_path}")
    return 3 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())








