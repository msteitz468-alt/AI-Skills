#!/usr/bin/env python3
"""Build a deterministic, reviewable folder-context migration plan."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath

from migration_common import (
    ACCOUNT_ROUTED_CATEGORIES,
    APPLICATION_ROUTED_CATEGORIES,
    MOVE_LOG_HEADERS,
    PLAN_HEADERS,
    POLICY_ROUTED_CATEGORIES,
    QUOTE_PROPOSAL_FOLDER,
    load_register,
    normalize_policy_number,
    parse_relative_path,
    row_effective_year,
    safe_component,
    sha256_file,
    to_native,
    year_from_term,
)

OVERRIDE_HEADERS = [
    "source_path",
    "action",
    "artifact_kind",
    "client_name",
    "lob",
    "policy_term",
    "policy_number",
    "effective_date",
    "document_category",
    "year",
    "carrier",
    "final_filename",
    "destination_relative_path",
    "reason",
]

MAX_WINDOWS_TEMP_PATH = 240
TERM_RE = re.compile(r"(?<!\d)(\d{2})[-_ ](\d{2})(?!\d)")
YEAR_RE = re.compile(r"(?<!\d)(20\d{2})(?!\d)")

CATEGORY_PATTERNS = [
    ("Application - Submission", ("application", "submission", "sov", "tiv", "underwriting packet")),
    ("Binder - Bind Order", ("binder", "bind order", "bind request")),
    ("Accounting", ("accounting", "invoice", "premium finance")),
    ("Policy - End - Summary", ("policy", "policies", "endorsement", "endt")),
    ("Certificates", ("certificate", "certificates", "coi")),
    ("Audits", ("audit", "audits")),
    ("Carrier Correspondence", ("carrier correspondence",)),
    ("Correspondence & Email", ("correspondence", "email", "emails")),
]

ROOT_FAMILY_PATTERNS = [
    ("Schedules", ("schedule", "schedules", "specs")),
    ("Loss Runs", ("loss run", "loss runs", "loss history")),
    ("Quotes", ("quote", "quotes", "proposal", "proposals", "indication")),
    ("Applications", ("application", "applications", "submission", "submissions")),
    ("Policies", ("policy", "policies", "endorsement", "endt", "binder", "certificate", "audit")),
    ("Stewardship", ("stewardship", "program review", "renewal strategy")),
    ("Broker of Record Info", ("broker of record", "bor")),
    ("Account", ("account", "surplus lines", "record of insurance", "pre-renewal")),
]


def normalized_words(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def phrase_present(text: str, phrase: str) -> bool:
    haystack = f" {normalized_words(text)} "
    needle = normalized_words(phrase)
    return bool(needle) and f" {needle} " in haystack


def unique_phrase_match(text: str, values: set[str]) -> str:
    matches = {value for value in values if phrase_present(text, value)}
    return next(iter(matches)) if len(matches) == 1 else ""


def detect_named_value(text: str, patterns: list[tuple[str, tuple[str, ...]]]) -> str:
    matches = {
        value
        for value, phrases in patterns
        if any(phrase_present(text, phrase) for phrase in phrases)
    }
    return next(iter(matches)) if len(matches) == 1 else ""


def extract_year(text: str) -> str:
    years = set(YEAR_RE.findall(text))
    for start, _ in TERM_RE.findall(text):
        years.add(f"20{start}")
    return next(iter(years)) if len(years) == 1 else ""


def extract_term(text: str, register_rows: list[dict[str, str]]) -> str:
    supported_terms = {row["policy_term"].strip() for row in register_rows}
    explicit = {
        f"{start}-{end}"
        for start, end in TERM_RE.findall(text)
        if f"{start}-{end}" in supported_terms
    }
    if len(explicit) == 1:
        return next(iter(explicit))
    if explicit:
        return ""

    year = extract_year(text)
    if not year:
        return ""
    terms = {
        row["policy_term"].strip()
        for row in register_rows
        if row_effective_year(row) == year
    }
    return next(iter(terms)) if len(terms) == 1 else ""


def match_register_row(
    text: str,
    policy_term: str,
    register_rows: list[dict[str, str]],
) -> dict[str, str] | None:
    haystack = normalize_policy_number(text)
    candidates = [
        row
        for row in register_rows
        if len(row["normalized_policy_number"].strip()) >= 5
        and row["normalized_policy_number"].strip() in haystack
    ]
    if policy_term:
        term_candidates = [
            row for row in candidates if row["policy_term"].strip() == policy_term
        ]
        if len(term_candidates) == 1:
            return term_candidates[0]
    return candidates[0] if len(candidates) == 1 else None


def is_quote_source(relative: PurePosixPath) -> bool:
    parents = " ".join(relative.parts[:-1])
    return any(
        phrase_present(parents, value)
        for value in ("quote", "quotes", "proposal", "proposals")
    )


def fit_destination(
    root: Path,
    destination: PurePosixPath,
) -> tuple[PurePosixPath | None, bool]:
    native = to_native(root, destination)
    collision = native.with_name(f"{native.stem} (999){native.suffix}")
    temporary = collision.with_name(
        f".{collision.name}.migrationtmp-{'0' * 32}"
    )
    excess = len(str(temporary)) - MAX_WINDOWS_TEMP_PATH
    if excess <= 0:
        return destination, False

    shortened_stem = native.stem[: max(1, len(native.stem) - excess)].rstrip(" .")
    if not shortened_stem:
        return None, False
    shortened = native.with_name(f"{shortened_stem}{native.suffix}")
    collision = shortened.with_name(f"{shortened.stem} (999){shortened.suffix}")
    temporary = collision.with_name(
        f".{collision.name}.migrationtmp-{'0' * 32}"
    )
    if len(str(temporary)) > MAX_WINDOWS_TEMP_PATH:
        return None, False
    relative = PurePosixPath(*shortened.relative_to(root).parts)
    return relative, True


def read_inventory(path: Path, root: Path) -> list[dict[str, object]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read inventory {path}: {exc}") from exc
    inventory_root = payload.get("client_root")
    if inventory_root and Path(str(inventory_root)).expanduser().resolve() != root:
        raise ValueError("inventory client_root does not match the selected client root")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("inventory records must be a JSON list")
    return records


def read_move_log(path: Path) -> dict[str, list[dict[str, str]]]:
    history: dict[str, list[dict[str, str]]] = defaultdict(list)
    if not path.is_file():
        return history
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MOVE_LOG_HEADERS:
            raise ValueError(
                f"move log headers must exactly equal {MOVE_LOG_HEADERS!r}; "
                f"found {reader.fieldnames!r}"
            )
        for row in reader:
            if row["result"].strip() in {
                "moved",
                "copied",
                "duplicate_destination",
            }:
                history[row["source_sha256"].strip().lower()].append(row)
    return history


def read_overrides(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != OVERRIDE_HEADERS:
            raise ValueError(
                f"override headers must exactly equal {OVERRIDE_HEADERS!r}; "
                f"found {reader.fieldnames!r}"
            )
        rows: dict[str, dict[str, str]] = {}
        for index, row in enumerate(reader, start=2):
            source = row["source_path"].replace("\\", "/").strip()
            if not source:
                raise ValueError(f"override row {index} has an empty source_path")
            key = source.casefold()
            if key in rows:
                raise ValueError(f"override row {index} duplicates source_path {source!r}")
            rows[key] = {field: value.strip() for field, value in row.items()}
        return rows


def make_leave_row(
    record: dict[str, object],
    relative: PurePosixPath,
    reason: str,
    fields: dict[str, str] | None = None,
    action: str = "leave",
) -> dict[str, str]:
    fields = fields or {}
    return {
        "source_path": relative.as_posix(),
        "source_sha256": str(record.get("sha256") or ""),
        "size_bytes": str(record.get("size_bytes") or ""),
        "artifact_kind": fields.get("artifact_kind", str(record.get("artifact_hint") or "other")),
        "client_name": fields.get("client_name", ""),
        "lob": fields.get("lob", ""),
        "policy_term": fields.get("policy_term", ""),
        "policy_number": fields.get("policy_number", ""),
        "effective_date": fields.get("effective_date", ""),
        "document_category": fields.get("document_category", ""),
        "final_filename": "",
        "destination_relative_path": "",
        "confidence": "low" if action == "leave" else "high",
        "action": action,
        "reason": reason,
    }


def write_plan(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=PLAN_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic partial folder-context migration plan"
    )
    parser.add_argument("client_root")
    parser.add_argument("--inventory")
    parser.add_argument("--move-log")
    parser.add_argument("--overrides")
    parser.add_argument("--output")
    parser.add_argument("--review-report")
    parser.add_argument(
        "--authorize-folder-context",
        action="store_true",
        help="Emit high-confidence move/copy actions after user review and authorization",
    )
    parser.add_argument(
        "--include-unresolved",
        action="store_true",
        help="Include unresolved records as leave rows instead of only in the review report",
    )
    parser.add_argument("--force", action="store_true", help="Replace existing outputs")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: client root is not a directory: {root}", file=sys.stderr)
        return 2

    inventory_path = (
        Path(args.inventory).expanduser().resolve()
        if args.inventory
        else root / "_Workflow" / "migration" / "legacy-file-inventory.json"
    )
    move_log_path = (
        Path(args.move_log).expanduser().resolve()
        if args.move_log
        else root / "_Workflow" / "migration" / "cleanup-move-log.csv"
    )
    overrides_path = Path(args.overrides).expanduser().resolve() if args.overrides else None
    output_path = (
        Path(args.output).expanduser().resolve()
        if args.output
        else root / "_Workflow" / "migration" / "plans" / "folder-context-plan.csv"
    )
    review_path = (
        Path(args.review_report).expanduser().resolve()
        if args.review_report
        else output_path.with_suffix(".review.json")
    )
    if not args.force and (output_path.exists() or review_path.exists()):
        print("ERROR: output already exists; use --force to replace it", file=sys.stderr)
        return 2

    try:
        register_rows, _, _ = load_register(root / "Policy_Register.csv")
        records = read_inventory(inventory_path, root)
        history = read_move_log(move_log_path)
        overrides = read_overrides(overrides_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    register_lobs = {
        row["lob"].strip()
        for row in register_rows
        if row["lob"].strip() and row["lob"].strip().casefold() != "not specified"
    }
    register_carriers = {
        row["carrier"].strip() for row in register_rows if row["carrier"].strip()
    }
    plan_rows: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    actionable_candidates: list[tuple[int, str, dict[str, str], dict[str, str]]] = []
    inventory_sources: set[str] = set()

    candidates = sorted(
        (
            record
            for record in records
            if isinstance(record, dict)
            and not record.get("protected")
            and not record.get("already_standard")
            and not record.get("error")
            and record.get("sha256")
        ),
        key=lambda record: str(record.get("relative_path", "")).casefold(),
    )

    for record in candidates:
        source_text = str(record.get("relative_path", "")).replace("\\", "/").strip()
        try:
            relative = parse_relative_path(source_text)
        except ValueError as exc:
            review.append({"source_path": source_text, "status": "error", "reason": str(exc)})
            continue
        source_key = relative.as_posix().casefold()
        inventory_sources.add(source_key)
        digest = str(record.get("sha256") or "").lower()
        override = overrides.get(source_key, {})

        if history.get(digest) and not override:
            reason = "Matching content already has a successful move/copy history entry."
            review.append({"source_path": relative.as_posix(), "status": "prior-history", "reason": reason})
            if args.include_unresolved:
                plan_rows.append(make_leave_row(record, relative, reason))
            continue

        context = relative.as_posix()
        policy_term = extract_term(context, register_rows)
        register_row = match_register_row(context, policy_term, register_rows)
        fields = {
            "artifact_kind": str(record.get("artifact_hint") or "other"),
            "client_name": register_row["client_name"].strip() if register_row else "",
            "lob": register_row["lob"].strip() if register_row else unique_phrase_match(context, register_lobs),
            "policy_term": register_row["policy_term"].strip() if register_row else policy_term,
            "policy_number": register_row["policy_number"].strip() if register_row else "",
            "effective_date": register_row["effective_date"].strip() if register_row else "",
            "document_category": detect_named_value(context, CATEGORY_PATTERNS),
            "year": row_effective_year(register_row) if register_row else extract_year(context),
            "carrier": register_row["carrier"].strip() if register_row else unique_phrase_match(context, register_carriers),
        }
        root_family = detect_named_value(context, ROOT_FAMILY_PATTERNS)
        if root_family == "Quotes":
            fields["artifact_kind"] = "quote"
        elif root_family == "Loss Runs":
            fields["artifact_kind"] = "loss-run"
        elif root_family == "Schedules":
            fields["artifact_kind"] = "schedule"
        elif root_family == "Applications":
            fields["artifact_kind"] = "application"
        elif root_family == "Policies":
            fields["artifact_kind"] = fields.get("artifact_kind") or "policy"
        elif root_family == "Stewardship":
            fields["artifact_kind"] = "stewardship"
        elif root_family == "Broker of Record Info":
            fields["artifact_kind"] = "bor"
        elif root_family == "Account":
            fields["artifact_kind"] = "account"

        for key in (
            "artifact_kind",
            "client_name",
            "lob",
            "policy_term",
            "policy_number",
            "effective_date",
            "document_category",
            "year",
            "carrier",
        ):
            if override.get(key):
                fields[key] = override[key]

        if not fields["year"] and fields["policy_term"]:
            fields["year"] = year_from_term(fields["policy_term"])

        explicit_action = override.get("action", "").casefold()
        if explicit_action and explicit_action not in {"move", "copy", "leave", "skip"}:
            review.append({"source_path": relative.as_posix(), "status": "error", "reason": f"Unsupported override action: {explicit_action}"})
            continue
        if explicit_action in {"leave", "skip"}:
            reason = override.get("reason") or "Explicit reviewed override."
            plan_rows.append(make_leave_row(record, relative, reason, fields, explicit_action))
            review.append({"source_path": relative.as_posix(), "status": explicit_action, "reason": reason})
            continue

        quote_source = is_quote_source(relative)
        quote_proposal = phrase_present(context, "quote proposal")
        action = explicit_action or ("copy" if quote_source else "move")
        filename = override.get("final_filename") or safe_component(relative.name)
        destination_text = override.get("destination_relative_path", "")
        basis: list[str] = []
        if register_row:
            basis.append("exact register policy-number match")
        if root_family:
            basis.append(f"root family {root_family}")
        if fields["document_category"]:
            basis.append(f"document category {fields['document_category']}")
        if quote_source:
            basis.append("quote/proposal source preserved by copy")
        if quote_proposal:
            basis.append("quote proposal multi-line presentation")
        if override:
            basis.append("reviewed override")

        missing: list[str] = []
        if destination_text:
            try:
                destination = parse_relative_path(destination_text)
            except ValueError as exc:
                review.append({"source_path": relative.as_posix(), "status": "error", "reason": str(exc)})
                continue
            filename = destination.name
        elif root_family == "Schedules" or (
            not root_family and fields["document_category"] == "" and phrase_present(context, "schedule")
        ):
            if not fields["year"]:
                missing.append("schedule year")
                destination = None
            else:
                destination = PurePosixPath("Schedules", fields["year"], filename)
        elif root_family == "Loss Runs":
            if not fields["year"]:
                missing.append("loss-run pulled/valued/generated year")
                destination = None
            else:
                destination = PurePosixPath("Loss Runs", fields["year"], filename)
        elif root_family == "Quotes" or quote_source:
            if quote_proposal:
                if not fields["year"]:
                    missing.append("quote year")
                    destination = None
                else:
                    destination = PurePosixPath("Quotes", fields["year"], QUOTE_PROPOSAL_FOLDER, filename)
            else:
                for key in ("year", "lob", "carrier"):
                    if not fields[key]:
                        missing.append(f"quote {key}")
                destination = (
                    PurePosixPath("Quotes", fields["year"], fields["lob"], fields["carrier"], filename)
                    if not missing
                    else None
                )
        elif root_family == "Stewardship":
            if not fields["year"]:
                missing.append("stewardship year")
                destination = None
            else:
                destination = PurePosixPath("Stewardship", fields["year"], filename)
        elif root_family == "Broker of Record Info":
            destination = PurePosixPath("Broker of Record Info", filename)
        elif root_family == "Account":
            if not fields["year"]:
                missing.append("account year")
                destination = None
            else:
                destination = PurePosixPath("Account", fields["year"], filename)
        elif root_family == "Applications" or fields["document_category"] in APPLICATION_ROUTED_CATEGORIES:
            for key in ("year", "lob"):
                if not fields[key]:
                    missing.append(key)
            destination = (
                PurePosixPath("Applications", fields["year"], fields["lob"], filename)
                if not missing
                else None
            )
        elif root_family == "Policies" or fields["document_category"] in POLICY_ROUTED_CATEGORIES:
            for key in ("year", "lob"):
                if not fields[key]:
                    missing.append(key)
            destination = (
                PurePosixPath("Policies", fields["year"], fields["lob"], filename)
                if not missing
                else None
            )
        elif fields["document_category"] in ACCOUNT_ROUTED_CATEGORIES:
            if not fields["year"]:
                missing.append("year")
                destination = None
            else:
                destination = PurePosixPath("Account", fields["year"], filename)
        else:
            missing.append("root family or document category")
            destination = None

        if missing or destination is None:
            reason = "Unresolved deterministic routing: " + ", ".join(missing) + "."
            review.append({"source_path": relative.as_posix(), "status": "unresolved", "reason": reason})
            if args.include_unresolved:
                plan_rows.append(make_leave_row(record, relative, reason, fields))
            continue

        fitted, shortened = fit_destination(root, destination)
        if fitted is None:
            reason = "Destination cannot fit the Windows temporary-path safety limit."
            review.append({"source_path": relative.as_posix(), "status": "unresolved", "reason": reason})
            if args.include_unresolved:
                plan_rows.append(make_leave_row(record, relative, reason, fields))
            continue
        destination = fitted
        filename = destination.name

        existing = to_native(root, destination)
        if existing.is_file() and sha256_file(existing) == digest and not override:
            reason = "An identical approved destination already exists; source remains in place."
            review.append({"source_path": relative.as_posix(), "status": "duplicate-destination", "reason": reason})
            if args.include_unresolved:
                plan_rows.append(make_leave_row(record, relative, reason, fields))
            continue

        reason_bits = list(basis)
        if shortened:
            reason_bits.append("filename shortened for Windows temporary-path safety")
        if override.get("reason"):
            reason_bits.append(override["reason"])
        reason = "; ".join(reason_bits) + "."
        row = {
            "source_path": relative.as_posix(),
            "source_sha256": digest,
            "size_bytes": str(record.get("size_bytes") or ""),
            "artifact_kind": fields["artifact_kind"],
            "client_name": fields["client_name"],
            "lob": fields["lob"],
            "policy_term": fields["policy_term"],
            "policy_number": fields["policy_number"],
            "effective_date": fields["effective_date"],
            "document_category": fields["document_category"],
            "final_filename": filename,
            "destination_relative_path": destination.as_posix(),
            "confidence": "high",
            "action": action,
            "reason": "User-authorized folder-context routing. " + reason,
        }
        score = (4 if register_row else 0) + (2 if root_family else 0) + (1 if override else 0)
        actionable_candidates.append((score, source_key, row, fields))

    unknown_overrides = sorted(set(overrides) - inventory_sources)
    if unknown_overrides:
        print(f"ERROR: overrides reference sources not present in inventory: {unknown_overrides}", file=sys.stderr)
        return 4

    by_hash: dict[str, list[tuple[int, str, dict[str, str], dict[str, str]]]] = defaultdict(list)
    for candidate in actionable_candidates:
        by_hash[candidate[2]["source_sha256"]].append(candidate)
    for digest, duplicates in sorted(by_hash.items()):
        ranked = sorted(duplicates, key=lambda item: (-item[0], item[1]))
        winner = ranked[0]
        if args.authorize_folder_context:
            plan_rows.append(winner[2])
            review.append({"source_path": winner[2]["source_path"], "status": "actionable", "reason": winner[2]["reason"]})
        else:
            reason = "Candidate requires explicit --authorize-folder-context after review."
            review.append({"source_path": winner[2]["source_path"], "status": "candidate", "reason": reason, "proposed_destination": winner[2]["destination_relative_path"]})
            if args.include_unresolved:
                source_record = next(record for record in candidates if str(record.get("sha256") or "").lower() == digest and str(record.get("relative_path", "")).replace("\\", "/").casefold() == winner[1])
                plan_rows.append(make_leave_row(source_record, parse_relative_path(winner[2]["source_path"]), reason, winner[3]))
        for duplicate in ranked[1:]:
            reason = f"Duplicate content suppressed in favor of {winner[2]['source_path']}."
            review.append({"source_path": duplicate[2]["source_path"], "status": "duplicate-content", "reason": reason})

    plan_rows.sort(key=lambda row: row["source_path"].casefold())
    review.sort(key=lambda row: row.get("source_path", "").casefold())
    try:
        write_plan(output_path, plan_rows)
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_payload = {
            "client_root": str(root),
            "authorized": args.authorize_folder_context,
            "plan_row_count": len(plan_rows),
            "actionable_count": sum(row["action"] in {"move", "copy"} for row in plan_rows),
            "review": review,
        }
        review_path.write_text(
            json.dumps(review_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"ERROR: could not write outputs: {exc}", file=sys.stderr)
        return 5

    print(
        f"Folder-context plan written: {output_path} "
        f"({len(plan_rows)} rows; {review_payload['actionable_count']} actionable)"
    )
    print(f"Review report: {review_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
