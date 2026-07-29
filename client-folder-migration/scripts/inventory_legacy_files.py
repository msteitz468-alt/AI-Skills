#!/usr/bin/env python3
"""Inventory legacy files and identify protected or already-standard paths."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path, PurePosixPath

from migration_common import (
    is_protected_path,
    is_standard_path,
    load_register,
    sha256_file,
)

LEGACY_FILES_DIR_NAME = "legacy files"

SKIP_DESCENT = {
    ".git", ".svn", ".hg", ".codex", ".agents", "_workflow", "epic_attach",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "site-packages",
}


def artifact_hint(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in {".msg", ".eml"}:
        return "email"
    if ext == ".md":
        return "markdown"
    if ext == ".json":
        return "json"
    if ext == ".pdf":
        return "pdf"
    if ext in {".xlsx", ".xls", ".csv"}:
        return "spreadsheet"
    if ext in {".docx", ".doc"}:
        return "document"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory legacy client files")
    parser.add_argument("client_root")
    parser.add_argument("--output", help="Write JSON inventory directly to this path using UTF-8 without a BOM")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"client root is not a directory: {root}"}, indent=2), file=sys.stderr)
        return 2

    try:
        _, supported, terms = load_register(root / "Policy_Register.csv")
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 3

    records: list[dict[str, object]] = []
    protected_count = 0
    standard_count = 0
    legacy_count = 0

    def walk(folder: Path) -> None:
        nonlocal protected_count, standard_count, legacy_count
        try:
            entries = sorted(folder.iterdir(), key=lambda p: p.name.casefold())
        except OSError as exc:
            records.append({"relative_path": str(folder.relative_to(root)), "error": str(exc)})
            return
        for path in entries:
            relative_native = path.relative_to(root)
            relative = PurePosixPath(*relative_native.parts)
            if path.is_dir():
                if path.name.casefold() == LEGACY_FILES_DIR_NAME:
                    records.append({
                        "relative_path": relative.as_posix(),
                        "protected": True,
                        "already_standard": False,
                        "excluded_reason": "Legacy Files preserved archive; not inventoried unless specifically requested.",
                    })
                    protected_count += 1
                    continue
                if path.name.casefold() in SKIP_DESCENT:
                    continue
                walk(path)
                continue
            if not path.is_file():
                continue
            protected = is_protected_path(relative)
            standard = is_standard_path(relative, supported, terms)
            if protected:
                protected_count += 1
            elif standard:
                standard_count += 1
            else:
                legacy_count += 1
            try:
                stat = path.stat()
                digest = None if protected else sha256_file(path)
                record = {
                    "relative_path": relative.as_posix(),
                    "size_bytes": stat.st_size,
                    "sha256": digest,
                    "extension": path.suffix.lower(),
                    "artifact_hint": artifact_hint(path),
                    "protected": protected,
                    "already_standard": standard,
                }
            except OSError as exc:
                record = {
                    "relative_path": relative.as_posix(),
                    "protected": protected,
                    "already_standard": standard,
                    "error": str(exc),
                }
            records.append(record)

    walk(root)
    output = {
        "client_root": str(root),
        "record_count": len(records),
        "protected_count": protected_count,
        "already_standard_count": standard_count,
        "legacy_candidate_count": legacy_count,
        "records": records,
    }
    payload = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        output_path = Path(args.output).expanduser()
        if not output_path.is_absolute():
            output_path = root / output_path
        output_path = output_path.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
        print(f"Inventory written: {output_path}")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


