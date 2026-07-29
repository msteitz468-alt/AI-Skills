#!/usr/bin/env python3
"""Create the standardized client folder structure from Policy_Register.csv."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from migration_common import (
    PERMANENT_ROOT_FAMILIES,
    QUOTE_PROPOSAL_FOLDER,
    QUOTE_ROOT,
    ROOT_YEAR_CATEGORIES,
    load_register,
    row_effective_year,
    safe_component,
    sha256_file,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create the target migration folder structure")
    parser.add_argument("client_root")
    args = parser.parse_args()

    root = Path(args.client_root).expanduser().resolve()
    if not root.is_dir():
        print(f"ERROR: client root is not a directory: {root}", file=sys.stderr)
        return 2

    register = root / "Policy_Register.csv"
    try:
        rows, supported, years = load_register(register)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    created: list[str] = []

    def ensure(relative: str) -> None:
        path = root / relative
        if not path.exists():
            path.mkdir(parents=True, exist_ok=False)
            created.append(relative.replace("\\", "/"))
        elif not path.is_dir():
            raise RuntimeError(f"target path exists but is not a directory: {path}")

    try:
        for relative in [
            "raw",
            "Epic_Attach",
            "Markdown",
            "_Workflow",
            "_Workflow/migration",
            "_Workflow/migration/plans",
            "_Workflow/migration/logs",
            "Account",
            "Account/Permanent",
            *PERMANENT_ROOT_FAMILIES,
        ]:
            ensure(relative)

        display_pairs: dict[tuple[str, str], tuple[str, str]] = {}
        quote_paths: set[tuple[str, str, str]] = set()
        for row in rows:
            lob = row["lob"].strip()
            year = row_effective_year(row)
            key = (lob.casefold(), year)
            if key in supported and year:
                safe_lob = safe_component(lob)
                display_pairs.setdefault(key, (safe_lob, year))
                carrier = safe_component(row["carrier"].strip())
                if carrier and carrier.casefold() != "not specified":
                    quote_paths.add((year, safe_lob, carrier))

        for _, (lob, year) in sorted(display_pairs.items(), key=lambda item: (item[1][1], item[1][0].casefold())):
            ensure(f"Policies/{year}/{lob}")
            ensure(f"Applications/{year}/{lob}")

        for year in sorted(years):
            for family in ROOT_YEAR_CATEGORIES:
                ensure(f"{family}/{year}")
            ensure(f"Account/{year}")
            ensure(f"Quotes/{year}/{QUOTE_PROPOSAL_FOLDER}")

        for year, lob, carrier in sorted(
            quote_paths, key=lambda item: (item[0], item[1].casefold(), item[2].casefold())
        ):
            ensure(f"Quotes/{year}/{lob}/{carrier}")
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: failed to create structure: {exc}", file=sys.stderr)
        return 4

    manifest_path = root / "_Workflow" / "migration" / "target-structure.json"
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "client_root": str(root),
        "policy_register_sha256": sha256_file(register),
        "policy_rows": len(rows),
        "folder_schema": "client-folder-workflow",
        "supported_lob_years": [
            {"lob_key": lob, "year": year} for lob, year in sorted(supported)
        ],
        "calendar_years": sorted(years),
        "permanent_root_families": PERMANENT_ROOT_FAMILIES,
        "root_year_categories": ROOT_YEAR_CATEGORIES,
        "quote_root": QUOTE_ROOT,
        "created_directories": created,
        "epic_attach_population_rule": "Historical migration files must not be placed in Epic_Attach.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"Target structure ready: {len(created)} directorie(s) created")
    print(f"Manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
