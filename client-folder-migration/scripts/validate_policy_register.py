#!/usr/bin/env python3
"""Validate a Phase-1 Policy_Register.csv."""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

HEADERS = [
    "client_name", "lob", "policy_number", "normalized_policy_number", "carrier",
    "effective_date", "expiration_date", "policy_term", "status",
    "parent_policy_number", "notes",
]
VALID_STATUSES = {"Active", "Future", "Expired", "Unknown", "Review Required"}


def normalize(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def parse_date(value: str, row_number: int, field: str, errors: list[str]) -> date | None:
    if not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        errors.append(f"row {row_number}: {field} is not a valid YYYY-MM-DD date: {value!r}")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Policy_Register.csv")
    parser.add_argument("register")
    args = parser.parse_args()

    path = Path(args.register).expanduser().resolve()
    if not path.is_file():
        print(f"ERROR: register not found: {path}", file=sys.stderr)
        return 2

    errors: list[str] = []
    warnings: list[str] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != HEADERS:
            errors.append(f"headers must exactly equal: {HEADERS!r}; found: {reader.fieldnames!r}")
            rows = []
        else:
            rows = list(reader)

    seen_exact: set[tuple[str, str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        policy_number = row["policy_number"].strip()
        normalized = row["normalized_policy_number"].strip()
        if not policy_number:
            errors.append(f"row {row_number}: policy_number is blank")
        expected = normalize(policy_number)
        if not normalized:
            errors.append(f"row {row_number}: normalized_policy_number is blank")
        elif normalized != expected:
            errors.append(
                f"row {row_number}: normalized_policy_number {normalized!r} does not match {expected!r}"
            )

        effective = parse_date(row["effective_date"], row_number, "effective_date", errors)
        expiration = parse_date(row["expiration_date"], row_number, "expiration_date", errors)
        if effective and expiration and expiration <= effective:
            errors.append(f"row {row_number}: expiration_date must be after effective_date")

        status = row["status"].strip()
        if status not in VALID_STATUSES:
            errors.append(f"row {row_number}: unsupported status {status!r}")

        key = (normalized, row["effective_date"].strip(), row["expiration_date"].strip())
        if key in seen_exact:
            errors.append(f"row {row_number}: exact duplicate policy-term key {key!r}")
        seen_exact.add(key)

        if row["lob"].strip() == "Not specified":
            warnings.append(f"row {row_number}: LOB not specified")
        if row["carrier"].strip() == "Not specified":
            warnings.append(f"row {row_number}: carrier not specified")

    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("Validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 3

    print(f"Validation passed: {len(rows)} policy term(s) in {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
