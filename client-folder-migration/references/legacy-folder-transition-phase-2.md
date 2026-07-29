# Legacy Folder Transition - Phase 2

## Contents

1. Purpose and prerequisites
2. Target structure
3. Phase 2 preflight
4. Inventory boundaries
5. Classification and routing authority
6. Migration plan schema
7. Naming rules
8. Safe application rules
9. Verification
10. Rename-only recovery
11. Definition of done

## 1. Purpose and prerequisites

Transform one legacy commercial-insurance client folder into the approved structure after `Policy_Register.csv` has been built and validated.

Prerequisites:

- The selected directory is the client root.
- `Policy_Register.csv` exists, is nonempty, and passes `validate_policy_register.py`.
- Phase 2 is performed in a sandbox or other approved workspace.
- No sibling client folder is inspected or modified.

Do not begin file moves when the register is missing, empty, or malformed.

## 2. Target structure

Use the same legacy-style permanent folder schema as `client-folder-workflow`. Create these roots if missing:

```text
<Client Root>/
|-- Policy_Register.csv
|-- raw/
|-- Epic_Attach/
|-- _Workflow/
|   `-- migration/
|       |-- plans/
|       |-- logs/
|       |-- legacy-file-inventory.json
|       |-- cleanup-move-log.csv
|       `-- verification-report.json
|-- Markdown/
|-- Account/
|   |-- Permanent/
|   `-- <YYYY>/
|       `-- <account category, when supported>/
|-- Applications/
|   `-- <YYYY>/
|       `-- <LOB>/
|-- Broker of Record Info/
|-- Loss Runs/
|   `-- <YYYY>/
|-- Stewardship/
|   `-- <YYYY>/
|-- Policies/
|   `-- <YYYY>/
|       `-- <LOB>/
|-- Quotes/
|   `-- <YYYY>/
|       |-- Quote Proposal/
|       `-- <LOB>/
|           `-- <Carrier>/
`-- Schedules/
    `-- <YYYY>/
```

Create `Policies/<YYYY>/<LOB>` and `Applications/<YYYY>/<LOB>` for each unique valid `lob + effective year` combination in the register. Do not create LOB folders for `Not specified` or a blank value. Create root-level `Account`, `Applications`, `Broker of Record Info`, `Loss Runs`, `Stewardship`, `Policies`, `Quotes`, and `Schedules` families.

Seed `Schedules/<YYYY>`, `Stewardship/<YYYY>`, `Account/<YYYY>`, `Quotes/<YYYY>/Quote Proposal/`, and `Quotes/<YYYY>/<LOB>/<Carrier>/` from register effective years and carriers when available. Create additional `Loss Runs/<YYYY>` only when a pulled, valued, or generated year is supportable for a loss-run file.

`Account` is a fallback for account-level material with no reliable single policy owner, not a substitute for researching an identifiable policy. Prefer calendar year folders under `Account` over the former LOB-root category tree.

Do not create the former per-LOB policy-root category structure (`GL/25-26/Policy - End - Summary`, etc.) for new work. Prefer `Schedules` over a parallel `SPECS` folder when creating new schedule/specs folders.

`Epic_Attach/` must remain empty during historical migration. It is reserved for future items pending upload to Applied EPIC.


## 3. Phase 2 preflight

Before generating a migration plan:

1. Compare the register policy terms against legacy top-level year folders, explicit `YY-YY` filename tokens, and detected policy years. If obvious legacy coverage exists outside the register, report the gap before planning moves.
2. Treat future-year folders or files, such as a 2026 folder when the register ends at `25-26`, as a register-coverage gap. Do not route those files to the latest known term unless the source explicitly supports that term.
3. Identify normalized policy numbers that appear in multiple register rows. For repeated policy numbers, require term evidence from policy dates, explicit term tokens, or folder year before routing. Exact policy-number matching alone is not enough when the number repeats across terms.
4. If the selected root resolves to a UNC path or a long mapped-drive path, keep planned filenames short enough for the mover's temporary filename, not just the final destination.
5. When several rows share the same planned destination, or an existing nonidentical destination requires a deterministic suffix such as ` (2)`, validate the temporary path for the collision-suffixed filename before applying.
6. If coverage gaps are substantial, pause and ask whether to build supplemental register rows or continue with unsupported files marked `leave`.


## 4. Inventory boundaries

Inventory every file under the client root except a root-level folder named exactly `Legacy Files`, unless the user specifically asks to process `<client-root>/Legacy Files/` by name. Treat that folder as a preserved archive: do not inventory, read, hash, copy, move, rename, delete, classify, route, or include its contents in any migration plan by default. For all other files, mark the following as protected and never move them:

- `AGENTS.md`, `SKILL.md`, `codex.md`
- `Policy_Register.csv`
- `.git`, `.svn`, `.hg`, `.codex`, `.agents`
- any nested folder named exactly `Legacy Files`, unless the user explicitly overrides that specific folder by name
- `_Workflow/`
- `Epic_Attach/`
- system and temporary files such as `Thumbs.db`, `.DS_Store`, and files beginning with `~$`
- installed skills, virtual environments, caches, and package directories

Mark a file `already_standard=true` when it is already located in:

- `Markdown/`;
- `raw/`;
- `Account/Permanent/`;
- `Account/<YYYY>/` or `Account/<YYYY>/<category>/`;
- `Applications/<YYYY>/<LOB>/` where the LOB/year pair is supported by the register;
- `Policies/<YYYY>/<LOB>/` where the LOB/year pair is supported by the register;
- `Schedules/<YYYY>/`, `Loss Runs/<YYYY>/`, or `Stewardship/<YYYY>/`;
- `Quotes/<YYYY>/Quote Proposal/` or `Quotes/<YYYY>/<LOB>/<Carrier>/`; or
- `Broker of Record Info/`.

Do not move files marked protected. Leave already-standard files in place unless the user explicitly asks for a renaming-only pass.

## 5. Classification and routing authority

Use this evidence order:

1. Exact normalized policy-number match in `Policy_Register.csv`
2. Readable issued policy, endorsement, binder, invoice, certificate, application, quote, or correspondence content
3. Existing policy-extraction Markdown or JSON content
4. Explicit metadata or document properties
5. Filename
6. Legacy folder path
7. Pattern inference only as a candidate

When a policy number matches exactly one register row, inherit the register's approved client name, LOB, policy term, carrier, policy dates, and display policy number. When a normalized policy number matches multiple register rows, resolve the term using stronger term evidence before inheriting routing details; if term evidence is weak, leave the file in place and flag the ambiguity in the plan reason. If the document clearly conflicts with the register, leave it in place and flag the conflict in the plan reason.

### Quotes and proposal source folders

Treat legacy folders named `Quotes`, `Quote`, `Proposals`, `Proposal`, or clearly equivalent quote/proposal folders as source-history folders. Do not move files out of those folders during the first-pass migration or folder-context cleanup. When a quote or proposal file has high-confidence routing evidence, plan a `copy` action to the approved standard destination and leave the original in place. If routing is uncertain, use `leave`. Record in `reason` that the source was preserved because it came from a quote/proposal folder.

### Root-level permanent families and RDW folders

Treat the following as approved root-level filing families, not preserve-only legacy folders:

- Any file whose filename contains `schedule` or `specs`, matched case-insensitively, routes to `Schedules/<YYYY>/` when the effective year or represented policy year is supportable. Prefer `Schedules` over creating a parallel `SPECS` tree.
- Loss-run packages route to `Loss Runs/<YYYY>/` based on the year the loss run was pulled, valued, or generated. Do not use policy effective year unless the document uses it as the pulled/generated year.
- Quote, indication, term, comparison, and quote-summary files route to `Quotes/<YYYY>/<LOB>/<Carrier>/` using the proposed effective year or represented quote year, then supported line of business, then supported carrier.
- Multi-line client-facing quote proposal presentations and companion workbooks route to `Quotes/<YYYY>/Quote Proposal/`.
- Issued policies, endorsements, binders, certificates, audits, policy accounting, and policy-specific correspondence route to `Policies/<YYYY>/<LOB>/`.
- Applications, SOVs, TIVs, underwriting packets, and submission support route to `Applications/<YYYY>/<LOB>/`.
- Stewardship reports and program reviews route to `Stewardship/<YYYY>/`.
- Broker-of-record materials route to `Broker of Record Info/`.
- Account-level multi-line materials with no reliable policy owner route to `Account/<YYYY>/` or `Account/<YYYY>/<category>/`.
- If the required year, LOB, or carrier is not supportable, use `leave` and state the missing evidence in `reason`.

Continue treating any client-root folder whose name contains `RDW`, matched case-insensitively, as preserve-in-place material. Always plan RDW files with `action=leave` and no destination or final filename.

### Folder-context cleanup mode

Use folder-context cleanup only when the user explicitly asks to move files based on legacy folders, current folders, or where files are located. This mode is for later cleanup passes after a conservative register-backed migration has left files in place.

In this mode, the legacy folder path may be the routing authority when it contains coherent year, LOB/account, and document-family evidence. Examples include `Quotes/2026/Excess/`, `Policies/2024/`, `Claims/Loss Runs/2025`, and folders named for proposals, applications, bind requests, surplus lines, or policy documents. The root-level `Legacy Files` archive rule and root-level RDW preservation rule still take precedence. The approved permanent families above are valid destinations when their required routing evidence is supportable.

Rules:

- Preserve `Policy_Register.csv`; do not fabricate register rows merely to make a folder-context move validate.
- Keep folder-context moves in a separate plan named with `folder-context` or equivalent.
- Use `move` only after the user has authorized the cleanup pass; record `confidence=high` in the plan but state in `reason` that the original basis was folder-context or medium-confidence routing.
- Use destinations in the workflow schema shape: `Policies/<YYYY>/<LOB>/filename`, `Applications/<YYYY>/<LOB>/filename`, `Account/<YYYY>/filename`, `Schedules/<YYYY>/filename`, `Quotes/<YYYY>/<LOB>/<Carrier>/filename`, `Quotes/<YYYY>/Quote Proposal/filename`, `Loss Runs/<YYYY>/filename`, `Stewardship/<YYYY>/filename`, `Broker of Record Info/filename`, or `Markdown/...` for knowledge files.
- Collapse legacy LOB-root category trees such as `GL/25-26/Policy - End - Summary/` into `Policies/<YYYY>/<LOB>/`.
- Allow `Account/<YYYY>/` when the legacy folder establishes account-level material but does not establish a policy LOB.
- Do not use folder context to override readable document content or an exact register match.
- Do not route archives as a unit unless the user explicitly asks; prefer extracting or leaving archives for review.
- After applying, verify with folder-context mode and report which destinations are register-standard versus folder-context-supported.

### Document classification labels

Plan CSV rows may still record these classification labels in `document_category` for auditability, but destinations use the permanent root families above rather than category subfolders under each LOB:

- `Application - Submission` → `Applications/<YYYY>/<LOB>/`
- `Binder - Bind Order`, `Accounting`, `Policy - End - Summary`, `Certificates`, `Audits`, `Carrier Correspondence` → `Policies/<YYYY>/<LOB>/`
- `Correspondence & Email` → `Account/<YYYY>/` when no single LOB owns the item; otherwise `Policies/<YYYY>/<LOB>/` when policy-owned

Use `Markdown/` only for policy-extraction knowledge files, annual policy masters, and directly related structured JSON knowledge files.

Use `Schedules/<YYYY>/`, `Loss Runs/<YYYY>/`, `Quotes/<YYYY>/<LOB>/<Carrier>/`, and `Quotes/<YYYY>/Quote Proposal/` for their root document families. Use `Account/Permanent/` for enduring account-level documents with no policy year, such as organizational records or permanent agreements.

## 6. Migration plan schema

Write UTF-8 CSV with this exact column order:

```text
source_path
source_sha256
size_bytes
artifact_kind
client_name
lob
policy_term
policy_number
effective_date
document_category
final_filename
destination_relative_path
confidence
action
reason
```

Rules:

- `source_path`: path relative to the client root.
- `source_sha256`: hash from the inventory; never recalculate by hand.
- `size_bytes`: source size from inventory.
- `artifact_kind`: concise type such as `policy`, `endorsement`, `binder`, `quote`, `invoice`, `certificate`, `audit`, `application`, `email`, `markdown-knowledge`, `json-knowledge`, or `other`.
- `destination_relative_path`: complete relative file path, including the final filename.
- `confidence`: `high`, `medium`, or `low`.
- `action`: `move`, `copy`, `leave`, or `skip`.
- Use `move` and `copy` only with `high` confidence.
- Use `copy` for high-confidence files in quote/proposal source folders that should also be filed into the standard structure while preserving the original.
- Use only `leave` for files in a root-level folder whose name contains `RDW`, matched case-insensitively; do not specify a destination or final filename. Files in `Schedules`, `SPECS` (legacy alternate name), `Loss Run`, `Loss Runs`, `Quotes`, `Policies`, `Applications`, `Account`, `Stewardship`, or `Broker of Record Info` folders should be routed to the approved root document families when the required evidence is supportable.
- Use `leave` for files requiring human review.
- Use `skip` only for protected, temporary, system, or unsupported artifacts.
- Every inventory record that is neither protected nor already standard must appear exactly once in the plan.
- For a user-authorized folder-context cleanup pass, a partial plan may include only the selected files being cleaned up, but the plan name and `reason` field must make that scope explicit.

## 7. Naming rules

Apply the commercial-lines standard in `commercial-lines-standard.md`.

General pattern:

```text
YY-YY Client Name - LOB Pol# PolicyNumber - Eff MM.DD.YY - Document Type or Description.ext
```

Requirements:

- Preserve the original extension.
- Use dots in filename dates.
- Omit unsupported fields rather than inventing them.
- Keep descriptions concise and specific.
- Use Windows-safe characters.
- Keep paths reasonably short, with enough room for deterministic collision suffixes and the mover's temporary filename.
- Do not use generic schema names for weakly classified material. Names such as `Policy.pdf`, `Notice.pdf`, or `Endt - MCS 90.pdf` are allowed only when reliable source evidence supports that document identity. Preserve the original basename or use `leave` for unsupported emails, archives, delivery letters, summaries, safety materials, driver materials, and other weakly classified files.
- For endorsements, preserve the endorsement number exactly when it is supported by the source filename, readable document content, or structured policy data. Do not remove the endorsement number when shortening a filename; shorten the description first. If no endorsement number is supported, use `Endt - [Description]` rather than inventing a number.
- For correspondence, identify the party and subject when supported.

### Folder-context validation commands

Build the plan in two passes. First generate deterministic candidates and a sibling review report without authorizing file actions:

```bash
python scripts/build_folder_context_plan.py <client-root> --output <client-root>/_Workflow/migration/plans/<run-id>-folder-context-plan.csv
```

The `.review.json` report records actionable candidates, unresolved evidence, prior move/copy history, duplicate content, existing identical destinations, and long-path decisions. The helper evaluates each file from its own path, filename, register match, and reviewed override. It must never borrow LOB or carrier evidence from sibling files in a broad quote folder.

When deterministic evidence is incomplete, supply a reviewed override CSV with this exact header order:

```text
source_path
action
artifact_kind
client_name
lob
policy_term
policy_number
effective_date
document_category
year
carrier
final_filename
destination_relative_path
reason
```

Use an override only after reviewing the source. Leave unused cells blank. Prefer supplying missing classification fields and allowing the helper to construct the destination; use `destination_relative_path` only when the complete destination was reviewed. Use `leave` or `skip` to record an explicit non-action decision.

After the user authorizes the cleanup, regenerate the same plan with `--authorize-folder-context` and `--force`. Omit `--overrides` when no overrides are needed:

```bash
python scripts/build_folder_context_plan.py <client-root> --overrides <reviewed-overrides.csv> --output <client-root>/_Workflow/migration/plans/<run-id>-folder-context-plan.csv --authorize-folder-context --force
```

The authorized plan is intentionally partial: unresolved records remain in the review report unless `--include-unresolved` is used to add `leave` rows. Every actionable row is high confidence and its reason begins with `User-authorized folder-context routing`. Quote/proposal source files use `copy`; other supported files use `move`. The helper suppresses content already covered by prior successful move/copy history, keeps only one deterministic action for identical source hashes, and shortens filenames when needed to fit the mover's collision-aware temporary-path limit.

For a folder-context cleanup plan, validate and apply with:

```bash
python scripts/apply_migration_plan.py <client-root> <plan.csv> --allow-folder-context --allow-partial-plan
python scripts/apply_migration_plan.py <client-root> <plan.csv> --allow-folder-context --allow-partial-plan --apply
python scripts/verify_migration.py <client-root> <plan.csv> --allow-folder-context
```

The flags are intentionally opt-in. Do not use them for the first conservative migration pass unless the user has already approved folder-context routing.

## 8. Safe application rules

Before each move or copy:

1. Resolve the source and destination within the selected client root.
2. Reject path traversal and absolute destination paths.
3. Confirm the source exists and is a regular file.
4. Recalculate the source SHA-256 and compare it with the plan.
5. Confirm the destination is an approved standard location, or an approved folder-context location when `--allow-folder-context` is being used.
6. Create the destination parent folder if needed.
7. Validate the exact resolved temporary path that will be used for safe copy, especially when a mapped drive resolves to a longer UNC path. This validation must model deterministic collision suffixes such as ` (2)` and ` (3)` before applying. If the temporary path is too long, shorten `final_filename` before applying.
8. If the exact destination does not exist, copy to a temporary file, verify its hash, and atomically rename it.
9. For `move`, remove the source only after destination hash verification succeeds. For `copy`, leave the source in place after destination hash verification succeeds.
10. If an identical destination exists, record `duplicate_destination` and leave the source in place; do not delete either copy.
11. If a nonidentical destination exists, append ` (2)`, ` (3)`, and so on before the extension, then move or copy to the first available name.
12. Append one result row to `cleanup-move-log.csv`.

Never remove directories, even when empty.

## 9. Verification

Verification must confirm:

- Every `move` or `copy` action has a successful log record or a clearly reported exception.
- Every successful destination exists and matches the source hash recorded in the plan.
- No protected file moved or copied.
- No file was written outside the client root.
- No nonidentical existing file was overwritten.
- `Epic_Attach/` remains free of historical migration files.
- All register-supported `Policies/<YYYY>/<LOB>` and `Applications/<YYYY>/<LOB>` structures exist.
- Every remaining nonstandard file is listed for review.
- Prior failed apply attempts, if any, are reported separately from the final verified plan result.

Write `_Workflow/migration/verification-report.json`.

## 10. Rename-only recovery

Use this mode when the migrated folder placement is correct but a standardized rename pass obscured the original document identity. This is a relabeling operation only; it must not move files back to legacy folders.

Procedure:

1. Read `_Workflow/migration/cleanup-move-log.csv` and use only rows with `result=moved` or `result=copied`.
2. For each row, treat `actual_destination` as the current file and `source_path` basename as the intended restored basename.
3. Verify the current file exists and its SHA-256 matches `source_sha256` before renaming.
4. Rename within the current folder only. If the original basename already exists, append deterministic suffixes such as ` (2)` before the extension.
5. If a later correction pass moved the logged destination, use source-hash search only when explicitly needed, and record that basis in the restore log.
6. Write `_Workflow/migration/rename-restore-log.csv`.

Commands:

```bash
python scripts/restore_original_filenames.py <client-root>
python scripts/restore_original_filenames.py <client-root> --apply
```

Use this mode before attempting document-by-document reclassification when the user's goal is simply to undo overbroad naming while preserving successful folder routing.

## 11. Definition of done

Phase 2 is complete when:

- the register remains valid and unchanged;
- the target structure exists;
- all high-confidence planned moves and copies were applied and hash-verified;
- all uncertain files remain in place and are reported;
- the move log is complete;
- the verification report is written; and
- no legacy directory was deleted.








