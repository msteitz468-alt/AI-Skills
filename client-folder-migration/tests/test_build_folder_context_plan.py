from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
BUILDER = SKILL_ROOT / "scripts" / "build_folder_context_plan.py"
APPLIER = SKILL_ROOT / "scripts" / "apply_migration_plan.py"

REGISTER_HEADERS = [
    "client_name",
    "lob",
    "policy_number",
    "normalized_policy_number",
    "carrier",
    "effective_date",
    "expiration_date",
    "policy_term",
    "status",
    "parent_policy_number",
    "notes",
]

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


def register_rows() -> list[dict[str, str]]:
    return [
        {
            "client_name": "Example Client",
            "lob": "General Liability",
            "policy_number": "GL-100",
            "normalized_policy_number": "GL100",
            "carrier": "Carrier Alpha",
            "effective_date": "2025-01-01",
            "expiration_date": "2026-01-01",
            "policy_term": "25-26",
            "status": "Active",
            "parent_policy_number": "",
            "notes": "",
        },
        {
            "client_name": "Example Client",
            "lob": "Automobile",
            "policy_number": "AUTO-200",
            "normalized_policy_number": "AUTO200",
            "carrier": "Carrier Beta",
            "effective_date": "2025-01-01",
            "expiration_date": "2026-01-01",
            "policy_term": "25-26",
            "status": "Active",
            "parent_policy_number": "",
            "notes": "",
        },
    ]


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def add_source(root: Path, relative: str, content: bytes) -> dict[str, object]:
    path = root.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return {
        "relative_path": relative,
        "size_bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "extension": path.suffix.lower(),
        "artifact_hint": "pdf",
        "protected": False,
        "already_standard": False,
    }


def prepare_root(folder: str) -> Path:
    root = Path(folder) / "client"
    root.mkdir()
    write_csv(root / "Policy_Register.csv", REGISTER_HEADERS, register_rows())
    return root


def write_inventory(root: Path, records: list[dict[str, object]]) -> Path:
    path = root / "_Workflow" / "migration" / "legacy-file-inventory.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"client_root": str(root.resolve()), "records": records}),
        encoding="utf-8",
    )
    return path


def run_builder(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILDER), str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def read_plan(root: Path) -> list[dict[str, str]]:
    path = root / "_Workflow" / "migration" / "plans" / "folder-context-plan.csv"
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == PLAN_HEADERS
        return list(reader)


class FolderContextPlanTests(unittest.TestCase):
    def test_mixed_quote_folder_does_not_borrow_sibling_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = prepare_root(folder)
            records = [
                add_source(root, "Legacy Quotes/2025/General Liability Carrier Alpha Quote.pdf", b"gl"),
                add_source(root, "Legacy Quotes/2025/Automobile Carrier Beta Quote.pdf", b"auto"),
                add_source(root, "Legacy Quotes/2025/Unlabeled Quote.pdf", b"unknown"),
            ]
            write_inventory(root, records)

            result = run_builder(root, "--authorize-folder-context")

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = read_plan(root)
            self.assertEqual(len(plan), 2)
            destinations = {row["destination_relative_path"] for row in plan}
            self.assertIn(
                "Quotes/2025/General Liability/Carrier Alpha/General Liability Carrier Alpha Quote.pdf",
                destinations,
            )
            self.assertIn(
                "Quotes/2025/Automobile/Carrier Beta/Automobile Carrier Beta Quote.pdf",
                destinations,
            )
            self.assertNotIn("Unlabeled Quote.pdf", " ".join(destinations))
            review = json.loads(
                (root / "_Workflow" / "migration" / "plans" / "folder-context-plan.review.json").read_text(encoding="utf-8")
            )
            unlabeled = next(item for item in review["review"] if item["source_path"].endswith("Unlabeled Quote.pdf"))
            self.assertEqual(unlabeled["status"], "unresolved")
            self.assertIn("quote lob", unlabeled["reason"])
            self.assertIn("quote carrier", unlabeled["reason"])

            validation = subprocess.run(
                [
                    sys.executable,
                    str(APPLIER),
                    str(root),
                    str(root / "_Workflow" / "migration" / "plans" / "folder-context-plan.csv"),
                    "--allow-folder-context",
                    "--allow-partial-plan",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_exact_register_and_document_category_build_policy_destination(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = prepare_root(folder)
            records = [add_source(root, "Legacy/Policies/25-26/GL-100 Policy.pdf", b"policy")]
            write_inventory(root, records)

            result = run_builder(root, "--authorize-folder-context")

            self.assertEqual(result.returncode, 0, result.stderr)
            row = read_plan(root)[0]
            self.assertEqual(row["lob"], "General Liability")
            self.assertEqual(row["policy_number"], "GL-100")
            self.assertEqual(
                row["destination_relative_path"],
                "Policies/2025/General Liability/GL-100 Policy.pdf",
            )
            self.assertTrue(row["reason"].startswith("User-authorized folder-context routing."))

    def test_reviewed_override_resolves_unlabeled_quote(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = prepare_root(folder)
            source = "Legacy Quotes/2025/Unlabeled Quote.pdf"
            records = [add_source(root, source, b"quote")]
            write_inventory(root, records)
            overrides = root / "reviewed-overrides.csv"
            write_csv(
                overrides,
                OVERRIDE_HEADERS,
                [
                    {
                        "source_path": source,
                        "action": "copy",
                        "artifact_kind": "quote",
                        "client_name": "Example Client",
                        "lob": "General Liability",
                        "policy_term": "25-26",
                        "policy_number": "",
                        "effective_date": "2025-01-01",
                        "document_category": "",
                        "year": "2025",
                        "carrier": "Carrier Alpha",
                        "final_filename": "",
                        "destination_relative_path": "",
                        "reason": "Reviewed against the quote cover page.",
                    }
                ],
            )

            result = run_builder(
                root,
                "--overrides",
                str(overrides),
                "--authorize-folder-context",
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            row = read_plan(root)[0]
            self.assertEqual(row["action"], "copy")
            self.assertEqual(
                row["destination_relative_path"],
                "Quotes/2025/General Liability/Carrier Alpha/Unlabeled Quote.pdf",
            )
            self.assertIn("reviewed override", row["reason"])

    def test_prior_history_duplicate_content_and_long_paths_are_handled(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = prepare_root(folder)
            duplicate_content = b"same quote"
            prior = add_source(root, "Legacy Quotes/2025/General Liability Carrier Alpha Prior.pdf", b"prior")
            records = [
                prior,
                add_source(root, "Legacy Quotes/2025/General Liability Carrier Alpha A.pdf", duplicate_content),
                add_source(root, "Legacy Quotes/2025/General Liability Carrier Alpha B.pdf", duplicate_content),
                add_source(root, f"Legacy/Schedules/2025/{'A' * 170}.pdf", b"schedule"),
            ]
            write_inventory(root, records)
            write_csv(
                root / "_Workflow" / "migration" / "cleanup-move-log.csv",
                MOVE_LOG_HEADERS,
                [
                    {
                        "run_id": "prior",
                        "applied_at_utc": "2026-01-01T00:00:00Z",
                        "plan_file": "prior.csv",
                        "source_path": str(prior["relative_path"]),
                        "planned_destination": "Quotes/2025/General Liability/Carrier Alpha/Prior.pdf",
                        "actual_destination": "Quotes/2025/General Liability/Carrier Alpha/Prior.pdf",
                        "source_sha256": str(prior["sha256"]),
                        "action": "copy",
                        "result": "copied",
                        "notes": "",
                    }
                ],
            )

            result = run_builder(root, "--authorize-folder-context")

            self.assertEqual(result.returncode, 0, result.stderr)
            plan = read_plan(root)
            self.assertEqual(len(plan), 2)
            quote_rows = [row for row in plan if row["artifact_kind"] == "quote"]
            self.assertEqual(len(quote_rows), 1)
            schedule_row = next(row for row in plan if row["artifact_kind"] == "schedule")
            self.assertLess(len(schedule_row["final_filename"]), 175)
            self.assertIn("filename shortened", schedule_row["reason"])
            review = json.loads(
                (root / "_Workflow" / "migration" / "plans" / "folder-context-plan.review.json").read_text(encoding="utf-8")
            )
            statuses = {item["status"] for item in review["review"]}
            self.assertIn("prior-history", statuses)
            self.assertIn("duplicate-content", statuses)


if __name__ == "__main__":
    unittest.main()
