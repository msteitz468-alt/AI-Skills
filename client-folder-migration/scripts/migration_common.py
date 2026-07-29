#!/usr/bin/env python3
"""Shared constants and safety helpers for client-folder migration scripts."""
from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path, PurePosixPath
from typing import Iterable

REGISTER_HEADERS = [
    "client_name", "lob", "policy_number", "normalized_policy_number", "carrier",
    "effective_date", "expiration_date", "policy_term", "status",
    "parent_policy_number", "notes",
]

# Classification labels retained in migration plans. Destination paths use the
# client-folder-workflow permanent families instead of these category folders.
DOCUMENT_CATEGORIES = [
    "Application - Submission",
    "Binder - Bind Order",
    "Accounting",
    "Policy - End - Summary",
    "Certificates",
    "Audits",
    "Carrier Correspondence",
    "Correspondence & Email",
]

POLICY_ROUTED_CATEGORIES = {
    "Binder - Bind Order",
    "Accounting",
    "Policy - End - Summary",
    "Certificates",
    "Audits",
    "Carrier Correspondence",
}

APPLICATION_ROUTED_CATEGORIES = {
    "Application - Submission",
}

ACCOUNT_ROUTED_CATEGORIES = {
    "Correspondence & Email",
}

# Permanent root families matching client-folder-workflow.
PERMANENT_ROOT_FAMILIES = [
    "Account",
    "Applications",
    "Broker of Record Info",
    "Loss Runs",
    "Stewardship",
    "Policies",
    "Quotes",
    "Schedules",
]

ROOT_YEAR_CATEGORIES = [
    "Schedules",
    "Loss Runs",
    "Stewardship",
]

QUOTE_ROOT = "Quotes"
QUOTE_PROPOSAL_FOLDER = "Quote Proposal"

PLAN_HEADERS = [
    "source_path",
    "source_sha256",
    "size_bytes",
    "artifact_kind",
    "client_name",
    "lob",
    "policy_term",
    "policy_number",
    "effective_date",
    "document_category",
    "final_filename",
    "destination_relative_path",
    "confidence",
    "action",
    "reason",
]

MOVE_LOG_HEADERS = [
    "run_id",
    "applied_at_utc",
    "plan_file",
    "source_path",
    "planned_destination",
    "actual_destination",
    "source_sha256",
    "action",
    "result",
    "notes",
]

PROTECTED_DIR_NAMES = {
    ".git", ".svn", ".hg", ".codex", ".agents", "_workflow", "epic_attach", "legacy files",
    "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "site-packages",
}

PROTECTED_FILE_NAMES = {
    "agents.md", "skill.md", "codex.md", "policy_register.csv",
    "thumbs.db", ".ds_store", "desktop.ini",
}
PRESERVE_ONLY_ROOT_DIR_NAMES: set[str] = set()

WINDOWS_INVALID_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
TERM_RE = re.compile(r"^\d{2}-\d{2}$")
YEAR_RE = re.compile(r"^\d{4}$")
HEX64_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_policy_number(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def safe_component(value: str) -> str:
    cleaned = WINDOWS_INVALID_RE.sub("-", value).strip().rstrip(". ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def is_windows_safe_filename(name: str) -> bool:
    return bool(name) and not WINDOWS_INVALID_RE.search(name) and not name.endswith((".", " "))


def parse_relative_path(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return path


def to_native(root: Path, relative: PurePosixPath) -> Path:
    return root.joinpath(*relative.parts)


def load_register(register_path: Path) -> tuple[list[dict[str, str]], set[tuple[str, str]], set[str]]:
    """Return rows, supported (lob.casefold(), year) pairs, and calendar years."""
    if not register_path.is_file():
        raise ValueError(f"Policy_Register.csv not found: {register_path}")

    with register_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != REGISTER_HEADERS:
            raise ValueError(
                f"Policy_Register.csv headers must exactly equal {REGISTER_HEADERS!r}; "
                f"found {reader.fieldnames!r}"
            )
        rows = list(reader)

    if not rows:
        raise ValueError("Policy_Register.csv is header-only; Phase 2 requires at least one policy row")

    supported: set[tuple[str, str]] = set()
    years: set[str] = set()
    for index, row in enumerate(rows, start=2):
        policy_number = row["policy_number"].strip()
        normalized = row["normalized_policy_number"].strip()
        if not policy_number or normalize_policy_number(policy_number) != normalized:
            raise ValueError(f"Policy_Register.csv row {index} has an invalid normalized policy number")
        lob = row["lob"].strip()
        year = row_effective_year(row)
        if year:
            years.add(year)
            if lob and lob.lower() != "not specified":
                supported.add((lob.casefold(), year))
    return rows, supported, years


def year_from_term(term: str) -> str:
    if TERM_RE.fullmatch(term):
        return f"20{term[:2]}"
    return ""


def row_effective_year(row: dict[str, str]) -> str:
    effective = row.get("effective_date", "").strip()
    if len(effective) >= 4 and effective[:4].isdigit():
        return effective[:4]
    return year_from_term(row.get("policy_term", "").strip())


def is_temp_or_system_name(name: str) -> bool:
    lower = name.lower()
    return lower in PROTECTED_FILE_NAMES or name.startswith("~$") or lower.endswith((".tmp", ".temp", ".lock"))


def is_protected_path(relative: PurePosixPath) -> bool:
    if any(part.casefold() in PROTECTED_DIR_NAMES for part in relative.parts[:-1]):
        return True
    return is_temp_or_system_name(relative.name)


def is_root_preserve_only_source_path(relative: PurePosixPath) -> bool:
    if not relative.parts:
        return False
    root_folder = relative.parts[0].casefold()
    return root_folder in PRESERVE_ONLY_ROOT_DIR_NAMES or "rdw" in root_folder


def is_root_year_category_path(parts: tuple[str, ...]) -> bool:
    if len(parts) < 3:
        return False
    return parts[0] in ROOT_YEAR_CATEGORIES and YEAR_RE.fullmatch(parts[1]) is not None


def is_quote_path(parts: tuple[str, ...]) -> bool:
    if len(parts) < 4 or parts[0] != QUOTE_ROOT or YEAR_RE.fullmatch(parts[1]) is None:
        return False
    if parts[2].casefold() == QUOTE_PROPOSAL_FOLDER.casefold():
        return True
    return len(parts) >= 5


def is_policies_or_applications_path(
    parts: tuple[str, ...],
    supported_lob_years: set[tuple[str, str]] | None = None,
    require_register: bool = True,
) -> bool:
    if len(parts) < 4:
        return False
    if parts[0].casefold() not in {"policies", "applications"}:
        return False
    if YEAR_RE.fullmatch(parts[1]) is None:
        return False
    if not require_register:
        return True
    if supported_lob_years is None:
        return False
    return (parts[2].casefold(), parts[1]) in supported_lob_years


def is_account_path(parts: tuple[str, ...]) -> bool:
    if len(parts) < 3 or parts[0].casefold() != "account":
        return False
    if parts[1].casefold() == "permanent":
        return True
    return YEAR_RE.fullmatch(parts[1]) is not None


def is_standard_path(
    relative: PurePosixPath,
    supported_lob_years: set[tuple[str, str]],
    years: set[str],
) -> bool:
    del years  # years reserved for callers that seed structure; path shape uses register pairs
    parts = relative.parts
    if not parts:
        return False

    first = parts[0].casefold()
    if first in {"markdown", "raw", "epic_attach", "_workflow"}:
        return True

    if is_root_year_category_path(parts) or is_quote_path(parts):
        return True

    if first == "broker of record info":
        return len(parts) >= 2

    if is_account_path(parts):
        return True

    return is_policies_or_applications_path(parts, supported_lob_years, require_register=True)


def is_folder_context_path(relative: PurePosixPath) -> bool:
    parts = relative.parts
    if len(parts) < 2:
        return False
    first = parts[0].casefold()
    if first == "markdown":
        return True
    if is_root_year_category_path(parts) or is_quote_path(parts):
        return True
    if first == "broker of record info":
        return True
    if is_account_path(parts):
        return True
    return is_policies_or_applications_path(parts, require_register=False)


def destination_is_approved(
    relative: PurePosixPath,
    supported_lob_years: set[tuple[str, str]],
    years: set[str],
) -> bool:
    parts = relative.parts
    if len(parts) < 2:
        return False
    if parts[0].casefold() == "markdown":
        return True
    return is_standard_path(relative, supported_lob_years, years)


def destination_is_folder_context_approved(relative: PurePosixPath) -> bool:
    parts = relative.parts
    if len(parts) < 2:
        return False
    if parts[0].casefold() == "markdown":
        return True
    return is_folder_context_path(relative)


def iter_files(root: Path, excluded_dir_names: Iterable[str] = ()):
    excluded = {name.casefold() for name in excluded_dir_names}
    for path in sorted(root.rglob("*"), key=lambda p: str(p).casefold()):
        if not path.is_file():
            continue
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part.casefold() in excluded for part in relative.parts[:-1]):
            continue
        yield path, PurePosixPath(*relative.parts)
