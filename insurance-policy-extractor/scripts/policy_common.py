#!/usr/bin/env python3
"""Shared standard-library helpers for the insurance policy extractor skill."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NOT_SPECIFIED = "Not specified"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def mojibake_repair_candidates(value: str) -> list[str]:
    """Return conservative UTF-8 repair candidates for a damaged path string."""
    candidates = [value]
    seen = {value}
    for _ in range(3):
        added: list[str] = []
        for candidate in candidates:
            for encoding in ("cp1252", "latin-1"):
                try:
                    repaired = candidate.encode(encoding).decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
                if repaired not in seen:
                    seen.add(repaired)
                    added.append(repaired)
        if not added:
            break
        candidates.extend(added)
    return candidates


def resolve_source_path(value: Any, expected_sha256: Any = None) -> Path | None:
    """Resolve an assigned source path, including common UTF-8 mojibake damage.

    Resolution stays within the assigned file's candidate parent directories. A
    sibling fallback is accepted only when its SHA-256 matches the assignment.
    """
    if not isinstance(value, str) or not value:
        return None

    candidate_paths = [Path(item).expanduser() for item in mojibake_repair_candidates(value)]
    existing: list[Path] = []
    for path in candidate_paths:
        if not path.is_file():
            continue
        resolved = path.resolve()
        existing.append(resolved)
        if not isinstance(expected_sha256, str) or sha256_file(resolved) == expected_sha256:
            return resolved

    if isinstance(expected_sha256, str) and expected_sha256:
        searched_parents: set[Path] = set()
        for path in candidate_paths:
            parent = path.parent
            if not parent.is_dir():
                continue
            parent = parent.resolve()
            if parent in searched_parents:
                continue
            searched_parents.add(parent)
            for sibling in parent.iterdir():
                if not sibling.is_file():
                    continue
                try:
                    if sha256_file(sibling) == expected_sha256:
                        return sibling.resolve()
                except OSError:
                    continue

    return existing[0] if existing else None


def normalize_policy_number(value: Any) -> str:
    if not isinstance(value, str) or value == NOT_SPECIFIED:
        return ""
    return "".join(char for char in value.upper() if char.isalnum())


def extract_year(date_value: Any) -> int | None:
    if not isinstance(date_value, str) or date_value == NOT_SPECIFIED:
        return None
    candidate = date_value.strip()
    if len(candidate) < 10:
        return None
    try:
        parsed = datetime.strptime(candidate[:10], "%Y-%m-%d")
    except ValueError:
        return None
    return parsed.year


def applicable_effective_date(record: dict[str, Any]) -> Any:
    document_type = record.get("document_type")
    if document_type == "endorsement":
        reference = record.get("base_policy_reference", {})
        if isinstance(reference, dict):
            return reference.get("base_policy_effective_date", NOT_SPECIFIED)
        return NOT_SPECIFIED
    if document_type in {"cancellation", "reinstatement", "audit"}:
        return record.get("transaction_effective_date", NOT_SPECIFIED)
    return record.get("policy_effective_date", NOT_SPECIFIED)


def append_review_flag(record: dict[str, Any], code: str, message: str) -> None:
    flags = record.setdefault("review_flags", [])
    if not isinstance(flags, list):
        record["review_flags"] = flags = []
    if any(isinstance(flag, dict) and flag.get("code") == code for flag in flags):
        return
    flags.append({"code": code, "message": message, "source_pages": []})
