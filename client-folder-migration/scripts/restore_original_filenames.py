#!/usr/bin/env python3
"""Restore original basenames for migrated files without changing their folders."""
from __future__ import annotations

import argparse
import csv
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from migration_common import MOVE_LOG_HEADERS, parse_relative_path, sha256_file, to_native

RESTORE_LOG_HEADERS = [
    "run_id",
    "applied_at_utc",
    "move_log_file",
    "source_path",
    "current_path",
    "planned_restore_path",
    "actual_restore_path",
    "source_sha256",
    "action",
    "result",
    "notes",
]

RESTORABLE_RESULTS = {"moved", "copied"}


def read_move_log(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MOVE_LOG_HEADERS:
            raise ValueError(f"move log headers must exactly equal {MOVE_LOG_HEADERS!r}; found {reader.fieldnames!r}")
        return list(reader)


def append_restore_log(path: Path, rows: list[dict[str, str]]) -> None:
    new_file = not path.exists() or path.stat().st_size == 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESTORE_LOG_HEADERS)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


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


def find_by_hash(root: Path, expected_hash: str, excluded: set[Path]) -> Path | None:
    for path in sorted(root.rglob("*"), key=lambda p: str(p).casefold()):
        if not path.is_file() or path in excluded:
            continue
        try:
            if sha256_file(path) == expected_hash:
                return path
        except OSError:
            continue
    return None


def restore_rows(root: Path, move_log_path: Path, rows: list[dict[str, str]], apply: bool, search_by_hash: bool) -> tuple[list[dict[str, str]], list[str]]:
    output_rows: list[dict[str, str]] = []
    errors: list[str] = []
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    applied_at = datetime.now(timezone.utc).isoformat()
    used_destinations: set[Path] = set()

    for row_number, row in enumerate(rows, start=2):
        result = row["result"].strip().lower()
        if result not in RESTORABLE_RESULTS:
            continue
        source_rel = parse_relative_path(row["source_path"])
        actual_text = row["actual_destination"].strip()
        if not actual_text:
            continue
        current_rel = parse_relative_path(actual_text)
        current_path = to_native(root, current_rel)
        expected_hash = row["source_sha256"].strip().lower()
        notes = ""

        if not current_path.is_file() and search_by_hash:
            replacement = find_by_hash(root, expected_hash, used_destinations)
            if replacement is not None:
                current_path = replacement
                current_rel = PurePosixPath(*replacement.relative_to(root).parts)
                notes = "Actual destination missing; matched replacement by source hash."

        original_name = source_rel.name
        planned_restore = current_path.with_name(original_name)
        actual_restore = collision_path(planned_restore)
        used_destinations.add(actual_restore)
        log_row = {
            "run_id": run_id,
            "applied_at_utc": applied_at,
            "move_log_file": str(move_log_path),
            "source_path": source_rel.as_posix(),
            "current_path": current_rel.as_posix(),
            "planned_restore_path": PurePosixPath(*planned_restore.relative_to(root).parts).as_posix(),
            "actual_restore_path": PurePosixPath(*actual_restore.relative_to(root).parts).as_posix(),
            "source_sha256": expected_hash,
            "action": "rename",
            "result": "dry_run",
            "notes": notes,
        }

        if not current_path.is_file():
            log_row["result"] = "failed"
            log_row["notes"] = (notes + "; " if notes else "") + "Current migrated file not found."
            errors.append(f"row {row_number}: current migrated file not found: {current_rel.as_posix()}")
        elif sha256_file(current_path) != expected_hash:
            log_row["result"] = "failed"
            log_row["notes"] = (notes + "; " if notes else "") + "Current file hash does not match move log."
            errors.append(f"row {row_number}: hash mismatch for {current_rel.as_posix()}")
        elif current_path == actual_restore:
            log_row["result"] = "already_original_name"
        elif apply:
            os.replace(current_path, actual_restore)
            log_row["result"] = "renamed"
            if actual_restore != planned_restore:
                log_row["notes"] = (notes + "; " if notes else "") + "Original basename collision; deterministic suffix added."
        output_rows.append(log_row)
    return output_rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore migrated files to their original basenames without moving folders")
    parser.add_argument("client_root")
    parser.add_argument("move_log", nargs="?", help="Defaults to _Workflow/migration/cleanup-move-log.csv")
    parser.add_argument("--apply", action="store_true", help="Rename files after validation")
    parser.add_argument("--search-by-hash", action="store_true", help="If a logged actual destination is missing, search the client root for a matching source hash")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    move_log_path = Path(args.move_log).expanduser().resolve() if args.move_log else root / "_Workflow" / "migration" / "cleanup-move-log.csv"
    if not root.is_dir():
        print(f"ERROR: client root is not a directory: {root}", file=sys.stderr)
        return 2
    if not move_log_path.is_file():
        print(f"ERROR: move log not found: {move_log_path}", file=sys.stderr)
        return 2

    try:
        rows = read_move_log(move_log_path)
        output_rows, errors = restore_rows(root, move_log_path, rows, args.apply, args.search_by_hash)
    except (ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    if errors:
        print("Restore validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 4

    restore_log_path = root / "_Workflow" / "migration" / "rename-restore-log.csv"
    append_restore_log(restore_log_path, output_rows)
    rename_count = sum(1 for row in output_rows if row["result"] in {"renamed", "dry_run"})
    already_count = sum(1 for row in output_rows if row["result"] == "already_original_name")
    rename_label = "renamed" if args.apply else "rename candidate(s)"
    print(f"Restore {'applied' if args.apply else 'validated'}: {rename_count} {rename_label}, {already_count} already original name")
    print(f"Restore log: {restore_log_path}")
    if not args.apply:
        print("Dry run only. Re-run with --apply to rename files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

