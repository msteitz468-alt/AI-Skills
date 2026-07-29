#!/usr/bin/env python3
"""Inventory insurance source files without loading their contents into model context."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from policy_common import NOT_SPECIFIED, atomic_write_json, load_json, sha256_file, utc_now

SUPPORTED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt", ".rtf",
    ".json", ".msg", ".eml", ".tif", ".tiff", ".jpg", ".jpeg", ".png"
}
TERMINAL_STATUSES = {"complete", "needs_review", "duplicate"}


def is_root_legacy_files_path(path: Path, source_root: Path) -> bool:
    try:
        relative = path.relative_to(source_root)
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0].casefold() == "legacy files"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_folder", type=Path)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument(
        "--extensions",
        help="Comma-separated extensions to include, such as .pdf,.docx,.msg",
    )
    return parser.parse_args()


def next_document_id(entries: list[dict[str, Any]]) -> str:
    highest = 0
    for entry in entries:
        value = str(entry.get("document_id", ""))
        if value.startswith("doc_") and value[4:].isdigit():
            highest = max(highest, int(value[4:]))
    return f"doc_{highest + 1:06d}"


def main() -> int:
    args = parse_args()
    source_root = args.source_folder.resolve()
    work_dir = args.work_dir.resolve()
    manifest_path = work_dir / "extraction_manifest.json"

    if not source_root.is_dir():
        raise SystemExit(f"Source folder not found: {source_root}")

    extensions = SUPPORTED_EXTENSIONS
    if args.extensions:
        extensions = {
            item.strip().lower() if item.strip().startswith(".") else f".{item.strip().lower()}"
            for item in args.extensions.split(",") if item.strip()
        }

    work_dir.mkdir(parents=True, exist_ok=True)
    (work_dir / "documents").mkdir(exist_ok=True)
    (work_dir / "drafts").mkdir(exist_ok=True)

    if manifest_path.exists():
        manifest = load_json(manifest_path)
    else:
        manifest = {
            "manifest_version": 1,
            "source_root": str(source_root),
            "work_dir": str(work_dir),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "supported_extensions": sorted(extensions),
            "files": [],
        }

    entries = manifest.setdefault("files", [])
    by_relative = {entry.get("relative_path"): entry for entry in entries}
    discovered_paths: set[str] = set()

    candidates = []
    for path in source_root.rglob("*"):
        if is_root_legacy_files_path(path, source_root):
            continue
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        try:
            path.resolve().relative_to(work_dir)
            continue
        except ValueError:
            pass
        candidates.append(path)

    for path in sorted(candidates, key=lambda p: str(p.relative_to(source_root)).lower()):
        relative_path = path.relative_to(source_root).as_posix()
        discovered_paths.add(relative_path)
        stat = path.stat()
        digest = sha256_file(path)
        modified = utc_now() if stat.st_mtime is None else __import__("datetime").datetime.fromtimestamp(
            stat.st_mtime, __import__("datetime").timezone.utc
        ).replace(microsecond=0).isoformat().replace("+00:00", "Z")

        existing = by_relative.get(relative_path)
        if existing and existing.get("sha256") == digest:
            existing.update({
                "source_path": str(path.resolve()),
                "exact_filename": path.name,
                "extension": path.suffix.lower(),
                "size_bytes": stat.st_size,
                "modified_time": modified,
                "last_seen_at": utc_now(),
            })
            continue

        if existing:
            history = existing.setdefault("history", [])
            history.append({
                "sha256": existing.get("sha256", NOT_SPECIFIED),
                "status": existing.get("status", NOT_SPECIFIED),
                "staged_json": existing.get("staged_json", NOT_SPECIFIED),
                "effective_year": existing.get("effective_year", NOT_SPECIFIED),
                "archived_at": utc_now(),
            })
            document_id = existing["document_id"]
            existing.clear()
            entry = existing
        else:
            document_id = next_document_id(entries)
            entry = {"document_id": document_id}
            entries.append(entry)
            by_relative[relative_path] = entry

        entry.update({
            "document_id": document_id,
            "relative_path": relative_path,
            "exact_filename": path.name,
            "source_path": str(path.resolve()),
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "modified_time": modified,
            "sha256": digest,
            "status": "pending",
            "duplicate_of": NOT_SPECIFIED,
            "staged_json": NOT_SPECIFIED,
            "document_type": NOT_SPECIFIED,
            "effective_year": NOT_SPECIFIED,
            "policy_number": NOT_SPECIFIED,
            "parent_policy_id": NOT_SPECIFIED,
            "review_flags": [],
            "attempts": 0,
            "last_error": NOT_SPECIFIED,
            "first_seen_at": utc_now(),
            "last_seen_at": utc_now(),
            "history": entry.get("history", []),
        })

    # Keep missing prior entries for audit, but mark their source as absent unless already terminal.
    for entry in entries:
        if entry.get("relative_path") not in discovered_paths and entry.get("status") not in TERMINAL_STATUSES:
            entry["status"] = "error"
            entry["last_error"] = "Source file is no longer present in the inventory root."

    # Recompute exact byte duplicates. The first document ID is canonical.
    hash_groups: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        digest = entry.get("sha256")
        if isinstance(digest, str) and digest and digest != NOT_SPECIFIED and entry.get("relative_path") in discovered_paths:
            hash_groups.setdefault(digest, []).append(entry)

    for group in hash_groups.values():
        group.sort(key=lambda item: item["document_id"])
        canonical = group[0]
        if canonical.get("status") == "duplicate":
            canonical["status"] = "pending"
            canonical["duplicate_of"] = NOT_SPECIFIED
        for duplicate in group[1:]:
            duplicate["status"] = "duplicate"
            duplicate["duplicate_of"] = canonical["document_id"]
            duplicate["staged_json"] = NOT_SPECIFIED

    manifest.update({
        "source_root": str(source_root),
        "work_dir": str(work_dir),
        "updated_at": utc_now(),
        "supported_extensions": sorted(extensions),
    })
    entries.sort(key=lambda item: item["document_id"])
    atomic_write_json(manifest_path, manifest)

    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    print(f"Manifest: {manifest_path}")
    print(f"Discovered source files: {len(discovered_paths)}")
    print("Status counts: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

