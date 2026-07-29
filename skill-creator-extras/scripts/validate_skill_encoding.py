#!/usr/bin/env python3
"""Validate and optionally normalize a skill's SKILL.md encoding."""
from __future__ import annotations

import argparse
import codecs
import sys
from pathlib import Path


def decode_skill(raw: bytes, path: Path) -> tuple[str | None, str | None]:
    try:
        return raw.decode("utf-8-sig"), None
    except UnicodeDecodeError as exc:
        return None, (
            f"{path}: invalid UTF-8 at byte {exc.start}: "
            f"{exc.reason}"
        )


def validate_frontmatter(text: str, path: Path) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append(f"{path}: YAML frontmatter must begin on the first line")
        return errors
    try:
        closing = lines.index("---", 1)
    except ValueError:
        errors.append(f"{path}: YAML frontmatter is missing its closing delimiter")
        return errors
    frontmatter = lines[1:closing]
    for field in ("name", "description"):
        if not any(line.startswith(f"{field}:") for line in frontmatter):
            errors.append(f"{path}: YAML frontmatter is missing {field!r}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate SKILL.md as UTF-8 and optionally remove a UTF-8 BOM"
    )
    parser.add_argument("skill_directory")
    parser.add_argument(
        "--normalize",
        action="store_true",
        help="Rewrite valid UTF-8 input without a BOM",
    )
    args = parser.parse_args()

    skill_dir = Path(args.skill_directory).expanduser().resolve()
    skill_path = skill_dir / "SKILL.md"
    if not skill_dir.is_dir():
        print(f"ERROR: skill directory not found: {skill_dir}", file=sys.stderr)
        return 2
    if not skill_path.is_file():
        print(f"ERROR: SKILL.md not found: {skill_path}", file=sys.stderr)
        return 2

    try:
        raw = skill_path.read_bytes()
    except OSError as exc:
        print(f"ERROR: could not read {skill_path}: {exc}", file=sys.stderr)
        return 2

    text, decode_error = decode_skill(raw, skill_path)
    if decode_error:
        print(f"ERROR: {decode_error}", file=sys.stderr)
        return 3
    assert text is not None

    errors = validate_frontmatter(text, skill_path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 4

    had_bom = raw.startswith(codecs.BOM_UTF8)
    if args.normalize:
        normalized = text.encode("utf-8")
        if normalized != raw:
            try:
                skill_path.write_bytes(normalized)
            except OSError as exc:
                print(
                    f"ERROR: could not normalize {skill_path}: {exc}",
                    file=sys.stderr,
                )
                return 5
            print(f"Normalized to UTF-8 without BOM: {skill_path}")
        else:
            print(f"Already UTF-8 without BOM: {skill_path}")
    elif had_bom:
        print(
            f"VALID with UTF-8 BOM: {skill_path}; "
            "run with --normalize to remove it"
        )
        return 0

    print(f"Encoding validation passed: {skill_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
