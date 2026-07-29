#!/usr/bin/env python3
"""Validate and safely apply an AI-reviewed legacy-file migration plan."""
from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from migration_common import (
    HEX64_RE,
    MOVE_LOG_HEADERS,
    PLAN_HEADERS,
    destination_is_approved,
    destination_is_folder_context_approved,
    is_root_preserve_only_source_path,
    is_protected_path,
    is_standard_path,
    is_windows_safe_filename,
    load_register,
    parse_relative_path,
    sha256_file,
    to_native,
)

VALID_ACTIONS = {"move", "copy", "leave", "skip"}
VALID_CONFIDENCE = {"high", "medium", "low"}
MAX_WINDOWS_TEMP_PATH = 240


def planned_temp_path(destination: Path) -> Path:
    return destination.with_name(f".{destination.name}.migrationtmp-{'0' * 32}")


def path_key(path: Path) -> str:
    return str(path).casefold()


def existing_hash(path: Path) -> str | None:
    if path.is_file():
        return sha256_file(path)
    return None


def planned_collision_path(destination: Path, planned_hash: str, occupied_hashes: dict[str, str]) -> tuple[Path, bool]:
    destination_key = path_key(destination)
    destination_hash = occupied_hashes.get(destination_key)
    if destination_hash is None:
        destination_hash = existing_hash(destination)
    if destination_hash == planned_hash:
        return destination, True
    if destination_hash is None:
        return destination, False

    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate = destination.with_name(f"{stem} ({counter}){suffix}")
        candidate_key = path_key(candidate)
        if candidate_key not in occupied_hashes and not candidate.exists():
            return candidate, False
        counter += 1


def load_plan(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != PLAN_HEADERS:
            raise ValueError(f"plan headers must exactly equal {PLAN_HEADERS!r}; found {reader.fieldnames!r}")
        return list(reader)


def validate_rows(
    root: Path,
    rows: list[dict[str, str]],
    supported: set[tuple[str, str]],
    terms: set[str],
    allow_folder_context: bool = False,
) -> list[str]:
    errors: list[str] = []
    seen_sources: set[str] = set()
    occupied_destination_hashes: dict[str, str] = {}

    for row_number, row in enumerate(rows, start=2):
        source_text = row["source_path"].strip()
        try:
            source_rel = parse_relative_path(source_text)
        except ValueError as exc:
            errors.append(f"row {row_number}: {exc}")
            continue

        source_key = source_rel.as_posix().casefold()
        if source_key in seen_sources:
            errors.append(f"row {row_number}: duplicate source_path {source_text!r}")
        seen_sources.add(source_key)

        action = row["action"].strip().lower()
        confidence = row["confidence"].strip().lower()
        if action not in VALID_ACTIONS:
            errors.append(f"row {row_number}: unsupported action {action!r}")
        if confidence not in VALID_CONFIDENCE:
            errors.append(f"row {row_number}: unsupported confidence {confidence!r}")
        if action in {"move", "copy"} and confidence != "high":
            errors.append(f"row {row_number}: {action} requires high confidence")

        source = to_native(root, source_rel)
        if not source.is_file():
            errors.append(f"row {row_number}: source file not found: {source_rel.as_posix()}")
            continue
        if is_protected_path(source_rel):
            errors.append(f"row {row_number}: protected file may not appear in migration plan: {source_rel.as_posix()}")
            continue
        if is_root_preserve_only_source_path(source_rel) and action != "leave":
            errors.append(
                f"row {row_number}: files in root-level RDW-named folders must use action 'leave': "
                f"{source_rel.as_posix()}"
            )
        if action in {"move", "copy"} and is_standard_path(source_rel, supported, terms):
            errors.append(f"row {row_number}: already-standard file may not be moved or copied: {source_rel.as_posix()}")

        planned_hash = row["source_sha256"].strip().lower()
        if not HEX64_RE.fullmatch(planned_hash):
            errors.append(f"row {row_number}: source_sha256 is not a 64-character hex digest")
        else:
            current_hash = sha256_file(source)
            if current_hash != planned_hash:
                errors.append(f"row {row_number}: source hash changed for {source_rel.as_posix()}")

        try:
            planned_size = int(row["size_bytes"].strip())
        except ValueError:
            errors.append(f"row {row_number}: size_bytes is not an integer")
        else:
            if planned_size != source.stat().st_size:
                errors.append(f"row {row_number}: source size changed for {source_rel.as_posix()}")

        destination_text = row["destination_relative_path"].strip()
        final_filename = row["final_filename"].strip()
        if action in {"move", "copy"}:
            try:
                destination_rel = parse_relative_path(destination_text)
            except ValueError as exc:
                errors.append(f"row {row_number}: {exc}")
                continue
            if destination_rel.name != final_filename:
                errors.append(f"row {row_number}: final_filename must equal destination basename")
            if not is_windows_safe_filename(final_filename):
                errors.append(f"row {row_number}: final_filename is not Windows-safe: {final_filename!r}")
            if source.suffix.lower() != Path(final_filename).suffix.lower():
                errors.append(f"row {row_number}: final filename must preserve the source extension")
            if not destination_is_approved(destination_rel, supported, terms):
                if not (allow_folder_context and destination_is_folder_context_approved(destination_rel)):
                    errors.append(f"row {row_number}: destination is outside the approved structure: {destination_rel.as_posix()}")
            if destination_rel.as_posix().casefold() == source_rel.as_posix().casefold():
                errors.append(f"row {row_number}: source and destination are identical")
            actual_destination, duplicate_destination = planned_collision_path(
                to_native(root, destination_rel),
                planned_hash,
                occupied_destination_hashes,
            )
            if not duplicate_destination:
                occupied_destination_hashes[path_key(actual_destination)] = planned_hash
                temp_path = planned_temp_path(actual_destination)
                if os.name == "nt" and len(str(temp_path)) > MAX_WINDOWS_TEMP_PATH:
                    errors.append(
                        f"row {row_number}: resolved temporary path is too long for reliable Windows/UNC moves "
                        f"after collision handling ({len(str(temp_path))} characters); shorten final_filename"
                    )
        elif destination_text or final_filename:
            errors.append(f"row {row_number}: leave/skip rows must not specify a destination or final filename")

    return errors


def collision_path(destination: Path) -> Path:
    if not destination.exists():
        return destination
    stem = destination.stem
    suffix = destination.suffix
    counter = 2
    while True:
        candidate = destination.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def append_log(log_path: Path, rows: list[dict[str, str]]) -> None:
    new_file = not log_path.exists() or log_path.stat().st_size == 0
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=MOVE_LOG_HEADERS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate or apply a client-folder migration plan")
    parser.add_argument("client_root")
    parser.add_argument("plan")
    parser.add_argument("--apply", action="store_true", help="Apply the validated plan")
    parser.add_argument("--allow-folder-context", action="store_true", help="Allow destinations inferred from legacy folder context even when the register lacks that LOB/term")
    parser.add_argument("--allow-partial-plan", action="store_true", help="Allow a plan that intentionally covers only selected nonstandard files")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    plan_path = Path(args.plan).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: client root is not a directory: {root}", file=sys.stderr)
        return 2
    if not plan_path.is_file():
        print(f"ERROR: plan not found: {plan_path}", file=sys.stderr)
        return 2

    try:
        _, supported, terms = load_register(root / "Policy_Register.csv")
        rows = load_plan(plan_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    errors = validate_rows(root, rows, supported, terms, allow_folder_context=args.allow_folder_context)

    inventory_path = root / "_Workflow" / "migration" / "legacy-file-inventory.json"
    if inventory_path.is_file() and not args.allow_partial_plan:
        try:
            inventory = json.loads(inventory_path.read_text(encoding="utf-8-sig"))
            expected = {
                str(record["relative_path"]).replace("\\", "/").casefold()
                for record in inventory.get("records", [])
                if not record.get("protected")
                and not record.get("already_standard")
                and not record.get("error")
            }
            planned = {row["source_path"].replace("\\", "/").strip().casefold() for row in rows}
            missing = sorted(expected - planned)
            if missing:
                errors.append(f"plan omits {len(missing)} nonstandard inventory file(s): {missing}")
        except (OSError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"could not validate plan coverage against inventory: {exc}")

    if errors:
        print("Plan validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 4

    move_count = sum(1 for row in rows if row["action"].strip().lower() == "move")
    copy_count = sum(1 for row in rows if row["action"].strip().lower() == "copy")
    leave_count = sum(1 for row in rows if row["action"].strip().lower() == "leave")
    skip_count = sum(1 for row in rows if row["action"].strip().lower() == "skip")
    print(f"Plan validation passed: {move_count} move, {copy_count} copy, {leave_count} leave, {skip_count} skip")
    if not args.apply:
        print("Dry run only. Re-run with --apply to perform moves/copies.")
        return 0

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    applied_at = datetime.now(timezone.utc).isoformat()
    log_rows: list[dict[str, str]] = []
    failures = 0

    for row in rows:
        action = row["action"].strip().lower()
        source_rel = parse_relative_path(row["source_path"])
        source = to_native(root, source_rel)
        base_log = {
            "run_id": run_id,
            "applied_at_utc": applied_at,
            "plan_file": str(plan_path),
            "source_path": source_rel.as_posix(),
            "planned_destination": row["destination_relative_path"].strip(),
            "actual_destination": "",
            "source_sha256": row["source_sha256"].strip().lower(),
            "action": action,
            "result": "",
            "notes": row["reason"].strip(),
        }

        if action == "leave":
            base_log["result"] = "left_in_place"
            log_rows.append(base_log)
            continue
        if action == "skip":
            base_log["result"] = "skipped"
            log_rows.append(base_log)
            continue

        destination_rel = parse_relative_path(row["destination_relative_path"])
        destination = to_native(root, destination_rel)
        destination.parent.mkdir(parents=True, exist_ok=True)
        planned_hash = row["source_sha256"].strip().lower()

        try:
            if destination.exists() and destination.is_file() and sha256_file(destination) == planned_hash:
                base_log["actual_destination"] = destination_rel.as_posix()
                base_log["result"] = "duplicate_destination"
                base_log["notes"] = (base_log["notes"] + "; " if base_log["notes"] else "") + "Identical destination already exists; source left in place."
                log_rows.append(base_log)
                continue

            actual_destination = collision_path(destination)
            actual_rel = PurePosixPath(*actual_destination.relative_to(root).parts)
            temp = actual_destination.with_name(f".{actual_destination.name}.migrationtmp-{uuid.uuid4().hex}")
            if os.name == "nt" and len(str(temp)) > MAX_WINDOWS_TEMP_PATH:
                raise RuntimeError(f"resolved temporary path is too long for reliable Windows/UNC moves ({len(str(temp))} characters)")
            shutil.copy2(source, temp)
            if sha256_file(temp) != planned_hash:
                raise RuntimeError("temporary copy hash mismatch")
            os.replace(temp, actual_destination)
            if sha256_file(actual_destination) != planned_hash:
                raise RuntimeError("destination hash mismatch after atomic rename")
            if action == "move":
                source.unlink()
            base_log["actual_destination"] = actual_rel.as_posix()
            base_log["result"] = "moved" if action == "move" else "copied"
            if actual_destination != destination:
                base_log["notes"] = (base_log["notes"] + "; " if base_log["notes"] else "") + "Destination collision; deterministic suffix added."
            log_rows.append(base_log)
        except Exception as exc:
            failures += 1
            try:
                if "temp" in locals() and temp.exists():
                    temp.unlink()
            except OSError:
                pass
            base_log["result"] = "failed"
            base_log["notes"] = (base_log["notes"] + "; " if base_log["notes"] else "") + str(exc)
            log_rows.append(base_log)

    log_path = root / "_Workflow" / "migration" / "cleanup-move-log.csv"
    append_log(log_path, log_rows)
    print(f"Application complete: {len(log_rows) - failures} recorded without failure, {failures} failed")
    print(f"Move log: {log_path}")
    return 5 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())











