#!/usr/bin/env python3
"""Discover legacy policy knowledge sources using the migration search order."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

SUPPORTED = {".md", ".json"}
EXCLUDED_DIRS = {
    ".git", ".svn", ".hg", ".codex", ".agents", "_workflow", "epic_attach",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "tmp", "temp", "temporary", "staging",
    "legacy files",
}
EXCLUDED_FILES = {
    "agents.md", "skill.md", "codex.md", "readme.md", "readme.json",
    "policy-source-manifest.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_excluded_dir_name(name: str) -> bool:
    """Return whether a directory name is excluded, case-insensitively."""
    return name.casefold() in EXCLUDED_DIRS


def is_excluded_directory(path: Path, root: Path) -> bool:
    """Reject a directory at or below an excluded traversal boundary."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(is_excluded_dir_name(part) for part in relative.parts)


def is_excluded(path: Path, root: Path) -> bool:
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    if path.name.lower() in EXCLUDED_FILES:
        return True
    return any(is_excluded_dir_name(part) for part in relative.parts[:-1])


def collect_under(folder: Path, root: Path) -> list[Path]:
    if is_excluded_directory(folder, root):
        return []

    out: list[Path] = []
    for current, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not is_excluded_dir_name(d))
        current_path = Path(current)
        for name in sorted(files):
            path = current_path / name
            if path.suffix.lower() in SUPPORTED and not is_excluded(path, root):
                out.append(path)
    return sorted(set(out), key=lambda p: str(p).lower())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find .md and .json policy sources, preferring Markdown/."
    )
    parser.add_argument("client_root", help="Legacy client root")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    if not root.is_dir():
        print(json.dumps({"error": f"client root is not a directory: {root}"}, indent=2), file=sys.stderr)
        return 2

    markdown_dirs = sorted(
        [p for p in root.iterdir() if p.is_dir() and p.name.lower() == "markdown"],
        key=lambda p: p.name.lower(),
    )
    primary: list[Path] = []
    for folder in markdown_dirs:
        primary.extend(collect_under(folder, root))
    primary = sorted(set(primary), key=lambda p: str(p).lower())

    if primary:
        mode = "markdown-first"
        files = primary
    else:
        mode = "recursive-fallback"
        files = collect_under(root, root)

    records = []
    for path in files:
        stat = path.stat()
        records.append({
            "relative_path": str(path.relative_to(root)),
            "absolute_path": str(path),
            "extension": path.suffix.lower(),
            "size_bytes": stat.st_size,
            "sha256": sha256(path),
        })

    output = {
        "client_root": str(root),
        "search_mode": mode,
        "markdown_directories": [str(p.relative_to(root)) for p in markdown_dirs],
        "source_count": len(records),
        "sources": records,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
