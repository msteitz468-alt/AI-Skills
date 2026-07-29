---
name: client-folder-migration
description: >
  Two-phase migration workflow for legacy commercial-insurance client folders.
  Use when Codex or ChatGPT must build a client Policy_Register.csv from existing
  Markdown or JSON policy knowledge, create the same legacy-style permanent folder
  schema as client-folder-workflow (Account, Applications, Policies, Quotes,
  Schedules, Loss Runs, Stewardship, Broker of Record Info), and safely plan, rename,
  and move legacy files into that structure with an auditable migration log,
  including explicit user-authorized folder-context moves based on legacy folder logic.
---

# Client Folder Migration

## Core rule

Treat the selected directory as one client root. Never inspect or modify sibling client folders. Build and validate the policy register before restructuring files, and always create a migration plan before moving anything.

## Root `Legacy Files` Protection

A folder named exactly `Legacy Files` directly under the selected client root is a preserved archive by default. Do not inventory, read, hash, copy, move, rename, delete, classify, route, or include anything inside `<client-root>/Legacy Files/` in migration plans unless the user specifically asks to process that folder by name. This root-level archive rule is distinct from ordinary legacy source folders used for routing context; the skill also treats any nested folder named exactly `Legacy Files` as protected unless the user explicitly overrides that folder by name.


Read these references before execution:

- [references/policy-register-phase-1.md](references/policy-register-phase-1.md) for register discovery and extraction.
- [references/commercial-lines-standard.md](references/commercial-lines-standard.md) for folder and filename standards.
- [references/legacy-folder-transition-phase-2.md](references/legacy-folder-transition-phase-2.md) for migration planning, application, and verification.

## Execution modes

- **Phase 1 only:** When the user asks only to build the policy register, complete Phase 1 and stop.
- **Full migration:** When the user asks to transition, migrate, reorganize, or convert a legacy client folder, complete Phase 1 and then Phase 2.
- **Resume Phase 2:** When a valid nonempty `Policy_Register.csv` already exists, preserve it and begin Phase 2 unless the user explicitly asks to rebuild it.
- **Folder-context cleanup:** When the user explicitly asks to move files based on legacy folders, current folders, or "where they are located," preserve the register, use legacy folder context as routing authority for selected files, and run the opt-in folder-context validation path in Phase 2.
- **Rename-only recovery:** When the user asks to restore original filenames, undo standardized names, or recover from an overbroad rename pass while keeping files in their current folders, preserve folder placement and use the rename-only recovery path in Phase 2. Do not move files back to legacy folders unless the user explicitly asks for a separate move-back plan.

## Runtime preflight

Before creating or changing any client file:

1. Verify that `python` can execute the bundled helpers, for example `python --version` and one helper with `--help`.
2. If `python` resolves only to a Microsoft Store alias or cannot run scripts, try `py -3` and use that launcher consistently for the entire migration.
3. If neither interpreter works, stop before modifying the client root. Do not silently reimplement the migration in shell commands; report the missing runtime and request installation or an explicitly approved fallback.
4. Use helpers' direct `--output` options for JSON evidence files. Do not pass Unicode JSON inventories through shell text pipelines that may change encoding or filenames.

## Phase 1 - Build `Policy_Register.csv`

1. Check whether `Policy_Register.csv` already exists:
   - If absent, continue.
   - If header-only and valid, populate it.
   - If nonempty and valid, preserve it. Do not overwrite or merge without explicit authorization.
   - If malformed, stop before restructuring files.
2. Run:

   ```bash
   python scripts/discover_policy_sources.py <client-root> > policy-source-manifest.json
   ```

   The helper must prune every directory named exactly `Legacy Files`, case-insensitively and at any depth, before recursive traversal. It must never list or hash files below that boundary during default discovery.

3. Use the manifest search order:
   - Search `Markdown/` first, recursively, for `.md` and `.json` files.
   - If one or more supported files are found there, use only those files.
   - Otherwise search the entire client root recursively for `.md` and `.json` files, excluding operational, temporary, instruction, and generated files.
4. Read every listed source and use AI judgment to extract one row per policy term. Merge endorsements into the parent policy row.
5. Write only `<client-root>/Policy_Register.csv` using the exact reference schema and UTF-8 with BOM.
6. Run:

   ```bash
   python scripts/validate_policy_register.py <client-root>/Policy_Register.csv
   ```

7. Remove the temporary source manifest unless the user asks to retain it.

## Phase 2 - Create and populate the new structure

### 2A. Create the target structure

1. Require a valid nonempty `Policy_Register.csv` before moving legacy files.
2. Run:

   ```bash
   python scripts/create_target_structure.py <client-root>
   ```

3. Create the operational roots and the permanent families matching `client-folder-workflow`: `Account`, `Applications`, `Broker of Record Info`, `Loss Runs`, `Stewardship`, `Policies`, `Quotes`, and `Schedules`. Seed `Policies/<YYYY>/<LOB>`, `Applications/<YYYY>/<LOB>`, `Schedules/<YYYY>`, `Account/<YYYY>`, and `Quotes/<YYYY>/...` from the register. Do not create the former per-LOB category tree. Do not populate `Epic_Attach`; it is a future pending-upload queue, not a historical archive.

### 2B. Inventory and classify legacy files

1. Run:

   ```bash
   python scripts/inventory_legacy_files.py <client-root> --output _Workflow/migration/legacy-file-inventory.json
   ```

2. Review every record where `already_standard` is false and `protected` is false. Treat any file under a folder named exactly `Legacy Files` as protected.
3. Before writing the plan, compare the register against legacy year folders and filename term tokens. Report future-year or missing-year coverage gaps instead of forcing unsupported files into the closest known term.
4. Use the policy register as the primary routing authority. Match policy numbers by normalized value before deciding LOB or policy term, but require term evidence when the normalized policy number appears in multiple register rows.
5. Classify each legacy file by:
   - client;
   - LOB;
   - policy term;
   - policy number when supported;
   - effective date when supported;
   - document category;
   - final filename;
   - destination;
   - confidence.
6. Do not infer a policy number, policy term, LOB, endorsement number, or effective date from weak evidence.
7. Route unresolved account-level material to the appropriate `Account/` folder only when the account-level classification is high confidence. Otherwise leave it in place.
8. When the user explicitly authorizes folder-context cleanup, classify medium-confidence files by the legacy folder path, term folder, and document-category folder. Promote those selected records to `high` confidence only for the approved cleanup pass, and state in `reason` that the move is user-authorized folder-context routing.

### 2C. Write and validate the migration plan

1. Write:

   ```text
   _Workflow/migration/plans/<run-id>-migration-plan.csv
   ```

2. Use the exact plan schema in the Phase 2 reference.
3. Include every nonstandard legacy file with an action of `move`, `copy`, `leave`, or `skip`.
4. Apply `move` or `copy` only to high-confidence records. Use `leave` for uncertain records.
5. For files in legacy `Quotes/` or proposal folders, preserve the original file in place. If the file can be filed with high confidence, use `copy` to place a permanent duplicate in the approved standard destination. If routing is uncertain, use `leave`.
6. For files anywhere under a folder named exactly `Legacy Files`, treat them as protected and exclude them from migration plans. Do not move, copy, rename, delete, hash for migration, or classify those files into the standard structure, including during folder-context cleanup.
7. Treat the permanent root families as approved filing destinations. Route files whose names contain `schedule` or `specs` to `Schedules/<YYYY>/`; route loss runs to `Loss Runs/<YYYY>/` based on pulled/valued/generated year; route quotes to `Quotes/<YYYY>/<LOB>/<Carrier>/` and multi-line client-facing proposals to `Quotes/<YYYY>/Quote Proposal/`; route issued policies/endorsements/binders/certificates/audits/policy accounting to `Policies/<YYYY>/<LOB>/`; route applications/SOVs/TIVs to `Applications/<YYYY>/<LOB>/`; route BOR materials to `Broker of Record Info/`; route stewardship materials to `Stewardship/<YYYY>/`; route unowned account-level material to `Account/<YYYY>/`. Use `leave` when required year, LOB, or carrier evidence is not supportable. Continue to leave root-level RDW-named folders in place.
8. Validate the plan without changing files:

   ```bash
   python scripts/apply_migration_plan.py <client-root> <plan.csv>
   ```

9. Resolve all validation errors before applying the plan.
10. For an explicit folder-context cleanup pass, build a deterministic candidate plan and review report before authorizing actions:

   ```bash
   python scripts/build_folder_context_plan.py <client-root> --output <client-root>/_Workflow/migration/plans/<run-id>-folder-context-plan.csv
   ```

   Review the adjacent `.review.json`. Add explicit reviewed decisions with `--overrides <reviewed-overrides.csv>` when deterministic evidence is incomplete. The override schema and decision rules are in the Phase 2 reference.
11. Only after the user authorizes folder-context routing, regenerate the partial plan with actionable rows:

   ```bash
   python scripts/build_folder_context_plan.py <client-root> --overrides <reviewed-overrides.csv> --output <client-root>/_Workflow/migration/plans/<run-id>-folder-context-plan.csv --authorize-folder-context --force
   ```

   Omit `--overrides` when the review report contains no decisions requiring an override. Every emitted `move` or `copy` row must state `User-authorized folder-context routing` in `reason`.
12. Validate the separate folder-context plan with:

   ```bash
   python scripts/apply_migration_plan.py <client-root> <plan.csv> --allow-folder-context --allow-partial-plan
   ```

### 2D. Apply and verify

1. Apply the validated plan:

   ```bash
   python scripts/apply_migration_plan.py <client-root> <plan.csv> --apply
   ```

   For a folder-context cleanup pass, apply with:

   ```bash
   python scripts/apply_migration_plan.py <client-root> <plan.csv> --allow-folder-context --allow-partial-plan --apply
   ```

2. The script must:
   - verify the source hash before every move or copy;
   - validate the exact apply-time temporary path after deterministic collision suffixes such as ` (2)` or ` (3)` have been added;
   - create parent folders only when needed;
   - preserve extensions;
   - never overwrite a nonidentical file;
   - use deterministic collision suffixes;
   - verify the destination hash before removing the source for moves;
   - leave the source in place for copy actions;
   - append results to `_Workflow/migration/cleanup-move-log.csv`.
3. Run:

   ```bash
   python scripts/verify_migration.py <client-root> <plan.csv>
   ```

   For a folder-context cleanup pass, verify with:

   ```bash
   python scripts/verify_migration.py <client-root> <plan.csv> --allow-folder-context
   ```

4. Report successful moves, successful copies, files intentionally left in place, skipped files, collisions, duplicate destinations, and remaining nonstandard files.

### 2E. Rename-only recovery

Use this path only when folder placement should remain intact and the problem is the standardized basename. Build the recovery from `_Workflow/migration/cleanup-move-log.csv`:

```bash
python scripts/restore_original_filenames.py <client-root>
python scripts/restore_original_filenames.py <client-root> --apply
```

Use `--search-by-hash` only when later correction passes moved a logged destination and the current file must be found by its recorded source hash. The helper writes `_Workflow/migration/rename-restore-log.csv`.

## Required routing rules

- Use an exact normalized policy-number match in `Policy_Register.csv` as the primary authority for LOB and policy term.
- Prefer readable document contents over legacy filenames or folders when they conflict.
- Treat the legacy folder path only as supporting evidence unless the user explicitly authorizes folder-context cleanup; in that mode, legacy folder path may be the routing authority for selected medium-confidence files.
- Create one permanent filed instance of each historical file by default. For legacy `Quotes/` or proposal folders, preserve the original and create a filed copy only when high-confidence routing is available. Do not copy historical files into `Epic_Attach`.
- Always leave every file under a root-level folder named exactly `Legacy Files` untouched unless the user specifically asks to process `<client-root>/Legacy Files/` by name. Treat those files as protected and exclude them from migration plans; do not inventory, read, move, copy, rename, delete, hash for migration, or classify them into the standard structure, even during folder-context cleanup. Apply the same protected treatment to nested folders named exactly `Legacy Files` unless the user explicitly overrides that specific folder by name.
- Use the same permanent folder schema as `client-folder-workflow`. Any filename containing `schedule` or `specs` routes to `Schedules/<YYYY>/` when the effective or represented year is supportable. Loss runs route to `Loss Runs/<YYYY>/` based on pulled, valued, or generated year. Quotes, indications, terms, comparisons, and quote summaries route to `Quotes/<YYYY>/<LOB>/<Carrier>/`; multi-line client-facing quote proposals route to `Quotes/<YYYY>/Quote Proposal/`. Policies, endorsements, binders, certificates, audits, and policy-owned correspondence route to `Policies/<YYYY>/<LOB>/`. Applications and submission packets route to `Applications/<YYYY>/<LOB>/`. Collapse legacy LOB-root category trees into these families. Continue preserving root-level RDW-named folders in place.
- Keep existing files already in the standard structure in place.
- Move policy-extraction Markdown and related structured JSON knowledge files into `Markdown/` only when they are not already there and their purpose is clear.
- Preserve `AGENTS.md`, `Policy_Register.csv`, workflow control files, system files, temporary lock files, and installed skill files.
- Never delete legacy directories. Leave emptied directories for a separate user-approved cleanup.
- Never overwrite, silently merge, or delete a nonidentical file.
- Do not collapse weak evidence into generic schema names such as `Policy.pdf`, `Notice.pdf`, or `Endt - MCS 90.pdf`. Apply policy or endorsement schema naming only when reliable evidence supports the policy number, effective date, endorsement token, and document type; otherwise preserve the original basename or leave the file for review.

## Deliverables

A successful full migration leaves:

- a validated `Policy_Register.csv`;
- the standardized client folder structure;
- legacy files moved or copied and renamed into approved destinations;
- `_Workflow/migration/legacy-file-inventory.json`;
- `_Workflow/migration/plans/<run-id>-migration-plan.csv`;
- `_Workflow/migration/cleanup-move-log.csv`;
- `_Workflow/migration/verification-report.json`; and
- a clear list of files left in legacy locations for review.













## Dependency Order and Operational Files

Treat bootstrap, inventory, and plan generation as a strict dependency chain: complete bootstrap first, complete and review the inventory second, then generate a migration plan. Parallelize only independent reads after their required generated inputs exist. Exclude `_Workflow`, `Policy_Register.csv`, `AGENTS.md`, lock files, manifests, and other operational control artifacts from document classification and migration assignments.
