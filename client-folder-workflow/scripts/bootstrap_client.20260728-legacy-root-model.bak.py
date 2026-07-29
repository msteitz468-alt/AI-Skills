#!/usr/bin/env python3
"""Safely initialize the control structure for a client-folder workflow."""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

POLICY_REGISTER = [
    "client_name", "lob", "policy_number", "normalized_policy_number", "carrier",
    "effective_date", "expiration_date", "policy_term", "status",
    "parent_policy_number", "notes",
]
LEDGER = [
    "run_id", "processed_at_pt", "source_email_sha256", "source_email_original_name",
    "source_email_final_path", "artifact_sha256", "artifact_kind", "artifact_original_name",
    "artifact_final_name", "client", "lob", "policy_term", "policy_number",
    "document_type", "permanent_path", "epic_path", "epic_state",
    "markdown_master_years", "markdown_master_paths", "markdown_update_state",
    "confidence", "notes",
]
EXCEPTIONS = [
    "run_id", "recorded_at_pt", "source_path", "source_sha256", "artifact_kind",
    "issue_code", "issue_summary", "evidence", "decision_needed", "confidence",
    "status", "notes",
]
PROPOSED = [
    "run_id", "proposed_at_pt", "source_path", "source_sha256", "client_name", "lob",
    "policy_number", "normalized_policy_number", "carrier", "effective_date",
    "expiration_date", "policy_term", "status", "parent_policy_number",
    "proposal_reason", "confidence", "review_status", "notes",
]


def write_header_if_missing(path: Path, headers: list[str]) -> str:
    if path.exists() and path.stat().st_size > 0:
        return "preserved"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow(headers)
    return "created"


def validate_headers(path: Path, required: list[str]) -> list[str]:
    if not path.exists() or path.stat().st_size == 0:
        return ["file missing or empty"]
    with path.open("r", newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return ["header row missing"]
    problems: list[str] = []
    for name in required:
        count = headers.count(name)
        if count != 1:
            problems.append(f"required column {name!r} occurs {count} times")
    return problems


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relocate_legacy_register(root: Path, workflow: Path) -> list[str]:
    """Move a legacy root register into _Workflow without losing conflicts."""
    legacy = root / "Policy_Register.csv"
    target = workflow / "Policy_Register.csv"
    if not legacy.exists():
        return []

    if not target.exists() or target.stat().st_size == 0:
        legacy.replace(target)
        print(f"relocated: {legacy} -> {target}")
        return []

    if legacy.stat().st_size > 0 and sha256(legacy) != sha256(target):
        return [
            "conflicting policy registers exist at "
            f"{legacy} and {target}; resolve them before processing raw"
        ]

    backup = workflow / "logs" / "legacy-root-Policy_Register.csv"
    suffix = 2
    while backup.exists():
        backup = workflow / "logs" / f"legacy-root-Policy_Register ({suffix}).csv"
        suffix += 1
    legacy.replace(backup)
    print(f"relocated duplicate legacy register: {legacy} -> {backup}")
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("client_root", help="Client root to initialize")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    raw = root / "raw"
    if not root.is_dir():
        print(f"ERROR: client root is not a directory: {root}", file=sys.stderr)
        return 2
    workflow = root / "_Workflow"
    for folder in (raw, workflow, workflow / "staging", workflow / "plans", workflow / "logs"):
        existed = folder.exists()
        folder.mkdir(parents=True, exist_ok=True)
        print(f"{'preserved' if existed else 'created'}: {folder}")

    relocation_errors = relocate_legacy_register(root, workflow)
    if relocation_errors:
        print("ERROR: policy register relocation failed:", file=sys.stderr)
        for error in relocation_errors:
            print(f"- {error}", file=sys.stderr)
        return 3

    files = {
        workflow / "Policy_Register.csv": POLICY_REGISTER,
        workflow / "processing-ledger.csv": LEDGER,
        workflow / "exceptions.csv": EXCEPTIONS,
        workflow / "proposed-policy-register-updates.csv": PROPOSED,
    }

    for path, headers in files.items():
        state = write_header_if_missing(path, headers)
        print(f"{state}: {path}")

    summary = workflow / "last-run-summary.md"
    if not summary.exists():
        summary.write_text(
            "# Last Run Summary\n\nNo verified processing run has completed yet.\n",
            encoding="utf-8",
        )
        print(f"created: {summary}")
    else:
        print(f"preserved: {summary}")

    errors: list[str] = []
    for path, headers in files.items():
        for problem in validate_headers(path, headers):
            errors.append(f"{path}: {problem}")

    if errors:
        print("ERROR: initialization validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 3

    print("Bootstrap validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
