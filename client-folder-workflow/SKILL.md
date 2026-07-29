---
name: client-folder-workflow
description: >
  End-to-end commercial insurance client-folder ingestion and filing workflow.
  Use when Codex or ChatGPT is asked to ingest a client raw folder, read and rename
  email files, extract and classify attachments, route policies, endorsements,
  quotes, proposals, indications, and submissions by LOB and policy term,
  maintain the legacy-style Account, Applications, Policies, Quotes, Schedules,
  Loss Runs, Account, and Stewardship filing structure, maintain a policy
  register plus annual JSON policy, quote, and submission knowledge outputs, stage Applied EPIC
  attachments by policy number, preserve an idempotent audit ledger, or perform a
  scoped rename-only cleanup of already-filed policy documents.
---

# Client Folder Workflow

## Core rule

Treat the selected directory as one client root. Never inspect or modify sibling client folders. Process only the requested client and only after building a written plan.

Invoke this installed skill explicitly when processing `raw/`. Do not create, copy, or require an `AGENTS.md` file in the client root; this skill and its bundled workflow schema are the instruction authority.

## Root `Legacy Files` Protection

A folder named exactly `Legacy Files` directly under the selected client root is a preserved archive by default. Do not inventory, read, extract from, stage, hash, copy, move, rename, delete, classify, route, ledger, or otherwise touch anything inside `<client-root>/Legacy Files/` unless the user specifically asks to process that folder by name. This is distinct from ordinary legacy source folders, year folders, or filing context elsewhere in the client root.


## `raw/Lost` Holding Area

After workflow control validation passes, ensure `<client-root>/raw/Lost/` exists. Treat it as a non-destructive holding area, not part of the active intake queue. Exclude everything already inside `raw/Lost/` from inventory, hashing, extraction, duplicate detection, classification, and reruns unless the user specifically asks to review that folder.

Move an active raw item to `raw/Lost/` only through the written processing plan when either:

- its SHA-256 matches an authoritative ledger record and a verified identical permanent file, so it is an exact duplicate already filed; or
- required parser, email, and document-evidence attempts cannot identify the client/artifact type or support any reliable filing destination.

Do not use `Lost` for an identifiable policy, endorsement, email, or other artifact that merely has a register conflict, missing decision, incomplete relationship, or other resolvable ambiguity; leave that item in the active `raw/` queue and write an exception. Preserve Lost-item bytes and original basenames, use deterministic collision suffixes, verify the post-move hash, and record the canonical ledger reference or identification failure in the plan and exceptions. Never create a duplicate permanent or EPIC copy, append a duplicate ledger row, or merge an unidentified item into annual JSON. Never delete `raw/Lost/` contents during routine cleanup.

Read [references/workflow-schema.md](references/workflow-schema.md) before performing the workflow. It is the authoritative specification for folder structure, filenames, policy-register matching, Markdown assignment, EPIC staging, ledger behavior, exceptions, and verification.
## Permanent filing model

Use the legacy-style client-root filing model defined in the schema: `Account`,
`Applications`, `Broker of Record Info`, `Loss Runs`, `Stewardship`,
`Markdown`, `Policies`, `Quotes`, and `Schedules`. Keep `raw/`,
`Epic_Attach/`, and `_Workflow/` as workflow-control folders alongside that
permanent structure. Do not create a parallel `SPECS` root or the former
per-LOB policy-root structure for new work.

## Execution Modes

- **Raw ingestion:** Run the complete execution sequence below.
- **Existing policy-folder cleanup:** Use only when the user asks to rename already-filed policy documents in named permanent folders. Inventory only those folders, validate the existing register, write a rename-only plan, and do not run unrelated raw ingestion, EPIC staging, ledger, or Markdown phases.

For existing policy-folder cleanup, rename only records that are clearly actual policies and have register-backed or document-backed policy number, term, LOB, and effective-date evidence. Exclude endorsements, binders, records of insurance, summaries, delivery letters, archives, and unsupported `Account` items unless document-level evidence independently satisfies the policy naming schema. Preserve the original basename for weakly classified items. Apply deterministic collision handling, verify hashes and extensions after every rename, and keep a plan plus audit log under `_Workflow`.

## Execution sequence

1. Confirm the client root and locate `raw/`.
2. Run `scripts/bootstrap_client.py <client-root>` before reading the ledger or register. The script must initialize missing control files without overwriting nonempty files.
3. Validate `_Workflow/Policy_Register.csv`. Stop before changing `raw/` if a nonempty register or workflow control file is malformed.
4. Ensure `raw/Lost/` exists, exclude it from active intake, inventory supported emails, and create a run-specific staging directory.
5. Inventory standalone documents in active `raw/` as well as email attachments; identify candidate policies, endorsements, declarations, and other issued policy documents before filing.
6. Extract email metadata and attachments without changing source bytes.
   - Invoke the installed `$email-production-renamer` helper `scripts/extract_email_metadata.py` for `.msg` files, with `--attachments-dir` pointed at the run-specific staging directory.
   - Use Aspose.Email FOSS for Python (`aspose-email-foss`) as the primary `.msg` decoder. Permit `extract_msg` only as the helper's per-message compatibility fallback, record the decoder used and all warnings, and do not start Outlook or use COM during ordinary processing.
   - Isolate MSG property reads so one failing metadata field does not make the whole email unreadable.
   - Preserve successful subject, sender, timestamp, body, recipient, and attachment evidence with property-specific warnings.
7. When any raw-file candidate or extracted attachment is an issued policy, endorsement, declaration, quote, proposal, indication, terms document, binder, application, submission, underwriting packet, or other insurance document with coverage terms, the main agent must spawn a subagent to run `$insurance-policy-extractor` on that document set before the processing plan is finalized. The subagent must follow the extractor's one-source-file-at-a-time boundary and produce JSON records. The main agent validates the subagent JSON and uses it as evidence for classification, audited register additions or proposals, annual JSON updates, Markdown merging, and ledger entries.
   - Done when every coverage-terms document is assigned to extraction or recorded as an exception, every completed extraction has main-agent-validated JSON, and every coverage-terms record has either row-level forms/endorsements/exclusions evidence or an explicit `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` review flag.
   - Subagent prompts must expressly require row-level extraction of sparse forms schedules. If a source lists only form numbers, the subagent must still capture one JSON row per visible form number and use `Not specified` for missing titles/descriptions, edition dates, coverage, or form type. `MISSING_FORMS_ENDORSEMENTS_SCHEDULE` is allowed only when no schedule/equivalent listing is visible after the searched pages/sections are documented.
8. Before any policy-looking PDF is held as metadata-only, generated/partial, unsupported, or low-confidence, prove that the document lacks filing-critical text by running at least one direct parser attempt. Use `pdftotext` when available; if it crashes, hangs, yields no output, or fails on a network path, rerun through the extractor helper (`draft_pdf_record.py`, including its local-copy/PyMuPDF fallback) and inspect the extracted text for policy number, endorsement number, LOB, carrier, and term. A narrowed extraction may skip detailed schedules, but it must not skip this minimum parser evidence for filing-critical documents.
9. Normalize every policy-number candidate and match against the approved register before deciding LOB, policy term, destination, EPIC folder, or Markdown year. For high-confidence issued new policies found in `raw`, follow the schema's audited register-append rules before routing.
   - Done when every policy-number candidate has been normalized and checked against the approved register, and each high-confidence new raw policy has been appended to `_Workflow/Policy_Register.csv`, audited in `_Workflow/proposed-policy-register-updates.csv`, revalidated, included in the applicable annual policy JSON, and cross-referenced in the plan.
10. Create `_Workflow/plans/<run-id>-processing-plan.csv` before moving or copying files.
11. Apply only high-confidence filing actions. As non-filing terminal actions, move verified already-filed duplicates and evidence-exhausted truly unidentified files to `raw/Lost/` according to the schema. Leave identifiable but unresolved source emails and standalone raw documents in active `raw/` and write exceptions.
12. Stage each processed renamed email only in `Epic_Attach`; file renamed attachments and standalone raw documents in their permanent folders; verify hashes.
13. Append or rebuild the correct annual policy JSON output using the validated extractor JSON and parent-policy effective-year rules.
14. Append or rebuild annual quote JSON outputs in `Markdown/Quotes/<YYYY>_Quotes.json` for quotes, proposals, indications, terms, and quote comparisons using proposed effective-year rules.
   - Done when every processed quote/proposal/indication/terms/comparison record with extractable terms has been merged or explicitly held for review, the annual quote JSON validates, rerun idempotency keys prevent duplicates, and the update is cross-referenced in the plan, ledger notes, and run summary.
15. Create independent copies in `Epic_Attach/<PolicyNumber>/` or `Epic_Attach/Account/`.
16. Commit ledger records, clean verified transient workflow artifacts according to the cleanup rules below, write the run summary, and perform the complete verification checklist.

## Required judgment rules

- Use an exact normalized `_Workflow/Policy_Register.csv` match as the primary routing authority.
- Do not let a register entry override an issued document that clearly proves the register is wrong; hold the item for review.
- For high-confidence issued new policies found in `raw`, append an audited approved row directly to `_Workflow/Policy_Register.csv`, revalidate the register, write `_Workflow/proposed-policy-register-updates.csv` with `review_status=approved_and_added`, append or rebuild the effective-year annual JSON, and then process as usual. For medium/low-confidence, ambiguous, incomplete, or conflicting unregistered policies, write a pending proposed row and hold for review.
- Do not route by LOB alone when policy-number evidence exists or is required.
- For management-liability placements, do not use `PL` as a catch-all LOB. Classify and file Directors & Officers as `D&O`, Employment Practices Liability as `EPL`, and Fiduciary Liability as `Fiduciary`; reserve `Management Liability` only for combined/multi-line schedules, towers, summaries, or correspondence that truly spans more than one of those coverages. Use `PL` only for true Professional Liability / E&O placements.
- For D&O, EPL, Fiduciary, Side A, DIC, Side A DIC, primary, and excess layers, include the layer label and liability range in the permanent filename when supported by the source, e.g. `D&O - Primary - $10M`, `D&O - 2nd Excess - $10M xs $20M`, or `D&O - Excess Side A DIC - $10M xs $40M`.
- Do not retain permanent email copies in shared-drive folders. Stage processed emails only in `Epic_Attach`; an email materially related to several policies may have EPIC copies in multiple policy-number folders.
- Route policies, applications, schedules/specs, loss runs, quotes, indications, terms, proposals, comparisons, emails, and account records using the schema's legacy-style permanent folders and its date-evidence, quote-proposal, display-name, filesystem-safety, and quote JSON rules.
- Never invent policy numbers, endorsement numbers, effective dates, policy terms, carriers, or LOBs; every register append must be supported by issued-document evidence and validated extractor JSON.
- Parse policy terms independently from document dates. Prefer explicit `YY-YY` or four-digit renewal-range tokens and policy effective/expiration evidence; never treat an `MM-DD-YY` filename date as a policy term.
- Never overwrite a nonidentical file or delete an existing client file.
- Treat files removed by the user from `Epic_Attach` as intentionally uploaded; do not recreate them unless restaging is explicitly requested.
- Treat `raw/Lost/` as a terminal, non-destructive holding area. Exclude it from future raw ingestion, never use it as permanent or EPIC storage, and never delete its contents during routine cleanup.
- Cleanup may remove only transient parser/staging artifacts after the related permanent files, EPIC copies, extraction records, annual JSON outputs, plans, logs, ledgers, and exceptions have been verified. Never delete manifests, shard assignments, final JSON records, `documents/`, `outputs/`, plans, logs, ledgers, proposed updates, exceptions, run summaries, or source/permanent/EPIC files as routine cleanup.

## Annual Quote JSON Rules

- Create `Markdown/Quotes/` when a processed batch includes quotes, proposals, indications, terms, quote comparisons, or quote summaries with extractable coverage terms.
- Store quote knowledge separately from issued policy knowledge in `Markdown/Quotes/<YYYY>_Quotes.json`, where `YYYY` is the proposed effective year or represented quote year.
- Include quote/proposal records for every quoted option, carrier, LOB, proposed term, premium, limits, sublimits, deductibles, subjectivities, exclusions, forms, quoted exposures, and source-document hash when available.
- Do not append quote rows to `_Workflow/Policy_Register.csv` unless a separate issued/bound document satisfies the high-confidence new-policy rules.
- Use quote JSON for future policy-check context, but do not let quote terms override issued policy or register evidence.
- Rebuild annual quote JSON idempotently by source hash and quote option key; reruns must not duplicate quote options.

## Annual submission JSON rules

- Create `Markdown/App-Submission/` when a processed batch includes applications, carrier submissions, SOVs, TIVs, underwriting packets, exposure schedules, or related submission support with extractable submission data.
- Store submission knowledge separately from issued policy and quote knowledge in `Markdown/App-Submission/<YYYY>_Submissions.json`, where `YYYY` is the proposed effective year or represented submission year.
- Include submission records for every submitted LOB, carrier/market, proposed term, named insured, exposure basis, schedules, values, operations, locations, vehicles, payroll, revenue, losses referenced, requested limits/deductibles when stated, subjectivities, and source-document hash when available.
- Do not append submission rows to `_Workflow/Policy_Register.csv` unless a separate issued/bound document satisfies the high-confidence new-policy rules.
- Use submission JSON for future renewal, marketing, policy-check, and proposal context, but do not let submission statements override issued policy, binder, quote, or register evidence.
- Rebuild annual submission JSON idempotently by source hash plus submission package key; reruns must not duplicate submission records.

## Annual policy JSON rules

- Ordinary annual or short-term policy: include only in the JSON file for the policy effective year.
- True multi-year policy longer than 366 days or explicitly identified as multi-year: include in every year from the effective year through the year before expiration.
- Exclude the expiration year.
- Assign endorsements to the parent policy's JSON year or years, not the endorsement effective year.
- Treat renewals as separate policy terms.
- Use the validated `$insurance-policy-extractor` JSON as the source for policy/endorsement JSON updates; do not substitute a filename-only or declaration-only summary when the full extractor workflow was required.
- Annual policy JSON files must include row-level forms, endorsements, exclusions, notices, and advisory notices for each policy/coverage where available. If the extractor JSON has `MISSING_FORMS_ENDORSEMENTS_SCHEDULE`, preserve that review flag in JSON instead of omitting the issue.

## Dependencies

Use available specialized skills or helpers for email parsing, policy extraction, PDF reading, and file maintenance. For `.msg`, use the installed `email-production-renamer/scripts/extract_email_metadata.py` helper backed by `aspose-email-foss`; keep `extract-msg` as its compatibility fallback and Outlook COM as an explicitly requested diagnostic only. Their output is evidence; this skill remains responsible for final classification, conflict handling, planning, and verification.

## Deliverables

A successful run leaves:

- processed emails staged only in `Epic_Attach`, plus permanently filed attachments and standalone documents;
- `Epic_Attach` copies organized by policy number;
- appended or rebuilt annual policy JSON outputs for every processed issued policy, endorsement, declaration, or policy-changing document, including high-confidence new raw policies before final filing;
- appended or rebuilt annual quote JSON outputs under `Markdown/Quotes/` for every processed quote, proposal, indication, terms document, quote comparison, or quote summary with extractable terms;
- appended or rebuilt annual submission JSON outputs under `Markdown/App-Submission/` for every processed application, carrier submission, SOV, TIV, underwriting packet, exposure schedule, or submission support file with extractable submission data;
- updated annual policy JSON files when applicable;
- an updated processing ledger;
- proposed register updates and exceptions where needed;
- a final run summary; and
- only identifiable unresolved items remaining in active `raw/`, with verified duplicates and truly unidentified files preserved under `raw/Lost/`.










## Dependency Order and Operational Files

Complete bootstrap before inventory and complete inventory before generating any filing or migration plan. Before assigning source files to extraction, exclude `_Workflow`, `Policy_Register.csv`, `AGENTS.md`, lock files, manifests, and other operational control artifacts. Parallelize only independent document reads after these generated-artifact dependencies are satisfied.
