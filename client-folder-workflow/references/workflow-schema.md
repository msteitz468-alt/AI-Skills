# Client Folder Workflow Specification

## 1. Purpose

Create one global, reusable client-folder workflow for commercial insurance accounts. The workflow must apply to all client folders without creating client-specific skills.

When a client folder contains a `raw` folder populated with email files or standalone insurance documents, Codex must:

1. Read and classify the emails.
2. Extract their attachments without altering the source content.
3. Identify policies, endorsements, and other insurance documents.
4. Spawn a subagent to run `$insurance-policy-extractor` for every issued policy, endorsement, declaration, or policy-changing document found directly in `raw` or extracted from raw emails, and require validated JSON output before final filing is considered complete. Validated output must include row-level Schedule of Forms and Endorsements, exclusions, notices, advisory notices, and form numbers, or an explicit `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` review flag.
5. Create the required client folder structure as needed.
6. Rename and file the emails, standalone raw documents, and extracted attachments in the permanent client folders.
7. Create and maintain annual policy-extraction JSON outputs for issued policies and endorsements.
8. Create and maintain separate annual quote-extraction JSON outputs under `Markdown/Quotes/` for quotes, proposals, indications, terms, quote comparisons, and quote summaries.
9. Create and maintain separate annual submission-extraction JSON outputs under `Markdown/App-Submission/` for applications, carrier submissions, SOVs, TIVs, underwriting packets, exposure schedules, and related submission support.
10. Place independent copies of all items that should be attached in Applied EPIC into `Epic_Attach`, organized by policy number.
11. Maintain an idempotent processing ledger so files removed from `Epic_Attach` after upload are not recreated during later runs.
12. Load and apply the approved client `_Workflow/Policy_Register.csv` as the primary routing authority.
13. Preserve auditability, avoid unsupported guesses, and verify every run before reporting completion.

## 2. Instruction and Skill Scope

- Invoke the globally installed `client-folder-workflow` skill explicitly when the user wants `raw/` processed.
- Do not create, copy, or require `AGENTS.md` in a client root. Keep all reusable instructions in the installed skill and this bundled schema.
- Treat the current directory as the client root and never access sibling client folders.
- Keep reusable workflow skills and scripts installed once at user level; do not copy skills into client folders.
- Use `task-observer`, `client-folder-workflow`, `email-production-renamer`, `folder-file-maintenance`, and `policy-extraction-workflow` when available. Route `.msg` decoding and attachment extraction through the installed `email-production-renamer/scripts/extract_email_metadata.py` helper.
- The installed skill and this bundled schema are the control plane. Deterministic extraction, hashing, planning, merging, and verification should use the installed scripts when available.
- Scripts provide evidence and perform approved file operations; Codex retains responsibility for insurance classification and exceptions.
- Always create a written processing plan before applying file changes.

## 5. Client Folder Schema

Each client root may contain many lines of business and policy years. Use the following legacy-style permanent filing model; create only the folders needed for the current files. `raw`, `Epic_Attach`, and `_Workflow` remain required workflow-control folders at the client root.

```text
<Client Root>\
|-- raw\
|   |-- [new .msg, .eml, .txt, standalone PDFs, and related active intake files]
|   `-- Lost\
|       `-- [verified duplicates and truly unidentified files excluded from reruns]
|
|-- Epic_Attach\
|   |-- <PolicyNumber>\
|   |   `-- [pending renamed email and document copies]
|   `-- Account\
|       `-- [pending items with no reliable policy number]
|
|-- _Workflow\
|   |-- Policy_Register.csv           # Approved policy routing authority
|   |-- staging\
|   |-- plans\
|   |-- logs\
|   |-- processing-ledger.csv
|   |-- proposed-policy-register-updates.csv
|   |-- exceptions.csv
|   `-- last-run-summary.md
|
|-- Markdown\
|   |-- 2025_Policies.json
|   |-- 2026_Policies.json
|   |-- 2027_Policies.json
|   |-- Quotes\
|   `-- App-Submission\
|
|-- Loss Runs\
|   `-- <YYYY>\
|
|-- Account\
|   `-- <YYYY>\
|       `-- <account category, when supported>\
|-- Applications\
|   `-- <YYYY>\
|       `-- <LOB>\
|-- Broker of Record Info\

|-- Stewardship\
|   `-- <YYYY>\
|
|-- Policies\
|   `-- <YYYY>\
|       `-- <LOB>\
|-- Quotes\
|   `-- <YYYY>\
|       |-- Quote Proposal\
|       `-- <LOB>\
|           `-- <Carrier>\
`-- Schedules\
    `-- <YYYY>\

```

### Folder rules

- `_Workflow/Policy_Register.csv` is the approved client policy-routing authority.
- `raw` is the intake queue.
- `raw/Lost` is a non-destructive terminal holding area for verified already-filed duplicates and truly unidentified files. Create it only after workflow control validation passes. Exclude its existing contents from inventory, hashing, extraction, duplicate detection, classification, planning, ledger reconciliation, and reruns unless the user specifically asks to review `raw/Lost` by name.
- `Epic_Attach` contains only items still pending attachment to Applied EPIC.
- `_Workflow` contains operational records and must never be copied into Applied EPIC.
- A root-level folder named exactly `Legacy Files` is a preserved archive and must not be inventoried, read, extracted from, staged, hashed, copied, moved, renamed, deleted, classified, routed, ledgered, or otherwise touched unless the user specifically asks to process `<client-root>/Legacy Files/` by name. This is separate from ordinary legacy filing context elsewhere in the client root.
- `Markdown` contains the client's annual policy-extraction knowledge masters, quote knowledge outputs, and submission knowledge outputs. It must contain one policy master Markdown file per applicable year, optional `Markdown/Quotes/` annual quote JSON files, optional `Markdown/App-Submission/` annual submission JSON files, and no routine email or document copies.
- `Markdown/Quotes/<YYYY>_Quotes.json` contains extracted quote, proposal, indication, terms, comparison, and quote-summary data for the proposed effective year or represented quote year. It is policy-check knowledge, not policy-routing authority.
- `Markdown/App-Submission/<YYYY>_Submissions.json` contains extracted application, carrier submission, SOV, TIV, underwriting packet, exposure schedule, and submission-support data for the proposed effective year or represented submission year. It is renewal, marketing, and policy-check knowledge, not policy-routing authority.
- `Applications/<YYYY>/<LOB>` contains applications, carrier submissions, SOVs, TIVs, underwriting packets, and submission support, using the proposed effective or represented submission year.
- `Policies/<YYYY>/<LOB>` contains issued policies, endorsements, binders, certificates, audits, accounting, and policy-specific correspondence, using the policy effective year. Retain a document-category subfolder only when an existing client structure has one or it is needed to prevent a supported collision; do not recreate the former universal category tree.
- `Schedules/<YYYY>` contains files whose filenames contain `schedule` or `specs`, using the supported policy term when available, otherwise the effective or represented year.
- `Loss Runs/<YYYY>` contains loss-run packages and claim-history pulls, using the year the loss run was pulled, valued, or generated.
- `Quotes/<YYYY>/<LOB>/<Carrier>` contains quotes, indications, terms, proposals, comparisons, and quote summaries, using proposed effective year or represented quote year, line of business, and carrier.
- `Quotes/<YYYY>/Quote Proposal/` contains client-facing quote proposal presentations and companion workbooks that summarize multiple lines or markets. Preserve the document family as `Quote Proposal`; do not route these presentations by every coverage line or carrier summarized inside them.
- `Account/<YYYY>` is the account-level shared-drive family for materials with no reliable policy owner. Do not retain processed emails here; stage them only in `Epic_Attach`.
- `Account/<YYYY>/<category>` contains accounting, surplus-lines, record-of-insurance, and multi-line materials. `Broker of Record Info` is a dedicated root family and must not be routed into a policy folder.
- `Stewardship/<YYYY>` contains stewardship reports, renewal strategy, program reviews, and related account-management deliverables.

- Annual master files are working knowledge sources for future policy checking and must not be staged in `Epic_Attach` unless the user explicitly requests it.
- `<LOB>` is the standardized policy-type abbreviation or name, such as `Auto`, `Cyber`, `Crime`, `D&O`, `EPL`, `Fiduciary`, `GL`, `International`, `KRE`, `Package`, `Pollution`, `Prof. Liab`, `Property`, `Management Liability`, `Umbrella-Excess`, or `WC`. For client-facing quote/proposal filenames and quote destination display categories, render `AUTO` as `Auto` and `PKG` as `Package`.
- For management-liability placements, do not use `PL` as a catch-all LOB. Classify and file Directors & Officers as `D&O`, Employment Practices Liability as `EPL`, and Fiduciary Liability as `Fiduciary`; reserve `Management Liability` only for combined/multi-line schedules, towers, summaries, or correspondence that truly spans more than one of those coverages. Use `Prof. Liab-E&O` only for true Professional Liability / E&O placements.
- For D&O, EPL, Fiduciary, Side A, DIC, Side A DIC, primary, and excess layers, include the layer label and liability range in permanent filenames when supported by the source. Examples: `YY-YY Client - D&O - Primary - $10M Pol# ...`, `YY-YY Client - D&O - 2nd Excess - $10M xs $20M Pol# ...`, and `YY-YY Client - D&O - Excess Side A DIC - $10M xs $40M Pol# ...`.
- `<YY-YY>` is the policy term, such as `26-27`.
- `Account` is the fallback for account-level items or items that cannot be tied reliably to a policy, such as corporate financials.
- Preserve an existing client structure when it already follows the standard. Do not create parallel duplicate structures with slightly different names.

## 6. Naming Standards

### 6.1 Emails

Use the email's internal received timestamp, normalized to Pacific Time. If unavailable, use sent time. If neither is reliable, use `00000000 0000` and flag the file for review.

```text
YYYYMMDD HHMM - CLIENT NAME - f. J. Smith - Brief Description - POL# PolicyNumber.msg
```

Rules:

- Preserve the original extension.
- Omit `- POL# PolicyNumber` when the policy number is not reliable.
- Clean repeated prefixes such as `RE`, `FW`, `FWD`, and external-security tags from the description.
- Keep the description concise and human-readable.
- Use the same client string in the filename and classification record.
- Use deterministic collision handling: append ` (2)`, ` (3)`, and so on when nonidentical files would otherwise have the same name.

### 6.2 Policies

```text
YY-YY [Client Name] - [LOB] Pol# [Policy#] - Eff MM.DD.YY - Policy.[ext]
```

### 6.3 Endorsements

```text
YY-YY [Client Name] - [LOB] Pol# [Policy#] - Eff MM.DD.YY - Endt [#] [Description].[ext]
```

### 6.4 Other insurance documents

Use the commercial-lines standard:

```text
YY-YY [Client Name] - [LOB] Pol# [Policy#] - Eff MM.DD.YY - [Document Type or Description].[ext]
```

Omit fields only when they do not apply or cannot be supported by the document evidence.

### 6.5 Permanent documents

```text
[Client Name] - Permanent - [Document Description].[ext]
```

### 6.6 Filesystem safety

- Use periods in filename dates: `04.15.26`.
- Remove or replace `< > : " / \ | ? *`, control characters, trailing periods, and trailing spaces.
- Preserve extensions and file bytes.
- Keep paths reasonably short for Windows.
- Do not rename a document to imply a policy number, endorsement number, effective date, or LOB that is not supported by evidence.

### 6.6A Quote and quote proposal filenames

For quotes, quote proposals, indications, terms, comparisons, and quote summaries, use the supported quote, release, proposal, or revision date in the final client-facing filename. Do not use extractor assignment IDs such as `doc_000001` in permanent or EPIC filenames; keep those IDs only in `_Workflow` plans, ledgers, extraction records, and quote JSON keys.

Use this evidence order for quote-date naming:

1. Explicit quote, release, proposal, revision, or presentation date in the document body.
2. Explicit quote/release date in the original filename.
3. Email date when the file came from an email and the document has no separate quote date.
4. Source modified date only when no better quote-date evidence is available; record that basis in the plan, ledger, and quote JSON.

Use periods in the final filename date, such as `03.31.26`.

Client-facing proposal presentations and companion workbooks that summarize multiple lines or markets must be named and filed as `Quote Proposal`, not as `Multiple Lines`, `Multiple Carriers`, or a coverage-spread label. Use:

```text
Quotes/<YYYY>/Quote Proposal/YY-YY [Client Name] - Quote Proposal - MM.DD.YY.[ext]
```

Use client-facing LOB display names in quote/proposal filenames and quote destination categories: `AUTO` becomes `Auto`, and `PKG` becomes `Package`. Preserve approved register values, normalized policy matching keys, extraction record IDs, and source evidence separately from these display labels. On Windows or SMB shares, treat case-only path changes as the same path; use a temporary filename or copy-first verified recovery path before removing any old-name duplicate, and never delete the only verified copy during a display-case correction.

For carrier- or LOB-specific quote files, use:

```text
Quotes/<YYYY>/<LOB>/<Carrier>/YY-YY [Client Name] - [LOB] - Quote - [Carrier-Option (if applicable)] - MM.DD.YY.[ext]
```

For related forms, endorsements, terms, or support packages that the user or document evidence ties to a quote, use the same quote date where supportable and label the document type, such as `Quote Support`.
### 6.7 Annual quote-extraction JSON outputs

Use one JSON file per applicable proposed-effective year:

```text
Markdown/Quotes/YYYY_Quotes.json
```

Example:

```text
Markdown/Quotes/2026_Quotes.json
```

Quote JSON files must remain separate from issued-policy annual JSON files.

### 6.8 Annual policy JSON files

Use one file per applicable year:

`	ext
Markdown/YYYY_Policies.json
`

Example:

`	ext
Markdown/2026_Policies.json
`

The annual policy JSON file is the single durable policy knowledge file for that year.

## 7. Processing Trigger

Run this workflow when the user asks Codex to process, organize, file, clean, ingest, or review the contents of a client `raw` folder.

The expected working directory is the client root or a parent folder from which the client root can be identified unambiguously.

Do not automatically process unrelated client folders in bulk unless the user explicitly requests a multi-client run.

## 7A. Policy Register

Use an approved client-level register at:

```text
<Client Root>\_Workflow\Policy_Register.csv
```

### Legacy root-register relocation

Run `scripts/bootstrap_client.py <client-root>` before reading the register. When a legacy `<Client Root>\Policy_Register.csv` exists:

- Move it to `_Workflow/Policy_Register.csv` when the destination is missing or empty, preserving the existing bytes.
- When both files are nonempty and identical, keep `_Workflow/Policy_Register.csv` as authoritative and relocate the redundant root copy under `_Workflow/logs` for auditability.
- When both files are nonempty and differ, preserve both, stop before processing `raw`, and require conflict resolution.
- Do not leave an active `Policy_Register.csv` at the client root after a successful relocation.

### Required columns

```text
client_name
lob
policy_number
normalized_policy_number
carrier
effective_date
expiration_date
policy_term
status
parent_policy_number
notes
```

Additional approved columns may be retained. Do not silently remove, rename, or reorder columns in an existing register.

### Normalization

For matching only, normalize policy numbers by:

1. Converting letters to uppercase.
2. Removing spaces, hyphens, periods, slashes, number signs, and other punctuation.
3. Retaining only letters and digits.

Store the display policy number exactly as approved in `policy_number`. Use `normalized_policy_number` only as the deterministic match key.

Examples:

```text
41-LX-013201492-0 -> 41LX0132014920
100 0004492       -> 1000004492
DOC 3431857-01    -> DOC343185701
```

### Register validation

Before classifying any intake item:

1. Confirm `_Workflow/Policy_Register.csv` exists and is readable.
2. Confirm every required column appears exactly once.
3. Confirm each nonblank `policy_number` has a nonblank normalized value.
4. Recompute the normalized form and compare it with `normalized_policy_number`.
5. Confirm no active rows share the same normalized policy number unless they intentionally represent the same policy and are clearly documented.
6. Confirm dates use `YYYY-MM-DD` when supplied.
7. Confirm `lob` and `policy_term` are populated for active policies when known.
8. If the register is missing on a new client, initialize a header-only `_Workflow/Policy_Register.csv` and continue with document-based classification; add new policy rows only when the high-confidence new-raw-policy register-add rules are satisfied and audited.
9. If a nonempty register is malformed or internally conflicting, log the issue and stop before changing `raw`.

### Routing authority

Use this evidence order for policy routing and naming:

1. Exact normalized policy-number match in `_Workflow/Policy_Register.csv`.
2. Issued policy or endorsement document text.
3. Clear declarations, schedules, or document metadata.
4. Existing annual policy JSON file.
5. Attachment filename.
6. Email subject and body.
7. Existing consistent client-folder context.
8. Pattern matching only as a candidate and never as sole proof.

When an exact register match exists, inherit the approved row's LOB, carrier, policy term, effective date, expiration date, display policy number, permanent folder path logic, EPIC policy folder, and Markdown-master assignment. Still compare the actual document with the register for consistency.

### Conflict handling

The register does not override a clearly issued document that proves the register is wrong. If a matched document conflicts materially with the register, do not auto-file the affected item. Record an exception with:

- Register row and normalized policy number
- Conflicting document value
- Source document and hash
- Fields in conflict
- Exact decision needed

Material conflicts include different carrier, LOB, policy term, named insured, effective date, expiration date, or a different policy number shown on an issued document.

### Multiple-policy emails

When one email references multiple registered policies:

- Route each attachment according to its own exact register match.
- Do not create a permanent shared-drive email copy.
- Place an EPIC copy of the email in each materially related policy-number folder when appropriate.
- Never choose a primary policy merely because it appears first in the subject or body.

### New raw policies and unregistered policy documents

When an issued policy, declaration, binder, or other policy-establishing document found in `raw` or extracted from a raw email contains a policy number not found in the approved register:

1. Verify the policy number, LOB, carrier, named insured, effective date, expiration date, and policy term from the issued document and the validated `$insurance-policy-extractor` JSON.
2. If the evidence is high confidence, the client identity is clear, the policy is not already represented by an active normalized policy number, and there is no material conflict, append an approved `Active` row directly to `_Workflow/Policy_Register.csv` before final routing. This is an explicit workflow-approved register append, not a silent modification.
3. Revalidate `_Workflow/Policy_Register.csv` immediately after the append, including normalized policy number, required columns, dates, active duplicates, LOB, and policy term.
4. Write an audit row to `_Workflow\proposed-policy-register-updates.csv` with `review_status` set to `approved_and_added`, preserving the source path, hash, extracted values, and reason for the register append.
5. Append or rebuild the applicable effective-year annual policy JSON output under `Markdown` from the validated extractor JSON before final filing. Ordinary annual policies belong only in the policy effective year; true multi-year policies follow the multi-year assignment rule.
6. After the register append and annual JSON update validate, process the email, standalone raw document, and extracted attachments as usual using the newly approved register row as the routing authority.
7. If evidence is medium or low confidence, the document is incomplete, the policy relationship is ambiguous, or any material conflict exists, do not append to `_Workflow/Policy_Register.csv`. Add a pending proposed row, record an exception, and leave the affected source in `raw` unchanged.
8. Do not use a pending proposed row as routing authority on later runs until it has been approved and added to `_Workflow/Policy_Register.csv`.

Use these columns for `_Workflow\proposed-policy-register-updates.csv`:

```text
run_id
proposed_at_pt
source_path
source_sha256
client_name
lob
policy_number
normalized_policy_number
carrier
effective_date
expiration_date
policy_term
status
parent_policy_number
proposal_reason
confidence
review_status
notes
```

Allowed `review_status` values:

```text
pending
approved_and_added
rejected
superseded
```

## 7B. Existing Policy-Folder Cleanup Mode

Use this mode only when the user asks to rename already-filed policy documents in specifically named permanent folders.

1. Limit inventory to the requested folders; do not inspect `raw`, sibling clients, or unrelated permanent folders.
2. Validate the existing `_Workflow/Policy_Register.csv` before proposing names.
3. Create a rename-only plan under `_Workflow/plans` with source path, source hash, proposed basename, evidence, confidence, and disposition.
4. Include only documents that are clearly actual policies and have register-backed or document-backed policy number, term, LOB, and effective-date evidence.
5. Exclude endorsements, binders, records of insurance, summaries, delivery letters, archives, and unsupported `Account` items unless document-level evidence independently satisfies the policy naming schema.
6. Preserve the original basename for weakly classified items. Do not collapse them into generic names such as `Policy.pdf` or `Notice.pdf`.
7. Apply deterministic collision handling, preserve extensions, verify hashes after each rename, and write an audit log under `_Workflow`.
8. Do not run raw ingestion, EPIC staging, processing-ledger, or annual policy JSON phases in this mode.

## 8. Transactional Workflow

### Phase 1 - Preflight and first-run initialization

1. Confirm the client root and locate `raw`.
2. Load global instructions, applicable skills, OPEN observations, and cross-cutting principles.
3. Create a unique `run_id` using a Pacific Time timestamp plus a collision-safe suffix.
4. Run `scripts/bootstrap_client.py <client-root>` to initialize the workflow control structure and apply the Section 7A legacy root-register relocation rule:
   - Create `_Workflow` when it does not exist.
   - Ensure `_Workflow\staging`, `_Workflow\plans`, and `_Workflow\logs` exist.
   - Do not create permanent LOB folders, `Epic_Attach`, or `Markdown` during bootstrap unless the current batch later requires them.
   - If conflicting root and `_Workflow` registers exist, make no changes to `raw` and stop for review.
5. Validate the resulting `_Workflow/Policy_Register.csv` before classifying any intake item:
   - If it does not exist, create a header-only register using Section 7A.
   - If it exists, validate it using Section 7A.
   - If a nonempty register is malformed, log the failure, make no changes to `raw`, and stop.
6. Initialize `_Workflow\processing-ledger.csv` when it does not exist or is a zero-byte file. Write exactly one header row using the required columns in Section 9. Treat a header-only ledger as a valid empty first-run ledger.
7. Initialize `_Workflow\exceptions.csv` when it does not exist or is a zero-byte file. Write exactly this header row:

   ```text
   run_id,recorded_at_pt,source_path,source_sha256,artifact_kind,issue_code,issue_summary,evidence,decision_needed,confidence,status,notes
   ```

8. Initialize `_Workflow\last-run-summary.md` when it does not exist with a short placeholder stating that no verified processing run has completed yet. Do not replace an existing run summary during bootstrap.
9. Initialize `_Workflow\proposed-policy-register-updates.csv` when it does not exist or is a zero-byte file using the exact columns in Section 7A. Treat a header-only file as valid.
10. Validate existing control files before continuing:
   - Do not overwrite, truncate, reorder, or silently migrate a nonempty ledger or exceptions file.
   - Confirm the processing ledger contains every required Section 9 column exactly once. Additional approved columns may be retained.
   - Confirm `exceptions.csv` contains the required initialization columns exactly once. Additional approved columns may be retained.
   - If a nonempty control file is malformed or has incompatible headers, write an initialization-failure note under `_Workflow\logs`, make no changes to `raw`, and stop for review.
11. Read the validated processing ledger. When it contains only its header, continue as a clean first run with no prior processed artifacts or EPIC states.
12. Ensure `<client-root>\raw\Lost` exists only after initialization and control-file validation succeed. Treat it as outside the active intake queue.
13. Create the run-specific staging folder `_Workflow\staging\<run_id>` only after initialization and control-file validation succeed.
14. Inventory all supported email files in active `raw`, excluding `raw\Lost` and all descendants.
15. Inventory existing client folders to avoid creating duplicate structures, excluding a root-level `Legacy Files` folder and excluding the contents of `raw\Lost` unless the user specifically asked to process either protected area by name.
15. Do not alter source files during preflight or initialization.

#### Raw-only client bootstrap rule

When the confirmed client root contains only `raw`, treat that as a supported new-client starting state. Create `_Workflow`, initialize a header-only `_Workflow/Policy_Register.csv` and the other control infrastructure described above, and proceed normally. Do not fail merely because no ledger, exception file, permanent filing folders, `Epic_Attach`, or `Markdown` folder exists yet.

### Phase 2 - Evidence extraction

Inventory standalone documents in active `raw` as well as email files. Do not recurse into or inspect `raw/Lost/`, and do not inventory or inspect `<client-root>/Legacy Files/` during this phase unless the user specifically asked to process that protected folder by name. When a standalone raw file is an issued policy, endorsement, declaration, quote, binder, proposal, or other insurance document, calculate its SHA-256 hash, read enough metadata to classify the document candidate, and preserve it as a source artifact until the written processing plan is approved/applied.

For each `.msg`, `.eml`, or `.txt` email:

1. Run the installed `email-production-renamer/scripts/extract_email_metadata.py` helper. For `.msg`, pass `--attachments-dir <run-staging>/email-attachments`; use `aspose-email-foss` as the primary decoder and `extract_msg` only as the helper's recorded compatibility fallback. Do not start Outlook or use COM during ordinary processing.
2. Extract subject, sender, recipients, sent/received timestamps, body preview, source SHA-256, decoder name, and property-specific warnings.
3. If both standalone `.msg` decoders fail, record an unreadable-email exception and retain the source in `raw`; use Outlook COM only when the user explicitly requests that diagnostic path.
4. Extract attachments into the run-specific staging folder while preserving their bytes and original extensions.
5. Record the parent email relationship for every attachment.
6. Calculate and verify a SHA-256 hash for every extracted attachment against the helper's JSON record.
7. Read document text and metadata where supported.
8. Treat extraction scripts as evidence providers, not final naming authorities.
9. Never edit the original email or attachment content.

### Phase 2A - Mandatory policy and quote JSON extraction subagent

Before finalizing the processing plan, identify every standalone raw document or extracted attachment that appears to be an issued policy, endorsement, declaration, other document that changes the policy record, quote, proposal, indication, terms document, quote comparison, or quote summary.

For those policy-changing or quote-term documents:

1. The main agent must spawn a subagent and instruct it to use `$insurance-policy-extractor`.
2. Give the subagent only the bounded document assignment, required extractor references, and any staged base-policy JSON needed for endorsement matching.
3. Require the subagent to process one source file at a time, extract the concise `$insurance-policy-extractor` field set, and write one JSON record per source document without storing full document text in JSON.
4. Require the subagent to append or rebuild the applicable annual policy JSON outputs under `Markdown` for issued policies, endorsements, declarations, and policy-changing documents. For quotes, proposals, indications, terms, quote comparisons, and quote summaries, require the subagent to create or update `Markdown/Quotes/<YYYY>_Quotes.json` using the proposed effective year or represented quote year. For applications, carrier submissions, SOVs, TIVs, underwriting packets, exposure schedules, and submission support, require the subagent to create or update `Markdown/App-Submission/<YYYY>_Submissions.json` using the proposed effective year or represented submission year.
5. The main agent must validate the subagent's JSON output against the source hash, assignment, lean schema expectations, policy effective-year assignment, endorsement-to-parent matching, and row-level forms/endorsement/exclusion schedule capture before using it.
6. If the subagent cannot complete a source because pages are unreadable, OCR is required but unavailable, policy relationships are ambiguous, or validation fails, leave the affected source in `raw` when possible and record an exception. Do not treat a declaration-page summary as a substitute for required extractor JSON.
7. Do not accept a metadata-only, generated/partial-artifact, unsupported, or low-confidence hold for any PDF that appears policy-related until the main agent or extraction worker has made and documented a direct text-extraction attempt. Use `pdftotext` when available; if it crashes, hangs, fails silently, fails on a network path, or yields no usable output, retry with `draft_pdf_record.py` and its local-copy/PyMuPDF fallback. Inspect the resulting text evidence for policy number, endorsement number, LOB, carrier, named insured, and policy term before deciding whether the item is fileable or truly unresolved. Time-saving narrowed extraction may defer detailed schedules, but it may not bypass this minimum parser-evidence gate.
8. Use the validated extractor JSON as the primary evidence for policy/endorsement annual JSON merging, audited register additions or proposed register updates, effective-year annual policy JSON updates, annual quote JSON updates, classification notes, and ledger `annual_policy_json_update_state`/JSON extraction notes. Do not accept a `complete` extraction for a coverage-terms document if both `endorsements_exclusions` and `schedules.forms` are empty without an explicit missing-schedule review flag and source note.

### Phase 3 - Register matching and classification

1. Load the validated `_Workflow/Policy_Register.csv`.
2. Normalize every policy-number candidate.
3. Attempt exact normalized matches before making any LOB or destination decision.
4. Apply Section 7A routing, conflict, multiple-policy, and new-raw-policy/unregistered-policy rules.

For every email and attachment, determine when supported:

- Client name
- Sender or document source
- LOB
- Policy term
- Policy number
- Carrier
- Effective date
- Expiration date
- Document type
- Endorsement number
- Brief description
- Permanent destination category
- Applied EPIC policy folder
- Confidence level
- Applicable annual policy JSON year or years
- Applicable quote JSON year and path when the artifact is a quote, proposal, indication, terms document, quote comparison, or quote summary

Use the authority order in Section 7A. Do not route by LOB alone when an exact policy-number match is available or required.

### Phase 4 - Build processing plan

Before moving or copying anything, write a processing plan under:

```text
_Workflow\plans\<run_id>-processing-plan.csv
```

Each planned artifact must include source, hash, detected policy number when applicable, normalized policy number when applicable, register match status, matched register row or exception reference, classification, final filename, permanent destination, EPIC destination, applicable annual policy JSON year or years, applicable quote JSON path/year when applicable, annual policy JSON/quote JSON action, confidence, and action.

Do not apply low-confidence filing or routing guesses automatically. A planned `move_to_lost_unidentified` is a non-filing terminal disposition permitted only after required evidence attempts prove no reliable identity or destination.

For every planned `Lost` move, also include `lost_reason`, `lost_destination`, the canonical ledger row/permanent path for an already-filed duplicate or the completed identification attempts for an unidentified item, the related exception code, and a post-move hash-verification action.

### Phase 4A - Classify and plan `raw/Lost` dispositions

Use `raw/Lost` only for these terminal dispositions:

1. **Verified already-filed duplicate**
   - The active raw item's SHA-256 exactly matches one authoritative processing-ledger artifact row.
   - The referenced permanent file exists and its recomputed SHA-256 matches the raw item.
   - A missing EPIC file does not disqualify the duplicate when the ledger state shows it was removed by the user; do not recreate it.
   - Set the plan action to `move_to_lost_duplicate`, reference the canonical ledger row and permanent path, write exception/audit code `DUPLICATE_ALREADY_FILED_MOVED_TO_LOST` with resolved status, and do not create another permanent file, EPIC copy, annual JSON record, or ledger row.
2. **Truly unidentified file**
   - Required email decoders, direct PDF parser/fallback, filename/metadata review, and other applicable evidence attempts are complete.
   - The client/artifact type or any reliable filing destination still cannot be identified.
   - Set the plan action to `move_to_lost_unidentified`, write exception code `UNIDENTIFIED_MOVED_TO_LOST` describing the attempts and decision needed, and do not create a permanent file, EPIC copy, annual JSON record, or policy-register proposal.

Do not move identifiable-but-unresolved artifacts to Lost. Register conflicts, unmatched endorsements, incomplete policy relationships, missing substantive pages, and other items with a supportable identity remain in active `raw` for review.

For both Lost actions, preserve the original basename. If a nonidentical file already uses the desired Lost name, append deterministic ` (2)`, ` (3)`, and later suffixes. Never overwrite or delete an existing Lost item. If the item came from email attachment staging rather than directly from active raw, preserve the parent-email relationship in the plan and exception before moving the staged attachment into Lost.

### Phase 5 - Apply permanent filing

For approved/high-confidence items:

1. Create only the required destination folders.
2. Move each processed source email from `raw` directly into its `Epic_Attach` destination under the renamed filename; do not create a permanent shared-drive email copy.
3. Copy extracted attachments from staging into their permanent document folders under their renamed filenames.
4. Verify file hashes after each copy or move.
5. Do not delete any existing client file.
6. Do not overwrite a nonidentical file.

Email routing:

- Do not file processed emails in permanent shared-drive folders.
- Move each processed email to `Epic_Attach/<PolicyNumber>` when one reliable policy number applies; otherwise move it to `Epic_Attach/Account`.
- When one email materially relates to several policies, create independent EPIC copies in each relevant policy-number folder and do not retain a shared-drive permanent copy.

Attachment routing:

- Policies, endorsements, binders, certificates, audits, accounting, and policy-specific correspondence -> `Policies/<YYYY>/<LOB>`.
- Applications, submissions, SOVs, TIVs, and underwriting packets -> `Applications/<YYYY>/<LOB>` and `Markdown/App-Submission/<YYYY>_Submissions.json` when extractable submission data is present.
- Files whose names contain `schedule` or `specs` -> `Schedules/<YY-YY or YYYY>`.
- Loss-run packages and claim-history pulls -> `Loss Runs/<YYYY>` based on pulled, valued, or generated year.
- Quotes, indications, terms, proposals, comparisons, and quote summaries -> `Quotes/<YYYY>/<LOB>/<Carrier>` and `Markdown/Quotes/<YYYY>_Quotes.json`; client-facing quote proposal presentations and companion workbooks -> `Quotes/<YYYY>/Quote Proposal/`.
- Broker-of-record materials -> `Broker of Record Info`.
- Account-level invoices, premium allocations, finance agreements, record-of-insurance materials, surplus-lines records, and multi-line documents -> `Account/<YYYY>/<category>`.
- Stewardship reports, renewal strategy, program reviews, and related account-management deliverables -> `Stewardship/<YYYY>`.

Lost routing:

- Move planned verified duplicates to `raw/Lost/<original-basename>` only after the canonical permanent hash is verified.
- Move planned truly unidentified raw items or staged attachments to `raw/Lost/<original-basename>` only after required evidence attempts and the exception row are complete.
- Verify the Lost copy's SHA-256 equals the source SHA-256, confirm the active source path no longer exists after the move, and retain the Lost destination in the plan, exception, apply log, and run summary.
- Do not treat `raw/Lost` as permanent client filing or Applied EPIC staging.
### Phase 6 - Create or update annual policy JSON files

Run this phase only when the processed documents include an issued policy, endorsement, or another policy document that changes the extracted policy record.

#### 6.1 Extraction standard

Use the validated $insurance-policy-extractor JSON as the required source of extracted policy data. The extraction subagent must follow that skill's one-source-file-at-a-time rules and JSON schema. Preserve, when available:

- Exact document names and document types
- Client and named insureds
- Locations
- Policy number, policy type, effective date, and expiration date
- Broker or agency
- Insurer, NAIC, and verified AM Best rating when the workflow requires it
- Premiums and component premiums
- Limits, sublimits, deductibles, and retentions
- Valuation methods
- Endorsements, exclusions, forms, and advisory notices
- Exposures
- Vehicle, equipment, property, location, and endorsement schedules
- Extraction notes, conflicts, and source-document references

For endorsements, exclusions, forms, and advisory notices, preserve row-level data in JSON whenever available. Required columns are coverage or policy part, form number, title/description, edition date, effective date when stated, form type, and source pages. This includes advisory notices, notices to policyholders, state amendatory endorsements, exclusions, coverage forms, common policy forms, and policy jacket forms. If the source has no visible form schedule or it cannot be read, the annual JSON must carry MISSING_FORMS_ENDORSEMENTS_SCHEDULE under review/missing-information notes.

Never invent information. Write Not specified when the source documents do not state a value.

Do not mark this phase complete until the applicable annual JSON output has been appended or rebuilt, validated, and cross-referenced in the processing plan, ledger notes, and run summary.

#### 6.2 Annual JSON year assignment rule

Assign each policy to its annual JSON file from the **parent policy term**, not from an endorsement's own effective date.

1. **Ordinary annual or short-term policy:** If the policy is not a true multi-year policy, place it only in the JSON file for the calendar year of the policy effective date. A normal policy that crosses into the next calendar year still appears only once.
2. **True multi-year policy:** Treat a policy as multi-year only when the document explicitly describes it as multi-year or the stated term is longer than 366 days. Place it in every calendar-year JSON file beginning with the effective year and ending with the year immediately before the expiration year.
3. **Expiration year exclusion:** Never place a multi-year policy in the calendar year matching its expiration date.
4. **Endorsements:** File every endorsement under its parent policy in the same JSON year or years assigned to that policy. Do not create a new annual assignment from the endorsement effective date.
5. **Renewals:** Treat each renewal as a separate policy term and assign it using the renewal policy's effective date.
6. **Ambiguous terms:** If the parent policy dates are missing, conflicting, or cannot be tied reliably to the endorsement, do not guess. Record an exception and hold the annual JSON update for review.

#### 6.3 JSON merge behavior

1. Create Markdown if it does not exist.
2. Create or rebuild the applicable Markdown/YYYY_Policies.json file.
3. When an annual JSON file exists, merge into it; do not replace the whole file with only the current run's documents.
4. Use the policy number plus parent policy effective and expiration dates as the primary policy-record key. Use document hash and exact document name to prevent duplicate source entries.
5. Keep endorsements tied to the correct parent policy and order them by endorsement effective date, then endorsement number when available.
6. For a true multi-year policy, synchronize the policy's current full extraction and endorsement history across every assigned annual JSON file.
7. Preserve unrelated policies, existing notes, and previously extracted details unless a newer issued document clearly supersedes them.
8. Record conflicts rather than silently discarding prior values. Identify the old value, new value, source document, and whether the newer document supersedes the earlier one.
9. Sort records by LOB, policy effective date, and policy number for predictable review.
10. Write updates atomically through a run-specific temporary file, validate the result, and then replace the annual JSON file.

#### 6.4 Required annual JSON structure

Each annual policy JSON file must include top-level documents[] and metadata, with one document record per source document or policy-changing artifact. The JSON is the AI-readable working file for future policy checking and handbook/report generation. Do not copy it to Epic_Attach during the routine workflow.

### Phase 6A - Create or update annual quote JSON outputs

Run this phase when the processed documents include a quote, proposal, indication, terms document, quote comparison, or quote summary with extractable coverage terms.

1. Create `Markdown/Quotes/` if it does not exist.
2. Assign each quote record to `Markdown/Quotes/<YYYY>_Quotes.json` using the proposed effective year. If proposed effective date is missing, use the represented quote year only when explicitly stated in the document, email, or filename. If no year is supportable, write an exception and hold the quote JSON update for review.
3. Use validated `$insurance-policy-extractor` JSON as the source. Do not rely on filename-only quote summaries when the document body is parseable.
4. Preserve one record per quoted option when a document includes multiple carrier options, LOB options, limits, or deductible alternatives.
5. Capture, when available: source filename, source SHA-256, client, named insured, carrier/market, broker/agency, LOB, proposed effective and expiration dates, quote version/date, option label, premiums, taxes/fees, limits, sublimits, deductibles/SIRs, retentions, valuation terms, subjectivities, exclusions, forms, quoted exposures, schedules, and review flags.
6. Quote JSON is evidence for later policy checking and proposal review, not approved policy-routing authority. Do not update `_Workflow/Policy_Register.csv` from quote JSON alone.
7. Merge idempotently by source hash plus carrier, LOB, proposed term, and option label. Re-running the workflow must not duplicate quote records.
8. Validate the annual quote JSON shape before final filing is marked complete.

Suggested annual quote JSON shape:

```json
{
  "calendar_year": 2026,
  "generated_at": "2026-07-22T00:00:00Z",
  "client": "Client Name",
  "quote_count": 1,
  "quotes": []
}
```

### Phase 6B - Create or update annual submission JSON outputs

Run this phase when the processed documents include an application, carrier submission, SOV, TIV, underwriting packet, exposure schedule, loss-summary support, supplemental application, or related submission support with extractable submission data.

1. Create `Markdown/App-Submission/` if it does not exist.
2. Assign each submission record to `Markdown/App-Submission/<YYYY>_Submissions.json` using the proposed effective year. If proposed effective date is missing, use the represented submission year only when explicitly stated in the document, email, or filename. If no year is supportable, write an exception and hold the submission JSON update for review.
3. Use validated `$insurance-policy-extractor` JSON or parser-supported structured extraction as the source when the document body is parseable. Do not rely on filename-only submission summaries when body text or schedules can be read.
4. Preserve one record per submitted package, and preserve child records for each submitted LOB, carrier/market, named insured, location schedule, vehicle schedule, payroll/revenue exposure, property value/SOV row, loss run reference, supplement, subjectivity, or requested coverage option when available.
5. Capture, when available: source filename, source SHA-256, client, named insureds, submitting broker/agency, carrier/market, LOB, proposed effective and expiration dates, submission date, submitted operations, exposures, schedules, values, locations, vehicles, payroll, revenue, loss history referenced, requested limits, requested deductibles/SIRs, target premiums when stated, subjectivities, forms, attachments included, and review flags.
6. Submission JSON is evidence for renewal, marketing, policy checking, and proposal review, not approved policy-routing authority. Do not update `_Workflow/Policy_Register.csv` from submission JSON alone.
7. Merge idempotently by source hash plus submission package key, submitted LOB, proposed term, and carrier/market when available. Re-running the workflow must not duplicate submission records.
8. Validate the annual submission JSON shape before final filing is marked complete.

Suggested annual submission JSON shape:

```json
{
  "calendar_year": 2026,
  "generated_at": "2026-07-22T00:00:00Z",
  "client": "Client Name",
  "submission_count": 1,
  "submissions": []
}
```
### Phase 7 - Stage Applied EPIC attachments

After permanent filing succeeds:

1. Move each processed renamed email directly into `Epic_Attach`; create an independent EPIC copy of each permanently filed attachment.
2. Use the finalized renamed basename; emails have no permanent-file copy.
3. Place each item under `Epic_Attach\<PolicyNumber>` when the policy number is reliable.
4. Place items with no reliable policy number under `Epic_Attach\Account`.
5. Do not use shortcuts, symbolic links, or hard links for EPIC copies.
6. Do not place logs, plans, manifests, or temporary files in `Epic_Attach`.

Multiple-policy rule:

- File each attachment under its own policy number.
- When one email materially relates to multiple policy numbers, place one EPIC copy of the email in each relevant policy-number folder.
- Do not retain a permanent archive copy of the email.
- If no policy is primary and no attachment establishes a policy number, use `Epic_Attach\Account`.

### Phase 8 - Commit ledger and clean staging

1. Append completed artifact records to `_Workflow\processing-ledger.csv`.
2. Record exceptions in `_Workflow\exceptions.csv`.
3. Remove run-specific staging files only after permanent attachment copies and required EPIC items are verified.
4. Clean transient extraction artifacts only after validation passes and all processed attachments have verified permanent and EPIC copies and all processed emails have verified EPIC destinations. Removable transient artifacts include parser drafts under shard `drafts/` folders, page image folders such as `*_pages/`, local-copy parser scratch files, and empty run staging folders. Preserve `extraction_manifest.json`, shard `assignment.json` files, final shard `records/`, staged `documents/`, validated `outputs/`, plans, logs, ledgers, proposed register updates, exceptions, run summaries, source files, permanent files, and EPIC files.
5. Write a cleanup note in the run summary with bytes removed and the artifact categories removed. If any unresolved source remains in `raw`, keep its extraction evidence unless it is clearly a parser scratch duplicate.
6. Leave unresolved source emails in `raw` unchanged.
7. Write `_Workflow\last-run-summary.md`.

Never remove, empty, deduplicate, or otherwise clean `raw/Lost` during routine staging cleanup.

### Phase 9 - Verification

Before reporting completion, verify:

- Every source email is either processed exactly once or explicitly listed as unresolved.
- `raw/Lost` exists, was excluded from active intake, and no pre-existing Lost content was inventoried or reprocessed.
- Every `.msg` record identifies `aspose-email-foss` as its decoder or contains a specific warning documenting the `extract-msg` fallback or total standalone-decoder failure.
- Every processed email exists in its permanent destination.
- Every extracted attachment exists in its permanent destination.
- Every pending EPIC item exists under the correct policy-number or `Account` folder.
- File hashes match the source/extracted bytes.
- Every detected policy number was normalized and checked against the approved register.
- Every issued policy, endorsement, declaration, or policy-changing document in `raw` or extracted from raw emails was assigned to a `$insurance-policy-extractor` subagent or recorded as an exception.
- Every policy-looking PDF held as metadata-only, generated/partial, unsupported, or low-confidence has documented parser evidence from `pdftotext` or `draft_pdf_record.py` fallback before it was held.
- Routine cleanup removed only verified transient parser/staging artifacts and preserved manifests, assignments, records, outputs, plans, logs, ledgers, exceptions, source/permanent files, and EPIC copies.
- Every completed extractor subagent assignment produced validated JSON and the applicable annual policy JSON, annual quote JSON, or annual submission JSON output was appended or rebuilt before final completion.
- Every issued policy, endorsement, declaration, quote, binder, proposal, or other coverage-terms record contains row-level forms/endorsements/exclusions in JSON, or is held/marked for review with MISSING_FORMS_ENDORSEMENTS_SCHEDULE.
- Every processed quote, proposal, indication, terms document, quote comparison, or quote summary with extractable terms appears in `Markdown/Quotes/<YYYY>_Quotes.json` or has an explicit exception explaining why quote JSON was held.
- Every processed application, carrier submission, SOV, TIV, underwriting packet, exposure schedule, supplemental application, or submission support file with extractable submission data appears in `Markdown/App-Submission/<YYYY>_Submissions.json` or has an explicit exception explaining why submission JSON was held.
- Exact register matches inherited the approved LOB, term, carrier, dates, and routing values.
- Register/document conflicts were held for review rather than auto-filed.
- High-confidence new raw policies were appended to `_Workflow/Policy_Register.csv`, audited in the proposed-update file as `approved_and_added`, and included in the applicable effective-year annual JSON before filing; unresolved unregistered policies were held for review.
- No unsupported policy number, endorsement number, LOB, or date was invented.
- No file was overwritten or deleted unexpectedly.
- Every `move_to_lost_duplicate` item matches exactly one authoritative ledger artifact and a recomputed identical permanent-file hash; no duplicate permanent, EPIC, annual JSON, or ledger record was created.
- Every `move_to_lost_unidentified` item has documented completed identification attempts and an exception; identifiable-but-unresolved artifacts were not moved to Lost.
- Every Lost move preserved the source bytes, original basename subject to deterministic collision suffixing, source relationship, and post-move SHA-256.
- No invalid filename characters remain.
- The ledger contains one authoritative record for each processed artifact.
- Every issued policy and endorsement is merged into the correct annual policy JSON file using the parent policy term.
- Ordinary policies appear in only the effective-year JSON file.
- True multi-year policies appear in each active-year JSON file but not the expiration-year JSON file.
- No endorsement was assigned independently from its parent policy.
- Annual policy JSON files validate successfully and retain unrelated existing policy records.
- A client root that began with only `raw` has a valid header-only `_Workflow/Policy_Register.csv`, a valid `_Workflow` structure, correctly initialized CSV headers, and no bootstrap-related changes to source files.

## 9. Applied EPIC Processing Ledger

The ledger is mandatory because the user will delete files from `Epic_Attach` after attaching them to Applied EPIC. A later run must interpret that deletion as intentional and must not recreate the file automatically.

Use:

```text
_Workflow\processing-ledger.csv
```

Required columns:

```text
run_id
processed_at_pt
source_email_sha256
source_email_original_name
source_email_final_path
artifact_sha256
artifact_kind
artifact_original_name
artifact_final_name
client
lob
policy_term
policy_number
document_type
permanent_path
epic_path
epic_state
annual_policy_json_years
annual_policy_json_paths
annual_policy_json_update_state
confidence
notes
```

Allowed `artifact_kind` values:

```text
email
attachment
```

Allowed `epic_state` values:

```text
pending
removed_by_user
not_applicable
review
restage_requested
```

Allowed `annual_policy_json_update_state` values:

```text
created
updated
unchanged
not_applicable
review
```

Use semicolon-separated values in `annual_policy_json_years` and `annual_policy_json_paths` when a true multi-year policy belongs in more than one annual master.

### Ledger behavior on later runs

- If an artifact hash is already in the ledger and its permanent file exists, do not process it again.
- When that hash reappears in active raw and the canonical permanent hash is verified, plan and move the reintroduced source to `raw/Lost` with disposition `move_to_lost_duplicate`; reference the existing ledger row rather than appending a duplicate row.
- If `epic_state` is `pending` and the EPIC file exists, leave it in place.
- If `epic_state` is `pending` and the EPIC file no longer exists, change the state to `removed_by_user` and do not recreate it.
- Treat `removed_by_user` as uploaded to EPIC or intentionally removed unless the user says otherwise.
- Recreate a removed EPIC item only when the user explicitly requests a restage; set `epic_state` to `restage_requested`, copy it, then return the state to `pending`.
- If the permanent archive file is missing, flag an exception. Do not silently reconstruct or replace it.
- If an artifact already exists in the ledger but its annual policy JSON, quote JSON, or submission JSON reference is missing or stale, repair only the annual policy JSON/quote JSON/submission JSON reference or merge state; do not duplicate the permanent or EPIC file.

## 10. Confidence and Exception Rules

Use three confidence levels:

```text
high
medium
low
```

### High confidence

Apply automatically when the required values are explicit in the document or supported by multiple consistent evidence sources.

### Medium confidence

Apply only when the destination is safe and reversible. Record the uncertainty in `notes`. Do not assign an uncertain policy number.

### Low confidence

- If the item is truly unidentified after required evidence attempts, plan `move_to_lost_unidentified`, write an exception, and preserve it under `raw/Lost`.
- If the item is identifiable but unresolved, leave the source email or standalone document in active `raw` unchanged.
- Do not stage files in `Epic_Attach`.
- Add a row to `_Workflow\exceptions.csv` with the evidence and the exact decision needed.

Common exception reasons:

- Unreadable or corrupted email.
- Password-protected or unreadable attachment.
- Client cannot be identified.
- Several plausible policy numbers with no reliable primary value.
- Policy term or LOB conflict.
- Attachment appears unrelated to the client.
- Destination collision with different file content.

## 11. Idempotency and Duplicate Handling

- Use SHA-256 hashes as the primary duplicate key.
- Re-running the workflow must not create duplicate permanent files or duplicate ledger rows.
- Do not treat matching filenames alone as proof of duplication.
- When two files have the same content, retain one permanent copy and reference the existing path in the ledger.
- When an exact duplicate reappears in active raw, verify the authoritative ledger row and canonical permanent hash, then move the reintroduced source to `raw/Lost` without creating another permanent, EPIC, annual JSON, or ledger record.
- When two files have different content but the same desired filename, append deterministic iteration suffixes.
- A file removed from `Epic_Attach` after being staged must not be restored automatically.
- Files already present in client permanent folders before the workflow began must not be altered unless the user explicitly requests folder cleanup.
- Re-running the workflow must not duplicate policy or endorsement records in annual policy JSON files, quote records in annual quote JSON files, or submission records in annual submission JSON files.

## 12. Safety Rules

- Do not delete existing client documents.
- Do not modify email or attachment content.
- Do not overwrite nonidentical files.
- Do not infer unsupported policy information.
- Do not silently modify the approved `_Workflow/Policy_Register.csv`; only append a new raw policy row when the workflow-approved high-confidence register-add rules are satisfied and audited.
- Do not route by LOB alone when the policy number is missing or conflicts with the register.
- Do not process outside the confirmed client root.
- Do not inventory or reprocess `raw/Lost`, and do not delete, overwrite, or routinely clean Lost contents.
- Do not place client-specific information into global skills or global cross-cutting principles.
- Keep task-observer records in `%USERPROFILE%\.codex\skill-observations`, not in client folders.
- Treat client-specific observations as `internal` and avoid unnecessary identifying detail.
- Preserve source-to-attachment relationships in the ledger.
- Do not assign an endorsement to a master year independently of its parent policy.
- Use a plan-then-apply workflow for every run.
- Verify before clearing staging or reporting success.

## 13. Task Observer Integration

Use the globally installed `task-observer` quietly during substantive runs. Apply relevant existing observations, log reusable workflow corrections without duplicating client-sensitive detail, and do not install or overwrite global skills automatically.

## 14. Run Summary

After each run, write `_Workflow\last-run-summary.md` with:

- Run ID and date/time.
- Policy register validation status and row count.
- Count of exact register matches, conflicts, register rows added, and pending unregistered policy proposals.
- Count of source emails found.
- Count of emails processed.
- Count of attachments extracted.
- Count of permanent files created.
- Count of files staged in `Epic_Attach` by policy number.
- Count of previously staged EPIC files detected as removed by the user.
- Count of annual policy JSON files created, updated, rebuilt, or unchanged.
- Count of annual policy JSON files appended, rebuilt, validated, or held for review.
- Count of annual quote JSON files appended, rebuilt, validated, or held for review.
- Count of annual submission JSON files appended, rebuilt, validated, or held for review.
- Count of policy and endorsement records merged by annual JSON year.
- Count and list of unresolved items.
- Count of files moved to `raw/Lost`, separated into verified duplicates and truly unidentified items, with their Lost destinations.
- Any verification failures.
- Any observations logged for future skill improvements.

Do not create a user-facing rename log outside `_Workflow` unless requested.







