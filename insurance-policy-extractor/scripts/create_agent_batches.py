#!/usr/bin/env python3
"""Create immutable, non-overlapping subagent assignments from pending manifest items."""
from __future__ import annotations

import argparse
from pathlib import Path

from policy_common import atomic_write_json, load_json, utc_now


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=5)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("--batch-size must be at least 1")

    manifest = load_json(args.manifest.resolve())
    pending = sorted(
        (entry for entry in manifest.get("files", []) if entry.get("status") == "pending"),
        key=lambda entry: entry.get("document_id", ""),
    )
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    batch_count = 0
    for offset in range(0, len(pending), args.batch_size):
        batch_count += 1
        batch_id = f"batch-{batch_count:03d}"
        batch_dir = output_dir / batch_id
        records_dir = batch_dir / "records"
        records_dir.mkdir(parents=True, exist_ok=False)
        assignments = []
        for entry in pending[offset: offset + args.batch_size]:
            document_id = entry["document_id"]
            assignments.append({
                "document_id": document_id,
                "exact_filename": entry["exact_filename"],
                "relative_path": entry["relative_path"],
                "source_path": entry["source_path"],
                "sha256": entry["sha256"],
                "output_record": str(records_dir / f"{document_id}.json"),
            })
        atomic_write_json(batch_dir / "assignment.json", {
            "batch_id": batch_id,
            "created_at": utc_now(),
            "manifest": str(args.manifest.resolve()),
            "document_count": len(assignments),
            "documents": assignments,
        })
    print(f"Assignments created: {batch_count}")
    print(f"Documents assigned: {len(pending)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())