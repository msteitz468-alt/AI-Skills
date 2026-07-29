#!/usr/bin/env python3
"""Return or claim the next single source file from an extraction manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from policy_common import NOT_SPECIFIED, atomic_write_json, load_json, utc_now


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--claim", action="store_true", help="Mark the returned item in_progress")
    parser.add_argument(
        "--reset-in-progress",
        action="store_true",
        help="Reset all in_progress items to pending before choosing the next item",
    )
    return parser.parse_args()


def public_item(entry: dict) -> dict:
    return {
        "status": entry.get("status"),
        "document_id": entry.get("document_id"),
        "source_path": entry.get("source_path"),
        "relative_path": entry.get("relative_path"),
        "exact_filename": entry.get("exact_filename"),
        "sha256": entry.get("sha256", NOT_SPECIFIED),
        "attempts": entry.get("attempts", 0),
    }


def main() -> int:
    args = parse_args()
    manifest_path = args.manifest.resolve()
    manifest = load_json(manifest_path)
    entries = manifest.get("files", [])

    if args.reset_in_progress:
        for entry in entries:
            if entry.get("status") == "in_progress":
                entry["status"] = "pending"
                entry["last_error"] = "Reset from in_progress by explicit request."

    in_progress = [entry for entry in entries if entry.get("status") == "in_progress"]
    if len(in_progress) > 1:
        print(json.dumps({
            "status": "error",
            "message": "Manifest has more than one in_progress item; resolve before continuing.",
            "document_ids": [item.get("document_id") for item in in_progress],
        }, indent=2))
        return 2

    if in_progress:
        selected = in_progress[0]
    else:
        pending = sorted(
            (entry for entry in entries if entry.get("status") == "pending"),
            key=lambda item: item.get("document_id", ""),
        )
        if not pending:
            print(json.dumps({"status": "none", "message": "No pending source files."}, indent=2))
            if args.reset_in_progress:
                manifest["updated_at"] = utc_now()
                atomic_write_json(manifest_path, manifest)
            return 0
        selected = pending[0]
        if args.claim:
            selected["status"] = "in_progress"
            selected["attempts"] = int(selected.get("attempts", 0)) + 1
            selected["claimed_at"] = utc_now()
            selected["last_error"] = NOT_SPECIFIED

    if args.claim or args.reset_in_progress:
        manifest["updated_at"] = utc_now()
        atomic_write_json(manifest_path, manifest)

    print(json.dumps(public_item(selected), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
